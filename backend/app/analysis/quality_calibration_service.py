"""Research Quality Score Calibration and Provider Failure Impact Service (Milestone 8G.4 & 8G.5).

Implements calibrated, explainable evidence strength evaluation:
1. Re-calibrates 5D evidence strength scores with scientific rigor.
2. Decouples research coverage from quality (low coverage caps maximum achievable tier).
3. Evaluates provider failure impacts with nuanced severity classification.
4. Corrects false consensus and domain-diversity illusions.
5. Enforces strict prerequisites for 'Very Strong' ratings.
"""

from dataclasses import dataclass, field
import json
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.entailment_service import (
    EntailmentClassification,
    validate_evidence_claim_entailment_heuristic,
)
from app.models import (
    Claim,
    Evidence,
    Investigation,
    ProviderFailureImpact,
    ResearchEvent,
    ResearchGapAnalysis,
    ResearchQualityCalibration,
    Source,
    SourceCredibilityAssessment,
    SourceLineageRelationship,
)
from app.research.source_credibility import (
    CanonicalSourceType,
    SourceVerificationStatus,
    evaluate_canonical_credibility,
)
from app.research.source_lineage import analyze_source_lineage


@dataclass
class DimensionBreakdown:
    empirical_depth: float  # max 25
    source_credibility: float  # max 25
    methodological_rigor: float  # max 15
    consensus_stability: float  # max 15
    source_independence: float  # max 20
    coverage_score: float  # 0 to 100
    failure_penalty: float  # deduction points
    raw_score: float  # 0 to 100
    calibrated_score: float  # 0 to 100
    calibrated_tier: str  # Very Strong, Strong, Moderate, Weak, Inconclusive
    reasons: list[str] = field(default_factory=list)
    # Milestone 9.2: 3 decoupled quality dimensions & empirical metrics
    operational_completeness: float = 100.0
    research_coverage: float = 0.0
    evidence_strength: float = 0.0
    direct_support_count: int = 0
    partial_support_count: int = 0
    contextual_count: int = 0
    contradiction_count: int = 0
    verified_peer_reviewed_count: int = 0
    effective_clusters: float = 0.0


