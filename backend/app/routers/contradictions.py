import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.contradiction_service import contradiction_service
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.db import get_session
from app.errors import BackendError
from app.models import ResearchContradiction, User
from app.schemas import (
    ContradictionDetectRequest,
    ContradictionResolveRequest,
    ResearchContradictionView,
)

router = APIRouter(prefix="/research/contradictions", tags=["contradiction_intelligence"])


@router.post("/detect", response_model=list[ResearchContradictionView])
async def detect_contradictions(
    payload: ContradictionDetectRequest | None = Body(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ResearchContradictionView]:
    """Detect scientific contradictions across claims and evidence both intra- and cross-investigation."""
    req = payload or ContradictionDetectRequest()
    if req.investigation_id:
        perm = PermissionService(session)
        await perm.check_investigation_access(user, req.investigation_id, "write")
    return await contradiction_service.detect_contradictions(
        session=session,
        investigation_id=req.investigation_id,
        cross_investigation=req.cross_investigation,
        provider_kind=req.provider_kind,
        model=req.model,
    )


@router.get("", response_model=list[ResearchContradictionView])
async def list_contradictions(
    investigation_id: uuid.UUID | None = Query(None, description="Filter by investigation ID"),
    status: str | None = Query(None, description="Filter by resolution status"),
    severity: str | None = Query(None, description="Filter by contradiction severity"),
    category: str | None = Query(None, description="Filter by contradiction category"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ResearchContradictionView]:
    """List detected research contradictions with optional filtering."""
    if investigation_id:
        perm = PermissionService(session)
        await perm.check_investigation_access(user, investigation_id, "read")
    results = await contradiction_service.list_contradictions(
        session=session,
        investigation_id=investigation_id,
        status=status,
        severity=severity,
        category=category,
    )
    if not results and investigation_id:
        # Detect on-demand if none found
        results = await contradiction_service.detect_contradictions(
            session=session,
            investigation_id=investigation_id,
            cross_investigation=True,
        )
    return results


@router.get("/{contradiction_id}", response_model=ResearchContradictionView)
async def get_contradiction_detail(
    contradiction_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResearchContradictionView:
    """Retrieve full details of a specific contradiction including resolution logs."""
    record = await contradiction_service.get_contradiction(session, contradiction_id)
    if record is None:
        raise BackendError(f"Contradiction {contradiction_id} not found", 404, "not_found")
    c = await session.get(ResearchContradiction, contradiction_id)
    if c and c.primary_investigation_id:
        perm = PermissionService(session)
        await perm.check_investigation_access(user, c.primary_investigation_id, "read")
    return record


@router.patch("/{contradiction_id}/resolve", response_model=ResearchContradictionView)
async def resolve_contradiction(
    contradiction_id: uuid.UUID,
    payload: ContradictionResolveRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResearchContradictionView:
    """Update contradiction resolution lifecycle status with rationale and evidence links."""
    c = await session.get(ResearchContradiction, contradiction_id)
    if c and c.primary_investigation_id:
        perm = PermissionService(session)
        await perm.check_investigation_access(user, c.primary_investigation_id, "write")
    try:
        return await contradiction_service.resolve_contradiction(
            session=session,
            contradiction_id=contradiction_id,
            payload=payload,
        )
    except ValueError as e:
        raise BackendError(str(e), 404, "not_found") from e
