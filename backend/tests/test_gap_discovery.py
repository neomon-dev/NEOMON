import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.gap_service import gap_engine
from app.db import SessionFactory
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
    Source,
)
from app.schemas import GapCategory, GapSeverity


@pytest.fixture
async def db_session():
    async with SessionFactory() as session:
        yield session


async def _create_test_investigation(
    session: AsyncSession, question: str = "How does AI impact enterprise workforce?"
) -> Investigation:
    inv_id = uuid.uuid4()
    inv = Investigation(
        id=inv_id,
        question=question,
        mode="deep",
        status="completed",
    )
    session.add(inv)
    await session.commit()
    return inv


@pytest.mark.asyncio
async def test_claim_without_evidence_creates_critical_gap(db_session: AsyncSession):
    """Claims without evidence must generate a critical/high severity gap with suggested queries."""
    inv = await _create_test_investigation(db_session, "What is the impact of generative AI?")
    
    # Add a priority 1 claim with NO evidence
    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="Generative AI replaces 40% of customer support roles.",
        priority=1,
        status="unassessed",
    )
    db_session.add(claim)
    await db_session.commit()

    result = await gap_engine.analyze_investigation(db_session, inv.id, force_regenerate=True)
    assert result.investigation_id == inv.id
    assert len(result.gaps) > 0

    no_ev_gap = next((g for g in result.gaps if g.gap_type == "no_supporting_evidence"), None)
    assert no_ev_gap is not None
    assert no_ev_gap.severity == GapSeverity.critical.value
    assert no_ev_gap.research_priority >= 6.0
    assert no_ev_gap.claim_ids == [claim.id]
    assert len(no_ev_gap.recommended_action.suggested_queries) > 0
    assert "generative ai" in no_ev_gap.recommended_action.suggested_queries[0].lower()


@pytest.mark.asyncio
async def test_claim_with_only_contextual_evidence_creates_gap(db_session: AsyncSession):
    """Claims supported solely by background definitions must be flagged as contextual-only."""
    inv = await _create_test_investigation(db_session, "How does semiconductor packaging affect GPU throughput?")
    
    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="CoWoS packaging technology determines AI accelerator memory throughput.",
        priority=1,
        status="unassessed",
    )
    source = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Encyclopedia of Semiconductor Packaging",
        canonical_url="https://ieee.org/packaging-encyclopedia",
        original_url="https://ieee.org/packaging-encyclopedia",
        source_type="peer_reviewed",
        publisher="IEEE",
        inclusion_status="included",
        relevance_score=0.8,
    )
    ev = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="CoWoS (Chip-on-Wafer-on-Substrate) refers to a 2.5D wafer-level packaging technology invented by TSMC.",
        evidence_type="contextual",
        relevance_score=0.75,
        relevance_reason="Defines the packaging mechanism without directional measurement.",
        extraction_method="rule_based",
        traceable=True,
    )
    db_session.add_all([claim, source, ev])
    await db_session.commit()

    result = await gap_engine.analyze_investigation(db_session, inv.id, force_regenerate=True)
    context_gap = next((g for g in result.gaps if g.gap_type == "only_contextual_evidence"), None)
    assert context_gap is not None
    assert context_gap.category == GapCategory.claim_coverage.value
    assert context_gap.claim_ids == [claim.id]


@pytest.mark.asyncio
async def test_single_source_dependency_detection(db_session: AsyncSession):
    """Claims supported by only one independent source origin must be flagged for lack of replication."""
    inv = await _create_test_investigation(db_session, "Does high-bandwidth memory cause GPU supply shortages?")
    
    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="HBM3e production constraints limit global GPU accelerator shipments.",
        priority=2,
        status="supported",
    )
    source = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="HBM Market Analysis 2024",
        canonical_url="https://trendforce.com/reports/hbm-2024",
        original_url="https://trendforce.com/reports/hbm-2024",
        source_type="industry_analysis",
        publisher="TrendForce",
        inclusion_status="included",
        relevance_score=0.9,
    )
    ev1 = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="HBM3e yield constraints severely constrained GPU accelerator output throughout Q2 2024.",
        evidence_type="supporting",
        relevance_score=0.88,
        relevance_reason="Direct empirical corroboration.",
        extraction_method="rule_based",
        traceable=True,
    )
    db_session.add_all([claim, source, ev1])
    await db_session.commit()

    result = await gap_engine.analyze_investigation(db_session, inv.id, force_regenerate=True)
    single_src_gap = next((g for g in result.gaps if g.gap_type == "single_source_dependency"), None)
    assert single_src_gap is not None
    assert single_src_gap.claim_ids == [claim.id]
    assert result.coverage.claims_single_source >= 1


