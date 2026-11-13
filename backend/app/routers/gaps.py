import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.gap_service import gap_engine
from app.db import get_session
from app.errors import BackendError
from app.models import Investigation
from app.schemas import (
    ResearchGapAnalysisResponse,
    ResearchGapAnalyzeRequest,
    ResearchGapVersionView,
    ResearchGapView,
)

router = APIRouter(prefix="/research/investigations/{investigation_id}/gaps", tags=["research_gaps"])


async def _verify_investigation_exists(investigation_id: uuid.UUID, session: AsyncSession) -> Investigation:
    investigation = await session.get(Investigation, investigation_id)
    if investigation is None:
        raise BackendError("Investigation not found.", 404, "not_found")
    return investigation


@router.post("/analyze", response_model=ResearchGapAnalysisResponse)
async def analyze_investigation_gaps(
    investigation_id: uuid.UUID,
    payload: ResearchGapAnalyzeRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> ResearchGapAnalysisResponse:
    """Analyze an investigation and persist a new versioned research gap analysis."""
    await _verify_investigation_exists(investigation_id, session)
    req = payload or ResearchGapAnalyzeRequest()
    try:
        return await gap_engine.analyze_investigation(
            session=session,
            investigation_id=investigation_id,
            provider_kind=req.provider_kind,
            model=req.model,
            force_regenerate=req.force_regenerate or True,
        )
    except ValueError as e:
        raise BackendError(str(e), 404, "not_found") from e


@router.get("", response_model=ResearchGapAnalysisResponse)
async def get_latest_investigation_gaps(
    investigation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ResearchGapAnalysisResponse:
    """Get the latest research gap analysis with coverage summary and gaps."""
    await _verify_investigation_exists(investigation_id, session)
    latest = await gap_engine.get_latest_gap_analysis(session, investigation_id)
    if latest is None:
        # Generate on-demand if no analysis exists yet
        latest = await gap_engine.analyze_investigation(
            session=session,
            investigation_id=investigation_id,
            force_regenerate=True,
        )
    return latest


@router.get("/versions", response_model=list[ResearchGapVersionView])
async def list_gap_analysis_versions(
    investigation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ResearchGapVersionView]:
    """List historical gap analysis versions for an investigation."""
    await _verify_investigation_exists(investigation_id, session)
    return await gap_engine.list_gap_analysis_versions(session, investigation_id)


@router.get("/versions/{version_or_id}", response_model=ResearchGapAnalysisResponse)
async def get_gap_analysis_version(
    investigation_id: uuid.UUID,
    version_or_id: str,
    session: AsyncSession = Depends(get_session),
) -> ResearchGapAnalysisResponse:
    """Retrieve a specific gap analysis version by version number or analysis UUID."""
    await _verify_investigation_exists(investigation_id, session)
    result = await gap_engine.get_gap_analysis_by_version_or_id(session, investigation_id, version_or_id)
    if result is None:
        raise BackendError(f"Gap analysis version '{version_or_id}' not found.", 404, "not_found")
    return result


@router.get("/items")
async def list_gap_items(
    investigation_id: uuid.UUID,
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    min_priority: float | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """List individual research gap items with filtering and pagination."""
    await _verify_investigation_exists(investigation_id, session)
    items, total = await gap_engine.list_gap_items(
        session=session,
        investigation_id=investigation_id,
        category=category,
        severity=severity,
        min_priority=min_priority,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
