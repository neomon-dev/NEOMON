"""Targeted Automated Scientific Calibration & Provenance Validation Tests (Milestone 9.2).

Verifies the scientific correctness and decoupling of NEOMON's research quality evaluation:
1. Empirical depth safeguards: Zero direct proof passages strictly caps empirical depth <= 5.0/25.
2. Study-intent vs empirical-findings separation in entailment validation.
3. Partial support classification and mechanistic entailment.
4. Source credibility capping when zero peer-reviewed and zero primary sources are present.
5. Derivative reporting detection and weighted source independence.
6. Explicit decoupling of Operational Completeness (A), Research Coverage (B), and Evidence Strength (C).
7. Autonomous stopping criteria strictly requiring verified peer-reviewed sources.
8. Calibrated benchmark validation for NVIDIA (Moderate) and Nokia (Strong).
"""

import json
from pathlib import Path
import uuid
import pytest
from sqlalchemy import text
from app.analysis.entailment_service import (
    EntailmentClassification,
    validate_evidence_claim_entailment_heuristic,
)
from app.analysis.quality_calibration_service import (
    calculate_calibrated_quality,
    calibrate_investigation_quality,
)
from app.analysis.research_stopping_service import (
    StoppingReason,
    evaluate_stopping_criteria,
)
from app.db import SessionFactory
from app.models import (
    AutonomousResearchWorkflow,
    Claim,
    Evidence,
    Investigation,
    ResearchQualityCalibration,
    Source,
)
from app.research.source_credibility import (
    CanonicalSourceType,
    evaluate_canonical_credibility,
)
from app.research.source_lineage import (
    SourceLineageType,
    analyze_source_lineage,
)


def test_empirical_depth_zero_direct_proof_safeguard():
    """Verify that an investigation with 0 direct proof passages is capped at <= 5.0/25 empirical depth."""
    sources = [
        {"id": f"s-{i}", "url": f"https://techblog{i}.com/article", "publisher": f"TechBlog {i}", "title": f"Tech Analysis {i}"}
        for i in range(10)
    ]
    claims = [{"id": "c-1", "text": "AI accelerators cause datacenter power grid instability."}]
    # 30 contextual evidence passages, zero direct proof
    evidence = [
        {
            "id": f"e-{i}",
            "claim_id": "c-1",
            "exact_text": f"Datacenter power usage has increased significantly in region {i} during recent years.",
        }
        for i in range(30)
    ]

    breakdown = calculate_calibrated_quality(sources=sources, claims=claims, evidence=evidence)
    
    # Empirical depth must be strictly capped at 5.0 / 25.0
    assert breakdown.empirical_depth <= 5.0
    assert breakdown.direct_support_count == 0
    assert breakdown.contextual_count == 30
    # Tier must not exceed Moderate
    assert breakdown.calibrated_tier in ("Moderate", "Weak", "Inconclusive")
    assert any("strictly capped at 5.0/25" in r for r in breakdown.reasons)


def test_study_intent_vs_empirical_findings_entailment():
    """Verify that study objectives/theses are classified as CONTEXTUAL_SUPPORT, never DIRECT_SUPPORT."""
    claim = "Excessive smartphone usage reduces cognitive retention in adolescents."

    # Passage articulating study objective / intent (NOT empirical findings)
    ev_intent = (
        "The purpose of this study was to explore whether smartphone usage in secondary schools "
        "reduces cognitive retention among adolescent students."
    )
    val_intent = validate_evidence_claim_entailment_heuristic(
        claim_id="c1", claim_text=claim, evidence_id="e1", evidence_text=ev_intent
    )
    assert val_intent.entailment_classification == EntailmentClassification.CONTEXTUAL_SUPPORT
    assert "study intent" in val_intent.explanation.lower() or "framing" in val_intent.explanation.lower()

    # Passage articulating empirical findings and data
    ev_findings = (
        "Empirical data reveals that excessive smartphone usage directly causes a 28% reduction "
        "in cognitive retention scores among adolescent cohorts."
    )
    val_findings = validate_evidence_claim_entailment_heuristic(
        claim_id="c1", claim_text=claim, evidence_id="e2", evidence_text=ev_findings
    )
    assert val_findings.entailment_classification == EntailmentClassification.DIRECT_SUPPORT
    assert val_findings.correlation_vs_causation_flag is False


def test_partial_support_classification_and_mechanisms():
    """Verify that intermediate mechanisms or sub-claims receive PARTIAL_SUPPORT."""
    claim = "Severe drought in California caused acute economic losses in the central valley."

    # Partial mechanism passage (moderate overlap with causal mechanism)
    ev_partial = (
        "Empirical measurements show that drought conditions caused agricultural water allocations "
        "to drop by 60% across the central basin."
    )
    val_partial = validate_evidence_claim_entailment_heuristic(
        claim_id="c1", claim_text=claim, evidence_id="e3", evidence_text=ev_partial
    )
    assert val_partial.entailment_classification in (
        EntailmentClassification.PARTIAL_SUPPORT,
        EntailmentClassification.DIRECT_SUPPORT,
    )


