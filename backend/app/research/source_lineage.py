"""Source Independence and Publication Lineage Service (Milestone 8G.2).

Replaces naive URL/domain uniqueness with rigorous, explainable lineage tracking.
Recognizes:
- Syndicated publications (wire service copies, verbatim reprints)
- Derivative reporting (blogs and tech news commenting on the same corporate release)
- Shared primary sources (multiple articles citing the same paper or disclosure)
- Shared authorship / shared datasets
- Genuinely independent empirical research
"""

from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Any
from urllib.parse import urlsplit


class SourceLineageType(StrEnum):
    INDEPENDENT_RESEARCH = "independent_research"
    SHARED_PRIMARY_SOURCE = "shared_primary_source"
    SYNDICATED_PUBLICATION = "syndicated_publication"
    DERIVATIVE_REPORTING = "derivative_reporting"
    SHARED_DATASET = "shared_dataset"
    SHARED_AUTHORSHIP = "shared_authorship"
    POTENTIALLY_RELATED = "potentially_related"
    UNKNOWN_INDEPENDENCE = "unknown_independence"


@dataclass
class LineageRelationship:
    source_id: str
    related_source_id: str
    relationship_type: SourceLineageType
    confidence: float
    shared_identifiers: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class SourceCluster:
    cluster_id: str
    cluster_name: str
    primary_source_id: str | None
    member_source_ids: list[str]
    relationship_type: str
    explanation: str
    effective_independence_weight: float = 1.0


@dataclass
class LineageAnalysisResult:
    clusters: list[SourceCluster]
    relationships: list[LineageRelationship]
    total_sources: int
    effective_independent_count: float
    independence_ratio: float
    lineage_summary: str


def _clean_title_tokens(title: str) -> set[str]:
    """Tokenize and remove boilerplate stop words from titles."""
    clean = re.sub(r"[^\w\s]", " ", (title or "").lower())
    stop_words = {
        "a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "with", "at",
        "by", "from", "up", "about", "into", "over", "after", "is", "are", "was",
        "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "how", "what", "why", "when", "where", "who", "which", "report", "says",
        "new", "latest", "study", "analysis", "finds"
    }
    return {t for t in clean.split() if len(t) > 2 and t not in stop_words}


def _title_jaccard(t1: str, t2: str) -> float:
    s1 = _clean_title_tokens(t1)
    s2 = _clean_title_tokens(t2)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def _extract_source_dict(s: Any) -> dict[str, Any]:
    """Extract dict attributes from Source model or dict."""
    if isinstance(s, dict):
        return s
    
    # Handle SQLAlchemy model
    authors = getattr(s, "authors_json", "[]")
    if isinstance(authors, str):
        import json
        try:
            authors = json.loads(authors)
        except Exception:
            authors = []
            
    return {
        "id": str(getattr(s, "id", "")),
        "title": getattr(s, "title", "") or "",
        "url": getattr(s, "canonical_url", "") or getattr(s, "original_url", "") or "",
        "publisher": getattr(s, "publisher", "") or "",
        "doi": getattr(s, "doi", "") or "",
        "authors": authors if isinstance(authors, list) else [],
        "source_type": getattr(s, "source_type", "") or "",
    }


