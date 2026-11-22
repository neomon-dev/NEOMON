import asyncio
import json
import logging
import re
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.protocol import (
    ArgumentPayload,
    ArgumentType,
    ClaimPayload,
    ConfidenceAssessment,
    DebatePayload,
    DecisionPayload,
    EvidenceProvenance,
    PlannerPayload,
    ReportSectionPayload,
)
from app.analysis.report_service import (
    build_18_report_sections,
    compute_evidence_strength,
    save_report_version,
)
from app.analysis.structured_parser import extract_json_object
from app.analysis.context_manager import (
    AGENT_BUDGETS,
    DEFAULT_BUDGET,
    build_specialist_agent_context,
    build_adjudication_compact_context,
    compact_evidence_text,
    estimate_tokens,
)
from app.analysis.scheduler import gpu_scheduler
from app.hardware.npu_service import npu_auxiliary_service
from app.research.scientific_integrity import classify_evidence_for_claim
from app.config import get_settings
from app.events import EventBroker
from app.models import (
    AdjudicationDecision,
    AgentArgument,
    AnalysisAgentExecution,
    AnalysisJob,
    Claim,
    ClaimEvidenceRelationship,
    DebateRound,
    Document,
    Evidence,
    ReportSection,
    ResearchReport,
    Source,
)
from app.providers import create_provider
from app.providers.base import AIProvider, ProviderRequestError
from app.providers.limiter import (
    InferenceStateCallback,
    ProviderQueueFullError,
    ProviderQueueTimeoutError,
    inference_state_listener,
)
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.research.relevance import assess_text
from app.schemas import AnalysisCoverageSummary, EventType, ProviderConfigRequest, ProviderKind


ROLE_ORDER = (
    "intelligence_planner",
    "advocate",
    "skeptic",
    "methodology_auditor",
    "source_intelligence",
    "citation_genealogy",
    "temporal_intelligence",
)


async def _publish(
    broker: EventBroker, event_type: EventType, investigation_id: uuid.UUID, **payload: object
) -> None:
    await broker.publish(event_type, {"investigation_id": str(investigation_id), **payload})


def _dump(value: object) -> str:
    return json.dumps(value, default=str)


def _safe_json_loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return fallback


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _evidence_text(item: Evidence) -> str:
    return item.exact_text.strip().replace("\n", " ")[:900]


def _rule_based_claims(question: str) -> list[ClaimPayload]:
    subject = question.rstrip("?").strip()
    return [
        ClaimPayload(
            text=subject,
            explanation="The submitted research question is the parent claim to investigate.",
            priority=1,
            search_objectives=[subject],
            evidence_categories=["supporting", "contradicting", "contextual"],
        ),
        ClaimPayload(
            text=f"What measurable outcomes are reported in studies addressing {subject.lower()}?",
            explanation="Separates reported outcomes from the broad question.",
            priority=2,
            search_objectives=[f"measurable outcomes {subject}"],
            evidence_categories=["supporting", "contradicting"],
        ),
        ClaimPayload(
            text=f"What methodological, source, and temporal limitations qualify findings about {subject.lower()}?",
            explanation="Tests whether the evidence supports a broad conclusion across contexts.",
            priority=2,
            search_objectives=[f"limitations methodology {subject}"],
            evidence_categories=["methodological_limitation", "contextual"],
        ),
    ]


logger = logging.getLogger(__name__)
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class _ArgumentsListPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arguments: list[ArgumentPayload]


class _DecisionsListPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[DecisionPayload]


class _ReportSectionsListPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: list[ReportSectionPayload]


def _extract_json_object(
    raw_content: str,
    *,
    response_model: type[BaseModel] | None = None,
) -> dict[str, Any]:
    """Decode a JSON object from raw model text, stripping thinking tags and optional markdown fences."""
    return extract_json_object(raw_content, response_model=response_model)


async def _optional_llm_json(
    provider: AIProvider | None,
    model: str | None,
    system: str,
    prompt: str,
    *,
    response_model: type[BaseModel] | None = None,
    stage_name: str = "analysis",
    on_state_change: InferenceStateCallback | None = None,
    validator: Callable[[dict[str, Any]], None] | None = None,
    last_validated_ref: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any], str | None]:
    if provider is None:
        return None, {}, None
    effective_model = model or (provider.config.model if isinstance(provider, AIProvider) else None)
    system_with_json_rule = (
        f"{system} Respond with a single valid JSON object only; do not include markdown code fences or prose."
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_with_json_rule},
        {"role": "user", "content": prompt},
    ]
    complete_kwargs: dict[str, Any] = {}
    budget = AGENT_BUDGETS.get(stage_name, DEFAULT_BUDGET)
    if response_model is not None:
        complete_kwargs["max_tokens"] = budget.max_completion_tokens
        if isinstance(provider, OpenAICompatibleProvider):
            complete_kwargs["response_schema"] = response_model.model_json_schema()
            complete_kwargs["schema_name"] = stage_name

    usage: dict[str, Any] = {}
    total_queue_wait_seconds = 0.0
    total_inference_seconds = 0.0
    max_attempts = 2 if response_model is not None else 1
    for attempt in range(max_attempts):
        attempt_queue_wait = 0.0
        queued_started_monotonic: float | None = None
        generating_started_monotonic: float | None = None

        async def _tracked_state(state: str, meta: dict[str, Any]) -> None:
            nonlocal attempt_queue_wait, queued_started_monotonic, generating_started_monotonic
            if state == "waiting_in_queue" and queued_started_monotonic is None:
                queued_started_monotonic = time.monotonic()
            elif state == "generating":
                raw_wait = meta.get("queue_wait_seconds")
                if isinstance(raw_wait, (int, float)):
                    attempt_queue_wait = float(raw_wait)
                elif queued_started_monotonic is not None:
                    attempt_queue_wait = time.monotonic() - queued_started_monotonic
                generating_started_monotonic = time.monotonic()
            if on_state_change is not None:
                await on_state_change(state, meta)

        try:
            if not isinstance(provider, AIProvider):
                await _tracked_state("generating", {})
            async with gpu_scheduler.lease(stage_name, estimated_prompt_tokens=estimate_tokens(prompt)):
                async with inference_state_listener(_tracked_state):
                    try:
                        result = await provider.complete(messages, model=model, **complete_kwargs)
                    except TypeError as type_err:
                        if "unexpected keyword argument" in str(type_err):
                            result = await provider.complete(messages, model=model)
                        else:
                            raise
        except (ProviderRequestError, ProviderQueueTimeoutError, ProviderQueueFullError, TimeoutError) as exc:
            if generating_started_monotonic is not None:
                total_inference_seconds += time.monotonic() - generating_started_monotonic
            elif queued_started_monotonic is not None and attempt_queue_wait == 0.0:
                attempt_queue_wait = time.monotonic() - queued_started_monotonic
            total_queue_wait_seconds += attempt_queue_wait
            enriched_usage = dict(usage)
            if total_queue_wait_seconds > 0:
                enriched_usage["queue_wait_seconds"] = round(total_queue_wait_seconds, 3)
            if total_inference_seconds > 0:
                enriched_usage["inference_duration_seconds"] = round(total_inference_seconds, 3)
            logger.warning(
                "Analysis stage failed: stage=%s model=%s error=%s",
                stage_name,
                effective_model,
                exc,
            )
            return None, enriched_usage, f"{exc} (stage={stage_name}, model={effective_model or 'default'})"

        if generating_started_monotonic is not None:
            total_inference_seconds += time.monotonic() - generating_started_monotonic
        if isinstance(result, dict):
            raw_wait = result.get("queue_wait_seconds")
            if isinstance(raw_wait, (int, float)):
                attempt_queue_wait = float(raw_wait)
        total_queue_wait_seconds += attempt_queue_wait

        usage = dict(result.get("usage", {})) if isinstance(result, dict) and isinstance(result.get("usage"), dict) else {}
        usage["queue_wait_seconds"] = round(total_queue_wait_seconds, 3)
        usage["inference_duration_seconds"] = round(total_inference_seconds, 3)
        content = result.get("content") if isinstance(result, dict) else None
        if not isinstance(content, str):
            return None, usage, f"provider returned no content (stage={stage_name}, model={effective_model or 'default'})"
        try:
            parsed = _extract_json_object(content, response_model=response_model)
            if response_model is not None:
                validated = response_model.model_validate(parsed)
                dumped = validated.model_dump(mode="json")
            else:
                dumped = parsed
            if last_validated_ref is not None:
                last_validated_ref.clear()
                last_validated_ref.append(dumped)
            if validator is not None:
                validator(dumped)
            return dumped, usage, None
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            if attempt + 1 < max_attempts:
                logger.warning(
                    "Structured output validation failed; running bounded correction retry: stage=%s model=%s error=%s",
                    stage_name,
                    effective_model,
                    exc,
                )
                messages.append({"role": "assistant", "content": content[:1200]})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your previous JSON output failed validation: {exc}. "
                            "Return ONLY a corrected JSON object strictly matching the schema, using only the originally supplied IDs."
                        ),
                    }
                )
                continue
            logger.warning(
                "Structured output validation failed permanently: stage=%s model=%s error=%s",
                stage_name,
                effective_model,
                exc,
            )
            return None, usage, str(exc)
    return None, usage, "structured output generation exhausted attempts"


