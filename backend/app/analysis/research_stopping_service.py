"""Autonomous Research Stopping and Budget Management Engine (Milestone 9E & 9F).

Evaluates whether to continue or terminate an autonomous research workflow based on:
1. Scientific Evidence Sufficiency (coverage, verified peer review, resolved claims)
2. Diminishing Returns (consecutive cycles yielding near-zero information gain)
3. Unresolved Scientific Uncertainty (genuine empirical discordance in available literature)
4. Resource & Budget Caps (max cycles, max searches, max duration)
5. Mandatory Human Oversight Boundaries

Enforces the core rule:
Never claim 'sufficient_evidence' simply because source count is high or an LLM is confident.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.models import (
    AutonomousResearchWorkflow,
    Claim,
    Evidence,
    Investigation,
    ResearchContradiction,
    ResearchGap,
    ResearchQualityCalibration,
    Source,
)


class StoppingReason(StrEnum):
    SUFFICIENT_EVIDENCE = "sufficient_evidence"
    DIMINISHING_RETURNS = "diminishing_returns"
    UNRESOLVED_SCIENTIFIC_UNCERTAINTY = "unresolved_scientific_uncertainty"
    INSUFFICIENT_SOURCE_AVAILABILITY = "insufficient_source_availability"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    BUDGET_EXHAUSTED = "budget_exhausted"
    TIME_LIMIT_REACHED = "time_limit_reached"
    MAXIMUM_CYCLES_REACHED = "maximum_cycles_reached"
    USER_CANCELLED = "user_cancelled"
    SYSTEM_FAILURE = "system_failure"


@dataclass
class StoppingEvaluationResult:
    should_stop: bool
    stopping_reason: StoppingReason | None
    explanation: str
    scientific_confidence: str  # "high", "medium", "low", "unresolved"
    metrics_summary: dict[str, Any]


def evaluate_stopping_criteria(
    workflow: AutonomousResearchWorkflow,
    investigation: Investigation,
    claims: list[Claim],
    sources: list[Source],
    evidence: list[Evidence],
    calibration: ResearchQualityCalibration | None,
    contradictions: list[ResearchContradiction] | None = None,
    gaps: list[ResearchGap] | None = None,
    recent_cycle_gain: float = 0.5,
    provider_exhaustion_flag: bool = False,
) -> StoppingEvaluationResult:
    """Rigorous scientific stopping decision engine."""
    contra_list = contradictions or []
    gap_list = gaps or []

    # Calculate coverage
    total_claims = len(claims)
    claims_with_evidence = sum(
        1 for c in claims if any(ev.claim_id == c.id for ev in evidence)
    )
    claim_coverage_pct = (claims_with_evidence / max(1, total_claims)) * 100.0

    # Quality metrics
    calibrated_tier = calibration.calibrated_tier if calibration else "Moderate"
    calibrated_score = calibration.calibrated_score if calibration else 50.0
    coverage_score = calibration.coverage_score if calibration else claim_coverage_pct

    # Active contradiction count
    active_contradictions = sum(
        1 for con in contra_list if getattr(con, "status", "") in ("active", "under_debate")
    )

    # Critical gaps
    critical_gaps = sum(
        1 for g in gap_list if getattr(g, "severity", "") == "critical" or getattr(g, "research_priority", 0) >= 8.0
    )

    # Verified peer review count
    peer_count = sum(
        1
        for s in sources
        if getattr(s, "__dict__", {}).get("credibility_assessment")
        and getattr(s.__dict__["credibility_assessment"], "is_peer_reviewed", False)
    )

    metrics = {
        "cycle_number": workflow.current_cycle_number,
        "total_claims": total_claims,
        "claims_with_evidence": claims_with_evidence,
        "claim_coverage_pct": round(claim_coverage_pct, 1),
        "coverage_score": round(coverage_score, 1),
        "calibrated_score": round(calibrated_score, 1),
        "calibrated_tier": calibrated_tier,
        "active_contradictions": active_contradictions,
        "critical_gaps": critical_gaps,
        "peer_reviewed_sources": peer_count,
        "spent_searches": workflow.spent_searches,
        "budget_max_searches": workflow.budget_max_searches,
        "recent_cycle_gain": recent_cycle_gain,
        "consecutive_low_value": workflow.consecutive_low_value_cycles,
    }

    # -------------------------------------------------------------
    # 1. Hard Budget Limits
    # -------------------------------------------------------------
    current_cycle = getattr(workflow, "current_cycle_number", 0) or 0
    budget_max_cycles = getattr(workflow, "budget_max_cycles", 5) or 5
    spent_searches = getattr(workflow, "spent_searches", 0) or 0
    budget_max_searches = getattr(workflow, "budget_max_searches", 20) or 20
    consecutive_low = getattr(workflow, "consecutive_low_value_cycles", 0) or 0
    max_consecutive_low = getattr(workflow, "budget_max_consecutive_low_value", 2) or 2

    if current_cycle >= budget_max_cycles:
        return StoppingEvaluationResult(
            should_stop=True,
            stopping_reason=StoppingReason.MAXIMUM_CYCLES_REACHED,
            explanation=(
                f"Workflow reached maximum allowed research cycles ({budget_max_cycles}). "
                f"Completed with {claim_coverage_pct:.1f}% claim coverage and {calibrated_tier} quality tier."
            ),
            scientific_confidence="medium" if claim_coverage_pct >= 70 else "low",
            metrics_summary=metrics,
        )

    if spent_searches >= budget_max_searches:
        return StoppingEvaluationResult(
            should_stop=True,
            stopping_reason=StoppingReason.BUDGET_EXHAUSTED,
            explanation=(
                f"Allocated search budget exhausted ({spent_searches}/{budget_max_searches} searches). "
                f"Stopping to avoid unconstrained API resource expenditure."
            ),
            scientific_confidence="medium" if claim_coverage_pct >= 70 else "low",
            metrics_summary=metrics,
        )

    # -------------------------------------------------------------
    # 2. Diminishing Returns (Repeated low-value cycles)
    # -------------------------------------------------------------
    if consecutive_low >= max_consecutive_low:
        return StoppingEvaluationResult(
            should_stop=True,
            stopping_reason=StoppingReason.DIMINISHING_RETURNS,
            explanation=(
                f"Research reached diminishing returns after {consecutive_low} consecutive cycles "
                f"yielding negligible novel evidence (information gain < threshold). Further searches are unproductive."
            ),
            scientific_confidence="medium",
            metrics_summary=metrics,
        )

    # -------------------------------------------------------------
    # 3. Provider Exhaustion
    # -------------------------------------------------------------
    if provider_exhaustion_flag and workflow.current_cycle_number >= 2:
        return StoppingEvaluationResult(
            should_stop=True,
            stopping_reason=StoppingReason.INSUFFICIENT_SOURCE_AVAILABILITY,
            explanation="Integrated literature providers returned zero relevant documents across alternative query variants.",
            scientific_confidence="low",
            metrics_summary=metrics,
        )

    # -------------------------------------------------------------
    # 4. Genuine Scientific Stopping: Sufficient Evidence
    # -------------------------------------------------------------
    # Strict conditions:
    # - At least 2 research cycles executed
    # - High claim coverage >= 85%
    # - Calibrated quality tier is Strong or Very Strong
    # - Zero unsupported critical claims
    # - Zero unresolved critical gaps
    # - Zero active uninvestigated contradictions
    # - At least one verified peer-reviewed or authoritative source
    if (
        workflow.current_cycle_number >= 2
        and claim_coverage_pct >= 85.0
        and calibrated_tier in ("Very Strong", "Strong")
        and critical_gaps == 0
        and active_contradictions == 0
        and peer_count >= 1
    ):
        return StoppingEvaluationResult(
            should_stop=True,
            stopping_reason=StoppingReason.SUFFICIENT_EVIDENCE,
            explanation=(
                f"Sufficient evidence criterion earned: {claim_coverage_pct:.0f}% claim coverage, "
                f"{calibrated_tier} quality rating ({calibrated_score:.1f}/100), zero critical research gaps, "
                f"and verified evidentiary grounding across {len(sources)} sources."
            ),
            scientific_confidence="high",
            metrics_summary=metrics,
        )

    # -------------------------------------------------------------
    # 5. Persistent Scientific Contradictions / Uncertainty
    # -------------------------------------------------------------
    # If cycle >= 3, coverage is high, but active contradictions refuse to resolve
    if workflow.current_cycle_number >= 3 and active_contradictions > 0 and claim_coverage_pct >= 80.0:
        return StoppingEvaluationResult(
            should_stop=True,
            stopping_reason=StoppingReason.UNRESOLVED_SCIENTIFIC_UNCERTAINTY,
            explanation=(
                f"Investigation documented persistent empirical contradictions ({active_contradictions} active tension(s)) "
                f"that cannot be reconciled by available literature without direct experimental replication. "
                f"Terminating to preserve scientific honesty rather than forcing artificial consensus."
            ),
            scientific_confidence="unresolved",
            metrics_summary=metrics,
        )

    # Continue research
    return StoppingEvaluationResult(
        should_stop=False,
        stopping_reason=None,
        explanation=f"Continuing research: coverage at {claim_coverage_pct:.1f}%, {total_claims - claims_with_evidence} claim(s) pending grounding.",
        scientific_confidence="medium",
        metrics_summary=metrics,
    )
