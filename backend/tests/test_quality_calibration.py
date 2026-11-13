"""Automated tests for Research Quality Calibration & Scientific Evidence Validation (Milestone 8G).

Verifies:
- Canonical source credibility with strict peer-review separation (8G.1)
- Explainable source lineage and independence clustering (8G.2)
- Logical evidence-to-claim entailment and correlation-vs-causation flagging (8G.3)
- Calibrated 5D evidence strength scoring and failure penalties (8G.4 & 8G.5)
- Regression Benchmark A: NVIDIA (prevents false 'very_strong' with 66.5% coverage and 8 failures)
- Regression Benchmark B: RAM Shortages (detects domain diversity illusion & correlation conflation)
- API endpoint integration
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.analysis.entailment_service import (
    EntailmentClassification,
    validate_evidence_claim_entailment_heuristic,
)
from app.analysis.quality_calibration_service import (
    calculate_calibrated_quality,
    calibrate_investigation_quality,
)
from app.db import SessionFactory
from app.main import app
from app.models import Claim, Evidence, Investigation, ProviderFailureImpact, Source
from app.research.source_credibility import (
    CanonicalSourceType,
    SourceVerificationStatus,
    evaluate_canonical_credibility,
)
from app.research.source_lineage import (
    SourceLineageType,
    analyze_source_lineage,
)


def test_canonical_source_credibility_separation():
    """Verify 8G.1 rules: DOI does not equal peer review; preprints are not peer-reviewed."""
    # 1. Academic peer-reviewed journal with DOI
    eval_ieee = evaluate_canonical_credibility(
        url="https://ieeexplore.ieee.org/document/10123456",
        publisher="IEEE",
        doi="10.1109/TPAMI.2024.12345",
        source_type_declared="academic",
    )
    assert eval_ieee.source_type == CanonicalSourceType.PEER_REVIEWED_JOURNAL
    assert eval_ieee.is_peer_reviewed is True
    assert eval_ieee.is_primary is True
    assert eval_ieee.verification_status == SourceVerificationStatus.VERIFIED

    # 2. Preprint with registered DOI (e.g. arXiv)
    eval_arxiv = evaluate_canonical_credibility(
        url="https://arxiv.org/abs/2403.99999",
        publisher="arXiv",
        doi="10.48550/arXiv.2403.99999",
        source_type_declared="preprint",
    )
    assert eval_arxiv.source_type == CanonicalSourceType.ACADEMIC_PREPRINT
    assert eval_arxiv.is_peer_reviewed is False  # Must NOT be marked peer-reviewed
    assert eval_arxiv.is_primary is True
    assert eval_arxiv.verification_status == SourceVerificationStatus.HIGH_CONFIDENCE

    # 3. Open repository DOI (Zenodo)
    eval_zenodo = evaluate_canonical_credibility(
        url="https://zenodo.org/records/1234567",
        publisher="Zenodo",
        doi="10.5281/zenodo.1234567",
    )
    assert eval_zenodo.is_peer_reviewed is False
    assert eval_zenodo.source_type == CanonicalSourceType.TECHNICAL_WHITEPAPER
    assert eval_zenodo.verification_status == SourceVerificationStatus.UNVERIFIED

    # 4. Corporate vendor whitepaper with DOI
    eval_vendor_doi = evaluate_canonical_credibility(
        url="https://solutions.commercial-vendor.com/whitepaper.pdf",
        publisher="Commercial Vendor Corp",
        doi="10.1000/182",
    )
    assert eval_vendor_doi.is_peer_reviewed is False
    assert eval_vendor_doi.credibility_score <= 0.65

    # 5. Government / Institutional authority
    eval_gov = evaluate_canonical_credibility(
        url="https://www.nist.gov/publications/ai-risk-standards",
        publisher="National Institute of Standards and Technology",
    )
    assert eval_gov.source_type == CanonicalSourceType.INSTITUTIONAL_REPORT
    assert eval_gov.is_primary is True
    assert eval_gov.is_peer_reviewed is False  # Authoritative primary, not peer-reviewed journal


def test_source_lineage_and_syndication_clustering():
    """Verify 8G.2: Syndicated publications and shared-lineage reports collapse into 1 cluster."""
    sources = [
        {
            "id": "src-1",
            "title": "Reuters: Memory chip prices jump as AI boom accelerates",
            "url": "https://www.reuters.com/tech/memory-chip-prices-2024",
            "publisher": "Reuters",
        },
        {
            "id": "src-2",
            "title": "Reuters: Memory chip prices jump as AI boom accelerates",
            "url": "https://finance.yahoo.com/news/reuters-memory-chip-prices",
            "publisher": "Yahoo Finance",
        },
        {
            "id": "src-3",
            "title": "Memory chip prices jump as AI boom accelerates",
            "url": "https://msn.com/en-us/money/memory-chip-prices",
            "publisher": "MSN Money",
        },
        {
            "id": "src-4",
            "title": "Independent Microarchitectural Evaluation of HBM3 vs DDR5",
            "url": "https://dl.acm.org/doi/10.1145/99999",
            "publisher": "ACM",
            "doi": "10.1145/99999",
            "authors": ["Dr. Alice Chen", "Dr. Bob Smith"],
        },
    ]

    res = analyze_source_lineage(sources)
    assert res.total_sources == 4
    # The 3 syndicated Reuters copies must collapse into 1 cluster, leaving 2 effective clusters
    assert res.effective_independent_count == 2.0
    assert res.independence_ratio == 0.5
    assert len(res.clusters) == 2


def test_evidence_claim_entailment_validation():
    """Verify 8G.3: Distinguishes direct support, contextual background, correlation, and refutation."""
    claim = "AI workload demand caused memory market shortages in 2024."

    # Direct Causal Proof
    ev_direct = (
        "Empirical production allocation data demonstrates that AI accelerator demand directly caused "
        "a 34% reduction in consumer DDR5 wafer allocation, triggering the 2024 market shortage."
    )
    val_direct = validate_evidence_claim_entailment_heuristic(
        claim_id="c1", claim_text=claim, evidence_id="e1", evidence_text=ev_direct
    )
    assert val_direct.entailment_classification == EntailmentClassification.DIRECT_SUPPORT
    assert val_direct.correlation_vs_causation_flag is False

    # Correlational / Associative (Benchmark B flaw)
    ev_corr = (
        "During 2024, high consumer RAM prices coincided with increased AI server purchases alongside "
        "broader technology sector inflation."
    )
    val_corr = validate_evidence_claim_entailment_heuristic(
        claim_id="c1", claim_text=claim, evidence_id="e2", evidence_text=ev_corr
    )
    assert val_corr.entailment_classification == EntailmentClassification.CONTEXTUAL_SUPPORT
    assert val_corr.correlation_vs_causation_flag is True
    assert len(val_corr.missing_inferential_steps) > 0

    # Refutation / Direct Contradiction
    ev_contra = (
        "Supply chain audit disproves the shortage hypothesis; fab output records confirm that "
        "consumer RAM inventories were elevated and no shortage occurred."
    )
    val_contra = validate_evidence_claim_entailment_heuristic(
        claim_id="c1", claim_text=claim, evidence_id="e3", evidence_text=ev_contra
    )
    assert val_contra.entailment_classification == EntailmentClassification.DIRECT_CONTRADICTION

    # Methodological Limitation
    ev_limit = (
        "Our market forecast is based on an uncalibrated simulation only with a small sample size of two vendors."
    )
    val_limit = validate_evidence_claim_entailment_heuristic(
        claim_id="c1", claim_text=claim, evidence_id="e4", evidence_text=ev_limit
    )
    assert val_limit.entailment_classification == EntailmentClassification.METHODOLOGICAL_LIMITATION


def test_regression_benchmark_a_nvidia():
    """Regression Benchmark A: 'What role NVIDIA played in the era of AI?'
    
    Verifies that low coverage (66.5%), 8 provider failures, and 0 peer-reviewed sources
    CANNOT achieve 'Very Strong' rating.
    """
    sources = [
        {"id": f"s-{i}", "title": f"Tech Article on NVIDIA {i}", "url": f"https://tech-news-{i}.com/nvidia", "publisher": "Tech Press"}
        for i in range(20)
    ]
    # 9 full text documents out of 20
    for i in range(9):
        sources[i]["full_text_retrieved"] = True

    claims = [
        {"id": f"c-{i}", "text": f"NVIDIA foundational role claim {i}"}
        for i in range(5)
    ]

    # Contextual evidence passages
    evidence = [
        {
            "id": f"e-{i}",
            "claim_id": f"c-{i % 3}",  # Only covers 3 of 5 claims
            "exact_text": f"NVIDIA was founded in 1993 and produces graphic chips used in computing.",
        }
        for i in range(12)
    ]

    # 8 provider failures
    failures = [
        {
            "provider": "crossref",
            "operation": "academic_search",
            "query": "nvidia transformer training empirical",
            "impact_severity": "significant_coverage",
            "missing_category": "academic_empirical",
        }
        for _ in range(8)
    ]

    breakdown = calculate_calibrated_quality(
        sources=sources,
        claims=claims,
        evidence=evidence,
        failure_impacts=failures,
    )

    # In Benchmark A, uncalibrated score was 'Very Strong'.
    # Under calibrated 8G:
    # 1. Zero peer-reviewed sources
    # 2. Coverage is well below threshold (<70%)
    # 3. 8 significant provider failures incur penalty
    # The tier MUST NOT be Very Strong or Strong!
    assert breakdown.calibrated_tier in ("Moderate", "Weak", "Inconclusive")
    assert breakdown.coverage_score < 70.0
    assert breakdown.failure_penalty >= 20.0


def test_regression_benchmark_b_ram_shortages():
    """Regression Benchmark B: 'How does AI contribute to RAM shortages?'
    
    Verifies syndication detection, correlation-vs-causation flagging, and independence correction.
    """
    # 5 outlets reporting on the same press release
    sources = [
        {"id": "s1", "title": "Memory Prices Spurt As AI Server Orders Swell", "url": "https://tomshardware.com/ram-ai", "publisher": "Tom's Hardware"},
        {"id": "s2", "title": "Memory Prices Spurt As AI Server Orders Swell", "url": "https://techspot.com/ram-ai", "publisher": "TechSpot"},
        {"id": "s3", "title": "Memory Prices Spurt As AI Server Orders Swell", "url": "https://wccftech.com/ram-ai", "publisher": "Wccftech"},
        {"id": "s4", "title": "Memory Prices Spurt As AI Server Orders Swell", "url": "https://pcgamer.com/ram-ai", "publisher": "PC Gamer"},
        {"id": "s5", "title": "Memory Prices Spurt As AI Server Orders Swell", "url": "https://anandtech.com/ram-ai", "publisher": "AnandTech"},
    ]

    claims = [{"id": "c1", "text": "AI causes consumer RAM shortages."}]

    evidence = [
        {
            "id": "e1",
            "claim_id": "c1",
            "exact_text": "During 2024, consumer RAM prices rose alongside AI hardware deployments.",
        }
    ]

    breakdown = calculate_calibrated_quality(
        sources=sources,
        claims=claims,
        evidence=evidence,
    )

    # Effective independent count must collapse to 1 cluster
    assert breakdown.source_independence < 15.0
    assert any("conflating correlation with causation" in r for r in breakdown.reasons)


@pytest.mark.asyncio
async def test_quality_audit_api_integration():
    """Verify Quality Audit API endpoints."""
    inv_id = uuid.uuid4()
    async with SessionFactory() as session:
        inv = Investigation(id=inv_id, question="Quantum computing cryptographic vulnerability audit?", mode="deep")
        c = Claim(id=uuid.uuid4(), investigation_id=inv_id, text="Shor algorithm poses theoretical risk to RSA.")
        src = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="Shor's Algorithm Security Review",
            canonical_url="https://ieeexplore.ieee.org/document/888888",
            original_url="https://ieeexplore.ieee.org/document/888888",
            source_type="academic",
            publisher="IEEE",
            doi="10.1109/TIT.1997.100",
        )
        ev = Evidence(
            id=uuid.uuid4(),
            source_id=src.id,
            claim_id=c.id,
            exact_text="Shor algorithm proves polynomial time factorization of integers on fault-tolerant quantum computers.",
            evidence_type="direct",
            relevance_score=0.92,
            extraction_method="direct_snippet",
        )
        fail = ProviderFailureImpact(
            investigation_id=inv_id,
            provider="tavily",
            operation="web_search",
            query="quantum crypto",
            failure_type="timeout",
            impact_severity="harmless_optional",
            explanation="Optional search provider timed out, academic sources secured.",
        )
        session.add_all([inv, c, src, ev, fail])
        await session.commit()

    with TestClient(app) as client:
        # 1. Trigger calibration
        cal_resp = client.post(f"/api/v1/research/investigations/{inv_id}/quality/calibrate")
        assert cal_resp.status_code == 200
        cal_data = cal_resp.json()
        assert cal_data["investigation_id"] == str(inv_id)
        assert "calibrated_tier" in cal_data
        assert cal_data["verified_peer_reviewed_count"] == 1

        # 2. Get Audit Report
        audit_resp = client.get(f"/api/v1/research/investigations/{inv_id}/quality/audit")
        assert audit_resp.status_code == 200
        audit_data = audit_resp.json()
        assert audit_data["total_sources"] == 1
        assert audit_data["verified_peer_reviewed_count"] == 1

        # 3. Get Lineage
        lin_resp = client.get(f"/api/v1/research/investigations/{inv_id}/quality/lineage")
        assert lin_resp.status_code == 200
        lin_data = lin_resp.json()
        assert lin_data["total_sources"] == 1
        assert len(lin_data["clusters"]) == 1

        # 4. Get Validations
        val_resp = client.get(f"/api/v1/research/investigations/{inv_id}/quality/validations")
        assert val_resp.status_code == 200
        vals = val_resp.json()
        assert len(vals) == 1
        assert vals[0]["entailment_classification"] in ("direct_support", "contextual_support")

        # 5. Get Failures
        fail_resp = client.get(f"/api/v1/research/investigations/{inv_id}/quality/failures")
        assert fail_resp.status_code == 200
        fails = fail_resp.json()
        assert len(fails) == 1
        assert fails[0]["impact_severity"] == "harmless_optional"

        # 6. List Audits
        list_resp = client.get("/api/v1/research/quality/audits")
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert any(item["investigation_id"] == str(inv_id) for item in items)
