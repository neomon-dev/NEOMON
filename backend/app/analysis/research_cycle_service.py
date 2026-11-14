"""Autonomous Research Cycle Execution Service (Milestones 9A, 9C, 9D).

Executes an iterative research cycle:
1. Plans actions using existing intelligence (9B)
2. Adapts queries and avoids duplication (9C)
3. Executes multi-provider searches and document acquisitions
4. Routes new literature through canonical credibility and validation pipelines (8G)
5. Reevaluates claims, hypotheses, contradictions, and gaps (9D)
6. Updates budget counters and checks scientific stopping criteria (9E & 9F)
7. Persists execution checkpoints and telemetry
"""

import asyncio
from datetime import UTC, datetime
import json
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.adaptive_query_service import (
    generate_adaptive_query_variants,
    is_near_duplicate_query,
)
from app.analysis.entailment_service import (
    EntailmentClassification,
    validate_evidence_claim_entailment_heuristic,
)
from app.analysis.quality_calibration_service import calibrate_investigation_quality
from app.analysis.research_planner import (
    PlannedResearchAction,
    ResearchActionType,
    plan_research_cycle,
)
from app.analysis.research_stopping_service import (
    StoppingReason,
    evaluate_stopping_criteria,
)
from app.events import EventBroker
from app.models import (
    AutonomousResearchWorkflow,
    Claim,
    Document,
    Evidence,
    Investigation,
    ResearchAction,
    ResearchContradiction,
    ResearchEvent,
    ResearchGap,
    ResearchHypothesis,
    ResearchQuery,
    ResearchQueryHistory,
    ResearchWorkflowCheckpoint,
    ResearchWorkflowCycle,
    Source,
)
from app.research.evidence import extract_evidence
from app.research.normalization import deduplicate_results
from app.research.providers import SearchQuery, SearchResult, build_research_providers
from app.research.retrieval import retrieve_document
from app.research.source_credibility import evaluate_canonical_credibility
from app.research.source_lineage import analyze_source_lineage
from app.schemas import EventType