@pytest.mark.asyncio
async def test_unresolved_evidence_provenance_flagged_critically(db_session: AsyncSession):
    """Evidence with untraceable or mismatched provenance must trigger a critical gap and reduce coverage."""
    inv = await _create_test_investigation(db_session, "Impact of remote work on productivity")
    
    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="Remote work increases individual software developer output by 15%.",
        priority=1,
        status="supported",
    )
    source = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Software Engineering Productivity Study",
        canonical_url="https://acm.org/papers/remote-work",
        original_url="https://acm.org/papers/remote-work",
        source_type="peer_reviewed",
        publisher="ACM",
        inclusion_status="included",
        relevance_score=0.85,
    )
    ev_corrupted = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="Fabricated quotation that does not exist in any document.",
        evidence_type="supporting",
        relevance_score=0.8,
        relevance_reason="[UNRESOLVED PROVENANCE] Exact text was not found in the linked document content.",
        extraction_method="rule_based",
        traceable=False,
    )
    db_session.add_all([claim, source, ev_corrupted])
    await db_session.commit()

    result = await gap_engine.analyze_investigation(db_session, inv.id, force_regenerate=True)
    prov_gap = next((g for g in result.gaps if g.gap_type == "unresolved_provenance"), None)
    assert prov_gap is not None
    assert prov_gap.severity == GapSeverity.critical.value
    assert result.coverage.unresolved_provenance_count >= 1
    assert prov_gap.recommended_action.action_type == "full_text_acquisition"


@pytest.mark.asyncio
async def test_unresolved_contradiction_gap_detection(db_session: AsyncSession):
    """Claims with conflicting evidence but no resolving adjudication must be flagged."""
    inv = await _create_test_investigation(db_session, "Does coffee consumption improve cognitive performance?")
    
    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="Daily caffeine intake consistently improves working memory retention.",
        priority=1,
        status="conflicted",
    )
    source1 = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Cognitive Neuroscience Journal 2023",
        canonical_url="https://nature.com/neuro/caffeine-study",
        original_url="https://nature.com/neuro/caffeine-study",
        source_type="peer_reviewed",
        publisher="Nature",
        inclusion_status="included",
        relevance_score=0.9,
    )
    source2 = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Clinical Pharmacology Review 2024",
        canonical_url="https://thelancet.com/caffeine-pharmacology",
        original_url="https://thelancet.com/caffeine-pharmacology",
        source_type="peer_reviewed",
        publisher="The Lancet",
        inclusion_status="included",
        relevance_score=0.9,
    )
    ev_supp = Evidence(
        id=uuid.uuid4(),
        source_id=source1.id,
        claim_id=claim.id,
        exact_text="Clinical trials demonstrates significant increase in working memory task accuracy under 200mg caffeine.",
        evidence_type="supporting",
        relevance_score=0.88,
        relevance_reason="Demonstrates positive effect.",
        extraction_method="rule_based",
        traceable=True,
    )
    ev_contra = Evidence(
        id=uuid.uuid4(),
        source_id=source2.id,
        claim_id=claim.id,
        exact_text="Controlled multi-cohort evaluation contradicts prior findings; caffeine did not improve retention metrics.",
        evidence_type="contradicting",
        relevance_score=0.89,
        relevance_reason="Refutes memory improvements.",
        extraction_method="rule_based",
        traceable=True,
    )
    db_session.add_all([claim, source1, source2, ev_supp, ev_contra])
    await db_session.commit()

    result = await gap_engine.analyze_investigation(db_session, inv.id, force_regenerate=True)
    contra_gap = next((g for g in result.gaps if g.gap_type == "unresolved_contradiction"), None)
    assert contra_gap is not None
    assert contra_gap.severity == GapSeverity.critical.value
    assert contra_gap.recommended_action.action_type == "conflict_resolution"