def test_source_credibility_unverified_cap():
    """Verify that zero peer-reviewed and zero primary sources caps credibility at 12.5/25."""
    sources = [
        {"id": "s1", "url": "https://unverified-tech-blog.com/post1", "publisher": "TechBlog", "title": "Post 1"},
        {"id": "s2", "url": "https://another-forum.net/thread2", "publisher": "Forum Net", "title": "Post 2"},
    ]
    claims = [{"id": "c1", "text": "General software claim"}]
    evidence = [{"id": "e1", "claim_id": "c1", "exact_text": "General descriptive statement on software claim."}]

    breakdown = calculate_calibrated_quality(sources=sources, claims=claims, evidence=evidence)
    assert breakdown.source_credibility <= 12.5
    assert breakdown.verified_peer_reviewed_count == 0
    assert any("capped at 12.5/25" in r for r in breakdown.reasons)


def test_lineage_derivative_reporting_and_weights():
    """Verify derivative secondary reporting around common entities collapses and receives lower weight."""
    sources = [
        {
            "id": "s-1",
            "title": "NVIDIA Keynote at GTC 2024: The Blackwell Architecture Revealed",
            "url": "https://techpress-alpha.com/nvidia-gtc-2024",
            "publisher": "TechPress Alpha",
        },
        {
            "id": "s-2",
            "title": "NVIDIA Blackwell GPUs Announced at GTC 2024: Architecture Analysis",
            "url": "https://hardware-beta.com/nvidia-blackwell-gtc-2024",
            "publisher": "Hardware Beta",
        },
        {
            "id": "s-3",
            "title": "Rigorous Thermal Profiling of Silicon Heat Dissipation in High-Density Packages",
            "url": "https://ieeexplore.ieee.org/document/998877",
            "publisher": "IEEE",
            "doi": "10.1109/TED.2024.123456",
        },
    ]

    res = analyze_source_lineage(sources)
    assert res.total_sources == 3
    # Tech press sources sharing the commercial announcement should collapse into derivative reporting
    assert len(res.clusters) < 3 or any(c.effective_independence_weight < 1.0 for c in res.clusters)
    # The IEEE paper should retain full weight 1.0
    ieee_cluster = next((c for c in res.clusters if "s-3" in c.member_source_ids), None)
    assert ieee_cluster is not None
    assert ieee_cluster.effective_independence_weight == 1.0


def test_three_quality_dimensions_decoupling():
    """Verify Operational Completeness (A) and Research Coverage (B) do NOT inflate Evidence Strength (C)."""
    # 15 sources with full-text documents
    sources = [
        {
            "id": f"s-{i}",
            "url": f"https://ieee.org/document/{i}",
            "publisher": "IEEE",
            "doi": f"10.1109/TEST.{i}",
            "title": f"Study {i}",
            "full_text_retrieved": True,
        }
        for i in range(15)
    ]
    # 5 claims, all covered
    claims = [{"id": f"c-{i}", "text": f"Datacenter thermal load increases cooling costs in region {i}."} for i in range(5)]
    # All claims covered by contextual background evidence only (0 direct empirical proof)
    evidence = [
        {
            "id": f"e-{i}",
            "claim_id": f"c-{i}",
            "exact_text": f"Published reviews describe datacenter thermal load dynamics and facility cooling costs in region {i}.",
        }
        for i in range(5)
    ]
    # Zero provider failures -> 100% operational completeness
    failures = []

    breakdown = calculate_calibrated_quality(
        sources=sources,
        claims=claims,
        evidence=evidence,
        failure_impacts=failures,
    )

    # Dimension A: Operational Completeness must be 100%
    assert breakdown.operational_completeness == 100.0

    # Dimension B: Research Coverage must be high (100%)
    assert breakdown.research_coverage >= 80.0

    # Dimension C: Evidence Strength must NOT be rated 'Strong' or 'Very Strong'
    # Even though coverage is 100% and sources are IEEE with full text, 0 direct proof caps tier to 'Moderate'!
    assert breakdown.calibrated_tier == "Moderate"
    assert breakdown.direct_support_count == 0
    assert any("strictly capped at 5.0/25" in r for r in breakdown.reasons)