async def _create_execution(
    session: AsyncSession,
    job: AnalysisJob,
    identifier: str,
    model: str | None,
    *,
    status: str = "generating",
) -> AnalysisAgentExecution:
    effective_model = model or job.default_model
    execution = AnalysisAgentExecution(job_id=job.id, agent_identifier=identifier, model=effective_model, status=status)
    execution.started_at = datetime.now(UTC)
    session.add(execution)
    await session.commit()
    return execution


def _make_state_callback(
    session: AsyncSession,
    broker: EventBroker,
    execution: AnalysisAgentExecution,
    investigation_id: uuid.UUID,
    role: str,
    db_lock: asyncio.Lock,
) -> InferenceStateCallback:
    async def on_state(state: str, meta: dict[str, Any]) -> None:
        async with db_lock:
            execution.status = state
            try:
                usage_dict = json.loads(execution.token_usage_json) if execution.token_usage_json else {}
                if not isinstance(usage_dict, dict):
                    usage_dict = {}
            except (ValueError, TypeError):
                usage_dict = {}
            if "queue_position" in meta:
                usage_dict["queue_position"] = meta["queue_position"]
            if "queue_depth" in meta:
                usage_dict["queue_depth"] = meta["queue_depth"]
            if "queue_wait_seconds" in meta:
                usage_dict["queue_wait_seconds"] = meta["queue_wait_seconds"]
            execution.token_usage_json = _dump(usage_dict)
            await session.commit()
        event_type = EventType.analysis_agent_started if state == "generating" else EventType.analysis_agent_queued
        await _publish(
            broker,
            event_type,
            investigation_id,
            agent=role,
            execution_id=str(execution.id),
            status=state,
            **meta,
        )

    return on_state


async def _mark_unfinished_executions_cancelled(
    session: AsyncSession,
    broker: EventBroker,
    job_id: uuid.UUID,
    investigation_id: uuid.UUID,
) -> None:
    pending = list(
        (
            await session.scalars(
                select(AnalysisAgentExecution).where(
                    AnalysisAgentExecution.job_id == job_id,
                    AnalysisAgentExecution.status.in_(("waiting_in_queue", "generating", "running", "queued")),
                )
            )
        ).all()
    )
    if not pending:
        return
    now = datetime.now(UTC)
    for item in pending:
        item.status = "cancelled"
        item.error_message = "Analysis cancelled."
        item.completed_at = now
    await session.commit()
    for item in pending:
        await _publish(
            broker,
            EventType.analysis_agent_cancelled,
            investigation_id,
            agent=item.agent_identifier,
            execution_id=str(item.id),
            status="cancelled",
        )


async def _mark_unfinished_executions_failed(
    session: AsyncSession,
    broker: EventBroker,
    job_id: uuid.UUID,
    investigation_id: uuid.UUID,
    error_message: str,
) -> None:
    pending = list(
        (
            await session.scalars(
                select(AnalysisAgentExecution).where(
                    AnalysisAgentExecution.job_id == job_id,
                    AnalysisAgentExecution.status.in_(("waiting_in_queue", "generating", "running", "queued")),
                )
            )
        ).all()
    )
    if not pending:
        return
    now = datetime.now(UTC)
    for item in pending:
        item.status = "failed"
        item.error_message = error_message
        item.completed_at = now
    await session.commit()
    for item in pending:
        await _publish(
            broker,
            EventType.analysis_agent_failed,
            investigation_id,
            agent=item.agent_identifier,
            execution_id=str(item.id),
            status="failed",
            error=error_message,
        )


