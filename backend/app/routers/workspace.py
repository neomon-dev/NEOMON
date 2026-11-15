import json
import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, desc, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.definitions import AGENT_DEFINITIONS
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService, DEFAULT_GLOBAL_WORKSPACE_ID
from app.config import get_settings
from app.db import get_session
from app.errors import BackendError
from app.models import (
    AgentArgument,
    AnalysisAgentExecution,
    AnalysisJob,
    Claim,
    ClaimEvidenceRelationship,
    Document,
    Evidence,
    ExtractionExecution,
    Investigation,
    OpenAccessLocation,
    Source,
    User,
)
from app.schemas import (
    AgentExecutionObservatoryItem,
    AgentObservatoryResponse,
    AgentRosterSummary,
    EvidenceClaimLink,
    ObservatorySummary,
    OpenAccessLocationSummary,
    SourceDocumentSummary,
    WorkspaceEvidenceItem,
    WorkspaceEvidencePageResponse,
    WorkspaceSourceItem,
    WorkspaceSourcePageResponse,
)

router = APIRouter(tags=["workspace"])

_ACTIVE_JOB_STATUSES = {"queued", "planning", "researching", "debating", "adjudicating", "reporting"}


def _safe_json_loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return fallback


def _safe_float(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _duration_seconds(start: Any, end: Any) -> float | None:
    if start is None or end is None:
        return None
    s = start.replace(tzinfo=None) if getattr(start, "tzinfo", None) is not None else start
    e = end.replace(tzinfo=None) if getattr(end, "tzinfo", None) is not None else end
    return round(max(0.0, (e - s).total_seconds()), 3)


async def _ensure_investigation(
    session: AsyncSession, user: User, investigation_id: uuid.UUID | None
) -> None:
    if investigation_id is None:
        return
    perm = PermissionService(session)
    await perm.check_investigation_access(user, investigation_id, "read")


@router.get("/research/evidence", response_model=WorkspaceEvidencePageResponse)
async def list_workspace_evidence(
    investigation_id: uuid.UUID | None = None,
    source_id: uuid.UUID | None = None,
    claim_id: uuid.UUID | None = None,
    q: str | None = None,
    evidence_type: str | None = None,
    relationship_type: str | None = None,
    inclusion_status: str | None = None,
    traceable: bool | None = None,
    min_relevance: float | None = Query(default=None, ge=0.0, le=1.0),
    max_relevance: float | None = Query(default=None, ge=0.0, le=1.0),
    sort: str = Query(default="relevance_desc", pattern="^(relevance_desc|relevance_asc|recent_desc)$"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceEvidencePageResponse:
    await _ensure_investigation(session, user, investigation_id)
    perm = PermissionService(session)
    user_workspaces = await perm.get_user_workspaces(user.id)
    if not user_workspaces:
        return WorkspaceEvidencePageResponse(items=[], total=0, limit=limit, offset=offset)

    inv_scope = Investigation.workspace_id.in_(user_workspaces)
    if DEFAULT_GLOBAL_WORKSPACE_ID in user_workspaces:
        inv_scope = or_(inv_scope, Investigation.workspace_id.is_(None))

    conditions: list[Any] = []
    if investigation_id is not None:
        conditions.append(Source.investigation_id == investigation_id)
    else:
        conditions.append(Source.investigation_id.in_(select(Investigation.id).where(inv_scope)))
    if source_id is not None:
        conditions.append(Evidence.source_id == source_id)
    if claim_id is not None:
        conditions.append(
            or_(
                Evidence.claim_id == claim_id,
                exists(
                    select(ClaimEvidenceRelationship.id)
                    .join(Claim, ClaimEvidenceRelationship.claim_id == Claim.id)
                    .where(
                        ClaimEvidenceRelationship.evidence_id == Evidence.id,
                        ClaimEvidenceRelationship.claim_id == claim_id,
                        Claim.investigation_id == Source.investigation_id,
                    )
                ),
            )
        )
    if evidence_type:
        conditions.append(Evidence.evidence_type == evidence_type)
    if relationship_type:
        conditions.append(
            or_(
                Evidence.evidence_type == relationship_type,
                exists(
                    select(ClaimEvidenceRelationship.id)
                    .join(Claim, ClaimEvidenceRelationship.claim_id == Claim.id)
                    .where(
                        ClaimEvidenceRelationship.evidence_id == Evidence.id,
                        ClaimEvidenceRelationship.relationship_type == relationship_type,
                        Claim.investigation_id == Source.investigation_id,
                    )
                ),
            )
        )
    if inclusion_status:
        conditions.append(Source.inclusion_status == inclusion_status)
    if traceable is not None:
        conditions.append(Evidence.traceable.is_(traceable))
    if min_relevance is not None:
        conditions.append(Evidence.relevance_score >= min_relevance)
    if max_relevance is not None:
        conditions.append(Evidence.relevance_score <= max_relevance)

    search_term = q.strip() if q else ""
    if search_term:
        pattern = f"%{search_term.lower()}%"
        conditions.append(
            or_(
                func.lower(Evidence.exact_text).like(pattern),
                func.lower(func.coalesce(Evidence.surrounding_context, "")).like(pattern),
                func.lower(func.coalesce(Evidence.section_name, "")).like(pattern),
                func.lower(Source.title).like(pattern),
                func.lower(func.coalesce(Claim.text, "")).like(pattern),
                exists(
                    select(ClaimEvidenceRelationship.id)
                    .join(Claim, ClaimEvidenceRelationship.claim_id == Claim.id)
                    .where(
                        ClaimEvidenceRelationship.evidence_id == Evidence.id,
                        Claim.investigation_id == Source.investigation_id,
                        func.lower(Claim.text).like(pattern),
                    )
                ),
            )
        )

    count_stmt = (
        select(func.count(Evidence.id))
        .select_from(Evidence)
        .join(Source, Evidence.source_id == Source.id)
        .join(Investigation, Source.investigation_id == Investigation.id)
        .outerjoin(Claim, and_(Evidence.claim_id == Claim.id, Claim.investigation_id == Source.investigation_id))
    )
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = int((await session.scalar(count_stmt)) or 0)

    order_clauses = (
        (Evidence.relevance_score.asc(), Evidence.id)
        if sort == "relevance_asc"
        else (desc(func.coalesce(Evidence.retrieval_timestamp, Investigation.created_at)), Evidence.relevance_score.desc(), Evidence.id)
        if sort == "recent_desc"
        else (Evidence.relevance_score.desc(), Evidence.id)
    )

    query_stmt = (
        select(Evidence, Source, Investigation, Document, Claim)
        .select_from(Evidence)
        .join(Source, Evidence.source_id == Source.id)
        .join(Investigation, Source.investigation_id == Investigation.id)
        .outerjoin(Document, Evidence.document_id == Document.id)
        .outerjoin(Claim, and_(Evidence.claim_id == Claim.id, Claim.investigation_id == Source.investigation_id))
        .order_by(*order_clauses)
        .offset(offset)
        .limit(limit)
    )
    if conditions:
        query_stmt = query_stmt.where(*conditions)

    rows = (await session.execute(query_stmt)).all()
    evidence_ids = [ev.id for ev, _, _, _, _ in rows]

    links_by_evidence: dict[uuid.UUID, list[EvidenceClaimLink]] = defaultdict(list)
    if evidence_ids:
        link_rows = (
            await session.execute(
                select(ClaimEvidenceRelationship, Claim, Source.investigation_id)
                .join(Claim, ClaimEvidenceRelationship.claim_id == Claim.id)
                .join(Evidence, ClaimEvidenceRelationship.evidence_id == Evidence.id)
                .join(Source, Evidence.source_id == Source.id)
                .where(
                    ClaimEvidenceRelationship.evidence_id.in_(evidence_ids),
                    Claim.investigation_id == Source.investigation_id,
                )
            )
        ).all()
        for rel, linked_claim, _ in link_rows:
            links_by_evidence[rel.evidence_id].append(
                EvidenceClaimLink(
                    claim_id=linked_claim.id,
                    claim_text=linked_claim.text,
                    claim_status=linked_claim.status,
                    relationship_type=rel.relationship_type,
                    explanation=rel.explanation,
                )
            )

    items = [
        WorkspaceEvidenceItem(
            id=ev.id,
            investigation_id=inv.id,
            investigation_question=inv.question,
            source_id=src.id,
            source_title=src.title,
            source_type=src.source_type,
            source_url=src.original_url,
            source_canonical_url=src.canonical_url,
            source_publisher=src.publisher,
            source_publication_date=src.publication_date,
            source_inclusion_status=src.inclusion_status,
            source_rejection_reason=src.rejection_reason,
            source_open_access_status=src.open_access_status,
            document_id=doc.id if doc else ev.document_id,
            document_title=doc.title if doc else None,
            document_url=doc.document_url if doc else None,
            document_access_level=doc.access_level if doc else None,
            document_extraction_quality=doc.extraction_quality if doc else None,
            document_version_type=doc.version_type if doc else None,
            claim_id=claim.id if claim else None,
            claim_text=claim.text if claim else None,
            claim_status=claim.status if claim else None,
            linked_claims=links_by_evidence.get(ev.id, []),
            exact_text=ev.exact_text,
            surrounding_context=ev.surrounding_context,
            evidence_type=ev.evidence_type,
            relevance_score=ev.relevance_score,
            relevance_reason=ev.relevance_reason,
            extraction_method=ev.extraction_method,
            page_number=ev.page_number,
            section_name=ev.section_name,
            retrieval_timestamp=ev.retrieval_timestamp,
            traceable=ev.traceable,
        )
        for ev, src, inv, doc, claim in rows
    ]

    return WorkspaceEvidencePageResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/research/sources", response_model=WorkspaceSourcePageResponse)
async def list_workspace_sources(
    investigation_id: uuid.UUID | None = None,
    source_id: uuid.UUID | None = None,
    q: str | None = None,
    inclusion_status: str | None = None,
    source_type: str | None = None,
    access_level: str | None = None,
    open_access_status: str | None = None,
    sort: str = Query(default="relevance_desc", pattern="^(relevance_desc|relevance_asc|recent_desc|evidence_desc)$"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceSourcePageResponse:
    await _ensure_investigation(session, user, investigation_id)
    perm = PermissionService(session)
    user_workspaces = await perm.get_user_workspaces(user.id)
    if not user_workspaces:
        return WorkspaceSourcePageResponse(items=[], total=0, limit=limit, offset=offset)

    inv_scope = Investigation.workspace_id.in_(user_workspaces)
    if DEFAULT_GLOBAL_WORKSPACE_ID in user_workspaces:
        inv_scope = or_(inv_scope, Investigation.workspace_id.is_(None))

    conditions: list[Any] = []
    if investigation_id is not None:
        conditions.append(Source.investigation_id == investigation_id)
    else:
        conditions.append(Source.investigation_id.in_(select(Investigation.id).where(inv_scope)))
    if source_id is not None:
        conditions.append(Source.id == source_id)
    if inclusion_status:
        conditions.append(Source.inclusion_status == inclusion_status)
    if source_type:
        conditions.append(Source.source_type == source_type)
    if open_access_status:
        conditions.append(Source.open_access_status == open_access_status)
    if access_level:
        if access_level == "none":
            conditions.append(~exists(select(Document.id).where(Document.source_id == Source.id)))
        else:
            conditions.append(
                exists(
                    select(Document.id).where(
                        Document.source_id == Source.id,
                        Document.access_level == access_level,
                    )
                )
            )

    search_term = q.strip() if q else ""
    if search_term:
        pattern = f"%{search_term.lower()}%"
        conditions.append(
            or_(
                func.lower(Source.title).like(pattern),
                func.lower(func.coalesce(Source.publisher, "")).like(pattern),
                func.lower(func.coalesce(Source.doi, "")).like(pattern),
                func.lower(Source.original_url).like(pattern),
                func.lower(Source.canonical_url).like(pattern),
            )
        )

    count_stmt = select(func.count(Source.id)).select_from(Source).join(Investigation, Source.investigation_id == Investigation.id)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = int((await session.scalar(count_stmt)) or 0)

    ev_count_subq = (
        select(Evidence.source_id.label("source_id"), func.count(Evidence.id).label("ev_count"))
        .group_by(Evidence.source_id)
        .subquery()
    )
    order_clauses = (
        (Source.relevance_score.asc(), Source.id)
        if sort == "relevance_asc"
        else (desc(func.coalesce(Source.retrieval_timestamp, Investigation.created_at)), Source.relevance_score.desc(), Source.id)
        if sort == "recent_desc"
        else (desc(func.coalesce(ev_count_subq.c.ev_count, 0)), Source.relevance_score.desc(), Source.id)
        if sort == "evidence_desc"
        else (Source.relevance_score.desc(), Source.id)
    )

    stmt = (
        select(Source, Investigation)
        .select_from(Source)
        .join(Investigation, Source.investigation_id == Investigation.id)
        .outerjoin(ev_count_subq, ev_count_subq.c.source_id == Source.id)
        .order_by(*order_clauses)
        .offset(offset)
        .limit(limit)
    )
    if conditions:
        stmt = stmt.where(*conditions)

    rows = (await session.execute(stmt)).all()
    source_ids = [src.id for src, _ in rows]

    docs_by_source: dict[uuid.UUID, list[Document]] = defaultdict(list)
    oa_by_source: dict[uuid.UUID, list[OpenAccessLocation]] = defaultdict(list)
    ev_counts: dict[uuid.UUID, int] = {}
    latest_extraction: dict[uuid.UUID, ExtractionExecution] = {}

    if source_ids:
        doc_rows = (
            await session.scalars(
                select(Document).where(Document.source_id.in_(source_ids)).order_by(Document.retrieved_at.desc())
            )
        ).all()
        for doc in doc_rows:
            docs_by_source[doc.source_id].append(doc)

        oa_rows = (
            await session.scalars(select(OpenAccessLocation).where(OpenAccessLocation.source_id.in_(source_ids)))
        ).all()
        for loc in oa_rows:
            oa_by_source[loc.source_id].append(loc)

        ev_count_rows = (
            await session.execute(
                select(Evidence.source_id, func.count(Evidence.id))
                .where(Evidence.source_id.in_(source_ids))
                .group_by(Evidence.source_id)
            )
        ).all()
        ev_counts = {src_id: int(count) for src_id, count in ev_count_rows}

        ext_rows = (
            await session.scalars(
                select(ExtractionExecution)
                .where(ExtractionExecution.source_id.in_(source_ids))
                .order_by(ExtractionExecution.executed_at.desc())
            )
        ).all()
        for ext in ext_rows:
            latest_extraction.setdefault(ext.source_id, ext)

    items: list[WorkspaceSourceItem] = []
    for src, inv in rows:
        docs = docs_by_source.get(src.id, [])
        primary_doc = next((d for d in docs if d.document_url == src.selected_document_url), docs[0] if docs else None)
        oa_locs = oa_by_source.get(src.id, [])
        ext = latest_extraction.get(src.id)
        items.append(
            WorkspaceSourceItem(
                id=src.id,
                investigation_id=inv.id,
                investigation_question=inv.question,
                title=src.title,
                canonical_url=src.canonical_url,
                original_url=src.original_url,
                source_type=src.source_type,
                publisher=src.publisher,
                authors=list(_safe_json_loads(src.authors_json, [])),
                publication_date=src.publication_date,
                doi=src.doi,
                retrieval_timestamp=src.retrieval_timestamp,
                relevance_score=src.relevance_score,
                relevance_reasons=list(_safe_json_loads(src.relevance_reasons_json, [])),
                inclusion_status=src.inclusion_status,
                rejection_reason=src.rejection_reason,
                access_level=primary_doc.access_level if primary_doc else None,
                extraction_quality=primary_doc.extraction_quality if primary_doc else None,
                open_access_status=src.open_access_status,
                selected_document_url=src.selected_document_url,
                document_url=primary_doc.document_url if primary_doc else None,
                version_type=primary_doc.version_type if primary_doc else None,
                access_route=primary_doc.access_route if primary_doc else None,
                metadata_match_status=primary_doc.metadata_match_status if primary_doc else None,
                available_versions=[loc.version_type for loc in oa_locs],
                evidence_count=ev_counts.get(src.id, 0),
                document_count=len(docs),
                extraction_status=ext.status if ext else None,
                extraction_error=ext.error_message if ext else None,
                documents=[
                    SourceDocumentSummary(
                        id=doc.id,
                        title=doc.title,
                        content_type=doc.content_type,
                        access_level=doc.access_level,
                        extraction_quality=doc.extraction_quality,
                        document_url=doc.document_url,
                        version_type=doc.version_type,
                        access_route=doc.access_route,
                        metadata_match_status=doc.metadata_match_status,
                        page_count=doc.page_count,
                        retrieved_at=doc.retrieved_at,
                        headings=list(_safe_json_loads(doc.headings_json, [])),
                    )
                    for doc in docs
                ],
                open_access_locations=[
                    OpenAccessLocationSummary(
                        id=loc.id,
                        url=loc.url,
                        repository=loc.repository,
                        version_type=loc.version_type,
                        license=loc.license,
                        match_status=loc.match_status,
                        match_reason=loc.match_reason,
                        acquisition_status=loc.acquisition_status,
                        failure_reason=loc.failure_reason,
                    )
                    for loc in oa_locs
                ],
            )
        )

    return WorkspaceSourcePageResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/agents/observatory", response_model=AgentObservatoryResponse)
async def read_agent_observatory(
    investigation_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    agent_identifier: str | None = None,
    status: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgentObservatoryResponse:
    await _ensure_investigation(session, user, investigation_id)
    perm = PermissionService(session)
    user_workspaces = await perm.get_user_workspaces(user.id)
    if not user_workspaces:
        settings = get_settings()
        return AgentObservatoryResponse(
            summary=ObservatorySummary(
                total_jobs=0,
                active_jobs=0,
                total_executions=0,
                waiting_in_queue=0,
                generating=0,
                completed=0,
                failed=0,
                cancelled=0,
                provider_queue_wait_timeout_seconds=settings.provider_queue_wait_timeout_seconds,
                local_inference_timeout_seconds=settings.local_inference_timeout_seconds,
                local_provider_max_concurrency=settings.local_provider_max_concurrency,
            ),
            agents=[],
            executions=[],
            executions_total=0,
            limit=limit,
            offset=offset,
        )

    inv_scope = Investigation.workspace_id.in_(user_workspaces)
    if DEFAULT_GLOBAL_WORKSPACE_ID in user_workspaces:
        inv_scope = or_(inv_scope, Investigation.workspace_id.is_(None))

    settings = get_settings()
    name_map = {item.identifier: item.name for item in AGENT_DEFINITIONS}

    job_conditions: list[Any] = []
    if investigation_id is not None:
        job_conditions.append(AnalysisJob.investigation_id == investigation_id)
    elif job_id is not None:
        job_conditions.append(AnalysisJob.id == job_id)
        job_conditions.append(AnalysisJob.investigation_id.in_(select(Investigation.id).where(inv_scope)))
    else:
        job_conditions.append(AnalysisJob.investigation_id.in_(select(Investigation.id).where(inv_scope)))

    jobs_stmt = select(AnalysisJob.status)
    if job_conditions:
        jobs_stmt = jobs_stmt.where(*job_conditions)
    job_statuses = (await session.scalars(jobs_stmt)).all()
    total_jobs = len(job_statuses)
    active_jobs = sum(1 for item in job_statuses if item in _ACTIVE_JOB_STATUSES)

    scope_exec_stmt = (
        select(AnalysisAgentExecution, AnalysisJob)
        .join(AnalysisJob, AnalysisAgentExecution.job_id == AnalysisJob.id)
        .order_by(desc(func.coalesce(AnalysisAgentExecution.started_at, AnalysisJob.created_at)), AnalysisAgentExecution.id)
    )
    if job_conditions:
        scope_exec_stmt = scope_exec_stmt.where(*job_conditions)
    all_scope_execs = (await session.execute(scope_exec_stmt)).all()

    counts_by_role: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    latest_by_role: dict[str, tuple[AnalysisAgentExecution, AnalysisJob]] = {}
    status_totals: dict[str, int] = defaultdict(int)
    for exec_row, job_row in all_scope_execs:
        counts_by_role[exec_row.agent_identifier]["total"] += 1
        counts_by_role[exec_row.agent_identifier][exec_row.status] += 1
        status_totals[exec_row.status] += 1
        latest_by_role.setdefault(exec_row.agent_identifier, (exec_row, job_row))

    roster: list[AgentRosterSummary] = []
    for agent_def in AGENT_DEFINITIONS:
        role_counts = counts_by_role.get(agent_def.identifier, {})
        latest_pair = latest_by_role.get(agent_def.identifier)
        latest_exec = latest_pair[0] if latest_pair else None
        latest_job = latest_pair[1] if latest_pair else None
        latest_usage = _safe_json_loads(latest_exec.token_usage_json, {}) if latest_exec else {}
        if not isinstance(latest_usage, dict):
            latest_usage = {}
        roster.append(
            AgentRosterSummary(
                identifier=agent_def.identifier,
                name=agent_def.name,
                description=agent_def.description,
                system_instructions=agent_def.system_instructions,
                demo_mode=settings.demo_mode,
                total_executions=role_counts.get("total", 0),
                completed_count=role_counts.get("completed", 0),
                failed_count=role_counts.get("failed", 0),
                cancelled_count=role_counts.get("cancelled", 0),
                waiting_in_queue_count=role_counts.get("waiting_in_queue", 0) + role_counts.get("queued", 0),
                generating_count=role_counts.get("generating", 0) + role_counts.get("running", 0),
                latest_status=latest_exec.status if latest_exec else "ready",
                latest_model=(latest_exec.model or latest_job.default_model) if (latest_exec and latest_job) else None,
                latest_provider_kind=latest_job.provider_kind if latest_job else None,
                latest_job_id=latest_job.id if latest_job else None,
                latest_investigation_id=latest_job.investigation_id if latest_job else None,
                latest_started_at=latest_exec.started_at if latest_exec else None,
                latest_completed_at=latest_exec.completed_at if latest_exec else None,
                latest_queue_wait_seconds=_safe_float(latest_usage.get("queue_wait_seconds")),
                latest_inference_duration_seconds=_safe_float(latest_usage.get("inference_duration_seconds")),
                latest_error_message=latest_exec.error_message if latest_exec else None,
            )
        )

    exec_conditions = list(job_conditions)
    if agent_identifier:
        exec_conditions.append(AnalysisAgentExecution.agent_identifier == agent_identifier)
    if status:
        if status == "waiting_in_queue":
            exec_conditions.append(AnalysisAgentExecution.status.in_(("waiting_in_queue", "queued")))
        elif status == "generating":
            exec_conditions.append(AnalysisAgentExecution.status.in_(("generating", "running")))
        else:
            exec_conditions.append(AnalysisAgentExecution.status == status)

    exec_count_stmt = (
        select(func.count(AnalysisAgentExecution.id))
        .select_from(AnalysisAgentExecution)
        .join(AnalysisJob, AnalysisAgentExecution.job_id == AnalysisJob.id)
    )
    if exec_conditions:
        exec_count_stmt = exec_count_stmt.where(*exec_conditions)
    executions_total = int((await session.scalar(exec_count_stmt)) or 0)

    active_first = case(
        (AnalysisAgentExecution.status.in_(("generating", "running")), 0),
        (AnalysisAgentExecution.status.in_(("waiting_in_queue", "queued")), 1),
        else_=2,
    )
    exec_stmt = (
        select(AnalysisAgentExecution, AnalysisJob, Investigation)
        .join(AnalysisJob, AnalysisAgentExecution.job_id == AnalysisJob.id)
        .join(Investigation, AnalysisJob.investigation_id == Investigation.id)
        .order_by(
            active_first,
            desc(func.coalesce(AnalysisAgentExecution.started_at, AnalysisJob.created_at)),
            AnalysisAgentExecution.id,
        )
        .offset(offset)
        .limit(limit)
    )
    if exec_conditions:
        exec_stmt = exec_stmt.where(*exec_conditions)
    exec_rows = (await session.execute(exec_stmt)).all()

    exec_ids = [exec_row.id for exec_row, _, _ in exec_rows]
    arg_counts: dict[uuid.UUID, int] = defaultdict(int)
    claim_sets_by_exec: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    ev_sets_by_exec: dict[uuid.UUID, set[str]] = defaultdict(set)

    if exec_ids:
        arg_rows = (
            await session.scalars(select(AgentArgument).where(AgentArgument.execution_id.in_(exec_ids)))
        ).all()
        for arg in arg_rows:
            arg_counts[arg.execution_id] += 1
            claim_sets_by_exec[arg.execution_id].add(arg.claim_id)
            ev_ids = _safe_json_loads(arg.evidence_ids_json, [])
            if isinstance(ev_ids, list):
                for ev_id in ev_ids:
                    if isinstance(ev_id, str):
                        ev_sets_by_exec[arg.execution_id].add(ev_id)

    executions: list[AgentExecutionObservatoryItem] = []
    for exec_row, job_row, inv_row in exec_rows:
        parsed_output = _safe_json_loads(exec_row.output_json, None)
        if parsed_output is not None and not isinstance(parsed_output, dict):
            parsed_output = {"raw": parsed_output}
        usage = _safe_json_loads(exec_row.token_usage_json, {})
        if not isinstance(usage, dict):
            usage = {}

        total_duration = _duration_seconds(exec_row.started_at, exec_row.completed_at)

        claims_processed = len(claim_sets_by_exec.get(exec_row.id, set()))
        cited_evidence = len(ev_sets_by_exec.get(exec_row.id, set()))
        if parsed_output:
            if claims_processed == 0 and isinstance(parsed_output.get("claims"), list):
                claims_processed = len(parsed_output["claims"])
            if claims_processed == 0 and isinstance(parsed_output.get("decisions"), list):
                claims_processed = len(parsed_output["decisions"])
                dec_ev = {
                    ev_id
                    for dec in parsed_output["decisions"]
                    if isinstance(dec, dict) and isinstance(dec.get("evidence_ids"), list)
                    for ev_id in dec["evidence_ids"]
                    if isinstance(ev_id, str)
                }
                cited_evidence = max(cited_evidence, len(dec_ev))
            if cited_evidence == 0 and isinstance(parsed_output.get("sections"), list):
                sec_ev = {
                    ev_id
                    for sec in parsed_output["sections"]
                    if isinstance(sec, dict) and isinstance(sec.get("evidence_ids"), list)
                    for ev_id in sec["evidence_ids"]
                    if isinstance(ev_id, str)
                }
                sec_claims = {
                    cl_id
                    for sec in parsed_output["sections"]
                    if isinstance(sec, dict) and isinstance(sec.get("claim_ids"), list)
                    for cl_id in sec["claim_ids"]
                    if isinstance(cl_id, str)
                }
                cited_evidence = len(sec_ev)
                claims_processed = max(claims_processed, len(sec_claims))

        executions.append(
            AgentExecutionObservatoryItem(
                id=exec_row.id,
                job_id=job_row.id,
                investigation_id=inv_row.id,
                investigation_question=inv_row.question,
                agent_identifier=exec_row.agent_identifier,
                agent_name=name_map.get(exec_row.agent_identifier, exec_row.agent_identifier),
                status=exec_row.status,
                model=exec_row.model or job_row.default_model,
                provider_kind=job_row.provider_kind,
                started_at=exec_row.started_at,
                completed_at=exec_row.completed_at,
                total_duration_seconds=total_duration,
                queue_wait_seconds=_safe_float(usage.get("queue_wait_seconds")),
                inference_duration_seconds=_safe_float(usage.get("inference_duration_seconds")),
                token_usage=usage,
                argument_count=arg_counts.get(exec_row.id, 0),
                cited_evidence_count=cited_evidence,
                claims_processed_count=claims_processed,
                error_message=exec_row.error_message,
                output=parsed_output,
            )
        )

    return AgentObservatoryResponse(
        summary=ObservatorySummary(
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            total_executions=len(all_scope_execs),
            waiting_in_queue=status_totals.get("waiting_in_queue", 0) + status_totals.get("queued", 0),
            generating=status_totals.get("generating", 0) + status_totals.get("running", 0),
            completed=status_totals.get("completed", 0),
            failed=status_totals.get("failed", 0),
            cancelled=status_totals.get("cancelled", 0),
            provider_queue_wait_timeout_seconds=settings.provider_queue_wait_timeout_seconds,
            local_inference_timeout_seconds=settings.local_inference_timeout_seconds,
            local_provider_max_concurrency=settings.local_provider_max_concurrency,
        ),
        agents=roster,
        executions=executions,
        executions_total=executions_total,
        limit=limit,
        offset=offset,
    )