def calculate_calibrated_quality(
    sources: list[Any],
    claims: list[Any],
    evidence: list[Any],
    failure_impacts: list[dict[str, Any]] | None = None,
) -> DimensionBreakdown:
    """Perform deterministic research quality calibration across 5 dimensions."""
    failures = failure_impacts or []
    reasons: list[str] = []

    # ---------------------------------------------------------
    # 1. Lineage & Independence Analysis (Max 20 pts)
    # ---------------------------------------------------------
    lineage_res = analyze_source_lineage(sources)
    effective_clusters = getattr(lineage_res, "weighted_independence_count", lineage_res.effective_independent_count) or lineage_res.effective_independent_count
    total_sources = len(sources)

    if total_sources == 0:
        return DimensionBreakdown(
            empirical_depth=0.0,
            source_credibility=0.0,
            methodological_rigor=0.0,
            consensus_stability=0.0,
            source_independence=0.0,
            coverage_score=0.0,
            failure_penalty=0.0,
            raw_score=0.0,
            calibrated_score=0.0,
            calibrated_tier="Inconclusive",
            reasons=["No research sources available to assess."],
            operational_completeness=0.0,
            research_coverage=0.0,
            evidence_strength=0.0,
            direct_support_count=0,
            partial_support_count=0,
            contextual_count=0,
            contradiction_count=0,
            verified_peer_reviewed_count=0,
            effective_clusters=0.0,
        )

    # Base independence on true lineage clusters, not raw URL count
    # 1 cluster = 5 pts, 2 = 10 pts, 3 = 15 pts, 4+ = 20 pts
    source_independence = min(20.0, effective_clusters * 5.0)
    if effective_clusters < total_sources:
        deducted = min(10.0, (total_sources - effective_clusters) * 1.5)
        source_independence = max(3.0, source_independence - deducted)
        reasons.append(
            f"Lineage analysis collapsed {total_sources} sources into {lineage_res.effective_independent_count:.0f} clusters "
            f"({lineage_res.independence_ratio:.0%} independence ratio, effective weighted count: {effective_clusters:.1f}). "
            f"Independence score calibrated to {source_independence:.1f}/20."
        )
    else:
        reasons.append(f"Sources demonstrate full institutional and publication independence ({effective_clusters:.1f} distinct clusters).")

    # ---------------------------------------------------------
    # 2. Canonical Source Credibility (Max 25 pts)
    # ---------------------------------------------------------
    cred_evals = []
    verified_peer_reviewed_count = 0
    primary_source_count = 0

    for s in sources:
        url = getattr(s, "canonical_url", "") or getattr(s, "original_url", "") or s.get("url", "") if isinstance(s, dict) else getattr(s, "canonical_url", "")
        pub = getattr(s, "publisher", "") if not isinstance(s, dict) else s.get("publisher", "")
        doi = getattr(s, "doi", "") if not isinstance(s, dict) else s.get("doi", "")
        st_decl = getattr(s, "source_type", "") if not isinstance(s, dict) else s.get("source_type", "")
        title = getattr(s, "title", "") if not isinstance(s, dict) else s.get("title", "")

        eval_res = evaluate_canonical_credibility(
            url=url,
            publisher=pub,
            doi=doi,
            source_type_declared=st_decl,
            title=title,
        )
        cred_evals.append(eval_res)
        if eval_res.is_peer_reviewed:
            verified_peer_reviewed_count += 1
        if eval_res.is_primary:
            primary_source_count += 1

    avg_credibility = sum(e.credibility_score for e in cred_evals) / max(1, len(cred_evals))
    source_credibility = round(avg_credibility * 25.0, 1)

    if verified_peer_reviewed_count == 0 and primary_source_count == 0:
        source_credibility = min(12.5, source_credibility)
        reasons.append(
            "Source credibility capped at 12.5/25: zero verified peer-reviewed publications or primary studies present. Corpus consists of secondary reporting or unverified web articles."
        )
    elif verified_peer_reviewed_count == 0:
        reasons.append(
            "Zero verified peer-reviewed publications identified. Sources include primary industry/institutional materials or secondary journalism."
        )
    else:
        reasons.append(
            f"Identified {verified_peer_reviewed_count} verified peer-reviewed publication(s) and {primary_source_count} primary sources."
        )

    # ---------------------------------------------------------
    # 3. Empirical Depth & Entailment Validation (Max 25 pts)
    # ---------------------------------------------------------
    direct_support_count = 0
    partial_support_count = 0
    contextual_count = 0
    contradiction_count = 0
    correlation_flaws = 0

    claim_map = {str(getattr(c, "id", c.get("id", ""))) if isinstance(c, dict) else str(getattr(c, "id", "")): c for c in claims}

    for ev in evidence:
        ev_id = str(getattr(ev, "id", ev.get("id", ""))) if isinstance(ev, dict) else str(getattr(ev, "id", ""))
        cid = str(getattr(ev, "claim_id", ev.get("claim_id", ""))) if isinstance(ev, dict) else str(getattr(ev, "claim_id", ""))
        c_obj = claim_map.get(cid)
        c_text = (getattr(c_obj, "text", "") if c_obj and not isinstance(c_obj, dict) else c_obj.get("text", "") if c_obj else "") or "General research claim"
        ev_text = getattr(ev, "exact_text", "") if not isinstance(ev, dict) else ev.get("exact_text", "")

        val = validate_evidence_claim_entailment_heuristic(
            claim_id=cid or str(uuid.uuid4()),
            claim_text=c_text,
            evidence_id=ev_id,
            evidence_text=ev_text,
        )
        if val.entailment_classification == EntailmentClassification.DIRECT_SUPPORT:
            direct_support_count += 1
        elif val.entailment_classification == EntailmentClassification.PARTIAL_SUPPORT:
            partial_support_count += 1
        elif val.entailment_classification == EntailmentClassification.CONTEXTUAL_SUPPORT:
            contextual_count += 1
        elif val.entailment_classification == EntailmentClassification.DIRECT_CONTRADICTION:
            contradiction_count += 1
        
        if val.correlation_vs_causation_flag:
            correlation_flaws += 1

    total_evidence = len(evidence)
    if total_evidence > 0:
        direct_ratio = direct_support_count / total_evidence
        partial_ratio = partial_support_count / total_evidence
        contextual_ratio = contextual_count / total_evidence
        
        # Scoring: Direct (+4.0 max 20), Partial (+1.5 max 8), Contextual (+0.25 max 4)
        raw_depth = min(25.0, (min(20.0, direct_support_count * 4.0) + min(8.0, partial_support_count * 1.5) + min(4.0, contextual_count * 0.25)))
        
        # STRICT SAFEGUARDS FOR EMPIRICAL DEPTH
        if direct_support_count == 0 and partial_support_count == 0:
            empirical_depth = min(5.0, raw_depth)
            reasons.append(
                "Empirical depth strictly capped at 5.0/25: zero direct empirical proof passages and zero partial mechanisms; investigation relies entirely on contextual commentary."
            )
        elif direct_support_count == 0 and partial_support_count > 0:
            empirical_depth = min(10.0, raw_depth)
            reasons.append(
                f"Empirical depth capped at 10.0/25: zero direct empirical proof passages; {partial_support_count} partial mechanism passage(s) identified."
            )
        else:
            empirical_depth = raw_depth

        if correlation_flaws > 0:
            empirical_depth = max(2.0, empirical_depth - (correlation_flaws * 1.5))
            reasons.append(
                f"Flagged {correlation_flaws} evidence passage(s) conflating correlation with causation without mechanistic proof."
            )
        reasons.append(
            f"Empirical depth calibrated: {direct_support_count} direct proof passage(s) ({direct_ratio:.0%}), "
            f"{partial_support_count} partial mechanism passage(s) ({partial_ratio:.0%}), and "
            f"{contextual_count} contextual background passage(s) ({contextual_ratio:.0%})."
        )
    else:
        empirical_depth = 0.0
        reasons.append("Zero evidence passages extracted; empirical depth score is 0.")

    # ---------------------------------------------------------
    # 4. Methodological Rigor (Max 15 pts)
    # ---------------------------------------------------------
    full_text_count = sum(
        1 for s in sources if (getattr(s, "selected_document_url", "") or (isinstance(s, dict) and s.get("full_text_retrieved")))
    )
    full_text_ratio = full_text_count / max(1, total_sources)
    methodological_rigor = round(full_text_ratio * 15.0, 1)
    reasons.append(
        f"Full-text document acquisition rate: {full_text_count}/{total_sources} sources ({full_text_ratio:.0%}). "
        f"Methodological rigor: {methodological_rigor}/15."
    )

    # ---------------------------------------------------------
    # 5. Consensus Stability (Max 15 pts)
    # ---------------------------------------------------------
    # Balanced synthesis: presence of critical counter-evidence or mitigating conditions is scientifically healthy,
    # but unchecked contradictions indicate instability.
    if total_evidence == 0:
        consensus_stability = 0.0
    elif contradiction_count > 0:
        # Contradictions are documented and analyzed
        consensus_stability = 11.0
        reasons.append(f"Consensus stability: {contradiction_count} active contradiction(s) identified and isolated.")
    elif direct_support_count > 0 and effective_clusters >= 2:
        consensus_stability = 14.5
        reasons.append("Robust consensus stability verified across independent lineage clusters.")
    elif direct_support_count > 0 and effective_clusters <= 1:
        # Artificial consensus warning!
        consensus_stability = 8.0
        reasons.append("Warning: apparent consensus originates from a single syndicated or shared-lineage source cluster.")
    else:
        consensus_stability = 6.0
        reasons.append("Limited empirical grounding prevents establishing stable scientific consensus.")

    # ---------------------------------------------------------
    # 6. Research Coverage Score (0 to 100%)
    # ---------------------------------------------------------
    total_claims = len(claims)
    if total_claims > 0:
        # Claims with at least one direct or contextual evidence passage
        covered_claim_ids = {str(getattr(ev, "claim_id", ev.get("claim_id", ""))) if isinstance(ev, dict) else str(getattr(ev, "claim_id", "")) for ev in evidence}
        covered_claim_count = len(covered_claim_ids.intersection(claim_map.keys()))
        claim_coverage_ratio = covered_claim_count / total_claims
    else:
        claim_coverage_ratio = 1.0 if total_evidence > 0 else 0.0

    coverage_score = round(((claim_coverage_ratio * 0.6) + (full_text_ratio * 0.4)) * 100.0, 1)

    # ---------------------------------------------------------
    # 7. Provider Failure Penalties (8G.5)
    # ---------------------------------------------------------
    failure_penalty = 0.0
    critical_failures_count = 0
    for f in failures:
        sev = f.get("impact_severity", "harmless_optional")
        if sev == "critical_loss":
            failure_penalty += 12.0
            critical_failures_count += 1
            reasons.append(f"Critical retrieval failure on {f.get('provider')}: query '{f.get('query', '')[:40]}' caused loss of {f.get('missing_category', 'evidence')}.")
        elif sev == "significant_coverage":
            failure_penalty += 7.0
            reasons.append(f"Significant provider failure on {f.get('provider')}: query '{f.get('query', '')[:40]}'.")
        elif sev == "partial_coverage":
            failure_penalty += 3.0
        # harmless_optional incurs 0 penalty

    failure_penalty = min(30.0, failure_penalty)

    # ---------------------------------------------------------
    # 8. Calibration & Score Harmonization
    # ---------------------------------------------------------
    raw_score = round(
        empirical_depth + source_credibility + methodological_rigor + consensus_stability + source_independence,
        1
    )
    calibrated_score = max(0.0, round(raw_score - failure_penalty, 1))

    # 3 Distinct Quality Dimensions (Milestone 9.2 Decoupling)
    operational_completeness = max(0.0, round(100.0 - (failure_penalty * 2.5), 1))
    research_coverage = coverage_score
    evidence_strength = calibrated_score

    # TIER DETERMINATION WITH STRICT SCIENTIFIC CALIBRATION BOUNDARIES
    tier = "Moderate"

    if calibrated_score >= 85.0:
        # Very Strong requirements:
        # 1. Calibrated score >= 85
        # 2. Coverage score >= 80%
        # 3. Direct proof >= 2
        # 4. Verified peer review >= 1
        # 5. Zero critical retrieval failures
        # 6. Zero unaddressed contradictions
        if coverage_score < 80.0:
            tier = "Strong"
            reasons.append(
                f"Quality tier capped from 'Very Strong' to 'Strong' due to sub-threshold research coverage ({coverage_score:.1f}% < 80%)."
            )
        elif direct_support_count < 2:
            tier = "Strong"
            reasons.append(
                f"Quality tier capped from 'Very Strong' to 'Strong': requires at least 2 direct empirical proof passages (found {direct_support_count})."
            )
        elif verified_peer_reviewed_count == 0:
            tier = "Moderate"
            reasons.append(
                "Quality tier capped from 'Very Strong' to 'Moderate' due to absence of verified peer-reviewed publications."
            )
        elif critical_failures_count > 0:
            tier = "Moderate"
            reasons.append(
                f"Quality tier capped to 'Moderate' due to {critical_failures_count} unresolved critical retrieval failure(s)."
            )
        elif contradiction_count > 0:
            tier = "Moderate"
            reasons.append(
                f"Quality tier capped to 'Moderate' due to {contradiction_count} active unadjudicated contradiction(s)."
            )
        else:
            tier = "Very Strong"
    elif calibrated_score >= 70.0:
        # Strong requirements:
        # 1. Calibrated score >= 70
        # 2. Coverage score >= 60%
        # 3. Direct proof >= 1 OR (partial_support >= 2 AND verified_peer_reviewed >= 1)
        # 4. Zero critical failures
        # 5. Zero unaddressed contradictions
        if direct_support_count == 0 and not (partial_support_count >= 2 and verified_peer_reviewed_count >= 1):
            tier = "Moderate"
            reasons.append(
                "Quality tier capped to 'Moderate': corpus contains zero direct empirical proof passages; findings rest on secondary contextual reporting."
            )
        elif coverage_score < 60.0:
            tier = "Moderate"
            reasons.append(
                f"Quality tier capped from 'Strong' to 'Moderate' due to insufficient research coverage ({coverage_score:.1f}% < 60%)."
            )
        elif critical_failures_count > 0:
            tier = "Moderate"
            reasons.append("Quality tier capped to 'Moderate' due to critical retrieval failures.")
        elif contradiction_count > 0:
            tier = "Moderate"
            reasons.append(
                f"Quality tier capped to 'Moderate' due to {contradiction_count} active contradiction(s)."
            )
        else:
            tier = "Strong"
    elif calibrated_score >= 50.0:
        tier = "Moderate"
    elif calibrated_score >= 30.0:
        tier = "Weak"
    else:
        tier = "Inconclusive"

    return DimensionBreakdown(
        empirical_depth=empirical_depth,
        source_credibility=source_credibility,
        methodological_rigor=methodological_rigor,
        consensus_stability=consensus_stability,
        source_independence=source_independence,
        coverage_score=coverage_score,
        failure_penalty=failure_penalty,
        raw_score=raw_score,
        calibrated_score=calibrated_score,
        calibrated_tier=tier,
        reasons=reasons,
        operational_completeness=operational_completeness,
        research_coverage=research_coverage,
        evidence_strength=evidence_strength,
        direct_support_count=direct_support_count,
        partial_support_count=partial_support_count,
        contextual_count=contextual_count,
        contradiction_count=contradiction_count,
        verified_peer_reviewed_count=verified_peer_reviewed_count,
        effective_clusters=effective_clusters,
    )


