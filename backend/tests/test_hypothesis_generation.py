import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.gap_service import gap_engine
from app.analysis.hypothesis_service import hypothesis_service
from app.db import SessionFactory
from app.main import app
from app.models import (
    Claim,
    ClaimEvidenceRelationship,
    Document,
    Evidence,
    Investigation,
    ResearchHypothesis,
    Source,
)
from app.schemas import (
    HypothesisCategory,
    HypothesisEvaluationRequest,
    HypothesisStatus,
)


@pytest.fixture
async def db_session():
    async with SessionFactory() as session:
        yield session


async def _create_test_investigation(
    session: AsyncSession, question: str = "How do remote work arrangements affect team velocity?"
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
async def test_hypothesis_generation_grounded_in_gaps(db_session: AsyncSession):
    """Hypotheses must be derived from claims and unaddressed gaps with explicit falsification criteria."""
    inv = await _create_test_investigation(db_session, "How does automated code review affect deployment safety?")

    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="Automated pull request checks reduce post-deployment defects by 35%.",
        priority=1,
        status="analyzed",
    )
    db_session.add(claim)

    source = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Software Quality Metrics",
        canonical_url="https://example.org/metrics",
        original_url="https://example.org/metrics",
        source_type="crossref",
        doi="10.1000/182",
    )
    db_session.add(source)

    ev_supp = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="Automated checks caught 120 regression issues before production release.",
        relevance_score=0.88,
        evidence_type="supporting",
        extraction_method="heuristic",
    )
    ev_chall = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="Complex architectural logic errors bypassed automated linting without warning.",
        relevance_score=0.75,
        evidence_type="contradicting",
        extraction_method="heuristic",
    )
    db_session.add_all([ev_supp, ev_chall])
    await db_session.commit()

    # Pre-generate gaps so hypothesis engine can leverage them
    await gap_engine.analyze_investigation(db_session, inv.id, force_regenerate=True)

    # Generate hypotheses
    result = await hypothesis_service.generate_hypotheses(db_session, inv.id, force_regenerate=True)
    assert result.investigation_id == inv.id
    assert len(result.hypotheses) > 0

    first_hyp = result.hypotheses[0]
    assert first_hyp.title
    assert first_hyp.statement
    assert first_hyp.rationale
    assert first_hyp.falsification_criteria, "Hypothesis must possess explicit falsification criteria"
    assert first_hyp.status == HypothesisStatus.proposed.value
    assert first_hyp.testability_score >= 1.0
    assert first_hyp.falsifiability_score >= 1.0
    assert len(first_hyp.independent_variables) > 0
    assert len(first_hyp.dependent_variables) > 0


@pytest.mark.asyncio
async def test_hypothesis_status_lifecycle_and_evaluation(db_session: AsyncSession):
    """Test hypothesis review status transitions and multi-dimensional evaluation."""
    inv = await _create_test_investigation(db_session, "What is the efficacy of retrieval-augmented generation?")

    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="RAG systems eliminate 90% of factual hallucinations in domain specific queries.",
        priority=1,
    )
    db_session.add(claim)
    await db_session.commit()

    gen_resp = await hypothesis_service.generate_hypotheses(db_session, inv.id, force_regenerate=True)
    assert len(gen_resp.hypotheses) > 0
    hyp = gen_resp.hypotheses[0]

    # Update status to under_review
    updated = await hypothesis_service.update_hypothesis_status(
        session=db_session,
        investigation_id=inv.id,
        hypothesis_id=hyp.id,
        new_status=HypothesisStatus.under_review.value,
        review_comments="Initial methodological scrutiny initiated.",
    )
    assert updated.status == HypothesisStatus.under_review.value

    # Submit evaluation
    eval_req = HypothesisEvaluationRequest(
        reviewer_role="domain_expert",
        status=HypothesisStatus.supported_by_subsequent_evidence,
        evidence_grounding_score=8.5,
        novelty_score=7.8,
        logical_consistency_score=9.0,
        falsifiability_score=8.7,
        testability_score=8.9,
        methodological_feasibility_score=8.0,
        review_comments="Rigorous evaluation confirms falsifiability and empirical testability.",
    )
    evaluated = await hypothesis_service.evaluate_hypothesis(
        session=db_session,
        investigation_id=inv.id,
        hypothesis_id=hyp.id,
        payload=eval_req,
    )
    assert evaluated.status == HypothesisStatus.supported_by_subsequent_evidence.value
    assert evaluated.testability_score == 8.9
    assert evaluated.evidence_grounding_score == 8.5
    assert len(evaluated.evaluations) >= 1
    assert evaluated.evaluations[-1].reviewer_role == "domain_expert"


@pytest.mark.asyncio
async def test_hypotheses_api_routes(db_session: AsyncSession):
    """Test API endpoints for hypotheses listing, generation, and status update."""
    inv = await _create_test_investigation(db_session, "How does distributed consensus scale?")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Generate
        gen_res = await client.post(
            f"/api/v1/research/investigations/{inv.id}/hypotheses/generate",
            json={"force_regenerate": True},
        )
        assert gen_res.status_code == 200
        data = gen_res.json()
        assert data["investigation_id"] == str(inv.id)
        assert len(data["hypotheses"]) > 0
        hyp_id = data["hypotheses"][0]["id"]

        # List
        list_res = await client.get(f"/api/v1/research/investigations/{inv.id}/hypotheses")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) >= 1

        # Get Single
        get_res = await client.get(f"/api/v1/research/investigations/{inv.id}/hypotheses/{hyp_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == hyp_id

        # Patch Status
        patch_res = await client.patch(
            f"/api/v1/research/investigations/{inv.id}/hypotheses/{hyp_id}/status",
            json={"status": "under_review", "review_comments": "Scrutinizing variables."},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "under_review"
