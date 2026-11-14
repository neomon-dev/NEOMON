import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.hypothesis_service import hypothesis_service
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.db import get_session
from app.errors import BackendError
from app.models import Investigation, User
from app.schemas import (
    HypothesisEvaluationRequest,
    HypothesisGenerateRequest,
    HypothesisGenerationResponse,
    HypothesisStatusUpdateRequest,
    HypothesisView,
)

router = APIRouter(prefix="/research/investigations/{investigation_id}/hypotheses", tags=["hypotheses"])


async def _verify_investigation_exists(
    investigation_id: uuid.UUID, user: User, session: AsyncSession, capability: str = "read"
) -> Investigation:
    perm = PermissionService(session)
    return await perm.check_investigation_access(user, investigation_id, capability)


@router.post("/generate", response_model=HypothesisGenerationResponse)
async def generate_hypotheses(
    investigation_id: uuid.UUID,
    payload: HypothesisGenerateRequest | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HypothesisGenerationResponse:
    """Generate scientifically testable, falsifiable hypotheses for an investigation."""
    await _verify_investigation_exists(investigation_id, user, session, "write")
    req = payload or HypothesisGenerateRequest()
    try:
        return await hypothesis_service.generate_hypotheses(
            session=session,
            investigation_id=investigation_id,
            provider_kind=req.provider_kind,
            model=req.model,
            force_regenerate=req.force_regenerate,
            focus_gap_id=req.focus_gap_id,
        )
    except ValueError as e:
        raise BackendError(str(e), 400, "invalid_request") from e


@router.get("", response_model=list[HypothesisView])
async def list_hypotheses(
    investigation_id: uuid.UUID,
    category: str | None = Query(None, description="Filter by hypothesis category"),
    status: str | None = Query(None, description="Filter by hypothesis review status"),
    min_testability: float | None = Query(None, description="Minimum testability score (0-10)"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[HypothesisView]:
    """List all hypotheses generated for an investigation with optional filters."""
    await _verify_investigation_exists(investigation_id, user, session, "read")
    hypotheses = await hypothesis_service.list_hypotheses(
        session=session,
        investigation_id=investigation_id,
        category=category,
        status=status,
        min_testability=min_testability,
    )
    if not hypotheses:
        # Generate on-demand if none exist yet
        gen_resp = await hypothesis_service.generate_hypotheses(
            session=session,
            investigation_id=investigation_id,
            force_regenerate=True,
        )
        hypotheses = gen_resp.hypotheses
    return hypotheses


@router.get("/{hypothesis_id}", response_model=HypothesisView)
async def get_hypothesis_detail(
    investigation_id: uuid.UUID,
    hypothesis_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HypothesisView:
    """Get complete details and evaluation history for a single hypothesis."""
    await _verify_investigation_exists(investigation_id, user, session, "read")
    hyp = await hypothesis_service.get_hypothesis(session, investigation_id, hypothesis_id)
    if hyp is None:
        raise BackendError(f"Hypothesis {hypothesis_id} not found", 404, "not_found")
    return hyp


@router.patch("/{hypothesis_id}/status", response_model=HypothesisView)
async def update_hypothesis_status(
    investigation_id: uuid.UUID,
    hypothesis_id: uuid.UUID,
    payload: HypothesisStatusUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HypothesisView:
    """Update review status of a hypothesis."""
    await _verify_investigation_exists(investigation_id, user, session, "write")
    try:
        status_val = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
        return await hypothesis_service.update_hypothesis_status(
            session=session,
            investigation_id=investigation_id,
            hypothesis_id=hypothesis_id,
            new_status=status_val,
            review_comments=payload.review_comments,
        )
    except ValueError as e:
        raise BackendError(str(e), 404, "not_found") from e


@router.post("/{hypothesis_id}/evaluate", response_model=HypothesisView)
async def evaluate_hypothesis(
    investigation_id: uuid.UUID,
    hypothesis_id: uuid.UUID,
    payload: HypothesisEvaluationRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HypothesisView:
    """Submit a structured multi-dimensional evaluation for a hypothesis."""
    await _verify_investigation_exists(investigation_id, user, session, "write")
    try:
        return await hypothesis_service.evaluate_hypothesis(
            session=session,
            investigation_id=investigation_id,
            hypothesis_id=hypothesis_id,
            payload=payload,
        )
    except ValueError as e:
        raise BackendError(str(e), 404, "not_found") from e
