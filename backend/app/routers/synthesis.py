import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.synthesis_service import synthesis_service
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.db import get_session
from app.errors import BackendError
from app.models import User
from app.schemas import (
    CrossInvestigationSynthesisRequest,
    CrossInvestigationSynthesisResponse,
    CrossRelationshipView,
    GlobalClaimSearchResult,
    InvestigationSynthesisReportView,
    SharedEvidenceResult,
)

router = APIRouter(prefix="/research/synthesis", tags=["cross_investigation_synthesis"])


@router.post("/generate", response_model=CrossInvestigationSynthesisResponse)
async def generate_cross_investigation_synthesis(
    payload: CrossInvestigationSynthesisRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CrossInvestigationSynthesisResponse:
    """Perform multi-investigation synthesis, relationship discovery, and generate a comprehensive cross-synthesis report."""
    perm = PermissionService(session)
    for inv_id in payload.investigation_ids:
        await perm.check_investigation_access(user, inv_id, "write")
    try:
        report, relationships = await synthesis_service.synthesize_investigations(
            session=session,
            investigation_ids=payload.investigation_ids,
            provider_kind=payload.provider_kind,
            model=payload.model,
        )
        return CrossInvestigationSynthesisResponse(report=report, relationships=relationships)
    except ValueError as e:
        raise BackendError(str(e), 400, "invalid_request") from e


@router.get("/reports", response_model=list[InvestigationSynthesisReportView])
async def list_synthesis_reports(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[InvestigationSynthesisReportView]:
    """List persisted cross-investigation synthesis reports."""
    return await synthesis_service.list_synthesis_reports(session, limit=limit)


@router.get("/reports/{report_id}", response_model=InvestigationSynthesisReportView)
async def get_synthesis_report(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InvestigationSynthesisReportView:
    """Retrieve details of a specific cross-investigation synthesis report."""
    report = await synthesis_service.get_synthesis_report(session, report_id)
    if report is None:
        raise BackendError(f"Synthesis report {report_id} not found", 404, "not_found")
    return report


@router.get("/relationships", response_model=list[CrossRelationshipView])
async def list_cross_relationships(
    investigation_id: uuid.UUID | None = Query(None, description="Filter by participating investigation ID"),
    relationship_type: str | None = Query(None, description="Filter by relationship type (supports, challenges, etc.)"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CrossRelationshipView]:
    """List cross-investigation relationships with optional filters."""
    if investigation_id:
        perm = PermissionService(session)
        await perm.check_investigation_access(user, investigation_id, "read")
    return await synthesis_service.list_cross_relationships(
        session=session,
        investigation_id=investigation_id,
        relationship_type=relationship_type,
    )


@router.get("/claims/search", response_model=list[GlobalClaimSearchResult])
async def search_global_claims(
    query: str = Query("", description="Search term for claim text"),
    status: str | None = Query(None, description="Filter by claim status"),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[GlobalClaimSearchResult]:
    """Search claims across all investigations with linked question and evidence count."""
    return await synthesis_service.search_global_claims(
        session=session,
        query=query,
        status=status,
        limit=limit,
    )


@router.get("/shared-evidence", response_model=list[SharedEvidenceResult])
async def discover_shared_evidence(
    min_investigations: int = Query(2, ge=2, description="Minimum number of investigations sharing the source"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SharedEvidenceResult]:
    """Discover evidence and sources that are shared or referenced across multiple investigations."""
    return await synthesis_service.discover_shared_evidence(session, min_investigations=min_investigations)