@pytest.mark.asyncio
async def test_missing_full_text_and_primary_studies_detection(db_session: AsyncSession):
    """Sources without full-text documents and lack of peer-reviewed primary studies must be identified."""
    inv = await _create_test_investigation(db_session, "Quantum computing benchmarks")
    
    # Source with no Document or metadata-only
    source_preprint = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Early Experimental Notes on Quantum Supremacy",
        canonical_url="https://arxiv.org/abs/2401.99999",
        original_url="https://arxiv.org/abs/2401.99999",
        source_type="preprint",
        publisher="arXiv",
        inclusion_status="included",
        relevance_score=0.82,
    )
    db_session.add(source_preprint)
    await db_session.commit()

    result = await gap_engine.analyze_investigation(db_session, inv.id, force_regenerate=True)
    
    # Check missing full-text gap
    ft_gap = next((g for g in result.gaps if g.gap_type == "missing_full_text"), None)
    assert ft_gap is not None
    assert ft_gap.category == GapCategory.evidence_coverage.value

    # Check missing peer-reviewed primary studies gap
    primary_gap = next((g for g in result.gaps if g.gap_type == "missing_primary_studies"), None)
    assert primary_gap is not None
    assert primary_gap.severity == GapSeverity.high.value


@pytest.mark.asyncio
async def test_perspective_gaps_advocacy_and_mitigation(db_session: AsyncSession):
    """Investigations with one-sided debate or missing mitigating factors must be detected."""
    inv = await _create_test_investigation(db_session, "Consequences of automated AI layoffs")
    
    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="Enterprise automation leads directly to permanent headcount reduction.",
        priority=1,
    )
    db_session.add(claim)
    await db_session.flush()

    job = AnalysisJob(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        status="completed",
    )
    db_session.add(job)
    await db_session.flush()

    exec_adv = AnalysisAgentExecution(
        id=uuid.uuid4(),
        job_id=job.id,
        agent_identifier="advocate",
        status="completed",
    )
    db_session.add(exec_adv)
    await db_session.flush()

    # Only advocate argument, no skeptic argument
    arg_adv = AgentArgument(
        id=uuid.uuid4(),
        job_id=job.id,
        execution_id=exec_adv.id,
        claim_id=claim.id,
        agent_identifier="advocate",
        argument_type="advocate",
        text="Advocate position: Enterprise automation leads directly to permanent headcount reduction.",
        reasoning_summary="Automation causes permanent staff reductions without immediate re-absorption.",
        confidence_level="high",
        confidence_explanation="Supported by primary enterprise survey data.",
    )
    db_session.add(arg_adv)
    await db_session.commit()

    result = await gap_engine.analyze_investigation(db_session, inv.id, force_regenerate=True)
    
    # Check unbalanced advocacy gap
    adv_gap = next((g for g in result.gaps if g.gap_type == "unbalanced_advocacy_skepticism"), None)
    assert adv_gap is not None
    assert adv_gap.category == GapCategory.perspective.value
    assert adv_gap.severity == GapSeverity.high.value


@pytest.mark.asyncio
async def test_research_subquestion_generation(db_session: AsyncSession):
    """Under-evidenced claims must yield concrete proposed research subquestions."""
    inv = await _create_test_investigation(db_session, "Impact of AI on energy grid stability")
    
    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="Hyperscale AI datacenters destabilize regional electrical grids during peak training loads.",
        priority=1,
        status="unassessed",
    )
    db_session.add(claim)
    await db_session.commit()

    result = await gap_engine.analyze_investigation(db_session, inv.id, force_regenerate=True)
    subq_gap = next((g for g in result.gaps if g.gap_type == "unanswered_research_subquestion"), None)
    assert subq_gap is not None
    assert subq_gap.category == GapCategory.research_question.value
    assert "boundary conditions" in subq_gap.title.lower()
    assert len(subq_gap.recommended_action.suggested_queries) > 0


