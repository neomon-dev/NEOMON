import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.synthesis_service import synthesis_service
from app.db import SessionFactory
from app.main import app
from app.models import (
    Claim,
    CrossInvestigationRelationship,
    Evidence,
    Investigation,
    InvestigationSynthesisReport,
    Source,
)
from app.schemas import CrossRelationshipType


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
async def test_cross_investigation_synthesis_and_relationship_discovery(db_session: AsyncSession):
    """Test synthesis across two investigations with shared sources and conflicting/supporting claims."""
    # Investigation A
    inv_a = await _create_test_investigation(
        db_session, "How does remote work impact software engineering productivity?"
    )
    claim_a1 = Claim(
        id=uuid.uuid4(),
        investigation_id=inv_a.id,
        text="Remote work increases focused software engineering velocity by 25%.",
        priority=1,
    )
    claim_a2 = Claim(
        id=uuid.uuid4(),
        investigation_id=inv_a.id,
        text="Remote onboarding reduces team alignment during initial quarter.",
        priority=2,
    )
    source_shared = Source(
        id=uuid.uuid4(),
        investigation_id=inv_a.id,
        title="Engineering Org Benchmarks 2024",
        canonical_url="https://doi.org/10.1016/j.eng.2024.01",
        original_url="https://doi.org/10.1016/j.eng.2024.01",
        source_type="crossref",
        doi="10.1016/j.eng.2024.01",
    )
    db_session.add_all([claim_a1, claim_a2, source_shared])

    # Investigation B
    inv_b = await _create_test_investigation(
        db_session, "What are the organizational communication costs of hybrid work models?"
    )
    claim_b1 = Claim(
        id=uuid.uuid4(),
        investigation_id=inv_b.id,
        text="Remote work decreases software engineering communication velocity.",
        priority=1,
    )
    source_b_shared = Source(
        id=uuid.uuid4(),
        investigation_id=inv_b.id,
        title="Engineering Org Benchmarks 2024",
        canonical_url="https://doi.org/10.1016/j.eng.2024.01",
        original_url="https://doi.org/10.1016/j.eng.2024.01",
        source_type="crossref",
        doi="10.1016/j.eng.2024.01",
    )
    db_session.add_all([claim_b1, source_b_shared])
    await db_session.commit()

    # Run Synthesis
    report, rels = await synthesis_service.synthesize_investigations(
        session=db_session,
        investigation_ids=[inv_a.id, inv_b.id],
    )

    assert report.id is not None
    assert len(report.investigation_ids) == 2
    assert "remote" in report.summary.lower()
    assert len(report.shared_evidence) >= 1
    assert any("10.1016/j.eng.2024.01" in item.get("identifier", "") for item in report.shared_evidence)

    # Relationships verification
    assert len(rels) >= 1
    rel_types = [r.relationship_type for r in rels]
    assert CrossRelationshipType.shares_evidence_with.value in rel_types
    # There should also be directional tension (challenges) between a1 ("increases") and b1 ("decreases")
    assert any(r.relationship_type in [CrossRelationshipType.challenges.value, CrossRelationshipType.supports.value] for r in rels)


@pytest.mark.asyncio
async def test_global_claim_search_and_shared_evidence(db_session: AsyncSession):
    """Test global cross-investigation claim search and shared evidence discovery."""
    inv1 = await _create_test_investigation(db_session, "Study on distributed systems reliability.")
    inv2 = await _create_test_investigation(db_session, "Study on consensus algorithms performance.")

    c1 = Claim(id=uuid.uuid4(), investigation_id=inv1.id, text="Raft leader election latency averages 150ms.", priority=1)
    c2 = Claim(id=uuid.uuid4(), investigation_id=inv2.id, text="Paxos requires fewer network roundtrips than Raft.", priority=2)
    s1 = Source(
        id=uuid.uuid4(),
        investigation_id=inv1.id,
        title="Distributed Protocols",
        canonical_url="https://doi.org/10.1145/shared001",
        original_url="https://doi.org/10.1145/shared001",
        source_type="arxiv",
        doi="10.1145/shared001",
    )
    s2 = Source(
        id=uuid.uuid4(),
        investigation_id=inv2.id,
        title="Distributed Protocols",
        canonical_url="https://doi.org/10.1145/shared001",
        original_url="https://doi.org/10.1145/shared001",
        source_type="arxiv",
        doi="10.1145/shared001",
    )
    ev1 = Evidence(
        id=uuid.uuid4(),
        source_id=s1.id,
        claim_id=c1.id,
        exact_text="Raft consensus implementation achieves sub-200ms leader election.",
        evidence_type="supporting",
        extraction_method="heuristic",
    )
    ev2 = Evidence(
        id=uuid.uuid4(),
        source_id=s2.id,
        claim_id=c2.id,
        exact_text="Paxos roundtrip guarantees verified in simulated cluster.",
        evidence_type="supporting",
        extraction_method="heuristic",
    )
    db_session.add_all([c1, c2, s1, s2, ev1, ev2])
    await db_session.commit()

    # Search claims
    claims = await synthesis_service.search_global_claims(session=db_session, query="Raft")
    assert len(claims) >= 1
    assert any("Raft" in c.claim_text for c in claims)

    # Shared evidence discovery
    shared = await synthesis_service.discover_shared_evidence(session=db_session, min_investigations=2)
    assert len(shared) >= 1
    assert any(item.source_title == "Distributed Protocols" for item in shared)


@pytest.mark.asyncio
async def test_cross_synthesis_api_endpoints(db_session: AsyncSession):
    """Test REST API routes for cross-investigation synthesis."""
    inv1 = await _create_test_investigation(db_session, "Neural architecture search benchmarks.")
    inv2 = await _create_test_investigation(db_session, "Transformer parameter pruning strategies.")

    c1 = Claim(id=uuid.uuid4(), investigation_id=inv1.id, text="Architecture pruning saves 30% GPU memory.", priority=1)
    c2 = Claim(id=uuid.uuid4(), investigation_id=inv2.id, text="Parameter pruning decreases model inference latency.", priority=1)
    db_session.add_all([c1, c2])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # POST /research/synthesis/generate
        res = await client.post(
            "/api/v1/research/synthesis/generate",
            json={"investigation_ids": [str(inv1.id), str(inv2.id)]},
        )
        assert res.status_code == 200
        data = res.json()
        assert "report" in data
        assert "relationships" in data
        report_id = data["report"]["id"]

        # GET /research/synthesis/reports
        reports_res = await client.get("/api/v1/research/synthesis/reports")
        assert reports_res.status_code == 200
        assert len(reports_res.json()) >= 1

        # GET /research/synthesis/reports/{id}
        rep_res = await client.get(f"/api/v1/research/synthesis/reports/{report_id}")
        assert rep_res.status_code == 200
        assert rep_res.json()["id"] == report_id

        # GET /research/synthesis/claims/search
        search_res = await client.get("/api/v1/research/synthesis/claims/search?query=pruning")
        assert search_res.status_code == 200
        assert len(search_res.json()) >= 1

        # GET /research/synthesis/relationships
        rels_res = await client.get("/api/v1/research/synthesis/relationships")
        assert rels_res.status_code == 200