async def calibrate_investigation_quality(
    session: AsyncSession,
    investigation_id: uuid.UUID,
) -> dict[str, Any]:
    """Execute end-to-end scientific quality calibration for an investigation."""
    inv = await session.get(Investigation, investigation_id)
    if not inv:
        raise ValueError(f"Investigation {investigation_id} not found")

    # Load sources, claims, evidence, and existing failure events
    sources_res = await session.execute(
        select(Source).where(Source.investigation_id == investigation_id)
    )
    sources = list(sources_res.scalars().all())

    claims_res = await session.execute(
        select(Claim).where(Claim.investigation_id == investigation_id)
    )
    claims = list(claims_res.scalars().all())

    # Evidence linked to this investigation's sources
    source_ids = [s.id for s in sources]
    if source_ids:
        evidence_res = await session.execute(
            select(Evidence).where(Evidence.source_id.in_(source_ids))
        )
        evidence = list(evidence_res.scalars().all())
    else:
        evidence = []

    # Check for recorded provider failure impacts or derive from events
    failures_res = await session.execute(
        select(ProviderFailureImpact).where(ProviderFailureImpact.investigation_id == investigation_id)
    )
    existing_failures = list(failures_res.scalars().all())

    failure_dicts = []
    if existing_failures:
        failure_dicts = [
            {
                "provider": f.provider,
                "operation": f.operation,
                "query": f.query,
                "failure_type": f.failure_type,
                "impact_severity": f.impact_severity,
                "missing_category": f.missing_category,
            }
            for f in existing_failures
        ]
    else:
        # Check research events for provider failures
        events_res = await session.execute(
            select(ResearchEvent).where(
                ResearchEvent.investigation_id == investigation_id,
                ResearchEvent.event_type.in_(["provider_failed", "retrieval_failed", "query_failed"])
            )
        )
        failed_events = list(events_res.scalars().all())
        for ev in failed_events:
            p_name = ev.provider or "provider"
            msg = ev.message or ""
            sev = "partial_coverage"
            if "crossref" in p_name.lower() or "openalex" in p_name.lower():
                sev = "significant_coverage"
            failure_impact = ProviderFailureImpact(
                investigation_id=investigation_id,
                provider=p_name,
                operation="metadata_search",
                query=msg[:200],
                failure_type="timeout_or_error",
                retry_attempts=1,
                impact_severity=sev,
                missing_category="academic_empirical",
                explanation=f"Provider {p_name} operation failed: {msg[:100]}",
            )
            session.add(failure_impact)
            failure_dicts.append({
                "provider": p_name,
                "operation": "metadata_search",
                "query": msg[:200],
                "failure_type": "timeout_or_error",
                "impact_severity": sev,
                "missing_category": "academic_empirical",
            })

    # Run calibration
    breakdown = calculate_calibrated_quality(
        sources=sources,
        claims=claims,
        evidence=evidence,
        failure_impacts=failure_dicts,
    )

    # Persist or update ResearchQualityCalibration
    cal_res = await session.execute(
        select(ResearchQualityCalibration).where(
            ResearchQualityCalibration.investigation_id == investigation_id
        )
    )
    existing_cal = cal_res.scalar_one_or_none()

    dim_breakdown = {
        "empirical_depth": breakdown.empirical_depth,
        "source_credibility": breakdown.source_credibility,
        "methodological_rigor": breakdown.methodological_rigor,
        "consensus_stability": breakdown.consensus_stability,
        "source_independence": breakdown.source_independence,
        "coverage_score": breakdown.coverage_score,
        "failure_penalty": breakdown.failure_penalty,
        # Milestone 9.2: 3 decoupled dimensions & empirical metrics
        "operational_completeness": breakdown.operational_completeness,
        "research_coverage": breakdown.research_coverage,
        "evidence_strength": breakdown.evidence_strength,
        "direct_support_count": breakdown.direct_support_count,
        "partial_support_count": breakdown.partial_support_count,
        "contextual_count": breakdown.contextual_count,
        "contradiction_count": breakdown.contradiction_count,
        "verified_peer_reviewed_count": breakdown.verified_peer_reviewed_count,
        "effective_clusters": breakdown.effective_clusters,
    }

    if existing_cal:
        existing_cal.calibrated_tier = breakdown.calibrated_tier
        existing_cal.raw_score = breakdown.raw_score
        existing_cal.calibrated_score = breakdown.calibrated_score
        existing_cal.coverage_score = breakdown.coverage_score
        existing_cal.failure_penalty = breakdown.failure_penalty
        existing_cal.dimension_breakdown_json = json.dumps(dim_breakdown)
        existing_cal.calibration_reasons_json = json.dumps(breakdown.reasons)
    else:
        new_cal = ResearchQualityCalibration(
            investigation_id=investigation_id,
            calibrated_tier=breakdown.calibrated_tier,
            raw_score=breakdown.raw_score,
            calibrated_score=breakdown.calibrated_score,
            coverage_score=breakdown.coverage_score,
            failure_penalty=breakdown.failure_penalty,
            dimension_breakdown_json = json.dumps(dim_breakdown),
            calibration_reasons_json = json.dumps(breakdown.reasons),
        )
        session.add(new_cal)

    # Also update investigation's quality_status
    inv.quality_status = breakdown.calibrated_tier.lower().replace(" ", "_")
    inv.quality_summary = f"Calibrated quality tier: {breakdown.calibrated_tier} ({breakdown.calibrated_score:.1f}/100, coverage: {breakdown.coverage_score:.1f}%)"

    await session.commit()

    return {
        "investigation_id": str(investigation_id),
        "raw_score": breakdown.raw_score,
        "calibrated_score": breakdown.calibrated_score,
        "calibrated_tier": breakdown.calibrated_tier,
        "coverage_score": breakdown.coverage_score,
        "failure_penalty": breakdown.failure_penalty,
        "operational_completeness": breakdown.operational_completeness,
        "research_coverage": breakdown.research_coverage,
        "evidence_strength": breakdown.evidence_strength,
        "dimension_breakdown": dim_breakdown,
        "reasons": breakdown.reasons,
    }
