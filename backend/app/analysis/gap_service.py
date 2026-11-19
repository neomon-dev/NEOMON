"""Autonomous Research Gap Discovery Service for NEOMON.

Implements Milestone 8A:
- Deep multi-dimensional gap analysis:
  1. Claim coverage gaps (unsupported, single source, contradictory, contextual only, unresolved provenance).
  2. Evidence coverage gaps (missing full-text, preprints only / missing primary studies, lack of replication).
  3. Perspective gaps (unbalanced advocacy/skepticism, missing mitigating factors, tradeoff/disciplinary gaps).
  4. Research question gaps (unanswered subquestions with motivating claims and targeted search queries).
- Deterministic-first verification: observed facts cannot be overridden by LLM.
- Research priority and investigation coverage scoring.
- Actionable provider query recommendations.
- Versioned persistence with full traceability.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.protocol import EvidenceProvenance
from app.analysis.service import _extract_json_object
from app.models import (
    AdjudicationDecision,
    AgentArgument,
    AnalysisAgentExecution,
    AnalysisJob,
    Claim,
    ClaimEvidenceRelationship,
    Document,
    Evidence,
    Investigation,
    ResearchGap,
    ResearchGapAnalysis,
    Source,
)
from app.providers import create_provider
from app.providers.base import AIProvider
from app.research.relevance import _term_matches, _terms, question_focus
from app.research.scientific_integrity import (
    EvidenceCategory,
    SourceCredibilityType,
    assess_source_credibility,
    classify_evidence_for_claim,
    detect_source_independence_clusters,
)
from app.schemas import (
    GapCategory,
    GapConfidence,
    GapSeverity,
    RecommendedAction,
    ResearchCoverageSummary,
    ResearchGapAnalysisResponse,
    ResearchGapVersionView,
    ResearchGapView,
)

logger = logging.getLogger(__name__)


def _calculate_priority(
    severity: str,
    claim_priority: int = 2,
    has_contradiction: bool = False,
    has_unresolved_provenance: bool = False,
    independent_clusters: int = 1,
) -> float:
    """Calculate an objective research priority score from 1.0 to 10.0."""
    base_severity_scores = {
        GapSeverity.critical.value: 4.5,
        GapSeverity.high.value: 3.5,
        GapSeverity.moderate.value: 2.2,
        GapSeverity.low.value: 1.2,
    }
    score = base_severity_scores.get(severity, 2.5)

    # Claim priority weighting (priority 1 is highest in NEOMON)
    if claim_priority == 1:
        score += 2.5
    elif claim_priority == 2:
        score += 1.5
    elif claim_priority >= 3:
        score += 0.5

    # Conflict / integrity weighting
    if has_unresolved_provenance:
        score += 2.0
    if has_contradiction:
        score += 1.8

    # Cluster adjustment: fewer independent sources increases research urgency
    if independent_clusters <= 1:
        score += 1.0
    elif independent_clusters >= 3:
        score -= 0.5

    return round(max(1.0, min(10.0, score)), 1)


def _generate_provider_queries(subject: str, context: str, objective: str = "") -> list[str]:
    """Generate high-yield provider search queries tailored for search providers."""
    subj = subject.strip().rstrip("?.")
    clean_ctx = re.sub(r"[^\w\s-]", " ", context).strip()
    words = [w for w in clean_ctx.split() if len(w) > 3 and w.lower() not in {"this", "that", "with", "from", "have", "were"}]
    focus_kw = " ".join(words[:4]) if words else ""

    queries = []
    if focus_kw:
        queries.append(f"{subj} {focus_kw}")
    else:
        queries.append(f"{subj} empirical evidence")

    if objective:
        clean_obj = re.sub(r"[^\w\s-]", " ", objective).strip()
        obj_words = [w for w in clean_obj.split() if len(w) > 3][:4]
        if obj_words:
            queries.append(f"{subj} {' '.join(obj_words)}")

    queries.append(f"{subj} peer reviewed empirical findings")
    queries.append(f"{subj} counter evidence limitations")

    # Deduplicate preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for q in queries:
        q_norm = " ".join(q.lower().split())
        if q_norm not in seen:
            seen.add(q_norm)
            deduped.append(q)
    return deduped[:4]


class ResearchGapEngine:
    """Core engine for detecting evidence gaps, perspective imbalances, and unaddressed questions."""

    async def analyze_investigation(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        provider_kind: str | None = None,
        model: str | None = None,
        force_regenerate: bool = False,
    ) -> ResearchGapAnalysisResponse:
        """Run deep autonomous research gap analysis for an investigation."""
        # 1. Check if cached analysis exists when force_regenerate is False
        if not force_regenerate:
            existing = await self.get_latest_gap_analysis(session, investigation_id)
            if existing is not None:
                return existing

        # 2. Fetch full investigation record
        stmt_inv = select(Investigation).where(Investigation.id == investigation_id)
        res_inv = await session.execute(stmt_inv)
        inv = res_inv.scalar_one_or_none()
        if inv is None:
            raise ValueError(f"Investigation {investigation_id} not found")

        # 3. Load all related entities
        claims_stmt = (
            select(Claim)
            .where(Claim.investigation_id == investigation_id)
            .order_by(Claim.priority.asc())
        )
        claims = list((await session.execute(claims_stmt)).scalars().all())

        sources_stmt = (
            select(Source)
            .where(Source.investigation_id == investigation_id)
            .order_by(Source.relevance_score.desc())
        )
        sources = list((await session.execute(sources_stmt)).scalars().all())

        # Load documents for full-text checks
        source_ids = [s.id for s in sources]
        docs: list[Document] = []
        if source_ids:
            docs_stmt = select(Document).where(Document.source_id.in_(source_ids))
            docs = list((await session.execute(docs_stmt)).scalars().all())
        docs_by_source: dict[uuid.UUID, list[Document]] = defaultdict(list)
        for d in docs:
            docs_by_source[d.source_id].append(d)

        # Load evidence across sources and claims of this investigation
        claim_ids = [c.id for c in claims]
        evidence_items_dict: dict[uuid.UUID, Evidence] = {}

        if source_ids:
            ev_src_stmt = (
                select(Evidence)
                .where(Evidence.source_id.in_(source_ids))
                .order_by(Evidence.relevance_score.desc())
            )
            for ev in (await session.execute(ev_src_stmt)).scalars().all():
                evidence_items_dict[ev.id] = ev

        if claim_ids:
            ev_claim_stmt = (
                select(Evidence)
                .where(Evidence.claim_id.in_(claim_ids))
                .order_by(Evidence.relevance_score.desc())
            )
            for ev in (await session.execute(ev_claim_stmt)).scalars().all():
                evidence_items_dict[ev.id] = ev

            ev_rel_stmt = (
                select(Evidence)
                .join(ClaimEvidenceRelationship, Evidence.id == ClaimEvidenceRelationship.evidence_id)
                .where(ClaimEvidenceRelationship.claim_id.in_(claim_ids))
                .order_by(Evidence.relevance_score.desc())
            )
            for ev in (await session.execute(ev_rel_stmt)).scalars().all():
                evidence_items_dict[ev.id] = ev

        evidence_items = list(evidence_items_dict.values())

        # Load claim-evidence relationships
        rel_stmt = (
            select(ClaimEvidenceRelationship)
            .join(Claim, ClaimEvidenceRelationship.claim_id == Claim.id)
            .where(Claim.investigation_id == investigation_id)
        )
        relationships = list((await session.execute(rel_stmt)).scalars().all())
        evidence_by_claim: dict[uuid.UUID, list[Evidence]] = defaultdict(list)
        claim_ev_rel_map: dict[tuple[uuid.UUID, uuid.UUID], ClaimEvidenceRelationship] = {}
        ev_id_to_item = {e.id: e for e in evidence_items}
        for r in relationships:
            if r.evidence_id in ev_id_to_item:
                ev_obj = ev_id_to_item[r.evidence_id]
                evidence_by_claim[r.claim_id].append(ev_obj)
                claim_ev_rel_map[(r.claim_id, r.evidence_id)] = r

        # Fallback: if evidence has claim_id directly set
        for e in evidence_items:
            if e.claim_id and e.claim_id in [c.id for c in claims]:
                if e not in evidence_by_claim[e.claim_id]:
                    evidence_by_claim[e.claim_id].append(e)

        # Load adjudication decisions
        decisions_stmt = (
            select(AdjudicationDecision)
            .join(AnalysisJob, AdjudicationDecision.job_id == AnalysisJob.id)
            .where(AnalysisJob.investigation_id == investigation_id)
        )
        decisions = list((await session.execute(decisions_stmt)).scalars().all())
        decisions_by_claim = {d.claim_id: d for d in decisions}

        # Load arguments
        args_stmt = (
            select(AgentArgument)
            .join(AnalysisJob, AgentArgument.job_id == AnalysisJob.id)
            .where(AnalysisJob.investigation_id == investigation_id)
        )
        agent_arguments = list((await session.execute(args_stmt)).scalars().all())

        # 4. Perform Source Independence Clustering
        source_dicts = []
        for s in sources:
            source_dicts.append({
                "id": str(s.id),
                "title": s.title,
                "url": s.canonical_url or s.original_url,
                "publisher": s.publisher,
                "doi": s.doi,
                "source_type": s.source_type,
            })
        ind_result = detect_source_independence_clusters(source_dicts)
        independent_cluster_count = len(ind_result.clusters) if ind_result else len(sources)

        # 5. Deterministic Gap Discovery Across Dimensions
        discovered_gaps: list[dict[str, Any]] = []

        # Track investigation-wide metrics
        claims_with_direct_support = 0
        claims_with_conflicts = 0
        claims_unsupported = 0
        claims_single_source = 0
        unresolved_provenance_count = 0

        # Check evidence provenance across investigation
        for e in evidence_items:
            is_unresolved = (not getattr(e, "traceable", True)) or (
                "[UNRESOLVED PROVENANCE]" in (getattr(e, "relevance_reason", "") or "")
            )
            if is_unresolved:
                unresolved_provenance_count += 1

        # DIMENSION A: CLAIM COVERAGE GAPS
        for c in claims:
            c_ev = evidence_by_claim.get(c.id, [])
            c_sources = [ev_id_to_item[e.id].source_id for e in c_ev if e.id in ev_id_to_item]
            unique_c_sources = set(c_sources)

            # Categorize evidence for this claim
            supporting_ev = []
            contradicting_ev = []
            contextual_ev = []
            insufficient_ev = []
            provenance_flawed_ev = []

            for ev in c_ev:
                ev_type = getattr(ev, "evidence_type", "").lower()
                rel_type = ""
                if (c.id, ev.id) in claim_ev_rel_map:
                    rel_type = (claim_ev_rel_map[(c.id, ev.id)].relationship_type or "").lower()

                is_prov_bad = (not getattr(ev, "traceable", True)) or (
                    "[UNRESOLVED PROVENANCE]" in (getattr(ev, "relevance_reason", "") or "")
                )
                if is_prov_bad:
                    provenance_flawed_ev.append(ev)

                if rel_type == "supporting" or ev_type in {"supporting", "direct"}:
                    supporting_ev.append(ev)
                elif rel_type == "contradicting" or ev_type in {"contradicting", "counter"}:
                    contradicting_ev.append(ev)
                elif rel_type == "contextual" or ev_type == "contextual":
                    contextual_ev.append(ev)
                elif ev_type in {"insufficient", "unrelated"}:
                    insufficient_ev.append(ev)
                else:
                    # Fallback classify
                    classification = classify_evidence_for_claim(c.text, ev.exact_text)
                    if classification.category == EvidenceCategory.SUPPORTING:
                        supporting_ev.append(ev)
                    elif classification.category == EvidenceCategory.CONTRADICTING:
                        contradicting_ev.append(ev)
                    elif classification.category == EvidenceCategory.CONTEXTUAL:
                        contextual_ev.append(ev)
                    else:
                        insufficient_ev.append(ev)

            # Check 1: Claims without supporting evidence
            if not supporting_ev:
                claims_unsupported += 1
                severity = GapSeverity.critical.value if c.priority == 1 else GapSeverity.high.value
                prio = _calculate_priority(severity, claim_priority=c.priority, independent_clusters=0)
                queries = _generate_provider_queries(inv.question, c.text)
                discovered_gaps.append({
                    "category": GapCategory.claim_coverage.value,
                    "gap_type": "no_supporting_evidence",
                    "title": f"No supporting evidence for claim: '{c.text[:80]}...'",
                    "description": (
                        f"Claim '{c.text}' lacks any direct or empirical supporting evidence passages in the current corpus. "
                        "Conclusions depending on this claim are scientifically ungrounded."
                    ),
                    "claim_ids": [c.id],
                    "evidence_ids": [e.id for e in c_ev],
                    "source_ids": list(unique_c_sources),
                    "supporting_explanation": (
                        f"Analyzed {len(c_ev)} evidence passage(s) associated with this claim; 0 direct or supporting "
                        "passages corroborate the asserted directional finding."
                    ),
                    "missing_information": (
                        "Peer-reviewed empirical studies, benchmark metrics, or verified experimental results "
                        "corroborating this specific assertion."
                    ),
                    "severity": severity,
                    "research_priority": prio,
                    "confidence": GapConfidence.high.value,
                    "is_observed": True,
                    "recommended_action": RecommendedAction(
                        action_type="provider_search",
                        description=f"Execute targeted multi-provider retrieval focusing on empirical validation of '{c.text[:90]}'.",
                        suggested_queries=queries,
                        target_source_types=["peer_reviewed", "empirical_study", "benchmark"],
                        expected_contribution="Establishes evidentiary grounding for a foundational claim in the investigation.",
                    ),
                })
            else:
                claims_with_direct_support += 1

            # Check 2: Claims supported by only contextual evidence
            if not supporting_ev and not contradicting_ev and contextual_ev:
                severity = GapSeverity.high.value if c.priority == 1 else GapSeverity.moderate.value
                prio = _calculate_priority(severity, claim_priority=c.priority)
                queries = _generate_provider_queries(inv.question, f"{c.text} causal quantitative", c.text)
                discovered_gaps.append({
                    "category": GapCategory.claim_coverage.value,
                    "gap_type": "only_contextual_evidence",
                    "title": f"Contextual evidence only for claim: '{c.text[:80]}...'",
                    "description": (
                        f"Claim '{c.text}' is backed exclusively by definitional or background context. "
                        "No directional causal evidence has been extracted."
                    ),
                    "claim_ids": [c.id],
                    "evidence_ids": [e.id for e in contextual_ev],
                    "source_ids": list(unique_c_sources),
                    "supporting_explanation": (
                        f"All {len(contextual_ev)} passage(s) provide general context or definitions without testing "
                        "or corroborating the specific claim mechanism."
                    ),
                    "missing_information": (
                        "Direct directional evidence showing cause, effect, or quantitative correlation."
                    ),
                    "severity": severity,
                    "research_priority": prio,
                    "confidence": GapConfidence.high.value,
                    "is_observed": True,
                    "recommended_action": RecommendedAction(
                        action_type="provider_search",
                        description="Retrieve empirical studies demonstrating direct causal mechanisms rather than background definitions.",
                        suggested_queries=queries,
                        target_source_types=["peer_reviewed", "empirical_study"],
                        expected_contribution="Upgrades evidentiary strength from contextual background to direct proof.",
                    ),
                })

            # Check 3: Single source dependency (lack of independent corroboration)
            if supporting_ev:
                # Group supporting evidence sources by cluster
                supporting_sources = [ev_id_to_item[e.id].source_id for e in supporting_ev if e.id in ev_id_to_item]
                supp_unique_sources = set(supporting_sources)
                # Count independent clusters for these sources
                claim_clusters = set()
                for s_id in supp_unique_sources:
                    assigned = False
                    for cl in ind_result.clusters:
                        if str(s_id) in [str(x) for x in cl.source_ids]:
                            claim_clusters.add(cl.cluster_id)
                            assigned = True
                            break
                    if not assigned:
                        claim_clusters.add(str(s_id))

                if len(claim_clusters) <= 1:
                    claims_single_source += 1
                    severity = GapSeverity.high.value if c.priority == 1 else GapSeverity.moderate.value
                    prio = _calculate_priority(severity, claim_priority=c.priority, independent_clusters=1)
                    queries = _generate_provider_queries(inv.question, f"independent validation {c.text}")
                    discovered_gaps.append({
                        "category": GapCategory.claim_coverage.value,
                        "gap_type": "single_source_dependency",
                        "title": f"Single source dependency on claim: '{c.text[:80]}...'",
                        "description": (
                            f"Claim '{c.text}' is supported by evidence derived from only one independent origin cluster. "
                            "Conclusions risk single-source bias or syndication echo chambers."
                        ),
                        "claim_ids": [c.id],
                        "evidence_ids": [e.id for e in supporting_ev],
                        "source_ids": list(supp_unique_sources),
                        "supporting_explanation": (
                            f"Identified {len(supporting_ev)} supporting passage(s), but all originate from "
                            f"{'a single origin cluster' if len(supp_unique_sources) > 1 else 'one individual source'}. "
                            "Independent multi-center replication is missing."
                        ),
                        "missing_information": (
                            "Independent replication from distinct research teams, publishers, or institutional frameworks."
                        ),
                        "severity": severity,
                        "research_priority": prio,
                        "confidence": GapConfidence.high.value,
                        "is_observed": True,
                        "recommended_action": RecommendedAction(
                            action_type="provider_search",
                            description="Search for independent empirical investigations from competing research labs or alternate journals.",
                            suggested_queries=queries,
                            target_source_types=["peer_reviewed", "research_organization"],
                            expected_contribution="Validates findings across independent institutions and mitigates publishing bias.",
                        ),
                    })

            # Check 4: Unresolved contradiction
            if supporting_ev and contradicting_ev:
                claims_with_conflicts += 1
                dec = decisions_by_claim.get(c.id)
                is_unresolved = (dec is None) or (dec.decision in {"contradictory", "inconclusive", "unassessed"})
                severity = GapSeverity.critical.value if c.priority == 1 else GapSeverity.high.value
                prio = _calculate_priority(severity, claim_priority=c.priority, has_contradiction=True)
                queries = _generate_provider_queries(inv.question, f"discrepancy boundary conditions {c.text}")
                discovered_gaps.append({
                    "category": GapCategory.claim_coverage.value,
                    "gap_type": "unresolved_contradiction",
                    "title": f"Unresolved empirical contradiction for claim: '{c.text[:80]}...'",
                    "description": (
                        f"Claim '{c.text}' has conflicting empirical evidence ({len(supporting_ev)} supporting vs "
                        f"{len(contradicting_ev)} contradicting) without a decisive evidentiary resolution."
                    ),
                    "claim_ids": [c.id],
                    "evidence_ids": [e.id for e in supporting_ev + contradicting_ev],
                    "source_ids": list(unique_c_sources),
                    "supporting_explanation": (
                        f"Found {len(supporting_ev)} supporting and {len(contradicting_ev)} contradicting passage(s). "
                        f"Adjudication state: {dec.decision if dec else 'no adjudication record'}."
                    ),
                    "missing_information": (
                        "Comparative studies or meta-analyses examining differences in testing methodologies, sample cohorts, "
                        "or operational thresholds that account for the conflicting findings."
                    ),
                    "severity": severity,
                    "research_priority": prio,
                    "confidence": GapConfidence.high.value,
                    "is_observed": True,
                    "recommended_action": RecommendedAction(
                        action_type="conflict_resolution",
                        description="Conduct targeted query focusing on comparative trial conditions and boundary parameters.",
                        suggested_queries=queries,
                        target_source_types=["meta_analysis", "systematic_review", "peer_reviewed"],
                        expected_contribution="Reconciles conflicting evidentiary claims and establishes clear boundary conditions.",
                    ),
                })

            # Check 5: Unresolved provenance flaws on evidence
            if provenance_flawed_ev:
                prio = _calculate_priority(GapSeverity.critical.value, claim_priority=c.priority, has_unresolved_provenance=True)
                queries = _generate_provider_queries(inv.question, f"primary document {c.text}")
                discovered_gaps.append({
                    "category": GapCategory.claim_coverage.value,
                    "gap_type": "unresolved_provenance",
                    "title": f"Unresolved evidence provenance on claim: '{c.text[:80]}...'",
                    "description": (
                        f"{len(provenance_flawed_ev)} evidence passage(s) tied to '{c.text}' failed provenance integrity verification "
                        "(e.g., text mismatch, missing full-text backing, or section hallucination)."
                    ),
                    "claim_ids": [c.id],
                    "evidence_ids": [e.id for e in provenance_flawed_ev],
                    "source_ids": list({ev_id_to_item[e.id].source_id for e in provenance_flawed_ev if e.id in ev_id_to_item}),
                    "supporting_explanation": (
                        "Passages failed strict string containment or integrity checks against document content records. "
                        "Unresolved provenance severely degrades research defensibility."
                    ),
                    "missing_information": (
                        "Verified primary document full-text with matching cryptographic content hash and validated section headers."
                    ),
                    "severity": GapSeverity.critical.value,
                    "research_priority": prio,
                    "confidence": GapConfidence.high.value,
                    "is_observed": True,
                    "recommended_action": RecommendedAction(
                        action_type="full_text_acquisition",
                        description="Re-acquire verified open-access document full-text and re-extract passages with strict offsets.",
                        suggested_queries=queries,
                        target_source_types=["open_access_pdf", "author_accepted_manuscript"],
                        expected_contribution="Restores cryptographic provenance auditability for challenged evidence.",
                    ),
                })

        # DIMENSION B: EVIDENCE COVERAGE GAPS
        # Check 1: Missing full text documents
        sources_without_full_text = []
        for s in sources:
            s_docs = docs_by_source.get(s.id, [])
            has_ft = any(getattr(d, "access_level", "") == "full_text" for d in s_docs)
            if not has_ft:
                sources_without_full_text.append(s)

        if sources_without_full_text:
            ft_ratio = (len(sources) - len(sources_without_full_text)) / max(1, len(sources))
            severity = GapSeverity.high.value if ft_ratio < 0.5 else GapSeverity.moderate.value
            prio = _calculate_priority(severity, claim_priority=2)
            discovered_gaps.append({
                "category": GapCategory.evidence_coverage.value,
                "gap_type": "missing_full_text",
                "title": f"Missing full-text documents for {len(sources_without_full_text)} source(s)",
                "description": (
                    f"{len(sources_without_full_text)} of {len(sources)} sources have only abstract or metadata-level coverage. "
                    "In-depth methodology, experimental protocols, and nuanced qualifiers remain uninspected."
                ),
                "claim_ids": [c.id for c in claims[:3]],
                "evidence_ids": [],
                "source_ids": [s.id for s in sources_without_full_text[:10]],
                "supporting_explanation": (
                    f"Only {len(sources) - len(sources_without_full_text)} of {len(sources)} sources have full-text records. "
                    "Abstract-only evidence is prone to over-simplification."
                ),
                "missing_information": "Complete article text, methodology descriptions, and statistical tables.",
                "severity": severity,
                "research_priority": prio,
                "confidence": GapConfidence.high.value,
                "is_observed": True,
                "recommended_action": RecommendedAction(
                    action_type="full_text_acquisition",
                    description="Trigger OpenAlex, Unpaywall, and arXiv open-access full-text retrieval for incomplete sources.",
                    suggested_queries=[f"doi:{s.doi}" for s in sources_without_full_text if s.doi][:3] or [
                        f"{inv.question} full text pdf download",
                    ],
                    target_source_types=["open_access_repository", "institutional_archive"],
                    expected_contribution="Unlocks deep evidentiary validation and methodological audit beyond brief abstracts.",
                ),
            })

        # Check 2: Missing primary / peer-reviewed empirical studies
        peer_reviewed_count = 0
        for s in sources:
            cred = assess_source_credibility(
                publisher=s.publisher,
                url=s.canonical_url or s.original_url,
                doi=s.doi,
                source_type_declared=s.source_type,
            )
            if cred.is_peer_reviewed or cred.source_type in {
                SourceCredibilityType.PEER_REVIEWED,
                SourceCredibilityType.GOVERNMENT_INSTITUTIONAL,
                SourceCredibilityType.RESEARCH_ORGANIZATION,
            }:
                peer_reviewed_count += 1

        if peer_reviewed_count == 0 and sources:
            prio = _calculate_priority(GapSeverity.high.value, claim_priority=1)
            discovered_gaps.append({
                "category": GapCategory.evidence_coverage.value,
                "gap_type": "missing_primary_studies",
                "title": "Absence of peer-reviewed primary studies",
                "description": (
                    f"All {len(sources)} current sources are preprints, trade journalism, or secondary commentary. "
                    "No formal peer-reviewed academic or rigorous institutional empirical studies were found."
                ),
                "claim_ids": [c.id for c in claims[:2]],
                "evidence_ids": [],
                "source_ids": [s.id for s in sources],
                "supporting_explanation": (
                    "Source credibility evaluation determined zero peer-reviewed journals or institutional research reports "
                    "in the ingested source catalog."
                ),
                "missing_information": "Peer-reviewed scientific literature with formal methodological validation.",
                "severity": GapSeverity.high.value,
                "research_priority": prio,
                "confidence": GapConfidence.high.value,
                "is_observed": True,
                "recommended_action": RecommendedAction(
                    action_type="provider_search",
                    description="Execute targeted academic searches across Crossref and OpenAlex prioritizing indexed journals.",
                    suggested_queries=_generate_provider_queries(inv.question, "journal peer-reviewed"),
                    target_source_types=["peer_reviewed", "academic_journal"],
                    expected_contribution="Grounds findings in peer-reviewed scientific consensus.",
                ),
            })

        # Check 3: Lack of replication
        if independent_cluster_count < 3 and len(sources) > 0:
            severity = GapSeverity.moderate.value
            prio = _calculate_priority(severity, claim_priority=2, independent_clusters=independent_cluster_count)
            discovered_gaps.append({
                "category": GapCategory.evidence_coverage.value,
                "gap_type": "lack_of_replication",
                "title": f"Low cross-institution replication ({independent_cluster_count} independent source clusters)",
                "description": (
                    f"The investigation relies on only {independent_cluster_count} independent origin cluster(s). "
                    "Widespread multi-site empirical replication has not yet been demonstrated."
                ),
                "claim_ids": [c.id for c in claims[:3]],
                "evidence_ids": [],
                "source_ids": [s.id for s in sources],
                "supporting_explanation": (
                    f"Genealogy and clustering algorithms identified only {independent_cluster_count} distinct author/publisher "
                    "origins across all ingested citations."
                ),
                "missing_information": "Independent confirmatory replications by unaffiliated third parties.",
                "severity": severity,
                "research_priority": prio,
                "confidence": GapConfidence.high.value,
                "is_observed": True,
                "recommended_action": RecommendedAction(
                    action_type="provider_search",
                    description="Search for independent replications or contrasting evaluations from other research entities.",
                    suggested_queries=_generate_provider_queries(inv.question, "independent replication confirmation"),
                    target_source_types=["peer_reviewed", "replicated_study"],
                    expected_contribution="Confirms generalizability and rules out isolated experimental artifacts.",
                ),
            })

        # DIMENSION C: PERSPECTIVE GAPS
        advocate_args = [a for a in agent_arguments if getattr(a, "argument_type", "") == "advocate" or "advocate" in getattr(a, "text", "").lower()]
        skeptic_args = [a for a in agent_arguments if getattr(a, "argument_type", "") == "skeptic" or "skeptic" in getattr(a, "text", "").lower()]

        # Check 1: Unbalanced advocacy vs skepticism
        if len(advocate_args) > 0 and len(skeptic_args) == 0:
            severity = GapSeverity.high.value
            prio = _calculate_priority(severity, claim_priority=1)
            discovered_gaps.append({
                "category": GapCategory.perspective.value,
                "gap_type": "unbalanced_advocacy_skepticism",
                "title": "Unbalanced debate: complete absence of skeptical counterarguments",
                "description": (
                    "The analysis generated advocate arguments but zero skeptical counterarguments. "
                    "Alternative hypotheses, confounding factors, and methodological biases remain unexamined."
                ),
                "claim_ids": [c.id for c in claims],
                "evidence_ids": [],
                "source_ids": [],
                "supporting_explanation": (
                    f"Analysis debate logged {len(advocate_args)} advocate argument(s) and 0 skeptic argument(s). "
                    "A critical perspective check is essential for balanced scientific inquiry."
                ),
                "missing_information": "Systematic evaluation of failure modes, competing explanations, and confounding variables.",
                "severity": severity,
                "research_priority": prio,
                "confidence": GapConfidence.high.value,
                "is_observed": True,
                "recommended_action": RecommendedAction(
                    action_type="perspective_investigation",
                    description="Run targeted skeptic query to extract critical counter-evidence and alternative explanations.",
                    suggested_queries=_generate_provider_queries(inv.question, "limitations confounding counter-evidence"),
                    target_source_types=["peer_reviewed", "critical_review"],
                    expected_contribution="Restores dialectical balance and identifies potential confirmation biases.",
                ),
            })

        # Check 2: Missing mitigating factors
        has_mitigating = any(
            getattr(e, "evidence_type", "").lower() == "mitigating"
            or any(m in getattr(e, "exact_text", "").lower() for m in ("mitigat", "compensat", "offset", "cushion", "alternative"))
            for e in evidence_items
        )
        if not has_mitigating and len(evidence_items) > 0:
            severity = GapSeverity.moderate.value
            prio = _calculate_priority(severity, claim_priority=2)
            discovered_gaps.append({
                "category": GapCategory.perspective.value,
                "gap_type": "missing_mitigating_factors",
                "title": "Missing mitigating factors and adaptation mechanisms",
                "description": (
                    f"Evidence focuses on negative or primary effects of '{inv.question}' without investigating "
                    "mitigating policies, engineering adaptations, or offsetting counter-mechanisms."
                ),
                "claim_ids": [c.id for c in claims[:2]],
                "evidence_ids": [],
                "source_ids": [],
                "supporting_explanation": (
                    "Zero evidence passages describe compensatory strategies, mitigating factors, or technical adaptations."
                ),
                "missing_information": "Empirical data on interventions, technical efficiency improvements, or policy offsets.",
                "severity": severity,
                "research_priority": prio,
                "confidence": GapConfidence.medium.value,
                "is_observed": True,
                "recommended_action": RecommendedAction(
                    action_type="perspective_investigation",
                    description="Investigate potential mitigating adaptations, economic adjustments, or engineering solutions.",
                    suggested_queries=_generate_provider_queries(inv.question, "mitigating factors adaptation solutions"),
                    target_source_types=["peer_reviewed", "industry_analysis"],
                    expected_contribution="Provides a comprehensive picture by accounting for adaptive responses.",
                ),
            })

        # DIMENSION D: RESEARCH QUESTION GAPS (Proposed Subquestions)
        # Generate targeted subquestions grounded in unresolved claims and gaps
        for c in claims:
            c_ev = evidence_by_claim.get(c.id, [])
            if len(c_ev) <= 1:
                sub_q = f"Under what boundary conditions and timescales does '{c.text.rstrip('.')}' manifest in practice?"
                prio = _calculate_priority(GapSeverity.high.value if c.priority == 1 else GapSeverity.moderate.value, claim_priority=c.priority)
                discovered_gaps.append({
                    "category": GapCategory.research_question.value,
                    "gap_type": "unanswered_research_subquestion",
                    "title": f"Unanswered research subquestion: {sub_q}",
                    "description": (
                        f"Investigate the specific boundary conditions, operational parameters, and temporal horizon "
                        f"underlying '{c.text[:80]}'."
                    ),
                    "claim_ids": [c.id],
                    "evidence_ids": [e.id for e in c_ev],
                    "source_ids": [],
                    "supporting_explanation": (
                        f"Motivated by claim '{c.text}', which currently has only {len(c_ev)} evidence passage(s). "
                        "Resolving this subquestion is necessary to establish concrete limits for the broader conclusion."
                    ),
                    "missing_information": (
                        "Empirical measurements specifying operational parameters, thresholds, and timeline effects."
                    ),
                    "severity": GapSeverity.high.value if c.priority == 1 else GapSeverity.moderate.value,
                    "research_priority": prio,
                    "confidence": GapConfidence.high.value,
                    "is_observed": True,
                    "recommended_action": RecommendedAction(
                        action_type="subquestion_investigation",
                        description=f"Launch follow-up investigation targeting: {sub_q}",
                        suggested_queries=_generate_provider_queries(inv.question, f"boundary conditions limits {c.text}"),
                        target_source_types=["peer_reviewed", "empirical_study"],
                        expected_contribution="Clarifies exact conditions under which the phenomenon occurs.",
                    ),
                })

        # 6. LLM Refinement & Nuanced Perspective Discovery (Optional, Guarded)
        effective_provider_kind = provider_kind
        effective_model = model
        if not effective_provider_kind:
            # Check latest analysis job for provider settings
            stmt_job = (
                select(AnalysisJob)
                .where(AnalysisJob.investigation_id == investigation_id)
                .order_by(AnalysisJob.created_at.desc())
            )
            latest_job = (await session.execute(stmt_job)).scalars().first()
            if latest_job and latest_job.provider_kind:
                effective_provider_kind = latest_job.provider_kind
                effective_model = effective_model or latest_job.default_model

        if effective_provider_kind:
            try:
                llm_gaps = await self._run_llm_gap_analysis(
                    provider_kind=effective_provider_kind,
                    model=effective_model,
                    question=inv.question,
                    claims=claims,
                    sources=sources,
                    evidence_count=len(evidence_items),
                    existing_gap_types={g["gap_type"] for g in discovered_gaps},
                )
                for lg in llm_gaps:
                    # Guardrail: Only add non-duplicate high-value perspective/question gaps
                    if lg.get("gap_type") not in {g["gap_type"] for g in discovered_gaps}:
                        discovered_gaps.append(lg)
            except Exception as e:
                logger.warning(
                    "LLM gap analysis refinement failed gracefully; deterministic gaps preserved: %s", e
                )

        # 7. Deduplicate gaps and sort by priority descending
        seen_keys: set[str] = set()
        final_gaps: list[dict[str, Any]] = []
        for g in discovered_gaps:
            key = f"{g['category']}_{g['gap_type']}_{'_'.join(str(cid) for cid in g.get('claim_ids', []))}"
            if key not in seen_keys:
                seen_keys.add(key)
                final_gaps.append(g)

        # Sort by research_priority descending, then severity
        severity_order = {"critical": 4, "high": 3, "moderate": 2, "low": 1}
        final_gaps.sort(
            key=lambda x: (x.get("research_priority", 5.0), severity_order.get(x.get("severity", "moderate"), 2)),
            reverse=True,
        )

        # Count severities
        critical_count = sum(1 for g in final_gaps if g.get("severity") == GapSeverity.critical.value)
        high_count = sum(1 for g in final_gaps if g.get("severity") == GapSeverity.high.value)
        moderate_count = sum(1 for g in final_gaps if g.get("severity") == GapSeverity.moderate.value)
        low_count = sum(1 for g in final_gaps if g.get("severity") == GapSeverity.low.value)

        # 8. Compute Research Coverage Score (0.0 - 100.0)
        # Component 1: Claim Grounding (max 35 pts)
        claim_grounding_score = 0.0
        if claims:
            supp_ratio = claims_with_direct_support / len(claims)
            multi_source_ratio = (len(claims) - claims_single_source) / len(claims)
            claim_grounding_score = (supp_ratio * 25.0) + (multi_source_ratio * 10.0)

        # Component 2: Source Independence & Credibility (max 25 pts)
        ind_pts = min(25.0, independent_cluster_count * 5.0)
        academic_ratio = (peer_reviewed_count / max(1, len(sources))) if sources else 0.0
        source_cred_score = ind_pts * (0.5 + (academic_ratio * 0.5))

        # Component 3: Full Text Coverage (max 20 pts)
        ft_count = len(sources) - len(sources_without_full_text)
        ft_ratio = (ft_count / max(1, len(sources))) if sources else 0.0
        full_text_score = ft_ratio * 20.0

        # Component 4: Perspective & Debate Balance (max 20 pts)
        perspective_score = 0.0
        if advocate_args and skeptic_args:
            perspective_score += 10.0
        elif advocate_args or skeptic_args:
            perspective_score += 5.0
        if has_mitigating:
            perspective_score += 10.0

        base_coverage = claim_grounding_score + source_cred_score + full_text_score + perspective_score

        # Deduct penalties for severe defects
        prov_penalty = min(20.0, unresolved_provenance_count * 5.0)
        conflict_penalty = min(15.0, claims_with_conflicts * 5.0)
        final_coverage_score = round(max(0.0, min(100.0, base_coverage - prov_penalty - conflict_penalty)), 1)

        # Build coverage narrative
        narrative = (
            f"Overall research coverage score is {final_coverage_score}/100. "
            f"Evaluated {len(claims)} claim(s), {len(sources)} source(s), and {len(evidence_items)} evidence passage(s). "
            f"Established {independent_cluster_count} independent source cluster(s) with {ft_count} full-text document(s). "
            f"Identified {len(final_gaps)} actionable gap(s): {critical_count} critical, {high_count} high, "
            f"{moderate_count} moderate, and {low_count} low priority."
        )

        coverage_summary = ResearchCoverageSummary(
            coverage_score=final_coverage_score,
            total_claims=len(claims),
            claims_with_direct_support=claims_with_direct_support,
            claims_with_conflicts=claims_with_conflicts,
            claims_unsupported=claims_unsupported,
            claims_single_source=claims_single_source,
            total_sources=len(sources),
            independent_clusters=independent_cluster_count,
            full_text_count=ft_count,
            unresolved_provenance_count=unresolved_provenance_count,
            critical_gaps=critical_count,
            high_gaps=high_count,
            moderate_gaps=moderate_count,
            low_gaps=low_count,
            narrative=narrative,
        )

        # 9. Determine Next Version Number
        stmt_ver = (
            select(func.max(ResearchGapAnalysis.version_number))
            .where(ResearchGapAnalysis.investigation_id == investigation_id)
        )
        max_v = (await session.execute(stmt_ver)).scalar() or 0
        new_version_number = max_v + 1

        summary_text = (
            f"Version {new_version_number} Research Gap Discovery: {len(final_gaps)} gaps detected across "
            f"claim, evidence, perspective, and research question dimensions. Coverage rating: {final_coverage_score}%."
        )

        # 10. Persist to Database
        analysis_id = uuid.uuid4()
        analysis_record = ResearchGapAnalysis(
            id=analysis_id,
            investigation_id=investigation_id,
            version_number=new_version_number,
            summary=summary_text,
            critical_count=critical_count,
            high_count=high_count,
            moderate_count=moderate_count,
            low_count=low_count,
            coverage_score=final_coverage_score,
            coverage_summary_json=coverage_summary.model_dump_json(),
            created_at=datetime.now(UTC),
        )
        session.add(analysis_record)

        gap_views: list[ResearchGapView] = []
        for g_dict in final_gaps:
            g_id = uuid.uuid4()
            rec_action = g_dict.get("recommended_action")
            if isinstance(rec_action, dict):
                rec_action_obj = RecommendedAction(**rec_action)
            elif isinstance(rec_action, RecommendedAction):
                rec_action_obj = rec_action
            else:
                rec_action_obj = RecommendedAction(
                    action_type="provider_search",
                    description=f"Investigate: {g_dict.get('title', '')}",
                    suggested_queries=_generate_provider_queries(inv.question, g_dict.get("title", "")),
                    target_source_types=["peer_reviewed"],
                    expected_contribution="Resolves discovered gap.",
                )

            gap_model = ResearchGap(
                id=g_id,
                analysis_id=analysis_id,
                investigation_id=investigation_id,
                category=g_dict.get("category", GapCategory.claim_coverage.value),
                gap_type=g_dict.get("gap_type", "unspecified_gap"),
                title=g_dict.get("title", "Untitled Gap")[:250],
                description=g_dict.get("description", ""),
                claim_ids_json=json.dumps([str(cid) for cid in g_dict.get("claim_ids", [])]),
                evidence_ids_json=json.dumps([str(eid) for eid in g_dict.get("evidence_ids", [])]),
                source_ids_json=json.dumps([str(sid) for sid in g_dict.get("source_ids", [])]),
                supporting_explanation=g_dict.get("supporting_explanation", ""),
                missing_information=g_dict.get("missing_information", ""),
                severity=g_dict.get("severity", GapSeverity.moderate.value),
                research_priority=g_dict.get("research_priority", 5.0),
                confidence=g_dict.get("confidence", GapConfidence.medium.value),
                is_observed=g_dict.get("is_observed", True),
                recommended_action_json=rec_action_obj.model_dump_json(),
                created_at=datetime.now(UTC),
            )
            session.add(gap_model)

            gap_views.append(
                ResearchGapView(
                    id=g_id,
                    analysis_id=analysis_id,
                    investigation_id=investigation_id,
                    category=gap_model.category,
                    gap_type=gap_model.gap_type,
                    title=gap_model.title,
                    description=gap_model.description,
                    claim_ids=[uuid.UUID(str(cid)) for cid in g_dict.get("claim_ids", [])],
                    evidence_ids=[uuid.UUID(str(eid)) for eid in g_dict.get("evidence_ids", [])],
                    source_ids=[uuid.UUID(str(sid)) for sid in g_dict.get("source_ids", [])],
                    supporting_explanation=gap_model.supporting_explanation,
                    missing_information=gap_model.missing_information,
                    severity=gap_model.severity,
                    research_priority=gap_model.research_priority,
                    confidence=gap_model.confidence,
                    is_observed=gap_model.is_observed,
                    recommended_action=rec_action_obj,
                    created_at=analysis_record.created_at,
                )
            )

        await session.commit()

        return ResearchGapAnalysisResponse(
            id=analysis_id,
            investigation_id=investigation_id,
            version_number=new_version_number,
            summary=summary_text,
            coverage=coverage_summary,
            gaps=gap_views,
            created_at=analysis_record.created_at,
        )

    async def _run_llm_gap_analysis(
        self,
        provider_kind: str,
        model: str | None,
        question: str,
        claims: list[Claim],
        sources: list[Source],
        evidence_count: int,
        existing_gap_types: set[str],
    ) -> list[dict[str, Any]]:
        """Optional LLM enrichment for nuanced perspective and trade-off gaps."""
        try:
            from app.schemas import ProviderConfigRequest, ProviderKind
            p_kind = ProviderKind(provider_kind) if provider_kind in ProviderKind.__members__.values() else ProviderKind.ollama
            p_endpoint = "http://127.0.0.1:11434" if p_kind == ProviderKind.ollama else "http://127.0.0.1:1234"
            prov = create_provider(
                ProviderConfigRequest(
                    kind=p_kind,
                    endpoint=p_endpoint,
                    model=model,
                    allow_local_runtime=True,
                )
            )
        except Exception:
            return []

        prompt = (
            f"You are the Research Gap Analyst for NEOMON.\n"
            f"Research Question: {question}\n\n"
            f"Claims being tested ({len(claims)}):\n"
            + "\n".join(f"- [{c.priority}] {c.text}" for c in claims[:6])
            + f"\n\nSource catalog contains {len(sources)} sources and {evidence_count} evidence passages.\n"
            f"Existing detected gap categories: {', '.join(existing_gap_types)}.\n\n"
            "Identify up to 2 subtle, domain-specific gaps that are NOT yet covered, focusing on:\n"
            "1. Missing disciplinary perspectives (e.g. economic, sociological, engineering trade-offs).\n"
            "2. Unanswered follow-up research questions.\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "gaps": [\n'
            "    {\n"
            '      "category": "perspective" or "research_question",\n'
            '      "gap_type": "missing_tradeoff_perspective" or "missing_disciplinary_perspective" or "unanswered_research_subquestion",\n'
            '      "title": "short title",\n'
            '      "description": "detailed description",\n'
            '      "supporting_explanation": "why this perspective is missing",\n'
            '      "missing_information": "what data is needed",\n'
            '      "severity": "moderate" or "low",\n'
            '      "research_priority": 5.0,\n'
            '      "confidence": "medium",\n'
            '      "recommended_action": {\n'
            '        "action_type": "perspective_investigation",\n'
            '        "description": "action description",\n'
            '        "suggested_queries": ["query 1", "query 2"],\n'
            '        "target_source_types": ["peer_reviewed"],\n'
            '        "expected_contribution": "expected contribution"\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        response = await prov.generate(
            prompt,
            system_instruction="You are an expert scientific gap analyst. Return strictly valid JSON only.",
        )
        parsed = _extract_json_object(response.content)
        raw_list = parsed.get("gaps", [])
        valid_gaps: list[dict[str, Any]] = []
        for g in raw_list:
            if isinstance(g, dict) and "title" in g and "gap_type" in g:
                g["is_observed"] = True
                g["claim_ids"] = []
                g["evidence_ids"] = []
                g["source_ids"] = []
                if "recommended_action" not in g or not isinstance(g["recommended_action"], dict):
                    g["recommended_action"] = {
                        "action_type": "perspective_investigation",
                        "description": g.get("description", ""),
                        "suggested_queries": _generate_provider_queries(question, g.get("title", "")),
                        "target_source_types": ["peer_reviewed"],
                        "expected_contribution": "Broadens inquiry scope.",
                    }
                valid_gaps.append(g)
        return valid_gaps

    async def get_latest_gap_analysis(
        self, session: AsyncSession, investigation_id: uuid.UUID
    ) -> ResearchGapAnalysisResponse | None:
        """Fetch the most recent research gap analysis version for an investigation."""
        stmt = (
            select(ResearchGapAnalysis)
            .where(ResearchGapAnalysis.investigation_id == investigation_id)
            .order_by(ResearchGapAnalysis.version_number.desc())
        )
        analysis = (await session.execute(stmt)).scalars().first()
        if analysis is None:
            return None
        return await self._hydrate_analysis_response(session, analysis)

    async def get_gap_analysis_by_version_or_id(
        self, session: AsyncSession, investigation_id: uuid.UUID, version_or_id: str
    ) -> ResearchGapAnalysisResponse | None:
        """Fetch a specific gap analysis version by version number or UUID."""
        try:
            target_id = uuid.UUID(version_or_id)
            stmt = select(ResearchGapAnalysis).where(
                ResearchGapAnalysis.id == target_id,
                ResearchGapAnalysis.investigation_id == investigation_id,
            )
        except ValueError:
            target_v = int(version_or_id)
            stmt = select(ResearchGapAnalysis).where(
                ResearchGapAnalysis.version_number == target_v,
                ResearchGapAnalysis.investigation_id == investigation_id,
            )

        analysis = (await session.execute(stmt)).scalars().first()
        if analysis is None:
            return None
        return await self._hydrate_analysis_response(session, analysis)

    async def list_gap_analysis_versions(
        self, session: AsyncSession, investigation_id: uuid.UUID
    ) -> list[ResearchGapVersionView]:
        """List summary views of all historical gap analysis versions for an investigation."""
        stmt = (
            select(ResearchGapAnalysis)
            .where(ResearchGapAnalysis.investigation_id == investigation_id)
            .order_by(ResearchGapAnalysis.version_number.desc())
        )
        analyses = list((await session.execute(stmt)).scalars().all())
        views: list[ResearchGapVersionView] = []
        for a in analyses:
            views.append(
                ResearchGapVersionView(
                    id=a.id,
                    investigation_id=a.investigation_id,
                    version_number=a.version_number,
                    summary=a.summary,
                    coverage_score=a.coverage_score,
                    critical_count=a.critical_count,
                    high_count=a.high_count,
                    moderate_count=a.moderate_count,
                    low_count=a.low_count,
                    created_at=a.created_at,
                )
            )
        return views

    async def list_gap_items(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        category: str | None = None,
        severity: str | None = None,
        min_priority: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ResearchGapView], int]:
        """List individual gap items for the latest analysis with category/severity filtering."""
        latest = await self.get_latest_gap_analysis(session, investigation_id)
        if latest is None:
            return [], 0

        gaps = latest.gaps
        if category:
            gaps = [g for g in gaps if g.category.lower() == category.lower()]
        if severity:
            gaps = [g for g in gaps if g.severity.lower() == severity.lower()]
        if min_priority is not None:
            gaps = [g for g in gaps if g.research_priority >= min_priority]

        total = len(gaps)
        sliced = gaps[offset : offset + limit]
        return sliced, total

    async def _hydrate_analysis_response(
        self, session: AsyncSession, analysis: ResearchGapAnalysis
    ) -> ResearchGapAnalysisResponse:
        """Convert a ResearchGapAnalysis ORM model into a full ResearchGapAnalysisResponse schema."""
        gaps_stmt = (
            select(ResearchGap)
            .where(ResearchGap.analysis_id == analysis.id)
            .order_by(ResearchGap.research_priority.desc())
        )
        gaps = list((await session.execute(gaps_stmt)).scalars().all())

        gap_views: list[ResearchGapView] = []
        for g in gaps:
            claim_ids = [uuid.UUID(x) for x in json.loads(g.claim_ids_json or "[]")]
            evidence_ids = [uuid.UUID(x) for x in json.loads(g.evidence_ids_json or "[]")]
            source_ids = [uuid.UUID(x) for x in json.loads(g.source_ids_json or "[]")]
            rec_action_dict = json.loads(g.recommended_action_json or "{}")
            rec_action = RecommendedAction(**rec_action_dict) if rec_action_dict else RecommendedAction(
                action_type="investigate",
                description=g.description,
                suggested_queries=[],
                target_source_types=[],
                expected_contribution="Resolves gap",
            )

            gap_views.append(
                ResearchGapView(
                    id=g.id,
                    analysis_id=g.analysis_id,
                    investigation_id=g.investigation_id,
                    category=g.category,
                    gap_type=g.gap_type,
                    title=g.title,
                    description=g.description,
                    claim_ids=claim_ids,
                    evidence_ids=evidence_ids,
                    source_ids=source_ids,
                    supporting_explanation=g.supporting_explanation,
                    missing_information=g.missing_information,
                    severity=g.severity,
                    research_priority=g.research_priority,
                    confidence=g.confidence,
                    is_observed=g.is_observed,
                    recommended_action=rec_action,
                    created_at=g.created_at,
                )
            )

        coverage_data = json.loads(analysis.coverage_summary_json or "{}")
        coverage_summary = ResearchCoverageSummary(**coverage_data) if coverage_data else ResearchCoverageSummary(
            coverage_score=analysis.coverage_score,
            critical_gaps=analysis.critical_count,
            high_gaps=analysis.high_count,
            moderate_gaps=analysis.moderate_count,
            low_gaps=analysis.low_count,
            narrative=analysis.summary,
        )

        return ResearchGapAnalysisResponse(
            id=analysis.id,
            investigation_id=analysis.investigation_id,
            version_number=analysis.version_number,
            summary=analysis.summary,
            coverage=coverage_summary,
            gaps=gap_views,
            created_at=analysis.created_at,
        )


gap_engine = ResearchGapEngine()