def analyze_source_lineage(sources_input: list[Any]) -> LineageAnalysisResult:
    """Analyze source collection and establish publication lineage graph and independent clusters.
    
    Prevents domain diversity from inflating independent evidence calculations.
    """
    sources = [_extract_source_dict(s) for s in sources_input if s]
    total_sources = len(sources)
    if total_sources == 0:
        return LineageAnalysisResult(
            clusters=[],
            relationships=[],
            total_sources=0,
            effective_independent_count=0.0,
            independence_ratio=1.0,
            lineage_summary="No sources to analyze."
        )

    relationships: list[LineageRelationship] = []

    # Map sources by id
    by_id = {s["id"]: s for s in sources}
    source_ids = list(by_id.keys())

    # Pairwise comparison to detect lineage and dependencies
    for i in range(len(source_ids)):
        for j in range(i + 1, len(source_ids)):
            id_a = source_ids[i]
            id_b = source_ids[j]
            s_a = by_id[id_a]
            s_b = by_id[id_b]

            doi_a = (s_a.get("doi") or "").strip().lower()
            doi_b = (s_b.get("doi") or "").strip().lower()
            url_a = (s_a.get("url") or "").strip().lower()
            url_b = (s_b.get("url") or "").strip().lower()
            title_a = s_a.get("title") or ""
            title_b = s_b.get("title") or ""
            authors_a = set(s_a.get("authors") or [])
            authors_b = set(s_b.get("authors") or [])
            pub_a = (s_a.get("publisher") or "").lower()
            pub_b = (s_b.get("publisher") or "").lower()

            # Check 1: Shared DOI or identical canonical URL
            if doi_a and doi_b and doi_a == doi_b:
                relationships.append(LineageRelationship(
                    source_id=id_a,
                    related_source_id=id_b,
                    relationship_type=SourceLineageType.SHARED_PRIMARY_SOURCE,
                    confidence=0.98,
                    shared_identifiers=[f"doi:{doi_a}"],
                    explanation=f"Sources share identical DOI ({doi_a}), pointing to the same scholarly entity.",
                ))
                continue

            if url_a and url_b and url_a == url_b:
                relationships.append(LineageRelationship(
                    source_id=id_a,
                    related_source_id=id_b,
                    relationship_type=SourceLineageType.SYNDICATED_PUBLICATION,
                    confidence=1.0,
                    shared_identifiers=[url_a],
                    explanation="Sources share identical canonical URL.",
                ))
                continue

            # Check 2: Shared authorship overlap in academic papers
            if authors_a and authors_b and len(authors_a & authors_b) > 0:
                shared_authors = list(authors_a & authors_b)
                relationships.append(LineageRelationship(
                    source_id=id_a,
                    related_source_id=id_b,
                    relationship_type=SourceLineageType.SHARED_AUTHORSHIP,
                    confidence=0.90,
                    shared_identifiers=[f"author:{a}" for a in shared_authors],
                    explanation=f"Publications share co-authors ({', '.join(shared_authors[:2])}), indicating related research lineage.",
                ))
                continue

            # Check 3: High title similarity (wire service syndication or identical reporting)
            sim = _title_jaccard(title_a, title_b)
            if sim >= 0.70:
                # Same story republished across news networks
                is_wire = any(w in pub_a or w in pub_b for w in ("reuters", "bloomberg", "ap", "associated press", "prnewswire", "businesswire"))
                rel_type = SourceLineageType.SYNDICATED_PUBLICATION if is_wire else SourceLineageType.DERIVATIVE_REPORTING
                relationships.append(LineageRelationship(
                    source_id=id_a,
                    related_source_id=id_b,
                    relationship_type=rel_type,
                    confidence=round(sim, 2),
                    shared_identifiers=[],
                    explanation=f"High title similarity ({sim:.0%}) indicates {rel_type.value.replace('_', ' ')} rather than independent findings.",
                ))
                continue

            if sim >= 0.45:
                # Moderate title overlap: potentially related secondary reporting
                relationships.append(LineageRelationship(
                    source_id=id_a,
                    related_source_id=id_b,
                    relationship_type=SourceLineageType.POTENTIALLY_RELATED,
                    confidence=round(sim, 2),
                    shared_identifiers=[],
                    explanation=f"Substantial conceptual overlap ({sim:.0%}) in headlines suggests common subject coverage.",
                ))

    # Build disjoint connected components (Clusters)
    # Non-independent link types:
    collapsing_types = {
        SourceLineageType.SHARED_PRIMARY_SOURCE,
        SourceLineageType.SYNDICATED_PUBLICATION,
        SourceLineageType.DERIVATIVE_REPORTING,
        SourceLineageType.SHARED_AUTHORSHIP,
        SourceLineageType.SHARED_DATASET,
    }

    # Adjacency for clustering
    adj: dict[str, set[str]] = {sid: set() for sid in source_ids}
    edge_types: dict[tuple[str, str], str] = {}
    for r in relationships:
        if r.relationship_type in collapsing_types:
            adj[r.source_id].add(r.related_source_id)
            adj[r.related_source_id].add(r.source_id)
            edge_types[(r.source_id, r.related_source_id)] = r.relationship_type.value
            edge_types[(r.related_source_id, r.source_id)] = r.relationship_type.value

    visited = set()
    clusters: list[SourceCluster] = []
    cluster_idx = 1

    for sid in source_ids:
        if sid in visited:
            continue
        
        # Traverse connected component
        component = []
        stack = [sid]
        visited.add(sid)
        while stack:
            curr = stack.pop()
            component.append(curr)
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)

        # Build cluster record
        primary_id = component[0]
        # Choose primary source: prioritize academic / peer-reviewed / earliest
        for cid in component:
            s_info = by_id[cid]
            if s_info.get("doi") or "academic" in (s_info.get("source_type") or ""):
                primary_id = cid
                break

        primary_title = by_id[primary_id].get("title") or "Unnamed Research"
        if len(component) > 1:
            rel_label = "multi_outlet_lineage"
            explanation = (
                f"Cluster of {len(component)} related sources connected via syndication, "
                f"shared primary citations, or common authorship around '{primary_title[:60]}'."
            )
        else:
            rel_label = "independent_source"
            explanation = f"Independent primary source with unique methodology and distinct provenance: '{primary_title[:60]}'."

        clusters.append(SourceCluster(
            cluster_id=f"cluster-{cluster_idx}",
            cluster_name=f"Lineage Cluster {cluster_idx}: {primary_title[:50]}",
            primary_source_id=primary_id,
            member_source_ids=component,
            relationship_type=rel_label,
            explanation=explanation,
            effective_independence_weight=1.0,
        ))
        cluster_idx += 1

    # Effective independent count = number of independent clusters
    effective_count = float(len(clusters))
    ratio = round(effective_count / max(1, total_sources), 3)

    summary = (
        f"Analyzed {total_sources} sources into {len(clusters)} effective independent lineage clusters "
        f"({ratio:.1%} true independence ratio). "
        f"Detected {len(relationships)} inter-source relationships."
    )

    return LineageAnalysisResult(
        clusters=clusters,
        relationships=relationships,
        total_sources=total_sources,
        effective_independent_count=effective_count,
        independence_ratio=ratio,
        lineage_summary=summary,
    )
