import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.trend_service import trend_service
from app.db import get_session
from app.errors import BackendError
from app.schemas import (
    ResearchTrendAnalysisResponse,
    ResearchTrendAnalyzeRequest,
)

router = APIRouter(prefix="/research/trends", tags=["research_trends"])


@router.post("/analyze", response_model=ResearchTrendAnalysisResponse)
async def analyze_research_trends(
    payload: ResearchTrendAnalyzeRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> ResearchTrendAnalysisResponse:
    """Execute longitudinal research trend analysis across all investigations and sources."""
    req = payload or ResearchTrendAnalyzeRequest()
    return await trend_service.analyze_trends(
        session=session,
        provider_kind=req.provider_kind,
        model=req.model,
        temperature=req.temperature,
    )


@router.get("/latest", response_model=ResearchTrendAnalysisResponse)
async def get_latest_trend_analysis(
    session: AsyncSession = Depends(get_session),
) -> ResearchTrendAnalysisResponse:
    """Retrieve the latest research trend intelligence report (generates on-demand if none exists)."""
    latest = await trend_service.get_latest_trend_analysis(session)
    if latest is None:
        latest = await trend_service.analyze_trends(session=session)
    return latest


@router.get("", response_model=list[ResearchTrendAnalysisResponse])
async def list_trend_analyses(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[ResearchTrendAnalysisResponse]:
    """List historical research trend intelligence analyses."""
    return await trend_service.list_trend_analyses(session, limit=limit)


@router.get("/{trend_id}", response_model=ResearchTrendAnalysisResponse)
async def get_trend_analysis_by_id(
    trend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ResearchTrendAnalysisResponse:
    """Retrieve details of a specific trend analysis by ID."""
    record = await trend_service.get_trend_analysis(session, trend_id)
    if record is None:
        raise BackendError(f"Trend analysis {trend_id} not found", 404, "not_found")
    return record
