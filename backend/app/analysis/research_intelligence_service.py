"""Unified Research Intelligence Service for NEOMON.

Implements Milestone 8F:
- Global multi-entity research search across investigations, claims, evidence, sources,
  hypotheses, gaps, contradictions, and topics.
- Aggregated research intelligence overview metrics.
- Interconnects all intelligence modules into a cohesive operational system.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Claim,
    CrossInvestigationRelationship,
    Evidence,
    Investigation,
    ResearchContradiction,
    ResearchGap,
    ResearchHypothesis,
    ResearchTrendAnalysis,
    ResearchTrendTopic,
    Source,
)
from app.schemas import (
    GlobalResearchSearchResponse,
    GlobalResearchSearchResultItem,
    GlobalSearchCategory,
    UnifiedIntelligenceOverview,
)

logger = logging.getLogger(__name__)


class ResearchIntelligenceService:
    """Core coordinator for unified research intelligence metrics and global discovery."""

    async def get_unified_overview(self, session: AsyncSession) -> UnifiedIntelligenceOverview:
        """Compute aggregated cross-platform research intelligence overview metrics."""
        total_invs = int((await session.scalar(select(func.count(Investigation.id)))) or 0)
        total_claims = int((await session.scalar(select(func.count(Claim.id)))) or 0)
        total_ev = int((await session.scalar(select(func.count(Evidence.id)))) or 0)
        total_sources = int((await session.scalar(select(func.count(Source.id)))) or 0)
        total_gaps = int((await session.scalar(select(func.count(ResearchGap.id)))) or 0)
        total_hyps = int((await session.scalar(select(func.count(ResearchHypothesis.id)))) or 0)
        total_cross_rels = int((await session.scalar(select(func.count(CrossInvestigationRelationship.id)))) or 0)

        # Contradictions
        active_contras = int(
            (
                await session.scalar(
                    select(func.count(ResearchContradiction.id)).where(
                        ResearchContradiction.status.in_(["newly_detected", "under_investigation", "unresolved"])
                    )
                )
            )
            or 0
        )
        resolved_contras = int(
            (
                await session.scalar(
                    select(func.count(ResearchContradiction.id)).where(
                        ResearchContradiction.status.in_(["partially_resolved", "resolved_with_evidence", "scope_difference_identified", "methodological_difference_identified"])
                    )
                )
            )
            or 0
        )

        # Connected investigations count
        connected_srcs = (await session.scalars(select(CrossInvestigationRelationship.source_investigation_id))).all()
        connected_tgts = (await session.scalars(select(CrossInvestigationRelationship.target_investigation_id))).all()
        connected_set = set(connected_srcs).union(set(connected_tgts))

        # Trends count
        active_trends = int((await session.scalar(select(func.count(ResearchTrendTopic.id)))) or 0)

        return UnifiedIntelligenceOverview(
            total_investigations=total_invs,
            connected_investigations=len(connected_set),
            total_claims=total_claims,
            total_evidence=total_ev,
            total_sources=total_sources,
            total_gaps=total_gaps,
            total_hypotheses=total_hyps,
            active_contradictions=active_contras,
            resolved_contradictions=resolved_contras,
            total_cross_relationships=total_cross_rels,
            active_trends_count=active_trends,
            system_status="operational",
            last_updated=datetime.now(UTC),
        )

    async def search_global_research(
        self,
        session: AsyncSession,
        query: str = "",
        category: str = "all",
        limit: int = 40,
    ) -> GlobalResearchSearchResponse:
        """Universal search across all intelligence entities with relevance attribution."""
        q_term = query.strip()
        items: list[GlobalResearchSearchResultItem] = []

        # Load investigation question lookup map
        invs = list((await session.execute(select(Investigation))).scalars().all())
        inv_map = {inv.id: inv.question for inv in invs}

        cat_lower = category.lower()

        # 1. Investigations
        if cat_lower in {"all", "investigation"}:
            stmt = select(Investigation).order_by(Investigation.created_at.desc())
            if q_term:
                stmt = stmt.where(Investigation.question.ilike(f"%{q_term}%"))
            for inv in (await session.execute(stmt.limit(10))).scalars().all():
                items.append(
                    GlobalResearchSearchResultItem(
                        id=str(inv.id),
                        entity_type="investigation",
                        title=inv.question,
                        snippet=f"Investigation status: {inv.status} | Mode: {inv.mode}",
                        investigation_id=str(inv.id),
                        investigation_question=inv.question,
                        severity_or_status=inv.status,
                        created_at=inv.created_at,
                    )
                )

        # 2. Claims
        if cat_lower in {"all", "claim"}:
            stmt = select(Claim).order_by(Claim.priority.asc())
            if q_term:
                stmt = stmt.where(Claim.text.ilike(f"%{q_term}%"))
            for c in (await session.execute(stmt.limit(15))).scalars().all():
                items.append(
                    GlobalResearchSearchResultItem(
                        id=str(c.id),
                        entity_type="claim",
                        title=c.text[:120],
                        snippet=c.explanation or c.text,
                        investigation_id=str(c.investigation_id),
                        investigation_question=inv_map.get(c.investigation_id, ""),
                        severity_or_status=c.status,
                        score=float(c.priority),
                    )
                )

        # 3. Evidence
        if cat_lower in {"all", "evidence"}:
            stmt = select(Evidence).order_by(Evidence.relevance_score.desc())
            if q_term:
                stmt = stmt.where(Evidence.exact_text.ilike(f"%{q_term}%"))
            for ev in (await session.execute(stmt.limit(15))).scalars().all():
                items.append(
                    GlobalResearchSearchResultItem(
                        id=str(ev.id),
                        entity_type="evidence",
                        title=f"Evidence ({ev.evidence_type})",
                        snippet=ev.exact_text[:200],
                        investigation_id=None,
                        severity_or_status=ev.evidence_type,
                        score=ev.relevance_score,
                    )
                )

        # 4. Sources
        if cat_lower in {"all", "source"}:
            stmt = select(Source).order_by(Source.relevance_score.desc())
            if q_term:
                stmt = stmt.where(
                    or_(
                        Source.title.ilike(f"%{q_term}%"),
                        Source.doi.ilike(f"%{q_term}%"),
                    )
                )
            for s in (await session.execute(stmt.limit(10))).scalars().all():
                items.append(
                    GlobalResearchSearchResultItem(
                        id=str(s.id),
                        entity_type="source",
                        title=s.title,
                        snippet=f"Type: {s.source_type} | DOI: {s.doi or 'N/A'}",
                        investigation_id=str(s.investigation_id),
                        investigation_question=inv_map.get(s.investigation_id, ""),
                        score=s.relevance_score,
                    )
                )

        # 5. Hypotheses
        if cat_lower in {"all", "hypothesis"}:
            stmt = select(ResearchHypothesis).order_by(ResearchHypothesis.testability_score.desc())
            if q_term:
                stmt = stmt.where(
                    or_(
                        ResearchHypothesis.title.ilike(f"%{q_term}%"),
                        ResearchHypothesis.statement.ilike(f"%{q_term}%"),
                    )
                )
            for h in (await session.execute(stmt.limit(12))).scalars().all():
                items.append(
                    GlobalResearchSearchResultItem(
                        id=str(h.id),
                        entity_type="hypothesis",
                        title=h.title,
                        snippet=h.statement,
                        investigation_id=str(h.investigation_id),
                        investigation_question=inv_map.get(h.investigation_id, ""),
                        severity_or_status=h.status,
                        score=h.testability_score,
                        created_at=h.created_at,
                    )
                )

        # 6. Research Gaps
        if cat_lower in {"all", "gap"}:
            stmt = select(ResearchGap).order_by(ResearchGap.research_priority.desc())
            if q_term:
                stmt = stmt.where(
                    or_(
                        ResearchGap.title.ilike(f"%{q_term}%"),
                        ResearchGap.description.ilike(f"%{q_term}%"),
                    )
                )
            for g in (await session.execute(stmt.limit(12))).scalars().all():
                items.append(
                    GlobalResearchSearchResultItem(
                        id=str(g.id),
                        entity_type="gap",
                        title=g.title,
                        snippet=g.description,
                        investigation_id=str(g.investigation_id),
                        investigation_question=inv_map.get(g.investigation_id, ""),
                        severity_or_status=g.severity,
                        score=g.research_priority,
                    )
                )

        # 7. Contradictions
        if cat_lower in {"all", "contradiction"}:
            stmt = select(ResearchContradiction).order_by(ResearchContradiction.created_at.desc())
            if q_term:
                stmt = stmt.where(
                    or_(
                        ResearchContradiction.title.ilike(f"%{q_term}%"),
                        ResearchContradiction.description.ilike(f"%{q_term}%"),
                    )
                )
            for contra in (await session.execute(stmt.limit(10))).scalars().all():
                items.append(
                    GlobalResearchSearchResultItem(
                        id=str(contra.id),
                        entity_type="contradiction",
                        title=contra.title,
                        snippet=contra.description,
                        investigation_id=str(contra.primary_investigation_id),
                        investigation_question=inv_map.get(contra.primary_investigation_id, ""),
                        severity_or_status=contra.severity,
                        created_at=contra.created_at,
                    )
                )

        # 8. Trend Topics
        if cat_lower in {"all", "topic"}:
            stmt = select(ResearchTrendTopic).order_by(ResearchTrendTopic.growth_rate.desc())
            if q_term:
                stmt = stmt.where(ResearchTrendTopic.topic_name.ilike(f"%{q_term}%"))
            for t in (await session.execute(stmt.limit(10))).scalars().all():
                items.append(
                    GlobalResearchSearchResultItem(
                        id=str(t.id),
                        entity_type="topic",
                        title=t.topic_name,
                        snippet=t.summary_narrative,
                        severity_or_status=t.classification,
                        score=t.activity_score,
                    )
                )

        return GlobalResearchSearchResponse(
            items=items[:limit],
            total=len(items),
            query=q_term,
        )


research_intelligence_service = ResearchIntelligenceService()
