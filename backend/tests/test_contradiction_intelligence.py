import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.contradiction_service import contradiction_service
from app.db import SessionFactory
from app.main import app
from app.models import (
    Claim,
    ContradictionResolutionLog,
    Evidence,
    Investigation,
    ResearchContradiction,
    Source,
)
from app.schemas import (
    ContradictionCategory,
    ContradictionResolveRequest,
    ContradictionStatus,
)


@pytest.fixture
async def db_session():
    async with SessionFactory() as session:
        yield session


async def _create_test_investigation(
    session: AsyncSession, question: str
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
async def test_intra_investigation_evidence_contradiction(db_session: AsyncSession):
    """Claims with both supporting and contradicting evidence must be detected as empirical contradictions."""
    inv = await _create_test_investigation(
        db_session, "What is the effect of code completion tools on developer productivity?"
    )

    claim = Claim(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        text="AI code completion improves developer task completion speed by 55%.",
        priority=1,
    )
    source_survey = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Developer Self-Report Survey",
        canonical_url="https://example.org/survey2024",
        original_url="https://example.org/survey2024",
        source_type="crossref",
    )
    source_telemetry = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Git Commit Telemetry Benchmark",
        canonical_url="https://example.org/telemetry2024",
        original_url="https://example.org/telemetry2024",
        source_type="arxiv",
    )
    db_session.add_all([claim, source_survey, source_telemetry])

    ev_supp = Evidence(
        id=uuid.uuid4(),
        source_id=source_survey.id,
        claim_id=claim.id,
        exact_text="Survey respondents reported completing tasks 55% faster with copilot assistance.",
        evidence_type="supporting",
        relevance_score=0.9,
        extraction_method="heuristic",
    )
    ev_contra = Evidence(
        id=uuid.uuid4(),
        source_id=source_telemetry.id,
        claim_id=claim.id,
        exact_text="Telemetry analysis indicated code review cycle time increased by 18% due to subtle logical flaws.",
        evidence_type="contradicting",
        relevance_score=0.88,
        extraction_method="heuristic",
    )
    db_session.add_all([ev_supp, ev_contra])
    await db_session.commit()

    # Detect contradictions
    contradictions = await contradiction_service.detect_contradictions(
        session=db_session,
        investigation_id=inv.id,
        cross_investigation=False,
    )

    assert len(contradictions) >= 1
    contra = next((c for c in contradictions if claim.id in c.claim_ids), None)
    assert contra is not None
    assert contra.status == ContradictionStatus.newly_detected.value
    # Methodological divergence between survey and telemetry
    assert contra.category in [ContradictionCategory.methodological.value, ContradictionCategory.direct_factual.value]
    assert len(contra.supporting_passages) >= 1
    assert len(contra.conflicting_passages) >= 1
    assert contra.recommended_research_action


@pytest.mark.asyncio
async def test_contradiction_resolution_lifecycle(db_session: AsyncSession):
    """Test updating contradiction status and verifying persistent resolution logs."""
    inv = await _create_test_investigation(db_session, "Contradiction Resolution Test Study")
    claim = Claim(id=uuid.uuid4(), investigation_id=inv.id, text="Algorithm Alpha scales linearly.", priority=1)
    db_session.add(claim)

    source = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Scaling Study",
        canonical_url="https://example.org/scaling",
        original_url="https://example.org/scaling",
        source_type="crossref",
    )
    db_session.add(source)

    ev1 = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="Linear scaling observed up to 64 cluster nodes.",
        evidence_type="supporting",
        extraction_method="heuristic",
    )
    ev2 = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="Sub-linear throughput collapse observed beyond 128 cluster nodes.",
        evidence_type="contradicting",
        extraction_method="heuristic",
    )
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    detected = await contradiction_service.detect_contradictions(session=db_session, investigation_id=inv.id)
    assert len(detected) >= 1
    contra_id = detected[0].id

    # Resolve contradiction: scope_difference_identified
    payload = ContradictionResolveRequest(
        new_status=ContradictionStatus.scope_difference_identified.value,
        resolution_rationale="Scaling behavior exhibits a parametric threshold boundary at N=100 nodes.",
        resolving_evidence_ids=[ev2.id],
    )
    resolved = await contradiction_service.resolve_contradiction(
        session=db_session,
        contradiction_id=contra_id,
        payload=payload,
    )

    assert resolved.status == ContradictionStatus.scope_difference_identified.value
    assert len(resolved.resolution_logs) >= 1
    assert resolved.resolution_logs[-1].new_status == ContradictionStatus.scope_difference_identified.value
    assert "parametric threshold boundary" in resolved.resolution_logs[-1].resolution_rationale


@pytest.mark.asyncio
async def test_contradictions_api_endpoints(db_session: AsyncSession):
    """Test REST API routes for contradiction intelligence."""
    inv = await _create_test_investigation(db_session, "API route test investigation for contradictions.")
    claim = Claim(id=uuid.uuid4(), investigation_id=inv.id, text="Cache prefetching reduces L2 miss rate.", priority=1)
    source = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Cache Metrics",
        canonical_url="https://example.org/cache",
        original_url="https://example.org/cache",
        source_type="crossref",
    )
    db_session.add_all([claim, source])

    ev1 = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="L2 miss rate decreased by 40% in sequential access benchmarks.",
        evidence_type="supporting",
        extraction_method="heuristic",
    )
    ev2 = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="L2 cache thrashing increased by 25% under random graph traversal workloads.",
        evidence_type="contradicting",
        extraction_method="heuristic",
    )
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # POST /research/contradictions/detect
        detect_res = await client.post(
            "/api/v1/research/contradictions/detect",
            json={"investigation_id": str(inv.id), "cross_investigation": False},
        )
        assert detect_res.status_code == 200
        items = detect_res.json()
        assert len(items) >= 1
        cid = items[0]["id"]

        # GET /research/contradictions
        list_res = await client.get(f"/api/v1/research/contradictions?investigation_id={inv.id}")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # GET /research/contradictions/{id}
        get_res = await client.get(f"/api/v1/research/contradictions/{cid}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == cid

        # PATCH /research/contradictions/{id}/resolve
        patch_res = await client.patch(
            f"/api/v1/research/contradictions/{cid}/resolve",
            json={
                "new_status": "under_investigation",
                "resolution_rationale": "Verifying memory access pattern characteristics.",
                "resolving_evidence_ids": [],
            },
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "under_investigation"
