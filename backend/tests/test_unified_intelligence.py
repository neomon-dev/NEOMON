import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.hypothesis_service import hypothesis_service
from app.analysis.research_intelligence_service import research_intelligence_service
from app.db import SessionFactory
from app.main import app
from app.models import (
    Claim,
    Evidence,
    Investigation,
    ResearchContradiction,
    ResearchHypothesis,
    Source,
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
async def test_unified_intelligence_overview(db_session: AsyncSession):
    """Test aggregated intelligence metrics across the entire platform."""
    inv = await _create_test_investigation(db_session, "Unified Intelligence Platform Test Study")
    claim = Claim(id=uuid.uuid4(), investigation_id=inv.id, text="Automated metrics reduce manual reporting burden.", priority=1)
    db_session.add(claim)
    await db_session.commit()

    overview = await research_intelligence_service.get_unified_overview(session=db_session)

    assert overview.total_investigations >= 1
    assert overview.total_claims >= 1
    assert overview.system_status == "operational"
    assert overview.last_updated is not None


@pytest.mark.asyncio
async def test_global_research_search(db_session: AsyncSession):
    """Test multi-entity universal search across investigations, claims, hypotheses, contradictions."""
    inv = await _create_test_investigation(db_session, "Search inquiry on neuromorphic computing architectures.")
    claim = Claim(id=uuid.uuid4(), investigation_id=inv.id, text="Neuromorphic spike timing depends on synaptic delays.", priority=1)
    hyp = ResearchHypothesis(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Synaptic Delay Hypothesis in Neuromorphic Systems",
        statement="Synaptic plasticity attenuates under high frequency spiking regimes.",
        rationale="Empirical derivation.",
        category="mechanistic",
        status="proposed",
        falsification_criteria="Plasticity invariance under 200Hz frequency.",
        claim_ids_json=json.dumps([str(claim.id)]),
    )
    db_session.add_all([claim, hyp])
    await db_session.commit()

    # Search query
    res = await research_intelligence_service.search_global_research(
        session=db_session,
        query="Neuromorphic",
        category="all",
    )

    assert res.total >= 1
    assert any("neuromorphic" in item.title.lower() for item in res.items)


@pytest.mark.asyncio
async def test_knowledge_graph_ingestion_of_hypotheses_and_contradictions(db_session: AsyncSession):
    """Knowledge graph must ingest and render hypotheses and contradiction nodes and edges."""
    inv = await _create_test_investigation(db_session, "Knowledge graph integration test investigation.")
    claim = Claim(id=uuid.uuid4(), investigation_id=inv.id, text="Graph database queries scale logarithmically.", priority=1)
    source = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Graph Indexing Survey",
        canonical_url="https://example.org/graph2024",
        original_url="https://example.org/graph2024",
        source_type="crossref",
    )
    db_session.add_all([claim, source])

    ev = Evidence(
        id=uuid.uuid4(),
        source_id=source.id,
        claim_id=claim.id,
        exact_text="Adjacency list traversal latency remains sub-10ms for 10M vertices.",
        evidence_type="supporting",
        relevance_score=0.92,
        extraction_method="heuristic",
    )
    hyp = ResearchHypothesis(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Graph Partitioning Latency Hypothesis",
        statement="Graph sharding reduces edge traversal throughput when cut sizes exceed 15%.",
        rationale="Formulated from network partitioning costs.",
        category="causal",
        status="proposed",
        claim_ids_json=json.dumps([str(claim.id)]),
        supporting_evidence_ids_json=json.dumps([str(ev.id)]),
        falsification_criteria="Replication showing flat latency across varying cut sizes.",
        testability_score=8.4,
    )
    contra = ResearchContradiction(
        id=uuid.uuid4(),
        primary_investigation_id=inv.id,
        title="Discrepancy in Graph Sharding Overhead",
        description="Conflicting measurements reported in distributed vs single-node vertex queries.",
        category="methodological",
        severity="moderate",
        status="newly_detected",
        claim_ids_json=json.dumps([str(claim.id)]),
        evidence_ids_json=json.dumps([str(ev.id)]),
    )
    db_session.add_all([ev, hyp, contra])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/research/investigations/{inv.id}/graph")
        assert res.status_code == 200
        graph_data = res.json()

        # Check total counts
        counts = graph_data["total_counts"]
        assert counts["hypotheses"] >= 1
        assert counts["contradictions"] >= 1

        # Check node types
        node_types = [n["type"] for n in graph_data["nodes"]]
        assert "hypothesis" in node_types
        assert "contradiction" in node_types

        # Check edges
        edge_types = [e["relationship_type"] for e in graph_data["edges"]]
        assert "hypothesizes" in edge_types or "hypothesizes_for" in edge_types
        assert "contradicts" in edge_types or "observed_in" in edge_types


@pytest.mark.asyncio
async def test_intelligence_api_routes(db_session: AsyncSession):
    """Test REST API endpoints for unified overview and search."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /research/intelligence/overview
        overview_res = await client.get("/api/v1/research/intelligence/overview")
        assert overview_res.status_code == 200
        data = overview_res.json()
        assert "total_investigations" in data
        assert "total_claims" in data
        assert "system_status" in data

        # GET /research/intelligence/search
        search_res = await client.get("/api/v1/research/intelligence/search?query=test")
        assert search_res.status_code == 200
        assert "items" in search_res.json()
        assert "total" in search_res.json()