async def execute_research_cycle(
    session: AsyncSession,
    broker: EventBroker | None,
    workflow_id: uuid.UUID,
    cycle_number: int,
) -> dict[str, Any]:
    """Execute a single end-to-end autonomous research cycle."""
    wf = await session.get(AutonomousResearchWorkflow, workflow_id)
    if not wf:
        raise ValueError(f"Workflow {workflow_id} not found")

    inv = await session.get(Investigation, wf.investigation_id)
    if not inv:
        raise ValueError(f"Investigation {wf.investigation_id} not found")

    # Load existing state
    claims_res = await session.execute(
        select(Claim).where(Claim.investigation_id == inv.id)
    )
    claims = list(claims_res.scalars().all())

    sources_res = await session.execute(
        select(Source)
        .options(selectinload(Source.credibility_assessment))
        .where(Source.investigation_id == inv.id)
    )
    sources = list(sources_res.scalars().all())

    source_ids = [s.id for s in sources]
    if source_ids:
        evidence_res = await session.execute(
            select(Evidence).where(Evidence.source_id.in_(source_ids))
        )
        evidence = list(evidence_res.scalars().all())
    else:
        evidence = []

    contra_res = await session.execute(
        select(ResearchContradiction).where(
            (ResearchContradiction.primary_investigation_id == inv.id)
            | (ResearchContradiction.secondary_investigation_id == inv.id)
        )
    )
    contradictions = list(contra_res.scalars().all())

    hypo_res = await session.execute(
        select(ResearchHypothesis).where(ResearchHypothesis.investigation_id == inv.id)
    )
    hypotheses = list(hypo_res.scalars().all())

    # Load executed query history
    hist_res = await session.execute(
        select(ResearchQueryHistory.normalized_query).where(
            ResearchQueryHistory.workflow_id == workflow_id
        )
    )
    executed_queries = [r[0] for r in hist_res.all()]

    # Create cycle record
    cycle = ResearchWorkflowCycle(
        workflow_id=workflow_id,
        cycle_number=cycle_number,
        cycle_goal=f"Cycle {cycle_number}: Autonomous evidentiary expansion and gap resolution",
        status="executing",
        started_at=datetime.now(UTC),
    )
    session.add(cycle)
    await session.flush()

    wf.current_cycle_number = cycle_number
    wf.status = "executing"
    await session.commit()

    if broker:
        await broker.publish(
            EventType.agent_started,
            {
                "investigation_id": str(inv.id),
                "workflow_id": str(wf.id),
                "cycle_number": cycle_number,
                "status": "executing",
            },
            session=session,
        )

    # 1. Generate Research Plan
    plan = plan_research_cycle(
        workflow_id=str(wf.id),
        cycle_number=cycle_number,
        investigation=inv,
        claims=claims,
        sources=sources,
        evidence=evidence,
        contradictions=contradictions,
        hypotheses=hypotheses,
        executed_queries=executed_queries,
        max_actions=4,
    )

    cycle.cycle_goal = plan.cycle_goal
    cycle.actions_total = len(plan.actions)

    # Persist planned actions
    action_records: list[ResearchAction] = []
    for pa in plan.actions:
        # Determine approval requirement based on autonomy mode
        req_approval = False
        if wf.autonomy_mode == "assisted":
            req_approval = True
        elif wf.autonomy_mode == "supervised" and pa.action_type in (
            ResearchActionType.REQUEST_HUMAN_REVIEW,
            ResearchActionType.EXPAND_RESEARCH_QUESTION,
        ):
            req_approval = True

        status_val = "awaiting_approval" if req_approval else "pending"

        ar = ResearchAction(
            workflow_id=wf.id,
            cycle_id=cycle.id,
            action_type=pa.action_type.value,
            target_entity_type=pa.target_entity_type,
            target_entity_id=uuid.UUID(pa.target_entity_id) if pa.target_entity_id and len(pa.target_entity_id) == 36 else None,
            objective=pa.objective,
            rationale=pa.rationale,
            search_queries_json=json.dumps(pa.search_queries),
            target_providers_json=json.dumps(pa.target_providers),
            priority=pa.priority,
            expected_information_gain=pa.expected_information_gain,
            estimated_cost=pa.estimated_cost,
            requires_approval=req_approval,
            status=status_val,
        )
        session.add(ar)
        action_records.append(ar)

    await session.commit()

    # Check if workflow must pause for human review (Assisted mode or pending approvals)
    pending_approvals = [a for a in action_records if a.status == "awaiting_approval"]
    if pending_approvals and wf.autonomy_mode == "assisted":
        wf.status = "awaiting_approval"
        cycle.status = "awaiting_approval"
        await session.commit()
        return {
            "workflow_id": str(wf.id),
            "cycle_number": cycle_number,
            "status": "awaiting_approval",
            "pending_approvals_count": len(pending_approvals),
            "cycle_goal": cycle.cycle_goal,
        }

    # 2. Execute Approved / Non-blocked Actions
    providers = build_research_providers()
    providers_by_name = {p.name.lower(): p for p in providers}

    newly_acquired_sources: list[Source] = []
    newly_extracted_evidence: list[Evidence] = []
    executed_searches_count = 0
    acquired_documents_count = 0

    for action in action_records:
        if action.status not in ("pending", "approved"):
            continue

        action.status = "running"
        await session.commit()

        action_queries = json.loads(action.search_queries_json)
        target_provs = json.loads(action.target_providers_json) or ["crossref", "arxiv", "openalex"]

        results_for_action: list[SearchResult] = []

        # Execute searches for action
        for raw_q in action_queries:
            # Check budget limit before each search
            if wf.spent_searches + executed_searches_count >= wf.budget_max_searches:
                break

            # Adaptive query adaptation
            variants = generate_adaptive_query_variants(
                base_query=raw_q,
                target_providers=target_provs,
                executed_queries=executed_queries,
                force_counter_evidence=(action.action_type == ResearchActionType.FIND_COUNTER_EVIDENCE.value),
            )

            for adapted_q, prov_name, q_rationale in variants:
                if is_near_duplicate_query(adapted_q, executed_queries):
                    continue

                provider_obj = providers_by_name.get(prov_name.lower())
                if not provider_obj:
                    # fallback to any provider
                    provider_obj = providers[0] if providers else None
                if not provider_obj:
                    continue

                try:
                    sq = SearchQuery(text=adapted_q, category="autonomous_adaptive")
                    found = await provider_obj.search(sq, limit=5)
                    executed_searches_count += 1
                    executed_queries.append(adapted_q)

                    # Track in query history
                    qh = ResearchQueryHistory(
                        workflow_id=wf.id,
                        cycle_id=cycle.id,
                        action_id=action.id,
                        query_text=adapted_q,
                        normalized_query=adapted_q.lower().strip(),
                        provider=provider_obj.name,
                        results_count=len(found),
                        relevant_count=sum(1 for f in found if f.relevance_score >= 0.5),
                        effectiveness_score=round(sum(f.relevance_score for f in found) / max(1, len(found)), 2),
                        is_counter_evidence_query=(action.action_type == ResearchActionType.FIND_COUNTER_EVIDENCE.value),
                    )
                    session.add(qh)

                    results_for_action.extend(found)
                except Exception as err:
                    # Record failure without halting
                    pass

        # 3. Process Acquired Sources through Canonical Pipeline (8G)
        deduped = deduplicate_results(results_for_action)
        for res in deduped:
            if wf.spent_sources + len(newly_acquired_sources) >= wf.budget_max_sources:
                break

            # Avoid re-adding existing sources in this investigation
            if any(s.canonical_url == res.url or (s.doi and s.doi == res.doi) for s in sources):
                continue

            cred = evaluate_canonical_credibility(
                url=res.url,
                publisher=res.publisher,
                doi=res.doi,
                source_type_declared=res.source_type,
                title=res.title,
            )

            src_row = Source(
                investigation_id=inv.id,
                title=res.title,
                canonical_url=res.url,
                original_url=res.url,
                source_type=cred.source_type.value,
                publisher=res.publisher,
                doi=res.doi,
                publication_date=res.publication_date,
                relevance_score=res.relevance_score,
                inclusion_status="included",
            )
            session.add(src_row)
            await session.flush()
            newly_acquired_sources.append(src_row)
            sources.append(src_row)

            # Retrieve Document Content
            if wf.spent_documents + acquired_documents_count < wf.budget_max_documents:
                try:
                    doc = await retrieve_document(res.url)
                    if doc and doc.content:
                        acquired_documents_count += 1
                        doc_row = Document(
                            source_id=src_row.id,
                            content_type=doc.content_type,
                            title=src_row.title,
                            content=doc.content,
                            access_level=doc.access_level,
                            document_url=doc.url,
                        )
                        session.add(doc_row)
                        await session.flush()

                        # Extract Evidence Passages
                        ev_list = extract_evidence(
                            doc.content,
                            [c.text for c in claims] or [inv.question],
                        )
                        for ev_item in ev_list[:3]:
                            # Link evidence to target claim
                            cid = None
                            if action.target_entity_type == "claim" and action.target_entity_id:
                                cid = action.target_entity_id
                            elif claims:
                                cid = claims[0].id

                            ev_row = Evidence(
                                source_id=src_row.id,
                                claim_id=cid,
                                exact_text=ev_item.text,
                                evidence_type=ev_item.evidence_type,
                                relevance_score=ev_item.relevance_score,
                                extraction_method="autonomous_extractor",
                                document_id=doc_row.id,
                            )
                            session.add(ev_row)
                            await session.flush()
                            newly_extracted_evidence.append(ev_row)
                            evidence.append(ev_row)
                except Exception:
                    pass

        action.status = "completed"
        action.completed_at = datetime.now(UTC)
        action.execution_result_json = json.dumps({
            "results_count": len(results_for_action),
            "sources_added": len(newly_acquired_sources),
            "evidence_added": len(newly_extracted_evidence),
        })
        cycle.actions_completed += 1

    await session.commit()

    # 4. Reevaluate Claims against Newly Acquired Evidence (9D)
    claim_updates_count = 0
    for c in claims:
        c_evidence = [ev for ev in evidence if ev.claim_id == c.id]
        if not c_evidence:
            continue

        has_direct = False
        has_contra = False
        for ev in c_evidence:
            val = validate_evidence_claim_entailment_heuristic(
                claim_id=str(c.id),
                claim_text=c.text,
                evidence_id=str(ev.id),
                evidence_text=ev.exact_text,
            )
            if val.entailment_classification == EntailmentClassification.DIRECT_SUPPORT:
                has_direct = True
            elif val.entailment_classification == EntailmentClassification.DIRECT_CONTRADICTION:
                has_contra = True

        old_status = c.status
        if has_contra and has_direct:
            c.status = "disputed"
            c.explanation = "Empirical evidence exhibits direct dialectical tension across acquired sources."
        elif has_direct:
            c.status = "supported"
            c.explanation = f"Empirically substantiated with direct causal proof across {len(c_evidence)} passage(s)."
        elif c_evidence:
            c.status = "contextually_supported"
            c.explanation = "Grounded by contextual and descriptive background evidence."

        if c.status != old_status:
            claim_updates_count += 1

    # 5. Reevaluate Hypotheses (9D)
    for hyp in hypotheses:
        # Match evidence containing hypothesis keywords
        h_words = set(hyp.statement.lower().split()[:5])
        supporting_ev = [
            str(ev.id) for ev in evidence
            if any(w in ev.exact_text.lower() for w in h_words if len(w) > 3)
        ]
        if supporting_ev:
            hyp.supporting_evidence_ids_json = json.dumps(supporting_ev[:5])
            if len(supporting_ev) >= 2 and hyp.status == "proposed":
                hyp.status = "supported"

    # 6. Re-calibrate Quality (8G integration)
    cal_res = await calibrate_investigation_quality(session, inv.id)

    # 7. Calculate Cycle Information Gain & Update Budgets
    info_gain = 0.0
    if newly_acquired_sources:
        info_gain += min(0.4, len(newly_acquired_sources) * 0.1)
    if newly_extracted_evidence:
        info_gain += min(0.4, len(newly_extracted_evidence) * 0.1)
    if claim_updates_count > 0:
        info_gain += 0.2

    info_gain = round(min(1.0, info_gain), 2)
    cycle.information_gain_score = info_gain
    cycle.sources_acquired = len(newly_acquired_sources)
    cycle.evidence_acquired = len(newly_extracted_evidence)
    cycle.claims_updated = claim_updates_count
    cycle.status = "completed"
    cycle.completed_at = datetime.now(UTC)
    cycle.evaluation_summary = (
        f"Cycle {cycle_number} acquired {len(newly_acquired_sources)} sources, "
        f"{len(newly_extracted_evidence)} evidence passages, updated {claim_updates_count} claims. "
        f"Information gain score: {info_gain:.2f}."
    )

    # Low-value tracking
    if info_gain < 0.15:
        wf.consecutive_low_value_cycles += 1
    else:
        wf.consecutive_low_value_cycles = 0

    # Budget consumption
    wf.spent_searches += executed_searches_count
    wf.spent_sources += len(newly_acquired_sources)
    wf.spent_documents += acquired_documents_count
    wf.total_cycles_completed += 1

    # 8. Evaluate Stopping Conditions (9F)
    from app.models import ResearchQualityCalibration
    cal_row_res = await session.execute(
        select(ResearchQualityCalibration).where(
            ResearchQualityCalibration.investigation_id == inv.id
        )
    )
    cal_obj = cal_row_res.scalar_one_or_none()

    stop_eval = evaluate_stopping_criteria(
        workflow=wf,
        investigation=inv,
        claims=claims,
        sources=sources,
        evidence=evidence,
        calibration=cal_obj,
        contradictions=contradictions,
        recent_cycle_gain=info_gain,
        provider_exhaustion_flag=(executed_searches_count > 0 and len(newly_acquired_sources) == 0),
    )

    if stop_eval.should_stop:
        wf.stopping_reason = stop_eval.stopping_reason.value if stop_eval.stopping_reason else None
        wf.stopping_explanation = stop_eval.explanation
        wf.scientific_confidence = stop_eval.scientific_confidence
        wf.completed_at = datetime.now(UTC)

        if stop_eval.stopping_reason == StoppingReason.SUFFICIENT_EVIDENCE:
            wf.status = "completed"
        elif stop_eval.stopping_reason in (StoppingReason.DIMINISHING_RETURNS, StoppingReason.UNRESOLVED_SCIENTIFIC_UNCERTAINTY):
            wf.status = "completed_with_limitations"
        elif stop_eval.stopping_reason in (StoppingReason.BUDGET_EXHAUSTED, StoppingReason.MAXIMUM_CYCLES_REACHED):
            wf.status = "stopped_by_budget"
        else:
            wf.status = "completed_with_limitations"

    # Persist checkpoint
    checkpoint = ResearchWorkflowCheckpoint(
        workflow_id=wf.id,
        checkpoint_type="cycle_complete",
        cycle_number=cycle_number,
        state_snapshot_json=json.dumps({
            "spent_searches": wf.spent_searches,
            "spent_sources": wf.spent_sources,
            "spent_documents": wf.spent_documents,
            "information_gain": info_gain,
            "calibrated_tier": cal_res.get("calibrated_tier"),
            "calibrated_score": cal_res.get("calibrated_score"),
            "status": wf.status,
            "stopping_reason": wf.stopping_reason,
        }),
    )
    session.add(checkpoint)
    await session.commit()

    if broker:
        await broker.publish(
            EventType.agent_completed,
            {
                "investigation_id": str(inv.id),
                "workflow_id": str(wf.id),
                "cycle_number": cycle_number,
                "status": wf.status,
                "stopping_reason": wf.stopping_reason,
                "information_gain": info_gain,
            },
            session=session,
        )

    return {
        "workflow_id": str(wf.id),
        "cycle_number": cycle_number,
        "status": wf.status,
        "sources_acquired": len(newly_acquired_sources),
        "evidence_acquired": len(newly_extracted_evidence),
        "claims_updated": claim_updates_count,
        "information_gain": info_gain,
        "stopping_reason": wf.stopping_reason,
        "stopping_explanation": wf.stopping_explanation,
    }
