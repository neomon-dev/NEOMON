import json
import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService, DEFAULT_GLOBAL_WORKSPACE_ID
from app.db import get_session
from app.errors import BackendError
from app.models import (
    AdjudicationDecision,
    AgentArgument,
    AnalysisJob,
    AutonomousResearchWorkflow,
    Claim,
    ClaimEvidenceRelationship,
    Document,
    DocumentVersionRelationship,
    Evidence,
    Investigation,
    OpenAccessLocation,
    ResearchAction,
    ResearchContradiction,
    ResearchGap,
    ResearchGapAnalysis,
    ResearchHypothesis,
    ResearchQuery,
    ResearchWorkflowCycle,
    Source,
    User,
)
from app.schemas import (
    GraphEdgeView,
    GraphNodeType,
    GraphNodeView,
    GraphTotalCounts,
    InvestigationGraphResponse,
)

router = APIRouter(tags=["graph"])


def _safe_json_loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return fallback


def _truncate_label(value: str, limit: int = 86) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1].rstrip()}…"


def _parse_csv_set(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def _map_evidence_relationship(evidence_type: str) -> tuple[str, str]:
    mapping = {
        "supporting": ("supports", "supports"),
        "contradicting": ("contradicts", "contradicts"),
        "contextual": ("contextualizes", "contextualizes"),
        "methodological_limitation": ("methodological_limitation", "methodological limitation"),
    }
    return mapping.get(evidence_type, ("contextualizes", evidence_type.replace("_", " ")))


def _map_argument_relationship(argument_type: str) -> tuple[str, str]:
    mapping = {
        "supporting": ("supports", "argues: supports"),
        "contradicting": ("contradicts", "argues: contradicts"),
        "qualifying": ("contextualizes", "argues: qualifies"),
        "methodological_criticism": ("methodological_limitation", "methodological criticism"),
        "source_criticism": ("source_criticism", "source criticism"),
        "temporal_qualification": ("temporal_qualification", "temporal qualification"),
    }
    return mapping.get(argument_type, ("contextualizes", argument_type.replace("_", " ")))


def _parse_focus_node(focus_node_id: str | None) -> tuple[str, uuid.UUID] | None:
    if not focus_node_id:
        return None
    if ":" not in focus_node_id:
        raise BackendError("focus_node_id must use '<type>:<uuid>' format.", 422, "invalid_focus_node")
    node_type, raw_uuid = focus_node_id.split(":", 1)
    try:
        parsed_uuid = uuid.UUID(raw_uuid)
    except ValueError as exc:
        raise BackendError("focus_node_id contains an invalid UUID.", 422, "invalid_focus_node") from exc
    return node_type, parsed_uuid


async def _build_investigation_graph(
    *,
    session: AsyncSession,
    investigation: Investigation,
    node_types: str | None,
    relationship_types: str | None,
    focus_node_id: str | None,
    q: str | None,
    claim_limit: int,
    offset_claims: int,
    evidence_limit: int,
    max_nodes: int,
    expand_all: bool,
) -> InvestigationGraphResponse:
    focus = _parse_focus_node(focus_node_id)
    allowed_node_types = _parse_csv_set(node_types)
    allowed_rel_types = _parse_csv_set(relationship_types)
    search_term = q.strip().casefold() if q and q.strip() else ""

    # Batch-load all persisted entities for this single investigation (zero N+1 queries).
    claims = list(
        (
            await session.scalars(
                select(Claim).where(Claim.investigation_id == investigation.id).order_by(Claim.priority.asc(), Claim.id)
            )
        ).all()
    )
    sources = list(
        (
            await session.scalars(
                select(Source).where(Source.investigation_id == investigation.id).order_by(Source.relevance_score.desc(), Source.id)
            )
        ).all()
    )
    source_ids = [item.id for item in sources]
    source_map = {item.id: item for item in sources}
    claim_map = {item.id: item for item in claims}

    documents: list[Document] = []
    oa_locations: list[OpenAccessLocation] = []
    doc_version_rels: list[DocumentVersionRelationship] = []
    all_evidence: list[Evidence] = []

    if source_ids:
        documents = list(
            (
                await session.scalars(
                    select(Document).where(Document.source_id.in_(source_ids)).order_by(Document.retrieved_at.desc(), Document.id)
                )
            ).all()
        )
        oa_locations = list(
            (await session.scalars(select(OpenAccessLocation).where(OpenAccessLocation.source_id.in_(source_ids)))).all()
        )
        doc_version_rels = list(
            (
                await session.scalars(
                    select(DocumentVersionRelationship).where(DocumentVersionRelationship.source_id.in_(source_ids))
                )
            ).all()
        )
        all_evidence = list(
            (
                await session.scalars(
                    select(Evidence)
                    .where(Evidence.source_id.in_(source_ids))
                    .order_by(Evidence.relevance_score.desc(), Evidence.id)
                )
            ).all()
        )

    document_map = {item.id: item for item in documents}
    evidence_map = {item.id: item for item in all_evidence}

    claim_evidence_rels: list[ClaimEvidenceRelationship] = []
    if claim_map and evidence_map:
        raw_rels = (
            await session.scalars(
                select(ClaimEvidenceRelationship).where(ClaimEvidenceRelationship.claim_id.in_(list(claim_map)))
            )
        ).all()
        # Strict investigation isolation: drop any relationship whose evidence_id is outside this investigation.
        claim_evidence_rels = [item for item in raw_rels if item.evidence_id in evidence_map]

    query_count = int(
        (
            await session.scalar(
                select(func.count(ResearchQuery.id)).where(ResearchQuery.investigation_id == investigation.id)
            )
        )
        or 0
    )

    latest_job = await session.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.investigation_id == investigation.id)
        .order_by(desc(AnalysisJob.created_at), AnalysisJob.id)
    )
    arguments: list[AgentArgument] = []
    decisions: list[AdjudicationDecision] = []
    if latest_job is not None:
        raw_args = (
            await session.scalars(
                select(AgentArgument).where(AgentArgument.job_id == latest_job.id).order_by(AgentArgument.created_at, AgentArgument.id)
            )
        ).all()
        arguments = [item for item in raw_args if item.claim_id in claim_map]
        raw_decisions = (
            await session.scalars(
                select(AdjudicationDecision)
                .where(AdjudicationDecision.job_id == latest_job.id)
                .order_by(AdjudicationDecision.created_at, AdjudicationDecision.id)
            )
        ).all()
        decisions = [item for item in raw_decisions if item.claim_id in claim_map]

    latest_gap_analysis = await session.scalar(
        select(ResearchGapAnalysis)
        .where(ResearchGapAnalysis.investigation_id == investigation.id)
        .order_by(desc(ResearchGapAnalysis.version_number), ResearchGapAnalysis.id)
    )
    gaps: list[ResearchGap] = []
    if latest_gap_analysis is not None:
        gaps = list(
            (
                await session.scalars(
                    select(ResearchGap)
                    .where(ResearchGap.analysis_id == latest_gap_analysis.id)
                    .order_by(ResearchGap.research_priority.desc(), ResearchGap.id)
                )
            ).all()
        )

    hypotheses = list(
        (
            await session.scalars(
                select(ResearchHypothesis)
                .where(ResearchHypothesis.investigation_id == investigation.id)
                .order_by(desc(ResearchHypothesis.testability_score), ResearchHypothesis.id)
            )
        ).all()
    )

    contradictions = list(
        (
            await session.scalars(
                select(ResearchContradiction)
                .where(
                    (ResearchContradiction.primary_investigation_id == investigation.id)
                    | (ResearchContradiction.secondary_investigation_id == investigation.id)
                )
                .order_by(desc(ResearchContradiction.created_at), ResearchContradiction.id)
            )
        ).all()
    )

    workflows = list(
        (
            await session.scalars(
                select(AutonomousResearchWorkflow)
                .where(AutonomousResearchWorkflow.investigation_id == investigation.id)
                .order_by(desc(AutonomousResearchWorkflow.created_at), AutonomousResearchWorkflow.id)
            )
        ).all()
    )
    workflow_ids = [w.id for w in workflows]
    workflow_cycles = []
    actions = []
    if workflow_ids:
        workflow_cycles = list(
            (
                await session.scalars(
                    select(ResearchWorkflowCycle)
                    .where(ResearchWorkflowCycle.workflow_id.in_(workflow_ids))
                    .order_by(ResearchWorkflowCycle.cycle_number, ResearchWorkflowCycle.id)
                )
            ).all()
        )
        cycle_ids = [c.id for c in workflow_cycles]
        if cycle_ids:
            actions = list(
                (
                    await session.scalars(
                        select(ResearchAction)
                        .where(ResearchAction.cycle_id.in_(cycle_ids))
                        .order_by(ResearchAction.priority.desc(), ResearchAction.created_at)
                    )
                ).all()
            )

    total_counts = GraphTotalCounts(
        claims=len(claims),
        evidence=len(all_evidence),
        documents=len(documents),
        sources=len(sources),
        arguments=len(arguments),
        decisions=len(decisions),
        research_gaps=len(gaps),
        hypotheses=len(hypotheses),
        contradictions=len(contradictions),
        workflows=len(workflows),
        cycles=len(workflow_cycles),
        actions=len(actions),
    )

    # Index investigation relationships strictly from persisted FKs & junction tables.
    ev_by_claim: dict[uuid.UUID, list[tuple[Evidence, str, str]]] = defaultdict(list)
    seen_claim_ev_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for rel in claim_evidence_rels:
        ev = evidence_map.get(rel.evidence_id)
        if ev is not None and (rel.claim_id, rel.evidence_id) not in seen_claim_ev_pairs:
            ev_by_claim[rel.claim_id].append((ev, rel.relationship_type, rel.explanation))
            seen_claim_ev_pairs.add((rel.claim_id, rel.evidence_id))
    for ev in all_evidence:
        if ev.claim_id is not None and ev.claim_id in claim_map and (ev.claim_id, ev.id) not in seen_claim_ev_pairs:
            ev_by_claim[ev.claim_id].append((ev, ev.evidence_type, "Directly linked during evidence extraction."))
            seen_claim_ev_pairs.add((ev.claim_id, ev.id))

    claims_by_ev: dict[uuid.UUID, list[dict[str, str]]] = defaultdict(list)
    for cl_id, pairs in ev_by_claim.items():
        cl = claim_map[cl_id]
        for ev, rel_type, _ in pairs:
            claims_by_ev[ev.id].append({"claim_id": str(cl.id), "text": cl.text, "status": cl.status, "type": rel_type})

    args_by_claim: dict[uuid.UUID, list[AgentArgument]] = defaultdict(list)
    for arg in arguments:
        args_by_claim[arg.claim_id].append(arg)

    decision_by_claim: dict[uuid.UUID, AdjudicationDecision] = {}
    for dec in decisions:
        decision_by_claim.setdefault(dec.claim_id, dec)

    docs_by_source: dict[uuid.UUID, list[Document]] = defaultdict(list)
    for doc in documents:
        docs_by_source[doc.source_id].append(doc)

    oa_by_source: dict[uuid.UUID, list[OpenAccessLocation]] = defaultdict(list)
    for loc in oa_locations:
        oa_by_source[loc.source_id].append(loc)

    ev_by_source: dict[uuid.UUID, list[Evidence]] = defaultdict(list)
    ev_by_doc: dict[uuid.UUID, list[Evidence]] = defaultdict(list)
    for ev in all_evidence:
        ev_by_source[ev.source_id].append(ev)
        if ev.document_id is not None and ev.document_id in document_map:
            ev_by_doc[ev.document_id].append(ev)

    # Bounded selection / progressive expansion slice
    selected_claims: list[Claim]
    selected_evidence_ids: set[uuid.UUID] = set()
    selected_doc_ids: set[uuid.UUID] = set()
    selected_source_ids: set[uuid.UUID] = set()
    selected_arg_ids: set[uuid.UUID] = set()
    selected_dec_ids: set[uuid.UUID] = set()

    if expand_all:
        selected_claims = claims
        selected_evidence_ids = set(evidence_map)
        selected_doc_ids = set(document_map)
        selected_source_ids = set(source_map)
        selected_arg_ids = {item.id for item in arguments}
        selected_dec_ids = {item.id for item in decisions}
    elif focus is not None:
        focus_type, focus_uuid = focus
        if focus_type == GraphNodeType.claim.value and focus_uuid in claim_map:
            selected_claims = [claim_map[focus_uuid]]
            for ev, _, _ in ev_by_claim.get(focus_uuid, []):
                selected_evidence_ids.add(ev.id)
                selected_source_ids.add(ev.source_id)
                if ev.document_id and ev.document_id in document_map:
                    selected_doc_ids.add(ev.document_id)
            for arg in args_by_claim.get(focus_uuid, []):
                selected_arg_ids.add(arg.id)
            if focus_uuid in decision_by_claim:
                selected_dec_ids.add(decision_by_claim[focus_uuid].id)
        elif focus_type == GraphNodeType.source.value and focus_uuid in source_map:
            selected_claims = []
            selected_source_ids.add(focus_uuid)
            for doc in docs_by_source.get(focus_uuid, []):
                selected_doc_ids.add(doc.id)
            for ev in ev_by_source.get(focus_uuid, []):
                selected_evidence_ids.add(ev.id)
                for cl_info in claims_by_ev.get(ev.id, []):
                    cl_uuid = uuid.UUID(cl_info["claim_id"])
                    if cl_uuid in claim_map and claim_map[cl_uuid] not in selected_claims:
                        selected_claims.append(claim_map[cl_uuid])
        elif focus_type == GraphNodeType.document.value and focus_uuid in document_map:
            doc = document_map[focus_uuid]
            selected_claims = []
            selected_doc_ids.add(doc.id)
            selected_source_ids.add(doc.source_id)
            for ev in ev_by_doc.get(doc.id, []):
                selected_evidence_ids.add(ev.id)
                for cl_info in claims_by_ev.get(ev.id, []):
                    cl_uuid = uuid.UUID(cl_info["claim_id"])
                    if cl_uuid in claim_map and claim_map[cl_uuid] not in selected_claims:
                        selected_claims.append(claim_map[cl_uuid])
        elif focus_type == GraphNodeType.evidence.value and focus_uuid in evidence_map:
            ev = evidence_map[focus_uuid]
            selected_claims = []
            selected_evidence_ids.add(ev.id)
            selected_source_ids.add(ev.source_id)
            if ev.document_id and ev.document_id in document_map:
                selected_doc_ids.add(ev.document_id)
            for cl_info in claims_by_ev.get(ev.id, []):
                cl_uuid = uuid.UUID(cl_info["claim_id"])
                if cl_uuid in claim_map and claim_map[cl_uuid] not in selected_claims:
                    selected_claims.append(claim_map[cl_uuid])
            for arg in arguments:
                raw_ev_ids = _safe_json_loads(arg.evidence_ids_json, [])
                if str(ev.id) in raw_ev_ids:
                    selected_arg_ids.add(arg.id)
        else:
            selected_claims = claims[offset_claims : offset_claims + claim_limit]
    else:
        selected_claims = claims[offset_claims : offset_claims + claim_limit]
        for cl in selected_claims:
            for ev, _, _ in ev_by_claim.get(cl.id, []):
                if len(selected_evidence_ids) >= evidence_limit:
                    break
                selected_evidence_ids.add(ev.id)
            for arg in args_by_claim.get(cl.id, []):
                selected_arg_ids.add(arg.id)
            if cl.id in decision_by_claim:
                selected_dec_ids.add(decision_by_claim[cl.id].id)
        # Include top unlinked/orphaned evidence & sources up to bounded limits so empty-claim or unlinked research shows cleanly
        for ev in all_evidence:
            if len(selected_evidence_ids) >= evidence_limit:
                break
            selected_evidence_ids.add(ev.id)
        for ev_id in selected_evidence_ids:
            ev = evidence_map[ev_id]
            selected_source_ids.add(ev.source_id)
            if ev.document_id is not None and ev.document_id in document_map:
                selected_doc_ids.add(ev.document_id)
        if not selected_evidence_ids:
            for src in sources[:20]:
                selected_source_ids.add(src.id)
                for doc in docs_by_source.get(src.id, []):
                    selected_doc_ids.add(doc.id)

    # Ensure every selected entity's immediate target dependencies stay bounded by max_nodes
    nodes_by_id: dict[str, GraphNodeView] = {}

    def add_node(node: GraphNodeView) -> bool:
        if node.id in nodes_by_id:
            return True
        if len(nodes_by_id) >= max_nodes:
            return False
        nodes_by_id[node.id] = node
        return True

    inv_node_id = f"{GraphNodeType.investigation.value}:{investigation.id}"
    rq_node_id = f"{GraphNodeType.research_question.value}:{investigation.id}"

    add_node(
        GraphNodeView(
            id=inv_node_id,
            entity_id=investigation.id,
            type=GraphNodeType.investigation,
            label=f"Investigation ({investigation.mode})",
            description=investigation.quality_summary or f"{investigation.relevant_source_count} relevant sources · {investigation.full_text_count} full-text docs",
            investigation_id=investigation.id,
            status=investigation.status,
            has_hidden_neighbors=len(selected_claims) < len(claims),
            metadata={
                "mode": investigation.mode,
                "quality_status": investigation.quality_status,
                "quality_summary": investigation.quality_summary,
                "timeframe": investigation.timeframe,
                "relevant_source_count": investigation.relevant_source_count,
                "full_text_count": investigation.full_text_count,
                "evidence_gap": investigation.evidence_gap,
                "created_at": investigation.created_at.isoformat() if investigation.created_at else None,
            },
        )
    )
    add_node(
        GraphNodeView(
            id=rq_node_id,
            entity_id=investigation.id,
            type=GraphNodeType.research_question,
            label=_truncate_label(investigation.question, 92),
            description=investigation.question,
            investigation_id=investigation.id,
            status=investigation.quality_status,
            has_hidden_neighbors=len(selected_claims) < len(claims),
            metadata={
                "question": investigation.question,
                "mode": investigation.mode,
                "timeframe": investigation.timeframe,
                "quality_status": investigation.quality_status,
                "query_count": query_count,
            },
        )
    )

    for cl in selected_claims:
        ev_pairs = ev_by_claim.get(cl.id, [])
        supporting_ev = [
            {"id": str(ev.id), "text": ev.exact_text, "relevance_score": ev.relevance_score, "source_id": str(ev.source_id)}
            for ev, rel_type, _ in ev_pairs
            if rel_type == "supporting" or ev.evidence_type == "supporting"
        ]
        contradicting_ev = [
            {"id": str(ev.id), "text": ev.exact_text, "relevance_score": ev.relevance_score, "source_id": str(ev.source_id)}
            for ev, rel_type, _ in ev_pairs
            if rel_type == "contradicting" or ev.evidence_type == "contradicting"
        ]
        cl_args = args_by_claim.get(cl.id, [])
        cl_dec = decision_by_claim.get(cl.id)
        missing_prov: list[str] = []
        if not ev_pairs:
            missing_prov.append("no_persisted_evidence")
        if not cl_args:
            missing_prov.append("no_agent_arguments")
        if cl_dec is None:
            missing_prov.append("no_adjudication_decision")

        hidden_ev = any(ev.id not in selected_evidence_ids for ev, _, _ in ev_pairs)
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.claim.value}:{cl.id}",
                entity_id=cl.id,
                type=GraphNodeType.claim,
                label=_truncate_label(cl.text, 88),
                description=cl.text,
                investigation_id=investigation.id,
                status=cl.status,
                missing_provenance=missing_prov,
                has_hidden_neighbors=hidden_ev,
                metadata={
                    "claim_id": str(cl.id),
                    "full_text": cl.text,
                    "explanation": cl.explanation,
                    "priority": cl.priority,
                    "search_objectives": _safe_json_loads(cl.search_objectives_json, []),
                    "evidence_categories": _safe_json_loads(cl.evidence_categories_json, []),
                    "supporting_evidence": supporting_ev,
                    "contradicting_evidence": contradicting_ev,
                    "related_arguments": [
                        {
                            "id": str(arg.id),
                            "agent_identifier": arg.agent_identifier,
                            "argument_type": arg.argument_type,
                            "confidence_level": arg.confidence_level,
                            "text": arg.text,
                        }
                        for arg in cl_args
                    ],
                    "adjudication_decision": (
                        {
                            "id": str(cl_dec.id),
                            "decision": cl_dec.decision,
                            "explanation": cl_dec.explanation,
                            "unresolved_disagreements": _safe_json_loads(cl_dec.unresolved_disagreements_json, []),
                        }
                        if cl_dec
                        else None
                    ),
                },
            )
        )

    for ev_id in sorted(selected_evidence_ids, key=lambda item: (-evidence_map[item].relevance_score, str(item))):
        ev = evidence_map[ev_id]
        doc = document_map.get(ev.document_id) if ev.document_id else None
        src = source_map.get(ev.source_id)
        missing_prov = []
        if doc is None:
            missing_prov.append("missing_document")
        if not claims_by_ev.get(ev.id):
            missing_prov.append("missing_claim_link")
        if ev.page_number is None:
            missing_prov.append("missing_page_number")

        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.evidence.value}:{ev.id}",
                entity_id=ev.id,
                type=GraphNodeType.evidence,
                label=_truncate_label(ev.exact_text, 82),
                description=ev.exact_text,
                investigation_id=investigation.id,
                status=ev.evidence_type,
                missing_provenance=missing_prov,
                has_hidden_neighbors=False,
                metadata={
                    "evidence_id": str(ev.id),
                    "exact_text": ev.exact_text,
                    "surrounding_context": ev.surrounding_context,
                    "evidence_type": ev.evidence_type,
                    "relevance_score": ev.relevance_score,
                    "relevance_reason": ev.relevance_reason,
                    "extraction_method": ev.extraction_method,
                    "page_number": ev.page_number,
                    "section_name": ev.section_name,
                    "traceable": ev.traceable,
                    "associated_claims": claims_by_ev.get(ev.id, []),
                    "document_id": str(doc.id) if doc else None,
                    "document_title": doc.title if doc else None,
                    "document_access_level": doc.access_level if doc else None,
                    "source_id": str(src.id) if src else str(ev.source_id),
                    "source_title": src.title if src else None,
                    "source_url": src.original_url if src else None,
                },
            )
        )

    for doc_id in sorted(selected_doc_ids, key=str):
        doc = document_map[doc_id]
        src = source_map.get(doc.source_id)
        doc_ev = ev_by_doc.get(doc.id, [])
        hidden_ev = any(item.id not in selected_evidence_ids for item in doc_ev)
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.document.value}:{doc.id}",
                entity_id=doc.id,
                type=GraphNodeType.document,
                label=_truncate_label(doc.title or f"{doc.version_type} ({doc.access_level})", 80),
                description=(
                    f"{doc.content_type} · {doc.access_level.replace('_', ' ')} · "
                    f"{doc.extraction_quality} quality"
                    + (f" · {doc.page_count} page(s)" if doc.page_count else "")
                ),
                investigation_id=investigation.id,
                status=doc.access_level,
                missing_provenance=["missing_page_count"] if doc.page_count is None else [],
                has_hidden_neighbors=hidden_ev,
                metadata={
                    "document_id": str(doc.id),
                    "source_id": str(doc.source_id),
                    "source_title": src.title if src else None,
                    "title": doc.title,
                    "content_type": doc.content_type,
                    "access_level": doc.access_level,
                    "extraction_quality": doc.extraction_quality,
                    "document_url": doc.document_url,
                    "version_type": doc.version_type,
                    "access_route": doc.access_route,
                    "metadata_match_status": doc.metadata_match_status,
                    "page_count": doc.page_count,
                    "headings": _safe_json_loads(doc.headings_json, [])[:20],
                    "evidence_count": len(doc_ev),
                },
            )
        )

    for src_id in sorted(selected_source_ids, key=str):
        src = source_map[src_id]
        src_docs = docs_by_source.get(src.id, [])
        src_oas = oa_by_source.get(src.id, [])
        src_ev = ev_by_source.get(src.id, [])
        hidden_neighbors = any(doc.id not in selected_doc_ids for doc in src_docs) or any(
            item.id not in selected_evidence_ids for item in src_ev
        )
        versions: list[dict[str, Any]] = [
            {
                "document_id": str(doc.id),
                "version_type": doc.version_type,
                "access_level": doc.access_level,
                "access_route": doc.access_route,
                "document_url": doc.document_url,
            }
            for doc in src_docs
        ]
        for loc in src_oas:
            versions.append(
                {
                    "oa_location_id": str(loc.id),
                    "version_type": loc.version_type,
                    "repository": loc.repository,
                    "match_status": loc.match_status,
                    "acquisition_status": loc.acquisition_status,
                    "url": loc.url,
                }
            )
        missing_prov = ["missing_retrieved_document"] if not src_docs else []
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.source.value}:{src.id}",
                entity_id=src.id,
                type=GraphNodeType.source,
                label=_truncate_label(src.title, 84),
                description=f"{src.publisher or src.source_type} · {src.publication_date or 'date n/a'} · {src.inclusion_status}",
                investigation_id=investigation.id,
                status=src.inclusion_status,
                missing_provenance=missing_prov,
                has_hidden_neighbors=hidden_neighbors,
                metadata={
                    "source_id": str(src.id),
                    "title": src.title,
                    "authors": _safe_json_loads(src.authors_json, []),
                    "doi": src.doi,
                    "publication_date": src.publication_date,
                    "publisher": src.publisher,
                    "source_type": src.source_type,
                    "original_url": src.original_url,
                    "canonical_url": src.canonical_url,
                    "relevance_score": src.relevance_score,
                    "inclusion_status": src.inclusion_status,
                    "rejection_reason": src.rejection_reason,
                    "open_access_status": src.open_access_status,
                    "selected_document_url": src.selected_document_url,
                    "document_versions": versions,
                    "related_evidence": [
                        {"id": str(item.id), "exact_text": _truncate_label(item.exact_text, 140), "evidence_type": item.evidence_type}
                        for item in src_ev[:15]
                    ],
                    "evidence_count": len(src_ev),
                },
            )
        )

    arg_map = {item.id: item for item in arguments}
    for arg_id in sorted(selected_arg_ids, key=str):
        arg = arg_map[arg_id]
        cited_ev = [item for item in _safe_json_loads(arg.evidence_ids_json, []) if item in {str(e) for e in evidence_map}]
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.agent_argument.value}:{arg.id}",
                entity_id=arg.id,
                type=GraphNodeType.agent_argument,
                label=_truncate_label(f"{arg.agent_identifier.replace('_', ' ').title()}: {arg.argument_type.replace('_', ' ')}", 82),
                description=_truncate_label(arg.text, 260),
                investigation_id=investigation.id,
                status=arg.confidence_level,
                missing_provenance=["no_cited_evidence"] if not cited_ev else [],
                has_hidden_neighbors=any(uuid.UUID(eid) not in selected_evidence_ids for eid in cited_ev),
                metadata={
                    "argument_id": str(arg.id),
                    "claim_id": str(arg.claim_id),
                    "agent_identifier": arg.agent_identifier,
                    "argument_type": arg.argument_type,
                    "text": arg.text,
                    "evidence_basis": arg.evidence_basis,
                    "reasoning_summary": arg.reasoning_summary,
                    "limitations": _safe_json_loads(arg.limitations_json, []),
                    "confidence_level": arg.confidence_level,
                    "confidence_explanation": arg.confidence_explanation,
                    "evidence_ids": cited_ev,
                },
            )
        )

    dec_map = {item.id: item for item in decisions}
    for dec_id in sorted(selected_dec_ids, key=str):
        dec = dec_map[dec_id]
        cited_ev = [item for item in _safe_json_loads(dec.evidence_ids_json, []) if item in {str(e) for e in evidence_map}]
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.adjudication_decision.value}:{dec.id}",
                entity_id=dec.id,
                type=GraphNodeType.adjudication_decision,
                label=f"Decision: {dec.decision.replace('_', ' ')}",
                description=_truncate_label(dec.explanation, 260),
                investigation_id=investigation.id,
                status=dec.decision,
                missing_provenance=["no_cited_evidence"] if not cited_ev else [],
                metadata={
                    "decision_id": str(dec.id),
                    "claim_id": str(dec.claim_id),
                    "decision": dec.decision,
                    "explanation": dec.explanation,
                    "supporting_argument_ids": _safe_json_loads(dec.supporting_argument_ids_json, []),
                    "evidence_ids": cited_ev,
                    "unresolved_disagreements": _safe_json_loads(dec.unresolved_disagreements_json, []),
                },
            )
        )

    for gap in gaps:
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.research_gap.value}:{gap.id}",
                entity_id=gap.id,
                type=GraphNodeType.research_gap,
                label=_truncate_label(gap.title, 84),
                description=f"{gap.category.replace('_', ' ')} · {gap.severity} · priority {gap.research_priority}",
                investigation_id=investigation.id,
                status=gap.severity,
                missing_provenance=[],
                has_hidden_neighbors=False,
                metadata={
                    "gap_id": str(gap.id),
                    "category": gap.category,
                    "gap_type": gap.gap_type,
                    "severity": gap.severity,
                    "priority": gap.research_priority,
                    "confidence": gap.confidence,
                    "missing_information": gap.missing_information,
                    "explanation": gap.supporting_explanation,
                    "recommended_action": _safe_json_loads(gap.recommended_action_json, {}),
                },
            )
        )

    for hyp in hypotheses:
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.hypothesis.value}:{hyp.id}",
                entity_id=hyp.id,
                type=GraphNodeType.hypothesis,
                label=_truncate_label(hyp.title, 84),
                description=f"{hyp.category} · testability {hyp.testability_score:.1f} · {hyp.status}",
                investigation_id=investigation.id,
                status=hyp.status,
                missing_provenance=[],
                has_hidden_neighbors=False,
                metadata={
                    "hypothesis_id": str(hyp.id),
                    "statement": hyp.statement,
                    "category": hyp.category,
                    "status": hyp.status,
                    "falsification_criteria": hyp.falsification_criteria,
                    "testability_score": hyp.testability_score,
                    "falsifiability_score": hyp.falsifiability_score,
                    "novelty_score": hyp.novelty_score,
                    "evidence_grounding_score": hyp.evidence_grounding_score,
                    "generation_method": hyp.generation_method,
                },
            )
        )

    for contra in contradictions:
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.contradiction.value}:{contra.id}",
                entity_id=contra.id,
                type=GraphNodeType.contradiction,
                label=_truncate_label(contra.title, 84),
                description=f"{contra.category} · {contra.severity} severity · {contra.status}",
                investigation_id=investigation.id,
                status=contra.status,
                missing_provenance=[],
                has_hidden_neighbors=False,
                metadata={
                    "contradiction_id": str(contra.id),
                    "category": contra.category,
                    "severity": contra.severity,
                    "status": contra.status,
                    "description": contra.description,
                    "scope_differences": contra.scope_differences,
                    "methodological_differences": contra.methodological_differences,
                    "resolution_explanation": contra.resolution_explanation,
                },
            )
        )

    for wf in workflows:
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.autonomous_workflow.value}:{wf.id}",
                entity_id=wf.id,
                type=GraphNodeType.autonomous_workflow,
                label=_truncate_label(f"Workflow: {wf.title}", 84),
                description=f"{wf.autonomy_mode.title()} · Cycle {wf.current_cycle_number}/{wf.budget_max_cycles} · {wf.status}",
                investigation_id=investigation.id,
                status=wf.status,
                missing_provenance=[],
                has_hidden_neighbors=False,
                metadata={
                    "workflow_id": str(wf.id),
                    "title": wf.title,
                    "autonomy_mode": wf.autonomy_mode,
                    "current_cycle_number": wf.current_cycle_number,
                    "max_cycles": wf.budget_max_cycles,
                    "status": wf.status,
                    "research_objective": wf.research_objective,
                    "stopping_reason": wf.stopping_reason,
                    "total_sources_acquired": wf.spent_sources,
                    "total_evidence_acquired": 0,
                },
            )
        )

    for cyc in workflow_cycles:
        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.research_cycle.value}:{cyc.id}",
                entity_id=cyc.id,
                type=GraphNodeType.research_cycle,
                label=f"Cycle {cyc.cycle_number}: {cyc.status}",
                description=f"Gain: {cyc.information_gain_score:.2f} · Sources: +{cyc.sources_acquired} · Ev: +{cyc.evidence_acquired}",
                investigation_id=investigation.id,
                status=cyc.status,
                missing_provenance=[],
                has_hidden_neighbors=False,
                metadata={
                    "cycle_id": str(cyc.id),
                    "workflow_id": str(cyc.workflow_id),
                    "cycle_number": cyc.cycle_number,
                    "state": cyc.status,
                    "information_gain_score": cyc.information_gain_score,
                    "cycle_goal": cyc.cycle_goal,
                },
            )
        )

    for act in actions:
        target_p = None
        first_q = None
        try:
            p_list = _safe_json_loads(act.target_providers_json, [])
            if p_list:
                target_p = p_list[0]
        except Exception:
            pass
        try:
            q_list = _safe_json_loads(act.search_queries_json, [])
            if q_list:
                first_q = q_list[0]
        except Exception:
            pass

        add_node(
            GraphNodeView(
                id=f"{GraphNodeType.research_action.value}:{act.id}",
                entity_id=act.id,
                type=GraphNodeType.research_action,
                label=_truncate_label(f"Action: {act.action_type.replace('_', ' ')}", 84),
                description=f"Priority {act.priority} · {act.status} · {target_p or 'internal'}",
                investigation_id=investigation.id,
                status=act.status,
                missing_provenance=[],
                has_hidden_neighbors=False,
                metadata={
                    "action_id": str(act.id),
                    "cycle_id": str(act.cycle_id),
                    "action_type": act.action_type,
                    "priority": act.priority,
                    "status": act.status,
                    "target_entity_type": act.target_entity_type,
                    "target_entity_id": str(act.target_entity_id) if act.target_entity_id else None,
                    "target_provider": target_p,
                    "planned_query": first_q,
                },
            )
        )

    # Emit only persisted relationships whose source & target both exist in nodes_by_id; deduplicate safely.
    edges_by_key: dict[tuple[str, str, str], GraphEdgeView] = {}

    def add_edge(
        src_node: str,
        tgt_node: str,
        rel_type: str,
        label: str,
        *,
        classification: str | None = None,
        explanation: str | None = None,
    ) -> None:
        if src_node not in nodes_by_id or tgt_node not in nodes_by_id:
            return
        key = (src_node, tgt_node, rel_type)
        if key in edges_by_key:
            return
        edges_by_key[key] = GraphEdgeView(
            id=f"{src_node}->{tgt_node}:{rel_type}",
            source=src_node,
            target=tgt_node,
            relationship_type=rel_type,
            label=label,
            classification=classification,
            explanation=explanation,
        )

    add_edge(inv_node_id, rq_node_id, "poses_question", "poses question")
    for cl in selected_claims:
        cl_node = f"{GraphNodeType.claim.value}:{cl.id}"
        if rq_node_id in nodes_by_id:
            add_edge(rq_node_id, cl_node, "decomposes_to", "decomposes into")
        else:
            add_edge(inv_node_id, cl_node, "contains_claim", "contains claim")

        for ev, rel_type, explanation in ev_by_claim.get(cl.id, []):
            ev_node = f"{GraphNodeType.evidence.value}:{ev.id}"
            canonical_rel, edge_label = _map_evidence_relationship(rel_type)
            add_edge(
                cl_node,
                ev_node,
                canonical_rel,
                edge_label,
                classification=rel_type,
                explanation=explanation,
            )

    for ev_id in selected_evidence_ids:
        ev = evidence_map[ev_id]
        ev_node = f"{GraphNodeType.evidence.value}:{ev.id}"
        src_node = f"{GraphNodeType.source.value}:{ev.source_id}"
        if ev.document_id is not None and ev.document_id in document_map:
            doc_node = f"{GraphNodeType.document.value}:{ev.document_id}"
            add_edge(ev_node, doc_node, "evidenced_in", "from document")
        else:
            add_edge(
                ev_node,
                src_node,
                "extracted_from_source",
                "direct source link (no document)",
                explanation="Document record missing; linked directly via persisted source_id.",
            )

    for doc_id in selected_doc_ids:
        doc = document_map[doc_id]
        add_edge(
            f"{GraphNodeType.document.value}:{doc.id}",
            f"{GraphNodeType.source.value}:{doc.source_id}",
            "published_by",
            "source publication",
        )

    for rel in doc_version_rels:
        add_edge(
            f"{GraphNodeType.document.value}:{rel.document_id}",
            f"{GraphNodeType.document.value}:{rel.related_document_id}",
            "document_version",
            rel.relationship_type.replace("_", " "),
            classification=rel.relationship_type,
        )

    for arg_id in selected_arg_ids:
        arg = arg_map[arg_id]
        arg_node = f"{GraphNodeType.agent_argument.value}:{arg.id}"
        cl_node = f"{GraphNodeType.claim.value}:{arg.claim_id}"
        canonical_rel, edge_label = _map_argument_relationship(arg.argument_type)
        add_edge(
            cl_node,
            arg_node,
            canonical_rel,
            edge_label,
            classification=arg.argument_type,
            explanation=arg.reasoning_summary,
        )
        for raw_ev_id in _safe_json_loads(arg.evidence_ids_json, []):
            try:
                ev_uuid = uuid.UUID(str(raw_ev_id))
            except ValueError:
                continue
            if ev_uuid in evidence_map:
                add_edge(arg_node, f"{GraphNodeType.evidence.value}:{ev_uuid}", "cites_evidence", "cites evidence")

    for dec_id in selected_dec_ids:
        dec = dec_map[dec_id]
        dec_node = f"{GraphNodeType.adjudication_decision.value}:{dec.id}"
        add_edge(
            f"{GraphNodeType.claim.value}:{dec.claim_id}",
            dec_node,
            "adjudicated_by",
            f"adjudication: {dec.decision.replace('_', ' ')}",
            classification=dec.decision,
            explanation=dec.explanation,
        )
        for raw_arg_id in _safe_json_loads(dec.supporting_argument_ids_json, []):
            try:
                arg_uuid = uuid.UUID(str(raw_arg_id))
            except ValueError:
                continue
            if arg_uuid in arg_map:
                add_edge(
                    dec_node,
                    f"{GraphNodeType.agent_argument.value}:{arg_uuid}",
                    "weighs_argument",
                    "weighs argument",
                )

    for gap in gaps:
        gap_node = f"{GraphNodeType.research_gap.value}:{gap.id}"
        claim_ids = _safe_json_loads(gap.claim_ids_json, [])
        for cid in claim_ids:
            try:
                c_uuid = uuid.UUID(str(cid))
            except ValueError:
                continue
            if c_uuid in claim_map:
                add_edge(
                    f"{GraphNodeType.claim.value}:{c_uuid}",
                    gap_node,
                    "has_gap",
                    f"gap: {gap.gap_type.replace('_', ' ')}",
                    classification=gap.severity,
                    explanation=gap.description,
                )
        add_edge(
            gap_node,
            inv_node_id,
            "affects",
            "affects investigation",
            classification=gap.severity,
            explanation=gap.description,
        )

    for hyp in hypotheses:
        hyp_node = f"{GraphNodeType.hypothesis.value}:{hyp.id}"
        # Edge to investigation
        add_edge(hyp_node, inv_node_id, "hypothesizes_for", "hypothesizes for", classification=hyp.status)
        # Edge to claims
        claim_ids = _safe_json_loads(hyp.claim_ids_json, [])
        for cid in claim_ids:
            try:
                c_uuid = uuid.UUID(str(cid))
                if c_uuid in claim_map:
                    add_edge(hyp_node, f"{GraphNodeType.claim.value}:{c_uuid}", "hypothesizes", "hypothesizes", classification=hyp.category)
            except ValueError:
                pass
        # Supporting evidence edges
        for eid in _safe_json_loads(hyp.supporting_evidence_ids_json, []):
            try:
                e_uuid = uuid.UUID(str(eid))
                if e_uuid in evidence_map:
                    add_edge(f"{GraphNodeType.evidence.value}:{e_uuid}", hyp_node, "supports_hypothesis", "supports hypothesis", classification="supporting")
            except ValueError:
                pass
        # Challenging evidence edges
        for eid in _safe_json_loads(hyp.challenging_evidence_ids_json, []):
            try:
                e_uuid = uuid.UUID(str(eid))
                if e_uuid in evidence_map:
                    add_edge(f"{GraphNodeType.evidence.value}:{e_uuid}", hyp_node, "challenges", "challenges hypothesis", classification="contradicting")
            except ValueError:
                pass

    for contra in contradictions:
        contra_node = f"{GraphNodeType.contradiction.value}:{contra.id}"
        add_edge(contra_node, inv_node_id, "observed_in", "observed in", classification=contra.severity)
        # Claims
        for cid in _safe_json_loads(contra.claim_ids_json, []):
            try:
                c_uuid = uuid.UUID(str(cid))
                if c_uuid in claim_map:
                    add_edge(contra_node, f"{GraphNodeType.claim.value}:{c_uuid}", "contradicts", "contradicts claim", classification=contra.severity)
            except ValueError:
                pass
        # Evidence
        for eid in _safe_json_loads(contra.evidence_ids_json, []):
            try:
                e_uuid = uuid.UUID(str(eid))
                if e_uuid in evidence_map:
                    add_edge(contra_node, f"{GraphNodeType.evidence.value}:{e_uuid}", "conflicts_with", "conflicts with evidence", classification=contra.severity)
            except ValueError:
                pass

    for wf in workflows:
        add_edge(
            f"{GraphNodeType.autonomous_workflow.value}:{wf.id}",
            inv_node_id,
            "investigates",
            "investigates",
            classification=wf.status,
        )

    for cyc in workflow_cycles:
        add_edge(
            f"{GraphNodeType.autonomous_workflow.value}:{cyc.workflow_id}",
            f"{GraphNodeType.research_cycle.value}:{cyc.id}",
            "executes_cycle",
            f"cycle {cyc.cycle_number}",
            classification=cyc.status,
        )

    gap_ids_set = {g.id for g in gaps}
    hyp_ids_set = {h.id for h in hypotheses}
    for act in actions:
        add_edge(
            f"{GraphNodeType.research_cycle.value}:{act.cycle_id}",
            f"{GraphNodeType.research_action.value}:{act.id}",
            "performs_action",
            act.action_type.replace("_", " "),
            classification=act.status,
        )
        if act.target_entity_id is not None:
            if act.target_entity_type == "claim" and act.target_entity_id in claim_map:
                add_edge(
                    f"{GraphNodeType.research_action.value}:{act.id}",
                    f"{GraphNodeType.claim.value}:{act.target_entity_id}",
                    "targets_claim",
                    "targets claim",
                    classification=act.status,
                )
            elif act.target_entity_type == "gap" and act.target_entity_id in gap_ids_set:
                add_edge(
                    f"{GraphNodeType.research_action.value}:{act.id}",
                    f"{GraphNodeType.research_gap.value}:{act.target_entity_id}",
                    "targets_gap",
                    "targets gap",
                    classification=act.status,
                )
            elif act.target_entity_type == "hypothesis" and act.target_entity_id in hyp_ids_set:
                add_edge(
                    f"{GraphNodeType.research_action.value}:{act.id}",
                    f"{GraphNodeType.hypothesis.value}:{act.target_entity_id}",
                    "targets_hypothesis",
                    "targets hypothesis",
                    classification=act.status,
                )

    # Direct Investigation -> Claim fallback edge if ResearchQuestion is filtered out by node_types filter
    if allowed_node_types and GraphNodeType.research_question.value not in allowed_node_types:
        for cl in selected_claims:
            add_edge(inv_node_id, f"{GraphNodeType.claim.value}:{cl.id}", "contains_claim", "contains claim")

    # Apply node_types, search q, and relationship_types filters consistently without orphan edges.
    filtered_nodes = list(nodes_by_id.values())
    if allowed_node_types:
        filtered_nodes = [node for node in filtered_nodes if node.type.value in allowed_node_types]
    if search_term:
        filtered_nodes = [
            node
            for node in filtered_nodes
            if search_term in node.label.casefold()
            or search_term in node.description.casefold()
            or search_term in node.status.casefold()
        ]

    valid_node_ids = {node.id for node in filtered_nodes}
    filtered_edges = [
        edge
        for edge in edges_by_key.values()
        if edge.source in valid_node_ids
        and edge.target in valid_node_ids
        and (not allowed_rel_types or edge.relationship_type in allowed_rel_types)
    ]

    node_type_counts: dict[str, int] = defaultdict(int)
    for node in filtered_nodes:
        node_type_counts[node.type.value] += 1

    rel_type_counts: dict[str, int] = defaultdict(int)
    for edge in filtered_edges:
        rel_type_counts[edge.relationship_type] += 1

    truncated = (
        len(selected_claims) < total_counts.claims
        or len(selected_evidence_ids) < total_counts.evidence
        or len(selected_source_ids) < total_counts.sources
        or len(selected_doc_ids) < total_counts.documents
    )

    empty_reason: str | None = None
    if not filtered_nodes:
        empty_reason = "No nodes matched the active filters."
    elif total_counts.claims == 0 and total_counts.evidence == 0 and total_counts.sources == 0:
        empty_reason = "This investigation has not persisted claims, sources, or evidence passages yet."

    return InvestigationGraphResponse(
        investigation_id=investigation.id,
        investigation_question=investigation.question,
        investigation_status=investigation.status,
        nodes=filtered_nodes,
        edges=filtered_edges,
        truncated=truncated,
        total_counts=total_counts,
        node_type_counts=dict(node_type_counts),
        relationship_type_counts=dict(rel_type_counts),
        empty_reason=empty_reason,
    )


