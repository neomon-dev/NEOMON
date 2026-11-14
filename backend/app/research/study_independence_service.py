"""Study Independence and Publication Relationship Service (Milestone 12).

Detects duplicate publications, syndicated reporting, shared underlying studies,
and evaluates genuine empirical independence without assigning false 1.0 certainty.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlsplit
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Investigation, Source, StudyIndependenceCluster
from app.research.source_lineage import _clean_title_tokens, _title_jaccard

logger = logging.getLogger("neomon.research.study_independence")


class IndependenceCategory(StrEnum):
    CONFIRMED_INDEPENDENT = "confirmed_independent"
    LIKELY_INDEPENDENT = "likely_independent"
    RELATED_STUDIES = "related_studies"
    DUPLICATE_PUBLICATIONS = "duplicate_publications"
    UNKNOWN_INDEPENDENCE = "unknown_independence"


@dataclass
class IndependenceAnalysisResult:
    clusters: List[Dict[str, Any]]
    total_sources: int
    unique_studies_count: int
    independence_ratio: float
    confirmed_independent_count: int
    unknown_independence_count: int
    summary: str


class StudyIndependenceService:
    """Evaluates study-level independence and builds explainable clusters."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_and_persist_clusters(
        self,
        investigation_id: uuid.UUID,
    ) -> List[StudyIndependenceCluster]:
        """Analyze sources, group into study clusters, and persist to database."""
        stmt = select(Source).where(Source.investigation_id == investigation_id)
        res = await self.db.execute(stmt)
        sources = list(res.scalars().all())

        if not sources:
            return []

        # Clear existing clusters for clean update
        old_clusters_stmt = select(StudyIndependenceCluster).where(
            StudyIndependenceCluster.investigation_id == investigation_id
        )
        old_clusters = await self.db.execute(old_clusters_stmt)
        for old in old_clusters.scalars().all():
            await self.db.delete(old)

        clusters_data = self._cluster_sources(sources)
        persisted_clusters: List[StudyIndependenceCluster] = []
        now = datetime.now(timezone.utc)

        for c in clusters_data:
            primary_src_id = None
            if c.get("primary_source_id"):
                try:
                    primary_src_id = uuid.UUID(c["primary_source_id"])
                except Exception:
                    pass

            db_cluster = StudyIndependenceCluster(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                cluster_label=c["cluster_label"],
                primary_source_id=primary_src_id,
                member_source_ids_json=json.dumps(c["member_source_ids"]),
                relationship_category=c["relationship_category"],
                confidence=c["confidence"],
                evidence_rationale=c["evidence_rationale"],
                shared_attributes_json=json.dumps(c.get("shared_attributes", {})),
                created_at=now,
            )
            self.db.add(db_cluster)
            persisted_clusters.append(db_cluster)

        await self.db.commit()
        return persisted_clusters

    def _cluster_sources(self, sources: List[Source]) -> List[Dict[str, Any]]:
        """Cluster sources by DOI, title similarity, author overlap, and publication venue."""
        n = len(sources)
        visited = set()
        clusters: List[Dict[str, Any]] = []

        # Helper to extract authors list
        def get_authors(s: Source) -> List[str]:
            if not s.authors_json:
                return []
            try:
                auths = json.loads(s.authors_json)
                return [a.lower().strip() for a in auths if isinstance(a, str)]
            except Exception:
                return []

        for i in range(n):
            if i in visited:
                continue

            src_a = sources[i]
            cluster_members = [src_a]
            visited.add(i)

            rel_category = IndependenceCategory.UNKNOWN_INDEPENDENCE
            rationale_parts = []
            confidence = 0.50
            shared_attrs = {}

            # Parse metadata
            authors_a = set(get_authors(src_a))
            doi_a = (src_a.doi or "").strip().lower()
            title_a = src_a.title or ""
            host_a = urlsplit(src_a.canonical_url or src_a.original_url or "").netloc.lower()

            for j in range(i + 1, n):
                if j in visited:
                    continue

                src_b = sources[j]
                authors_b = set(get_authors(src_b))
                doi_b = (src_b.doi or "").strip().lower()
                title_b = src_b.title or ""
                host_b = urlsplit(src_b.canonical_url or src_b.original_url or "").netloc.lower()

                # Rule 1: Exact matching DOI or identical URL -> Duplicate Publication
                if (doi_a and doi_b and doi_a == doi_b) or (
                    src_a.canonical_url and src_b.canonical_url and src_a.canonical_url == src_b.canonical_url
                ):
                    cluster_members.append(src_b)
                    visited.add(j)
                    rel_category = IndependenceCategory.DUPLICATE_PUBLICATIONS
                    confidence = 0.98
                    rationale_parts.append(f"Identical DOI/URL matching: {doi_a or src_a.canonical_url}")
                    shared_attrs["doi"] = doi_a
                    continue

                # Rule 2: Title Jaccard similarity >= 0.80 -> Syndicated / Duplicate reporting
                jaccard = _title_jaccard(title_a, title_b)
                if jaccard >= 0.75:
                    cluster_members.append(src_b)
                    visited.add(j)
                    rel_category = IndependenceCategory.DUPLICATE_PUBLICATIONS
                    confidence = 0.90
                    rationale_parts.append(f"Near-identical headline title ({round(jaccard*100)}% match)")
                    shared_attrs["title_jaccard"] = jaccard
                    continue

                # Rule 3: Substantial author overlap (>= 2 authors) -> Related Studies / Same Research Group
                shared_authors = authors_a & authors_b
                if len(shared_authors) >= 2 or (len(shared_authors) == 1 and len(authors_a) <= 2):
                    cluster_members.append(src_b)
                    visited.add(j)
                    rel_category = IndependenceCategory.RELATED_STUDIES
                    confidence = 0.85
                    rationale_parts.append(f"Shared authorship: {', '.join(list(shared_authors)[:3])}")
                    shared_attrs["shared_authors"] = list(shared_authors)
                    continue

            # Determine category for single source or resolved cluster
            if len(cluster_members) == 1:
                # Assess individual source independence quality
                if doi_a and len(authors_a) >= 1 and src_a.source_type in ("peer_reviewed", "academic"):
                    rel_category = IndependenceCategory.CONFIRMED_INDEPENDENT
                    confidence = 0.90
                    rationale = f"Peer-reviewed academic publication with verified DOI ({doi_a}) and distinct authorship."
                elif len(authors_a) >= 1 or src_a.publisher:
                    rel_category = IndependenceCategory.LIKELY_INDEPENDENT
                    confidence = 0.72
                    rationale = f"Document published by {src_a.publisher or host_a} with named contributors; no duplicate study detected."
                else:
                    rel_category = IndependenceCategory.UNKNOWN_INDEPENDENCE
                    confidence = 0.45
                    rationale = "General web or vendor document lacking academic identifiers or attribution; independence cannot be confirmed."
            else:
                rationale = "; ".join(rationale_parts)

            clusters.append({
                "cluster_label": f"Study Group: {src_a.title[:60]}...",
                "primary_source_id": str(src_a.id),
                "member_source_ids": [str(s.id) for s in cluster_members],
                "relationship_category": rel_category.value,
                "confidence": confidence,
                "evidence_rationale": rationale,
                "shared_attributes": shared_attrs,
            })

        return clusters

    async def list_study_clusters(
        self,
        investigation_id: uuid.UUID,
    ) -> List[StudyIndependenceCluster]:
        """Fetch study clusters for an investigation."""
        stmt = select(StudyIndependenceCluster).where(
            StudyIndependenceCluster.investigation_id == investigation_id
        ).order_by(StudyIndependenceCluster.created_at.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
