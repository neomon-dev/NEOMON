import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.research_intelligence_service import research_intelligence_service
from app.db import get_session
from app.schemas import (
    GlobalResearchSearchResponse,
    GlobalSearchCategory,
    UnifiedIntelligenceOverview,
)

router = APIRouter(prefix="/research/intelligence", tags=["research_intelligence"])


@router.get("/overview", response_model=UnifiedIntelligenceOverview)
async def get_unified_overview(
    session: AsyncSession = Depends(get_session),
) -> UnifiedIntelligenceOverview:
    """Retrieve aggregated research intelligence metrics across all investigations and modules."""
    return await research_intelligence_service.get_unified_overview(session)


@router.get("/search", response_model=GlobalResearchSearchResponse)
async def search_global_research(
    query: str = Query("", description="Universal search term"),
    category: str = Query("all", description="Entity category filter: all, investigation, claim, evidence, source, hypothesis, gap, contradiction, topic"),
    limit: int = Query(40, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> GlobalResearchSearchResponse:
    """Universal search across investigations, claims, evidence, sources, hypotheses, gaps, contradictions, and topics."""
    return await research_intelligence_service.search_global_research(
        session=session,
        query=query,
        category=category,
        limit=limit,
    )
