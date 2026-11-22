import json
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.errors import BackendError
from app.models import Claim, Document, Evidence, Investigation, Source, User, WorkspaceMember
from app.auth.dependencies import get_current_user
from app.auth.rate_limiter import rate_limit_research
from app.collaboration.permission_service import PermissionService, DEFAULT_GLOBAL_WORKSPACE_ID
from app.research.normalization import content_hash
from app.research.retrieval import RetrievalError, retrieve_document
from app.research.service import run_investigation
from app.schemas import (
    ClaimResponse,
    EvidenceResponse,
    InvestigationCreate,
    InvestigationResponse,
    ResearchStartResponse,
    SourceResponse,
)

router = APIRouter(prefix="/research", tags=["research"])


async def get_investigation(investigation_id: uuid.UUID, session: AsyncSession) -> Investigation:
    investigation = await session.get(Investigation, investigation_id)
    if investigation is None:
        raise BackendError("Investigation not found.", 404, "not_found")
    return investigation


def investigation_response(investigation: Investigation, source_count: int = 0, evidence_count: int = 0) -> InvestigationResponse:
    return InvestigationResponse(
        id=investigation.id,
        question=investigation.question,
        mode=investigation.mode,
        status=investigation.status,
        created_at=investigation.created_at,
        source_count=source_count,
        evidence_count=evidence_count,
        quality_status=investigation.quality_status,
        quality_summary=investigation.quality_summary,
        relevant_source_count=investigation.relevant_source_count,
        full_text_count=investigation.full_text_count,
        evidence_gap=investigation.evidence_gap,
        workspace_id=investigation.workspace_id,
        owner_id=investigation.owner_id,
    )


def source_response(source: Source, document: Document | None = None) -> SourceResponse:
    return SourceResponse(
        id=source.id,
        title=source.title,
        canonical_url=source.canonical_url,
        original_url=source.original_url,
        source_type=source.source_type,
        publisher=source.publisher,
        authors=json.loads(source.authors_json) if source.authors_json else [],
        publication_date=source.publication_date,
        doi=source.doi,
        retrieval_timestamp=source.retrieval_timestamp,
        relevance_score=source.relevance_score,
        relevance_reasons=json.loads(source.relevance_reasons_json) if source.relevance_reasons_json else [],
        inclusion_status=source.inclusion_status,
        rejection_reason=source.rejection_reason,
        access_level=document.access_level if document else "metadata_only",
        extraction_quality=document.extraction_quality if document else "none",
        open_access_status=source.open_access_status,
        selected_document_url=source.selected_document_url,
        document_url=document.document_url if document else None,
        version_type=document.version_type if document else None,
        access_route=document.access_route if document else None,
        metadata_match_status=document.metadata_match_status if document else None,
        available_versions=sorted({item.version_type for item in source.open_access_locations}),
    )