@router.get("/research/graph", response_model=InvestigationGraphResponse)
async def read_workspace_graph(
    investigation_id: uuid.UUID | None = None,
    node_types: str | None = None,
    relationship_types: str | None = None,
    focus_node_id: str | None = None,
    q: str | None = None,
    claim_limit: int = Query(default=12, ge=1, le=100),
    offset_claims: int = Query(default=0, ge=0),
    evidence_limit: int = Query(default=40, ge=1, le=300),
    max_nodes: int = Query(default=160, ge=10, le=600),
    expand_all: bool = False,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvestigationGraphResponse:
    perm = PermissionService(session)
    if investigation_id is not None:
        investigation = await perm.check_investigation_access(user, investigation_id, "read")
    else:
        user_workspaces = await perm.get_user_workspaces(user.id)
        if not user_workspaces:
            user_workspaces = [DEFAULT_GLOBAL_WORKSPACE_ID]
        investigation = await session.scalar(
            select(Investigation)
            .where(Investigation.workspace_id.in_(user_workspaces))
            .order_by(desc(Investigation.created_at), Investigation.id)
        )
        if investigation is None:
            return InvestigationGraphResponse(
                nodes=[],
                edges=[],
                truncated=False,
                total_counts=GraphTotalCounts(),
                empty_reason="No research investigations have been created yet.",
            )

    return await _build_investigation_graph(
        session=session,
        investigation=investigation,
        node_types=node_types,
        relationship_types=relationship_types,
        focus_node_id=focus_node_id,
        q=q,
        claim_limit=claim_limit,
        offset_claims=offset_claims,
        evidence_limit=evidence_limit,
        max_nodes=max_nodes,
        expand_all=expand_all,
    )


@router.get("/research/investigations/{investigation_id}/graph", response_model=InvestigationGraphResponse)
async def read_investigation_graph(
    investigation_id: uuid.UUID,
    node_types: str | None = None,
    relationship_types: str | None = None,
    focus_node_id: str | None = None,
    q: str | None = None,
    claim_limit: int = Query(default=12, ge=1, le=100),
    offset_claims: int = Query(default=0, ge=0),
    evidence_limit: int = Query(default=40, ge=1, le=300),
    max_nodes: int = Query(default=160, ge=10, le=600),
    expand_all: bool = False,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvestigationGraphResponse:
    perm = PermissionService(session)
    investigation = await perm.check_investigation_access(user, investigation_id, "read")
    return await _build_investigation_graph(
        session=session,
        investigation=investigation,
        node_types=node_types,
        relationship_types=relationship_types,
        focus_node_id=focus_node_id,
        q=q,
        claim_limit=claim_limit,
        offset_claims=offset_claims,
        evidence_limit=evidence_limit,
        max_nodes=max_nodes,
        expand_all=expand_all,
    )