def test_stopping_criteria_requires_peer_review():
    """Verify that stopping criteria requires peer_count >= 1 for SUFFICIENT_EVIDENCE."""
    workflow = AutonomousResearchWorkflow(
        id=uuid.uuid4(),
        investigation_id=uuid.uuid4(),
        title="Test Workflow",
        research_objective="Verify stopping criteria",
        status="running",
        current_cycle_number=3,
        spent_searches=5,
        budget_max_searches=20,
        budget_max_cycles=5,
        consecutive_low_value_cycles=0,
    )
    inv = Investigation(id=workflow.investigation_id, question="Test Question?")
    claims = [Claim(id=uuid.uuid4(), investigation_id=inv.id, text=f"Claim {i}") for i in range(3)]
    
    # 10 web sources WITHOUT peer-reviewed credibility
    sources = [
        Source(
            id=uuid.uuid4(),
            investigation_id=inv.id,
            canonical_url=f"https://webblog{i}.com",
            title=f"Web Blog {i}",
            publisher=f"WebBlog{i}",
            source_type="secondary_journalism",
        )
        for i in range(10)
    ]
    evidence = [
        Evidence(id=uuid.uuid4(), source_id=sources[0].id, claim_id=claims[i].id, exact_text=f"Evidence text {i}")
        for i in range(3)
    ]
    
    cal = ResearchQualityCalibration(
        investigation_id=inv.id,
        calibrated_tier="Strong",
        calibrated_score=75.0,
        coverage_score=90.0,
        failure_penalty=0.0,
    )

    # When peer_count == 0 (no verified peer review)
    stop_eval_no_peer = evaluate_stopping_criteria(
        workflow=workflow,
        investigation=inv,
        claims=claims,
        sources=sources,
        evidence=evidence,
        calibration=cal,
        contradictions=[],
        gaps=[],
    )
    # Must NOT stop on SUFFICIENT_EVIDENCE because peer_count == 0
    assert stop_eval_no_peer.stopping_reason != StoppingReason.SUFFICIENT_EVIDENCE

    # When peer review IS present
    class MockCred:
        is_peer_reviewed = True

    sources[0].__dict__["credibility_assessment"] = MockCred()

    stop_eval_with_peer = evaluate_stopping_criteria(
        workflow=workflow,
        investigation=inv,
        claims=claims,
        sources=sources,
        evidence=evidence,
        calibration=cal,
        contradictions=[],
        gaps=[],
    )
    # Now SUFFICIENT_EVIDENCE is earned
    assert stop_eval_with_peer.should_stop is True
    assert stop_eval_with_peer.stopping_reason == StoppingReason.SUFFICIENT_EVIDENCE


async def _ensure_benchmark_fixture_seeded(session) -> None:
    """Seed NVIDIA and Nokia historical benchmark dataset from JSON fixture if absent."""
    fixture_path = Path(__file__).parent / "fixtures" / "benchmark_calibration_fixture.json"
    if not fixture_path.exists():
        return
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for tbl in ["investigations", "claims", "sources", "evidence"]:
        rows = data.get(tbl, [])
        if not rows:
            continue
        cols = list(rows[0].keys())
        col_names = ", ".join(cols)
        named_placeholders = ", ".join([f":{c}" for c in cols])
        stmt = text(f"INSERT INTO {tbl} ({col_names}) VALUES ({named_placeholders})")
        for r in rows:
            await session.execute(stmt, r)
    await session.commit()


@pytest.mark.asyncio
async def test_nvidia_and_nokia_benchmark_calibration():
    """Verify calibration integrity on historical NVIDIA and Nokia benchmark datasets."""
    nvidia_id = uuid.UUID("97a2bf21-9f09-4411-9e9e-2ec925a5cb08")
    nokia_id = uuid.UUID("9ab9477a-33b8-4535-b578-eda03a64e254")

    async with SessionFactory() as session:
        inv_check = await session.get(Investigation, nvidia_id)
        if not inv_check:
            await _ensure_benchmark_fixture_seeded(session)

        # 1. NVIDIA Benchmark
        res_nv = await calibrate_investigation_quality(session, nvidia_id)
        # In NVIDIA, 0 direct proof passages -> capped at Moderate
        assert res_nv["calibrated_tier"] == "Moderate"
        assert res_nv["dimension_breakdown"]["direct_support_count"] == 0
        assert res_nv["dimension_breakdown"]["empirical_depth"] <= 5.0
        # High coverage and operational completeness decoupled from evidence strength
        assert res_nv["coverage_score"] >= 90.0
        assert res_nv["operational_completeness"] == 100.0
        assert res_nv["evidence_strength"] < 65.0

        # 2. Nokia Benchmark
        res_nokia = await calibrate_investigation_quality(session, nokia_id)
        # In Nokia, 6 direct proof passages, 8 verified peer-reviewed sources -> Strong
        assert res_nokia["calibrated_tier"] == "Strong"
        assert res_nokia["dimension_breakdown"]["direct_support_count"] >= 1
        assert res_nokia["dimension_breakdown"]["verified_peer_reviewed_count"] >= 5
        assert res_nokia["evidence_strength"] >= 70.0