@router.post("/investigations", response_model=ResearchStartResponse, dependencies=[Depends(rate_limit_research())])
async def create_investigation(
    payload: InvestigationCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResearchStartResponse:
    ws_id = payload.workspace_id
    if not ws_id:
        user_ws = await session.scalar(
            select(WorkspaceMember.workspace_id)
            .where(WorkspaceMember.user_id == user.id)
            .order_by(WorkspaceMember.joined_at.asc())
            .limit(1)
        )
        ws_id = user_ws or DEFAULT_GLOBAL_WORKSPACE_ID
    perm = PermissionService(session)
    await perm.require_workspace_membership(user.id, ws_id, min_role="researcher")

    investigation = Investigation(
        question=payload.question,
        mode=payload.mode,
        timeframe=payload.timeframe,
        status="created",
        workspace_id=ws_id,
        owner_id=user.id,
    )
    session.add(investigation)
    await session.flush()
    queries, errors = await run_investigation(session, request.app.state.event_broker, investigation, payload)
    await session.commit()
    source_count = await session.scalar(select(func.count(Source.id)).where(Source.investigation_id == investigation.id))
    evidence_count = await session.scalar(
        select(func.count(Evidence.id)).join(Source).where(Source.investigation_id == investigation.id)
    )
    return ResearchStartResponse(
        investigation=investigation_response(investigation, source_count or 0, evidence_count or 0),
        queries=[
            {"id": row.id, "query": row.query, "category": row.category, "provider": row.provider, "executed_at": row.executed_at}
            for row in queries
        ],
        source_count=source_count or 0,
        evidence_count=evidence_count or 0,
        errors=errors,
    )


@router.get("/investigations/{investigation_id}", response_model=InvestigationResponse)
async def read_investigation(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvestigationResponse:
    perm = PermissionService(session)
    investigation = await perm.check_investigation_access(user, investigation_id, "read")
    source_count = await session.scalar(select(func.count(Source.id)).where(Source.investigation_id == investigation.id))
    evidence_count = await session.scalar(
        select(func.count(Evidence.id)).join(Source).where(Source.investigation_id == investigation.id)
    )
    return investigation_response(investigation, source_count or 0, evidence_count or 0)


@router.get("/investigations", response_model=list[InvestigationResponse])
async def list_investigations(
    workspace_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[InvestigationResponse]:
    perm = PermissionService(session)
    stmt = select(Investigation)

    if workspace_id:
        await perm.require_workspace_membership(user.id, workspace_id, min_role="viewer")
        if workspace_id == DEFAULT_GLOBAL_WORKSPACE_ID:
            stmt = stmt.where(or_(Investigation.workspace_id == workspace_id, Investigation.workspace_id.is_(None)))
        else:
            stmt = stmt.where(Investigation.workspace_id == workspace_id)
    else:
        user_ws_ids = await perm.get_user_workspaces(user.id)
        if not user_ws_ids:
            return []
        if DEFAULT_GLOBAL_WORKSPACE_ID in user_ws_ids:
            stmt = stmt.where(or_(Investigation.workspace_id.in_(user_ws_ids), Investigation.workspace_id.is_(None)))
        else:
            stmt = stmt.where(Investigation.workspace_id.in_(user_ws_ids))

    stmt = stmt.order_by(Investigation.created_at.desc())
    investigations = (await session.scalars(stmt)).all()
    if not investigations:
        return []
    source_counts = dict(
        (
            await session.execute(
                select(Source.investigation_id, func.count(Source.id)).group_by(Source.investigation_id)
            )
        ).all()
    )
    evidence_counts = dict(
        (
            await session.execute(
                select(Source.investigation_id, func.count(Evidence.id))
                .join(Evidence, Evidence.source_id == Source.id)
                .group_by(Source.investigation_id)
            )
        ).all()
    )
    return [
        investigation_response(
            investigation,
            source_counts.get(investigation.id, 0),
            evidence_counts.get(investigation.id, 0),
        )
        for investigation in investigations
    ]


@router.get("/investigations/{investigation_id}/sources", response_model=list[SourceResponse])
async def list_sources(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SourceResponse]:
    perm = PermissionService(session)
    await perm.check_investigation_access(user, investigation_id, "read")
    rows = (await session.execute(
        select(Source, Document)
        .options(selectinload(Source.open_access_locations))
        .outerjoin(Document)
        .where(Source.investigation_id == investigation_id)
    )).all()
    return [source_response(source, document) for source, document in rows]


@router.get("/investigations/{investigation_id}/evidence", response_model=list[EvidenceResponse])
async def list_evidence(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EvidenceResponse]:
    perm = PermissionService(session)
    await perm.check_investigation_access(user, investigation_id, "read")
    evidence = (
        await session.scalars(
            select(Evidence).join(Source).where(Source.investigation_id == investigation_id)
        )
    ).all()
    return [
        EvidenceResponse(
            id=item.id,
            source_id=item.source_id,
            claim_id=item.claim_id,
            exact_text=item.exact_text,
            surrounding_context=item.surrounding_context,
            evidence_type=item.evidence_type,
            relevance_score=item.relevance_score,
            extraction_method=item.extraction_method,
            page_number=item.page_number,
            section_name=item.section_name,
            retrieval_timestamp=item.retrieval_timestamp,
            document_id=item.document_id,
            relevance_reason=item.relevance_reason,
            traceable=item.traceable,
        )
        for item in evidence
    ]


@router.get("/investigations/{investigation_id}/claims", response_model=list[ClaimResponse])
async def list_claims(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ClaimResponse]:
    perm = PermissionService(session)
    await perm.check_investigation_access(user, investigation_id, "read")
    claims = (await session.scalars(select(Claim).where(Claim.investigation_id == investigation_id))).all()
    return [ClaimResponse(id=item.id, text=item.text, status=item.status) for item in claims]


@router.post("/investigations/{investigation_id}/cancel", response_model=InvestigationResponse)
async def cancel_investigation(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvestigationResponse:
    perm = PermissionService(session)
    investigation = await perm.check_investigation_access(user, investigation_id, "write")
    investigation.status = "cancelled"
    await session.commit()
    return investigation_response(investigation)


@router.post("/sources/{source_id}/refresh", response_model=SourceResponse)
async def refresh_source(
    source_id: uuid.UUID,
    investigation_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SourceResponse:
    source = await session.scalar(
        select(Source).options(selectinload(Source.open_access_locations)).where(Source.id == source_id)
    )
    if source is None or (investigation_id is not None and source.investigation_id != investigation_id):
        raise BackendError("Source not found.", 404, "not_found")
    perm = PermissionService(session)
    await perm.check_investigation_access(user, source.investigation_id, "write")

    try:
        retrieved = await retrieve_document(source.original_url)
    except RetrievalError as exc:
        raise BackendError(str(exc), 502, "retrieval_failed") from exc
    source.content_hash = content_hash(retrieved.content)
    doc = Document(
        source_id=source.id,
        content_type=retrieved.content_type,
        title=retrieved.title,
        content=retrieved.content,
        headings_json=json.dumps(retrieved.headings),
        page_count=retrieved.page_count,
        access_level=retrieved.access_level,
        extraction_quality=retrieved.extraction_quality,
        document_url=retrieved.final_url,
    )
    session.add(doc)
    await session.commit()
    return source_response(source, doc)