async def _finish_execution(
    session: AsyncSession,
    execution: AnalysisAgentExecution,
    output: object | None,
    usage: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    execution.status = "completed" if error is None else "failed"
    execution.output_json = _dump(output) if output is not None else None
    execution.token_usage_json = _dump(usage or {})
    execution.error_message = error
    execution.completed_at = datetime.now(UTC)
    await session.flush()


async def _cancelled(session: AsyncSession, job_id: uuid.UUID) -> bool:
    job = await session.get(AnalysisJob, job_id)
    return bool(job and job.cancel_requested)


async def _persist_claims(
    session: AsyncSession, investigation_id: uuid.UUID, payloads: list[ClaimPayload]
) -> list[Claim]:
    existing = list(
        (
            await session.scalars(
                select(Claim).where(Claim.investigation_id == investigation_id).order_by(Claim.id)
            )
        ).all()
    )
    existing_text = {_normalized(item.text) for item in existing}
    existing_ids = {item.id for item in existing}
    persisted_by_text = {_normalized(item.text): item for item in existing}
    planned: list[Claim] = []
    for payload in payloads:
        normalized = _normalized(payload.text)
        if normalized in existing_text:
            claim = persisted_by_text[normalized]
            claim.explanation = payload.explanation
            claim.priority = payload.priority
            claim.search_objectives_json = _dump(payload.search_objectives)
            claim.evidence_categories_json = _dump(payload.evidence_categories)
            claim.dependencies_json = _dump([str(item) for item in payload.dependencies])
            planned.append(claim)
            continue
        claim = Claim(
            id=payload.claim_id if payload.claim_id in existing_ids else uuid.uuid4(),
            investigation_id=investigation_id,
            text=payload.text,
            explanation=payload.explanation,
            priority=payload.priority,
            search_objectives_json=_dump(payload.search_objectives),
            evidence_categories_json=_dump(payload.evidence_categories),
            dependencies_json=_dump([str(item) for item in payload.dependencies]),
            status="unassessed",
        )
        session.add(claim)
        existing.append(claim)
        existing_text.add(normalized)
        persisted_by_text[normalized] = claim
        existing_ids.add(claim.id)
        planned.append(claim)
    await session.flush()
    return planned


def _validate_planner_claims(payload: object) -> list[ClaimPayload]:
    planner = PlannerPayload.model_validate(payload)
    seen: set[str] = set()
    for claim in planner.claims:
        normalized = _normalized(claim.text)
        if normalized in seen:
            raise ValueError("planner returned duplicate or overlapping claims")
        seen.add(normalized)
    return planner.claims


async def _associate_evidence(
    session: AsyncSession,
    investigation_id: uuid.UUID,
    claims: list[Claim],
    evidence: list[Evidence],
) -> dict[uuid.UUID, list[Evidence]]:
    existing_rows = list(
        (
            await session.scalars(
                select(ClaimEvidenceRelationship).join(Claim).where(Claim.investigation_id == investigation_id)
            )
        ).all()
    )
    existing_keys = {(item.claim_id, item.evidence_id) for item in existing_rows}
    associated: dict[uuid.UUID, list[Evidence]] = defaultdict(list)
    for claim in claims:
        objectives = json.loads(claim.search_objectives_json)
        for item in evidence:
            directly_linked = item.claim_id == claim.id
            if not item.traceable:
                continue
            assessment = assess_text(" ".join(objectives), item.exact_text)
            if not directly_linked and assessment.score < 0.2:
                continue
            classification = classify_evidence_for_claim(claim.text, item.exact_text)
            if not directly_linked and classification.category.value == "insufficient":
                continue
            associated[claim.id].append(item)
            if (claim.id, item.id) not in existing_keys:
                rel_type = classification.category.value if classification.category.value != "insufficient" else item.evidence_type
                explanation = (
                    f"Directly linked: classified as {rel_type} ({classification.confidence:.2f}) - {classification.reasoning}"
                    if directly_linked
                    else f"Claim association: {rel_type} ({classification.confidence:.2f}) - {classification.reasoning}"
                )
                session.add(
                    ClaimEvidenceRelationship(
                        claim_id=claim.id,
                        evidence_id=item.id,
                        relationship_type=rel_type,
                        explanation=explanation,
                    )
                )
                existing_keys.add((claim.id, item.id))
    await session.flush()
    return associated


def _candidate_evidence(
    evidence: list[Evidence], preferred: set[str], limit: int = 5
) -> list[Evidence]:
    selected = [item for item in evidence if item.evidence_type in preferred and item.traceable]
    return sorted(selected, key=lambda item: item.relevance_score, reverse=True)[:limit]


async def _add_argument(
    session: AsyncSession,
    job: AnalysisJob,
    execution: AnalysisAgentExecution,
    claim: Claim,
    agent_identifier: str,
    payload: ArgumentPayload,
    evidence_ids: set[uuid.UUID],
    source_ids: set[uuid.UUID],
    evidence_source_ids: dict[uuid.UUID, uuid.UUID] | None = None,
) -> AgentArgument:
    if payload.claim_id != claim.id:
        raise ValueError("argument claim does not match the execution claim")
    unknown_evidence = set(payload.evidence_ids) - evidence_ids
    unknown_sources = set(payload.source_ids) - source_ids
    if unknown_evidence or unknown_sources:
        raise ValueError("argument references evidence or sources outside the investigation")
    if evidence_source_ids is not None:
        expected_sources = {evidence_source_ids[item] for item in payload.evidence_ids}
        if set(payload.source_ids) != expected_sources:
            raise ValueError("argument source references do not match its evidence references")
    row = AgentArgument(
        id=payload.argument_id or uuid.uuid4(),
        job_id=job.id,
        execution_id=execution.id,
        claim_id=claim.id,
        agent_identifier=agent_identifier,
        argument_type=payload.argument_type.value,
        text=payload.text,
        evidence_ids_json=_dump([str(item) for item in payload.evidence_ids]),
        source_ids_json=_dump([str(item) for item in payload.source_ids]),
        evidence_basis=payload.evidence_basis,
        reasoning_summary=payload.reasoning_summary,
        limitations_json=_dump(payload.limitations),
        confidence_level=payload.confidence.level,
        confidence_explanation=payload.confidence.explanation,
    )
    session.add(row)
    await session.flush()
    return row


def _build_fallback_report_sections(
    question: str,
    claims: list[Claim],
    decisions: list[DecisionPayload],
    evidence: list[Evidence],
    sources: dict[uuid.UUID, Source],
    documents: dict[uuid.UUID, Document],
    warnings: list[str],
    provenance_for_fn: Callable[[list[uuid.UUID]], list[EvidenceProvenance]],
    arguments: list[Any] | None = None,
) -> list[ReportSectionPayload]:
    return build_18_report_sections(
        question=question,
        claims=claims,
        decisions=decisions,
        evidence=evidence,
        sources=sources,
        documents=documents,
        arguments=arguments or [],
        warnings=warnings,
        provenance_for_fn=provenance_for_fn,
    )


def compute_analysis_coverage(
    claims: list[Claim],
    executions: list[AnalysisAgentExecution],
    arguments: list[AgentArgument],
    decisions: list[AdjudicationDecision],
    evidence: list[Evidence],
) -> AnalysisCoverageSummary:
    required_agents = [
        "intelligence_planner",
        "advocate",
        "skeptic",
        "methodology_auditor",
        "source_intelligence",
        "citation_genealogy",
        "temporal_intelligence",
        "debate_moderator",
        "conflict_adjudicator",
        "report_intelligence",
    ]
    completed_agents = list(dict.fromkeys([e.agent_identifier for e in executions if e.status == "completed"]))
    failed_agents = list(dict.fromkeys([e.agent_identifier for e in executions if e.status == "failed"]))
    active_agent_ids = {
        e.agent_identifier for e in executions if e.status in {"waiting_in_queue", "generating", "running", "queued"}
    }
    pending_agents = [r for r in required_agents if r in active_agent_ids]
    skipped_agents = [
        r for r in required_agents if r not in completed_agents and r not in failed_agents and r not in pending_agents
    ]

    claims_total = len(claims)
    claims_evaluated = len(decisions)
    claims_without_arguments = sum(1 for c in claims if not any(a.claim_id == c.id for a in arguments))
    claims_without_evidence = sum(
        1
        for c in claims
        if not any(a.claim_id == c.id and _safe_json_loads(a.evidence_ids_json, []) for a in arguments)
    )
    claims_with_supporting = sum(
        1
        for c in claims
        if any(
            a.claim_id == c.id and a.argument_type == "supporting" and _safe_json_loads(a.evidence_ids_json, [])
            for a in arguments
        )
    )
    claims_with_conflicting = sum(
        1
        for c in claims
        if any(
            a.claim_id == c.id
            and a.argument_type in {"contradicting", "methodological_criticism"}
            and _safe_json_loads(a.evidence_ids_json, [])
            for a in arguments
        )
    )
    coverage_pct = round((len(completed_agents) / max(1, len(required_agents))) * 100.0, 1)
    is_partial = (
        len(failed_agents) > 0
        or claims_without_arguments > 0
        or claims_evaluated < claims_total
        or len(skipped_agents) > 0
    )
    return AnalysisCoverageSummary(
        required_agents=required_agents,
        completed_agents=completed_agents,
        failed_agents=failed_agents,
        skipped_agents=skipped_agents,
        pending_agents=pending_agents,
        claims_total=claims_total,
        claims_evaluated=claims_evaluated,
        claims_without_arguments=claims_without_arguments,
        claims_without_evidence=claims_without_evidence,
        claims_with_supporting_evidence=claims_with_supporting,
        claims_with_conflicting_evidence=claims_with_conflicting,
        coverage_percentage=coverage_pct,
        is_partially_completed=is_partial,
    )


_EXACT_CLAIM_RULE = (
    "\nOutput ONLY a valid JSON object matching this EXACT SCHEMA with no markdown fences or conversational text:\n"
    "{\n"
    '  "arguments": [\n'
    "    {\n"
    '      "claim_id": "<exact_claim_uuid_from_input>",\n'
    '      "argument_type": "supporting",\n'
    '      "text": "Evidence-grounded factual analysis...",\n'
    '      "evidence_ids": ["<exact_evidence_uuid_from_input>"],\n'
    '      "source_ids": ["<exact_source_uuid_from_input>"],\n'
    '      "evidence_basis": "direct",\n'
    '      "reasoning_summary": "Summary of reasoning...",\n'
    '      "limitations": ["Scope limitation..."],\n'
    '      "confidence": {\n'
    '        "level": "strong",\n'
    '        "explanation": "Why this confidence level was assigned..."\n'
    "      }\n"
    "    }\n"
    "  ]\n"
    "}\n"
    "Rules:\n"
    "- Output EXACTLY ONE argument object per supplied claim_id (do NOT omit any claim_id).\n"
    "- confidence MUST be an object with 'level' (strong|moderate|weak|insufficient|contested) and 'explanation'.\n"
    "- evidence_basis must be 'direct', 'indirect', or 'none'.\n"
    "- If no evidence supports the claim, set evidence_ids: [], source_ids: [], evidence_basis: 'none', confidence.level: 'insufficient'.\n"
    "- Use only the exact UUIDs supplied in the input."
)

ROLE_SYSTEM_INSTRUCTIONS: dict[str, str] = {
    "advocate": (
        "You are the Advocate agent in NEOMON. Construct the strongest evidence-grounded supporting case for each "
        "claim using ONLY the supplied supporting evidence passages. Highlight positive findings, effect direction, and "
        "supporting mechanisms while explicitly stating scope conditions. If no supporting evidence exists for a claim, "
        "explicitly output 'No supporting evidence found' rather than misusing non-supporting passages or inventing arguments. "
        f"Use argument_type 'supporting' or 'qualifying'. {_EXACT_CLAIM_RULE}"
    ),
    "skeptic": (
        "You are the Skeptic agent in NEOMON. Independently challenge each claim by examining contradicting evidence, "
        "mitigating factors (counterbalancing forces or efficiency improvements), and methodological limitations in the "
        "supplied evidence. If no contradicting or mitigating evidence exists, explicitly note 'No direct contradictions "
        "found in available evidence' and focus on scope limits. Use argument_type 'contradicting' or 'qualifying'. "
        f"{_EXACT_CLAIM_RULE}"
    ),
    "methodology_auditor": (
        "You are the Methodology Auditor agent in NEOMON. Evaluate study design rigor, sample size, control "
        "conditions, measurement validity, and generalizability limits across the supplied evidence. Use "
        "argument_type 'methodological_criticism'. "
        f"{_EXACT_CLAIM_RULE}"
    ),
    "source_intelligence": (
        "You are the Source Intelligence agent in NEOMON. Assess source credibility, publication venue/type, "
        "institutional independence, and potential secondary-reporting or venue bias in the supplied evidence. "
        "Use argument_type 'source_criticism'. "
        f"{_EXACT_CLAIM_RULE}"
    ),
    "citation_genealogy": (
        "You are the Citation Genealogy agent in NEOMON. Identify whether supplied evidence items appear to "
        "derive from shared underlying studies, datasets, or preprint/published versions rather than independent "
        "replications. Use argument_type 'qualifying' or 'source_criticism'. "
        f"{_EXACT_CLAIM_RULE}"
    ),
    "temporal_intelligence": (
        "You are the Temporal Intelligence agent in NEOMON. Evaluate publication recency, timeframe alignment "
        "with the investigation question, and whether older findings may be superseded by newer evidence. Use "
        "argument_type 'temporal_qualification'. "
        f"{_EXACT_CLAIM_RULE}"
    ),
}


def _role_argument(
    role: str,
    claim: Claim,
    evidence: list[Evidence],
    sources: dict[uuid.UUID, Source],
) -> ArgumentPayload:
    empty_text = f"No traceable persisted evidence was found for this agent's specific review of: {claim.text}"
    if role == "advocate":
        chosen = _candidate_evidence(evidence, {"supporting"})
        argument_type = ArgumentType.supporting
        lead = "Traceable evidence supports"
        empty_text = f"No supporting evidence found for claim: {claim.text}"
    elif role == "skeptic":
        chosen = _candidate_evidence(evidence, {"contradicting", "mitigating", "methodological_limitation"})
        argument_type = (
            ArgumentType.contradicting
            if any(item.evidence_type in {"contradicting", "mitigating"} for item in chosen)
            else ArgumentType.qualifying
        )
        lead = "Counter-evidence, mitigating factors, or limitations qualify"
        empty_text = f"No direct contradictions, mitigating factors, or methodological limitations found in available evidence for: {claim.text}"
    elif role == "methodology_auditor":
        chosen = _candidate_evidence(evidence, {"methodological_limitation"})
        argument_type = ArgumentType.methodological_criticism
        lead = "Methodological review identifies"
        empty_text = f"No methodological limitations identified in available evidence for: {claim.text}"
    elif role == "source_intelligence":
        chosen = _candidate_evidence(evidence, {"supporting", "contradicting", "mitigating", "contextual"}, 3)
        argument_type = ArgumentType.source_criticism
        lead = "Source-level inspection finds"
    elif role == "citation_genealogy":
        chosen = _candidate_evidence(evidence, {"supporting", "contradicting", "mitigating", "contextual"}, 3)
        argument_type = ArgumentType.source_criticism
        lead = "Citation-independence review finds"
    else:
        chosen = _candidate_evidence(evidence, {"supporting", "contradicting", "mitigating", "contextual"}, 3)
        argument_type = ArgumentType.temporal_qualification
        lead = "Temporal review finds"
    evidence_ids = [item.id for item in chosen]
    source_ids = [item.source_id for item in chosen]
    evidence_basis = (
        "direct"
        if any(item.claim_id == claim.id for item in chosen)
        else "indirect"
        if chosen
        else "none"
    )
    if chosen:
        excerpts = " ".join(_evidence_text(item) for item in chosen)
        text = f"{lead} {len(chosen)} persisted evidence passage(s) relevant to the claim: {excerpts}"
        confidence = ConfidenceAssessment(
            level="moderate" if len(chosen) > 1 else "weak",
            explanation="The assessment is limited to traceable passages persisted for this investigation.",
        )
        limitations = ["The agent did not infer facts absent from the persisted passages."]
    else:
        text = empty_text
        confidence = ConfidenceAssessment(
            level="insufficient",
            explanation="No qualifying evidence passage was available for this role.",
        )
        limitations = ["Relevant methodology, source, temporal, or contradictory evidence was unavailable."]
    return ArgumentPayload(
        claim_id=claim.id,
        argument_type=argument_type,
        text=text,
        evidence_ids=evidence_ids,
        source_ids=source_ids,
        evidence_basis=evidence_basis,
        reasoning_summary="Selection was restricted to traceable persisted evidence and source metadata.",
        limitations=limitations,
        confidence=confidence,
    )


async def _ensure_not_cancelled(session: AsyncSession, job: AnalysisJob) -> None:
    await session.refresh(job)
    if job.cancel_requested:
        raise asyncio.CancelledError("Analysis cancelled by user.")


async def run_analysis(
    session: AsyncSession,
    broker: EventBroker,
    job: AnalysisJob,
    question: str,
    provider_config: ProviderConfigRequest | None = None,
    role_models: dict[str, str] | None = None,
) -> None:
    provider: AIProvider | None = None
    role_models = role_models or {}
    warnings: list[str] = []
    job_id = job.id
    investigation_id = job.investigation_id
    db_lock = asyncio.Lock()
    try:
        provider = create_provider(provider_config) if provider_config else None
        job.status = "planning"
        job.started_at = datetime.now(UTC)
        await session.commit()
        await _publish(broker, EventType.analysis_stage_changed, job.investigation_id, stage=job.status)

        # Intel AI Boost NPU Auxiliary Intent and Domain Classification
        try:
            npu_classification = npu_auxiliary_service.classify_query(question)
            logger.info(
                "NPU classification for query '%s': domain=%s complexity=%s device=%s latency=%.2fms",
                question,
                npu_classification.domain,
                npu_classification.complexity,
                npu_classification.execution_device,
                npu_classification.latency_ms,
            )
        except Exception as npu_exc:
            logger.warning("NPU auxiliary classification bypassed: %s", npu_exc)

        evidence = list(
            (
                await session.scalars(
                    select(Evidence).join(Source).where(Source.investigation_id == job.investigation_id)
                )
            ).all()
        )
        sources = {
            item.id: item
            for item in (
                await session.scalars(select(Source).where(Source.investigation_id == job.investigation_id))
            ).all()
        }
        documents = {
            item.id: item
            for item in (
                await session.scalars(
                    select(Document).join(Source).where(Source.investigation_id == job.investigation_id)
                )
            ).all()
        }
        evidence_ids = {item.id for item in evidence}
        source_ids = set(sources)

        planner = await _create_execution(
            session,
            job,
            "intelligence_planner",
            role_models.get("intelligence_planner"),
            status="waiting_in_queue" if provider is not None else "generating",
        )
        planner_payload: dict[str, Any] | None
        if provider is None:
            await _publish(
                broker,
                EventType.analysis_agent_started,
                job.investigation_id,
                agent="intelligence_planner",
                execution_id=str(planner.id),
                status="generating",
            )
            planner_payload = {"claims": [item.model_dump(mode="json") for item in _rule_based_claims(question)]}
            planner_error = None
            usage = {}
            planner_mode = "rule_based"
        else:
            planner_payload, usage, planner_error = await _optional_llm_json(
                provider,
                role_models.get("intelligence_planner"),
                (
                    "You are the Intelligence Planner for NEOMON.\n"
                    "Decompose the research question into a claims array of 1 to 5 distinct, verifiable claims.\n"
                    "Output ONLY a valid JSON object matching the exact schema below. Do NOT include markdown fences, extra text, or any extra keys.\n\n"
                    "JSON SCHEMA:\n"
                    "{\n"
                    '  "claims": [\n'
                    "    {\n"
                    '      "text": "Clear, verifiable assertion (at least 10 chars)",\n'
                    '      "explanation": "Why this claim is critical to the research question",\n'
                    '      "priority": 1,\n'
                    '      "search_objectives": ["key factual aspect to verify"],\n'
                    '      "evidence_categories": ["empirical", "economic"],\n'
                    '      "dependencies": []\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                    "Rules:\n"
                    "- priority must be an integer between 1 and 5.\n"
                    "- search_objectives must be a non-empty array of strings.\n"
                    "- evidence_categories must be a non-empty array of strings.\n"
                    "- dependencies must be an empty list [] unless referencing previous claim UUIDs.\n"
                    "- Do NOT add any extra fields."
                ),
                json.dumps({"question": question}),
                response_model=PlannerPayload,
                stage_name="intelligence_planner",
                on_state_change=_make_state_callback(
                    session, broker, planner, investigation_id, "intelligence_planner", db_lock
                ),
            )
            planner_mode = "llm"
        claims: list[Claim] = []
        if planner_error is None:
            try:
                claim_payloads = _validate_planner_claims(planner_payload)
                claims = await _persist_claims(session, job.investigation_id, claim_payloads)
            except ValueError as exc:
                planner_error = str(exc)
        if planner_error:
            warnings.append(f"intelligence_planner: {planner_error}")
        await _finish_execution(
            session,
            planner,
            {
                "claims": [item.text for item in claims],
                "provider_output": planner_payload,
                "mode": planner_mode,
            },
            usage,
            planner_error,
        )
        await session.commit()
        await _publish(
            broker,
            EventType.analysis_agent_completed if planner_error is None else EventType.analysis_agent_failed,
            job.investigation_id,
            agent="intelligence_planner",
            execution_id=str(planner.id),
            warning=planner_error,
        )
        if planner_error is not None or not claims:
            raise ValueError(f"planner failed: {planner_error or 'no claims were persisted'}")

        associated_evidence = await _associate_evidence(session, job.investigation_id, claims, evidence)

        job.status = "researching"
        await session.commit()
        await _publish(broker, EventType.analysis_stage_changed, job.investigation_id, stage=job.status)
        semaphore = asyncio.Semaphore(job.max_concurrent_agents)
        executions_by_role: dict[str, AnalysisAgentExecution] = {}
        for role in ROLE_ORDER[1:]:
            executions_by_role[role] = await _create_execution(
                session,
                job,
                role,
                role_models.get(role),
                status="waiting_in_queue",
            )
            await _publish(
                broker,
                EventType.analysis_agent_queued,
                investigation_id,
                agent=role,
                execution_id=str(executions_by_role[role].id),
                status="waiting_in_queue",
            )

        async def prepare_role(role: str) -> tuple[str, list[ArgumentPayload] | None, dict[str, Any], str | None]:
            execution = executions_by_role[role]
            async with semaphore:
                if provider is None:
                    async with db_lock:
                        execution.status = "generating"
                        await session.commit()
                    await _publish(
                        broker,
                        EventType.analysis_agent_started,
                        investigation_id,
                        agent=role,
                        execution_id=str(execution.id),
                        status="generating",
                    )
                    return role, [
                        _role_argument(role, claim, associated_evidence.get(claim.id, []), sources)
                        for claim in claims
                    ], {}, None
                expected_claim_ids = {item.id for item in claims}
                evidence_source_map = {item.id: item.source_id for item in evidence}

                def _validate_role_payload(dumped: dict[str, Any]) -> None:
                    raw_arguments = dumped.get("arguments")
                    if not isinstance(raw_arguments, list):
                        raise ValueError("structured agent output must contain an arguments list")
                    parsed_items = [ArgumentPayload.model_validate(item) for item in raw_arguments]
                    seen_claims: set[uuid.UUID] = set()
                    duplicates: list[str] = []
                    for item in parsed_items:
                        if item.claim_id not in expected_claim_ids:
                            raise ValueError(f"agent output referenced claim {item.claim_id} outside the investigation")
                        if item.claim_id in seen_claims:
                            duplicates.append(str(item.claim_id))
                        seen_claims.add(item.claim_id)
                        if set(item.evidence_ids) - evidence_ids:
                            raise ValueError("argument references evidence outside the investigation")
                        expected_sources = {evidence_source_map[ev_id] for ev_id in item.evidence_ids if ev_id in evidence_source_map}
                        if not item.source_ids:
                            item.source_ids = list(expected_sources)
                        elif set(item.source_ids) - source_ids:
                            raise ValueError("argument references sources outside the investigation")
                        elif set(item.source_ids) != expected_sources:
                            item.source_ids = list(expected_sources)
                    if duplicates:
                        raise ValueError(
                            f"agent output contained duplicate claim arguments for claim_id(s): {', '.join(duplicates)}"
                        )
                    missing_claims = expected_claim_ids - seen_claims
                    if missing_claims:
                        missing_str = ", ".join(str(item) for item in sorted(missing_claims, key=str))
                        raise ValueError(f"agent output omitted claim_id(s): {missing_str}")

                specialist_context = build_specialist_agent_context(
                    role, claims, associated_evidence, sources, documents
                )
                llm_payload, usage, role_error = await _optional_llm_json(
                    provider,
                    role_models.get(role),
                    ROLE_SYSTEM_INSTRUCTIONS[role],
                    json.dumps(specialist_context),
                    response_model=_ArgumentsListPayload,
                    stage_name=role,
                    on_state_change=_make_state_callback(
                        session, broker, execution, investigation_id, role, db_lock
                    ),
                    validator=_validate_role_payload,
                )
                if role_error:
                    return role, None, usage, role_error
                raw_arguments = llm_payload.get("arguments") if llm_payload else None
                if not isinstance(raw_arguments, list):
                    return role, None, usage, "structured agent output must contain an arguments list"
                try:
                    _validate_role_payload(llm_payload)
                    parsed = [ArgumentPayload.model_validate(item) for item in raw_arguments]
                    return role, parsed, usage, None
                except ValueError as exc:
                    return role, None, usage, str(exc)

        is_local_provider = (
            provider_config is not None
            and (
                provider_config.kind in {ProviderKind.lm_studio, ProviderKind.ollama}
                or provider_config.allow_local_runtime
            )
        )
        if is_local_provider:
            prepared_roles = []
            for role in ROLE_ORDER[1:]:
                prepared_roles.append(await prepare_role(role))
        else:
            prepared_roles = await asyncio.gather(*(prepare_role(role) for role in ROLE_ORDER[1:]))

        evidence_source_map = {item.id: item.source_id for item in evidence}
        for role, prepared_arguments, usage, role_error in prepared_roles:
            if await _cancelled(session, job.id):
                raise asyncio.CancelledError()
            execution = executions_by_role[role]
            if role_error or prepared_arguments is None:
                await _finish_execution(session, execution, None, usage, role_error or "agent output was invalid")
                warnings.append(f"{role}: {role_error or 'agent output was invalid'}")
                await session.commit()
                await _publish(
                    broker,
                    EventType.analysis_agent_failed,
                    job.investigation_id,
                    agent=role,
                    execution_id=str(execution.id),
                    error=role_error or "agent output was invalid",
                )
                continue
            try:
                seen_arg_claims = {item.claim_id for item in prepared_arguments}
                for claim in claims:
                    if claim.id not in seen_arg_claims:
                        fallback_arg = _role_argument(role, claim, associated_evidence.get(claim.id, []), sources)
                        prepared_arguments.append(fallback_arg)
                        warnings.append(f"{role}: omitted claim {claim.id}; generated grounded fallback argument.")

                for payload in prepared_arguments:
                    unknown_ev = set(payload.evidence_ids) - evidence_ids
                    if unknown_ev:
                        valid_ev = [eid for eid in payload.evidence_ids if eid in evidence_ids]
                        payload.evidence_ids = valid_ev
                        payload.source_ids = [evidence_source_map[eid] for eid in valid_ev]
                        if not valid_ev:
                            payload.evidence_basis = "none"
                            payload.confidence = ConfidenceAssessment(
                                level="insufficient",
                                explanation="Filtered non-existent evidence IDs; no verified passages remained.",
                            )
                        warnings.append(f"{role}: filtered non-existent evidence IDs {unknown_ev} for claim {payload.claim_id}.")

                for claim in claims:
                    payload = next((item for item in prepared_arguments if item.claim_id == claim.id), None)
                    if payload is None:
                        raise ValueError(f"agent output omitted claim {claim.id}")
                    await _add_argument(
                        session,
                        job,
                        execution,
                        claim,
                        role,
                        payload,
                        evidence_ids,
                        source_ids,
                        evidence_source_map,
                    )
                await _finish_execution(
                    session,
                    execution,
                    {
                        "arguments_created": len(prepared_arguments),
                        "mode": "llm" if provider else "evidence_grounded",
                    },
                    usage,
                )
                await session.commit()
                await _publish(
                    broker,
                    EventType.analysis_agent_completed,
                    job.investigation_id,
                    agent=role,
                    execution_id=str(execution.id),
                    arguments_created=len(prepared_arguments),
                )
            except ValueError as exc:
                await session.rollback()
                refreshed = await session.get(AnalysisAgentExecution, execution.id)
                if refreshed is None:
                    refreshed = await _create_execution(session, job, role, role_models.get(role))
                await _finish_execution(session, refreshed, None, usage, str(exc))
                warnings.append(f"{role}: {exc}")
                await session.commit()
                await _publish(
                    broker,
                    EventType.analysis_agent_failed,
                    job.investigation_id,
                    agent=role,
                    execution_id=str(refreshed.id),
                    error=str(exc),
                )

        job.status = "debating"
        await session.commit()
        await _publish(broker, EventType.analysis_stage_changed, job.investigation_id, stage=job.status)
        arguments = list((await session.scalars(select(AgentArgument).where(AgentArgument.job_id == job.id))).all())
        if provider is not None and not arguments:
            warnings.append(
                "All specialist agents failed to produce validated arguments; downstream stages cannot infer ungrounded support."
            )
        arguments_by_claim: dict[uuid.UUID, list[AgentArgument]] = defaultdict(list)
        for argument in arguments:
            arguments_by_claim[argument.claim_id].append(argument)
        rounds = 0
        for round_number in range(1, job.max_debate_rounds + 1):
            unresolved: list[str] = []
            missing: list[str] = []
            for claim in claims:
                claim_arguments = arguments_by_claim.get(claim.id, [])
                has_support = any(item.argument_type == ArgumentType.supporting.value for item in claim_arguments)
                has_challenge = any(
                    item.argument_type in {ArgumentType.contradicting.value, ArgumentType.methodological_criticism.value}
                    for item in claim_arguments
                )
                if has_support and has_challenge:
                    unresolved.append(f"Support and challenge remain in tension for claim {claim.id}.")
                if not any(json.loads(item.evidence_ids_json) for item in claim_arguments):
                    missing.append(f"No evidence-backed argument was available for claim {claim.id}.")
            moderator = await _create_execution(
                session,
                job,
                "debate_moderator",
                role_models.get("debate_moderator"),
                status="waiting_in_queue" if provider is not None else "generating",
            )
            moderator_context = {
                "round_number": round_number,
                "claims": [{"claim_id": str(item.id), "text": item.text} for item in claims],
                "arguments": [
                    {
                        "argument_id": str(item.id),
                        "claim_id": str(item.claim_id),
                        "agent": item.agent_identifier,
                        "type": item.argument_type,
                        "text": item.text,
                        "evidence_ids": json.loads(item.evidence_ids_json),
                        "limitations": json.loads(item.limitations_json),
                    }
                    for item in arguments
                ],
            }
            if provider is None:
                await _publish(
                    broker,
                    EventType.analysis_agent_started,
                    investigation_id,
                    agent="debate_moderator",
                    execution_id=str(moderator.id),
                    status="generating",
                )
                debate_payload = DebatePayload(
                    round_number=round_number,
                    moderator_summary=(
                        f"Rule-based moderator compared {len(arguments)} persisted argument(s) across "
                        f"{len(claims)} claim(s); {len(unresolved)} disagreement(s) and {len(missing)} evidence gap(s) remain."
                    ),
                    unresolved_disagreements=unresolved + missing,
                    requested_follow_up=(
                        ["Obtain claim-specific evidence before adjudication."]
                        if missing
                        else ["Compare populations, methods, and time periods before adjudication."]
                        if unresolved
                        else []
                    ),
                )
                moderator_usage: dict[str, Any] = {}
                moderator_error = None
                moderator_mode = "rule_based"
            else:
                raw_moderator, moderator_usage, moderator_error = await _optional_llm_json(
                    provider,
                    role_models.get("debate_moderator"),
                    (
                        "Return JSON only with round_number, moderator_summary, unresolved_disagreements, "
                        "and requested_follow_up. Summarize only the supplied arguments and evidence IDs. "
                        "Identify missing evidence rather than inventing it."
                    ),
                    json.dumps(moderator_context),
                    response_model=DebatePayload,
                    stage_name="debate_moderator",
                    on_state_change=_make_state_callback(
                        session, broker, moderator, investigation_id, "debate_moderator", db_lock
                    ),
                )
                moderator_mode = "llm"
                try:
                    if moderator_error is None:
                        debate_payload = DebatePayload.model_validate(raw_moderator)
                        if debate_payload.round_number != round_number:
                            raise ValueError("moderator returned the wrong debate round")
                    else:
                        debate_payload = None
                except ValueError as exc:
                    moderator_error = str(exc)
                    debate_payload = None
            await _finish_execution(
                session,
                moderator,
                {"debate": debate_payload.model_dump(mode="json") if debate_payload else None, "mode": moderator_mode},
                moderator_usage,
                moderator_error,
            )
            await session.commit()
            if moderator_error or debate_payload is None:
                raise ValueError(f"debate moderator failed: {moderator_error or 'invalid output'}")
            session.add(
                DebateRound(
                    job_id=job.id,
                    round_number=round_number,
                    moderator_summary=debate_payload.moderator_summary,
                    unresolved_disagreements_json=_dump(debate_payload.unresolved_disagreements),
                    requested_follow_up_json=_dump(debate_payload.requested_follow_up),
                )
            )
            rounds = round_number
            await session.commit()
            await _publish(
                broker,
                EventType.analysis_debate_round,
                job.investigation_id,
                round_number=round_number,
                unresolved_count=len(unresolved),
            )
            if not unresolved:
                break

        await _ensure_not_cancelled(session, job)
        job.status = "adjudicating"
        await session.commit()
        await _publish(broker, EventType.analysis_stage_changed, job.investigation_id, stage=job.status)
        decisions: list[DecisionPayload] = []
        latest_unresolved = (
            list(
                (
                    await session.scalars(
                        select(DebateRound)
                        .where(DebateRound.job_id == job.id)
                        .order_by(DebateRound.round_number.desc())
                    )
                ).all()
            )[0]
            if rounds
            else None
        )
        unresolved = json.loads(latest_unresolved.unresolved_disagreements_json) if latest_unresolved else []
        adjudicator = await _create_execution(
            session,
            job,
            "conflict_adjudicator",
            role_models.get("conflict_adjudicator"),
            status="waiting_in_queue" if provider is not None else "generating",
        )
        adjudication_context = build_adjudication_compact_context(
            claims, arguments, evidence, associated_evidence, documents
        )
        if provider is None:
            await _publish(
                broker,
                EventType.analysis_agent_started,
                investigation_id,
                agent="conflict_adjudicator",
                execution_id=str(adjudicator.id),
                status="generating",
            )
            decisions = []
            for claim in claims:
                claim_arguments = arguments_by_claim.get(claim.id, [])
                support = [item for item in claim_arguments if item.argument_type == ArgumentType.supporting.value]
                challenges = [
                    item
                    for item in claim_arguments
                    if item.argument_type in {ArgumentType.contradicting.value, ArgumentType.methodological_criticism.value}
                ]
                support_evidence = [
                    item
                    for argument in support
                    for item in evidence
                    if item.id in set(json.loads(argument.evidence_ids_json))
                ]
                source_diversity = len({item.source_id for item in support_evidence})
                has_full_text = any(
                    documents[item.document_id].access_level == "full_text"
                    for item in support_evidence
                    if item.document_id in documents
                )
                if not support_evidence:
                    decision = "insufficient_evidence"
                elif challenges:
                    decision = "contradictory"
                elif source_diversity >= 2 and has_full_text:
                    decision = "moderately_supported"
                else:
                    decision = "weakly_supported"
                decisions.append(
                    DecisionPayload(
                        claim_id=claim.id,
                        decision=decision,
                        explanation=(
                            "Rule-based adjudication considered traceability, relevance, source diversity, "
                            "document access level, evidence basis, and recorded limitations; it did not use "
                            "argument counts as a vote."
                        ),
                        supporting_argument_ids=[item.id for item in support + challenges],
                        evidence_ids=[item.id for item in support_evidence],
                        unresolved_disagreements=[item for item in unresolved if str(claim.id) in item],
                    )
                )
            adjudicator_payload: object = {"decisions": [item.model_dump(mode="json") for item in decisions]}
            adjudicator_usage: dict[str, Any] = {}
            adjudicator_error = None
            adjudicator_mode = "rule_based"
        else:
            expected_claim_ids = {item.id for item in claims}
            argument_by_id = {item.id: item for item in arguments}

            def _validate_adjudication_payload(dumped: dict[str, Any]) -> None:
                raw_items = dumped.get("decisions")
                if not isinstance(raw_items, list):
                    raise ValueError("adjudicator output must contain a decisions array")
                parsed_decisions = [DecisionPayload.model_validate(item) for item in raw_items]
                if len(parsed_decisions) != len(expected_claim_ids) or {item.claim_id for item in parsed_decisions} != expected_claim_ids:
                    raise ValueError("adjudicator output must contain exactly one decision per claim")
                for item in parsed_decisions:
                    if set(item.evidence_ids) - evidence_ids:
                        raise ValueError("adjudicator output referenced evidence outside the investigation")
                    if any(argument_by_id.get(argument_id) is None for argument_id in item.supporting_argument_ids):
                        raise ValueError("adjudicator output referenced unknown argument_id")
                    if any(argument_by_id[argument_id].claim_id != item.claim_id for argument_id in item.supporting_argument_ids):
                        raise ValueError("adjudicator output referenced argument outside the claim")
                    if item.decision != "insufficient_evidence" and not item.evidence_ids and not item.supporting_argument_ids:
                        raise ValueError(
                            f"decision '{item.decision}' for claim {item.claim_id} has no cited evidence_ids or supporting_argument_ids; use 'insufficient_evidence' or cite full UUIDs"
                        )
                    if item.decision == "contradictory":
                        exp_lower = item.explanation.casefold()
                        has_conflict_marker = bool(
                            item.unresolved_disagreements
                            or re.search(
                                r"contradict|disagree|conflict|differ|challenge|mixed|however|although|null|limitation|oppos|concern|risk|counter|contrast|caveat|inconclusive",
                                exp_lower,
                            )
                        )
                        if not has_conflict_marker:
                            raise ValueError(
                                f"decision for claim {item.claim_id} is 'contradictory' but explanation describes only support without conflict or disagreement"
                            )

            raw_adjudication, adjudicator_usage, adjudicator_error = await _optional_llm_json(
                provider,
                role_models.get("conflict_adjudicator"),
                (
                    "Return JSON only with a decisions array containing exactly one decision per claim_id. For each "
                    "claim compare evidence relevance, exact_text, source diversity, access level, population, methodology, "
                    "evidence basis, and limitations. Do not classify support or contradiction based solely on relevance "
                    "score or with empty evidence_ids. Use 'insufficient_evidence' when no traceable evidence_ids support a "
                    "finding. Use 'contradictory' ONLY when supplied arguments or evidence show genuine opposing findings "
                    "or unresolved conflict, and ensure every decision label strictly matches its explanation. Cite full "
                    "supplied UUIDs only."
                ),
                json.dumps(adjudication_context),
                response_model=_DecisionsListPayload,
                stage_name="conflict_adjudicator",
                on_state_change=_make_state_callback(
                    session, broker, adjudicator, investigation_id, "conflict_adjudicator", db_lock
                ),
                validator=_validate_adjudication_payload,
            )
            adjudicator_mode = "llm"
            try:
                raw_decisions = raw_adjudication.get("decisions") if raw_adjudication else None
                if not isinstance(raw_decisions, list):
                    raise ValueError("adjudicator output must contain a decisions array")
                _validate_adjudication_payload(raw_adjudication)
                decisions = [DecisionPayload.model_validate(item) for item in raw_decisions]
                adjudicator_payload = {"decisions": [item.model_dump(mode="json") for item in decisions]}
            except ValueError as exc:
                adjudicator_error = str(exc)
                decisions = []
                adjudicator_payload = None
        expected_claim_ids = {item.id for item in claims}
        argument_by_id = {item.id: item for item in arguments}
        if adjudicator_error is None:
            if {item.claim_id for item in decisions} != expected_claim_ids:
                adjudicator_error = "adjudicator output must contain exactly one decision per claim"
            elif any(
                set(item.evidence_ids) - evidence_ids
                or any(argument_by_id.get(argument_id, None) is None for argument_id in item.supporting_argument_ids)
                or any(argument_by_id[argument_id].claim_id != item.claim_id for argument_id in item.supporting_argument_ids)
                for item in decisions
            ):
                adjudicator_error = "adjudicator output referenced evidence or arguments outside the claim"
        await _finish_execution(
            session,
            adjudicator,
            adjudicator_payload if adjudicator_error is None else None,
            adjudicator_usage,
            adjudicator_error,
        )
        await session.commit()
        if adjudicator_error:
            warnings.append(
                f"conflict_adjudicator: LLM adjudication encountered an error ({adjudicator_error}); applying evidence-grounded adjudication fallback."
            )
            existing_decision_claim_ids = {d.claim_id for d in decisions}
            for claim in claims:
                if claim.id not in existing_decision_claim_ids:
                    claim_arguments = arguments_by_claim.get(claim.id, [])
                    support = [item for item in claim_arguments if item.argument_type == ArgumentType.supporting.value]
                    challenges = [
                        item
                        for item in claim_arguments
                        if item.argument_type
                        in {ArgumentType.contradicting.value, ArgumentType.methodological_criticism.value}
                    ]
                    support_evidence = [
                        item
                        for argument in support
                        for item in evidence
                        if item.id in set(_safe_json_loads(argument.evidence_ids_json, []))
                    ]
                    has_contradicting_evidence = any(
                        item.evidence_type == "contradicting"
                        for argument in challenges
                        for item in evidence
                        if item.id in set(_safe_json_loads(argument.evidence_ids_json, []))
                    )
                    source_diversity = len({item.source_id for item in support_evidence})
                    has_full_text = any(
                        documents[item.document_id].access_level == "full_text"
                        for item in support_evidence
                        if item.document_id in documents
                    )
                    if not support_evidence and not has_contradicting_evidence:
                        decision_label = "insufficient_evidence"
                    elif has_contradicting_evidence:
                        decision_label = "contradictory"
                    elif source_diversity >= 2 and has_full_text:
                        decision_label = "moderately_supported"
                    else:
                        decision_label = "weakly_supported"
                    decisions.append(
                        DecisionPayload(
                            claim_id=claim.id,
                            decision=decision_label,
                            explanation=(
                                "Evidence-grounded adjudication fallback evaluated traceability, relevance, source diversity, "
                                "and access level; contradictory classification required documented opposing evidence."
                            ),
                            supporting_argument_ids=[item.id for item in support + challenges],
                            evidence_ids=[item.id for item in support_evidence],
                            unresolved_disagreements=[item for item in unresolved if str(claim.id) in item],
                        )
                    )
            adjudicator_error = None
        claims_by_id = {item.id: item for item in claims}
        for payload in decisions:
            session.add(
                AdjudicationDecision(
                    job_id=job.id,
                    claim_id=payload.claim_id,
                    decision=payload.decision,
                    explanation=payload.explanation,
                    supporting_argument_ids_json=_dump([str(item) for item in payload.supporting_argument_ids]),
                    evidence_ids_json=_dump([str(item) for item in payload.evidence_ids]),
                    unresolved_disagreements_json=_dump(payload.unresolved_disagreements),
                )
            )
            if payload.claim_id in claims_by_id:
                claims_by_id[payload.claim_id].status = payload.decision
        await session.commit()

        job.status = "reporting"
        await session.commit()
        await _publish(broker, EventType.analysis_stage_changed, job.investigation_id, stage=job.status)
        evidence_by_id = {item.id: item for item in evidence}

        def provenance_for(evidence_ids: list[uuid.UUID]) -> list[EvidenceProvenance]:
            provenance: list[EvidenceProvenance] = []
            for evidence_id in evidence_ids:
                item = evidence_by_id[evidence_id]
                source = sources[item.source_id]
                document = documents.get(item.document_id) if item.document_id else None
                provenance.append(
                    EvidenceProvenance(
                        evidence_id=evidence_id,
                        source_url=source.original_url,
                        access_level=document.access_level if document else "metadata_only",
                        document_url=document.document_url if document else None,
                        version_type=document.version_type if document else None,
                        page_number=item.page_number,
                        section_name=item.section_name,
                    )
                )
            return provenance

        report_agent = await _create_execution(
            session,
            job,
            "report_intelligence",
            role_models.get("report_intelligence"),
            status="waiting_in_queue" if provider is not None else "generating",
        )
        if provider is None:
            await _publish(
                broker,
                EventType.analysis_agent_started,
                investigation_id,
                agent="report_intelligence",
                execution_id=str(report_agent.id),
                status="generating",
            )
            report_sections = build_18_report_sections(
                question=question,
                claims=claims,
                decisions=decisions,
                evidence=evidence,
                sources=sources,
                documents=documents,
                arguments=arguments,
                warnings=warnings,
                provenance_for_fn=provenance_for,
            )
            report_payload: object = {
                "sections": [item.model_dump(mode="json") for item in report_sections],
                "mode": "rule_based",
            }
            report_usage: dict[str, Any] = {}
            report_error = None
        else:
            report_context = {
                "question": question,
                "claims": [{"claim_id": str(item.id), "text": item.text} for item in claims],
                "decisions": [item.model_dump(mode="json") for item in decisions],
                "arguments": [
                    {
                        "argument_id": str(item.id),
                        "claim_id": str(item.claim_id),
                        "agent": item.agent_identifier,
                        "text": item.text,
                        "evidence_ids": json.loads(item.evidence_ids_json),
                        "limitations": json.loads(item.limitations_json),
                    }
                    for item in arguments
                ],
                "evidence": [
                    {
                        "evidence_id": str(item.id),
                        "exact_text": compact_evidence_text(item.exact_text, max_length=400),
                        "type": item.evidence_type,
                        "source_url": sources[item.source_id].original_url,
                        "access_level": documents[item.document_id].access_level if item.document_id in documents else "metadata_only",
                        "document_url": documents[item.document_id].document_url if item.document_id in documents else None,
                        "page_number": item.page_number,
                        "section_name": item.section_name,
                    }
                    for item in evidence[:16]
                ],
            }
            raw_report, report_usage, report_error = await _optional_llm_json(
                provider,
                role_models.get("report_intelligence"),
                (
                    "Return JSON only with a sections array. Every factual section must cite only supplied "
                    "evidence_ids and claim_ids. Include findings, limitations, research gaps, source URLs, "
                    "access levels, and document provenance through the supplied IDs. Do not claim that a "
                    "passage establishes more than it says."
                ),
                json.dumps(report_context),
                response_model=_ReportSectionsListPayload,
                stage_name="report_intelligence",
                on_state_change=_make_state_callback(
                    session, broker, report_agent, investigation_id, "report_intelligence", db_lock
                ),
            )
            try:
                raw_sections = raw_report.get("sections") if raw_report else None
                if not isinstance(raw_sections, list):
                    raise ValueError("report output must contain a sections array")
                report_sections = [ReportSectionPayload.model_validate(item) for item in raw_sections]
            except ValueError as exc:
                report_error = str(exc)
                report_sections = []
            report_payload = {"sections": [item.model_dump(mode="json") for item in report_sections], "mode": "llm"}
        report_claim_ids = {item.id for item in claims}
        report_evidence_ids = {
            evidence_id
            for section in report_sections
            for evidence_id in section.evidence_ids
        }
        report_claim_references = {claim_id for section in report_sections for claim_id in section.claim_ids}
        if report_error is None and (
            not report_sections
            or not report_evidence_ids.issubset(evidence_ids)
            or not report_claim_references.issubset(report_claim_ids)
        ):
            report_error = "report references claims or evidence outside the investigation"
        if report_error is not None:
            warnings.append(
                f"report_intelligence: LLM generation failed ({report_error}); synthesized transparent report from persisted findings."
            )
            report_sections = _build_fallback_report_sections(
                question, claims, decisions, evidence, sources, documents, warnings, provenance_for
            )
            report_payload = {
                "sections": [item.model_dump(mode="json") for item in report_sections],
                "mode": "rule_based_fallback",
                "llm_error": report_error,
            }
            await _finish_execution(session, report_agent, report_payload, report_usage, report_error)
            await session.commit()
            report_error = None
        else:
            for section in report_sections:
                section.provenance = provenance_for(section.evidence_ids)
            await _finish_execution(session, report_agent, report_payload, report_usage)
            await session.commit()

        assessment = "insufficient_evidence" if all(item.decision == "insufficient_evidence" for item in decisions) else "qualified"
        report = ResearchReport(
            job_id=job.id,
            executive_summary=(
                f"Analysis completed across {len(claims)} atomic claim(s), {len(arguments)} argument(s), "
                f"and {rounds} bounded debate round(s). Findings remain traceable to persisted evidence."
            ),
            overall_assessment=assessment,
            evidence_gap=" ".join(warnings) or None,
        )
        session.add(report)
        await session.flush()
        for position, section in enumerate(report_sections):
            session.add(
                ReportSection(
                    report_id=report.id,
                    section_type=section.section_type,
                    title=section.title,
                    content=section.content,
                    claim_ids_json=_dump([str(item) for item in section.claim_ids]),
                    evidence_ids_json=_dump([str(item) for item in section.evidence_ids]),
                    provenance_json=_dump([item.model_dump(mode="json") for item in section.provenance]),
                    position=position,
                )
            )

        evidence_strength_summary = compute_evidence_strength(claims, sources, documents, evidence, decisions)
        await save_report_version(
            session=session,
            investigation_id=job.investigation_id,
            job_id=job.id,
            executive_summary=report.executive_summary,
            overall_assessment=report.overall_assessment,
            evidence_gap=report.evidence_gap,
            sections=report_sections,
            evidence_strength=evidence_strength_summary,
        )

        all_executions = list(
            (
                await session.scalars(
                    select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == job.id)
                )
            ).all()
        )
        coverage_summary = compute_analysis_coverage(claims, all_executions, arguments, decisions, evidence)
        job.status = (
            "completed_with_warnings" if (warnings or coverage_summary.is_partially_completed) else "completed"
        )
        job.error_message = " ".join(warnings) or None
        job.completed_at = datetime.now(UTC)
        await session.commit()
        await _publish(
            broker,
            EventType.analysis_completed,
            job.investigation_id,
            job_id=str(job.id),
            status=job.status,
            warnings=warnings,
            coverage=coverage_summary.model_dump(mode="json"),
        )
    except asyncio.CancelledError:
        await session.rollback()
        await _mark_unfinished_executions_cancelled(session, broker, job_id, investigation_id)
        cancelled = await session.get(AnalysisJob, job_id)
        if cancelled:
            cancelled.status = "cancelled"
            cancelled.cancel_requested = True
            cancelled.completed_at = datetime.now(UTC)
            await session.commit()
            await _publish(
                broker,
                EventType.analysis_failed,
                cancelled.investigation_id,
                job_id=str(cancelled.id),
                status="cancelled",
                error="Analysis cancelled.",
            )
        raise
    except Exception as exc:
        await session.rollback()
        await _mark_unfinished_executions_failed(session, broker, job_id, investigation_id, str(exc))
        failed = await session.get(AnalysisJob, job_id)
        if failed:
            failed.status = "failed"
            failed.error_message = str(exc)
            failed.completed_at = datetime.now(UTC)
            await session.commit()
            await _publish(
                broker, EventType.analysis_failed, failed.investigation_id, job_id=str(failed.id), error=str(exc)
            )
    finally:
        if provider is not None:
            await provider.close()