@pytest.mark.asyncio
async def test_llm_failure_graceful_fallback(db_session: AsyncSession):
    """When LLM provider raises an exception or returns invalid JSON, gap analysis must succeed via deterministic fallback."""
    inv = await _create_test_investigation(db_session, "Neural network pruning benchmarks")
    
    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="Structured magnitude pruning maintains 98% accuracy at 50% parameter sparsity.",
        priority=2,
        status="unassessed",
    )
    db_session.add(claim)
    await db_session.commit()

    with patch.object(gap_engine, "_run_llm_gap_analysis", side_effect=RuntimeError("LLM API connection timed out")):
        result = await gap_engine.analyze_investigation(
            db_session, inv.id, provider_kind="ollama", model="llama3", force_regenerate=True
        )
        assert result.investigation_id == inv.id
        assert len(result.gaps) > 0
        assert result.coverage.coverage_score >= 0.0


@pytest.mark.asyncio
async def test_gap_analysis_versioning_and_isolation(db_session: AsyncSession):
    """Repeated analyses must create incremental versions, and investigations must remain completely isolated."""
    inv1 = await _create_test_investigation(db_session, "Investigation One: Memory Bandwidth")
    inv2 = await _create_test_investigation(db_session, "Investigation Two: Quantum Teleportation")

    c1 = Claim(id=uuid.uuid4(), investigation_id=inv1.id, text="Claim in Investigation One", priority=1)
    c2 = Claim(id=uuid.uuid4(), investigation_id=inv2.id, text="Claim in Investigation Two", priority=1)
    db_session.add_all([c1, c2])
    await db_session.commit()

    # Run investigation 1 version 1
    v1 = await gap_engine.analyze_investigation(db_session, inv1.id, force_regenerate=True)
    assert v1.version_number == 1

    # Run investigation 1 version 2
    v2 = await gap_engine.analyze_investigation(db_session, inv1.id, force_regenerate=True)
    assert v2.version_number == 2
    assert v2.id != v1.id

    # List versions for inv1
    versions_inv1 = await gap_engine.list_gap_analysis_versions(db_session, inv1.id)
    assert len(versions_inv1) == 2
    assert versions_inv1[0].version_number == 2
    assert versions_inv1[1].version_number == 1

    # Run investigation 2
    v_inv2 = await gap_engine.analyze_investigation(db_session, inv2.id, force_regenerate=True)
    assert v_inv2.version_number == 1

    # Ensure isolation: inv2 has 1 version, inv1 has 2 versions
    versions_inv2 = await gap_engine.list_gap_analysis_versions(db_session, inv2.id)
    assert len(versions_inv2) == 1
    assert versions_inv2[0].investigation_id == inv2.id


@pytest.mark.asyncio
async def test_gap_api_endpoints_via_client(client, db_session: AsyncSession):
    """Test all research gap REST endpoints via FastAPI TestClient."""
    inv = await _create_test_investigation(db_session, "Are solid state batteries production viable?")
    claim = Claim(id=uuid.uuid4(), investigation_id=inv.id, text="Solid state electrolyte achieves 1000 Wh/L", priority=1)
    db_session.add(claim)
    await db_session.commit()
    inv_id = str(inv.id)

    # 1. POST /research/investigations/{id}/gaps/analyze
    post_res = client.post(f"/api/v1/research/investigations/{inv_id}/gaps/analyze", json={"force_regenerate": True})
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["investigation_id"] == inv_id
    assert "coverage" in post_data
    assert "gaps" in post_data
    assert isinstance(post_data["coverage"]["coverage_score"], (int, float))

    # 2. GET /research/investigations/{id}/gaps
    get_res = client.get(f"/api/v1/research/investigations/{inv_id}/gaps")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == post_data["id"]

    # 3. GET /research/investigations/{id}/gaps/versions
    ver_res = client.get(f"/api/v1/research/investigations/{inv_id}/gaps/versions")
    assert ver_res.status_code == 200
    assert len(ver_res.json()) >= 1

    # 4. GET /research/investigations/{id}/gaps/versions/{version_or_id}
    spec_res = client.get(f"/api/v1/research/investigations/{inv_id}/gaps/versions/1")
    assert spec_res.status_code == 200
    assert spec_res.json()["version_number"] == 1

    # 5. GET /research/investigations/{id}/gaps/items with filtering
    items_res = client.get(f"/api/v1/research/investigations/{inv_id}/gaps/items?limit=10&offset=0")
    assert items_res.status_code == 200
    items_data = items_res.json()
    assert "items" in items_data
    assert "total" in items_data
    assert items_data["total"] >= len(items_data["items"])
