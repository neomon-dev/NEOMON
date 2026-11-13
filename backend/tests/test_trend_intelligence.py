import json
import uuid
from datetime import UTC, datetime
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.trend_service import trend_service
from app.db import SessionFactory
from app.main import app
from app.models import (
    Claim,
    Evidence,
    Investigation,
    ResearchContradiction,
    ResearchGap,
    ResearchTrendAnalysis,
    ResearchTrendTopic,
    Source,
)
from app.schemas import TrendClassification


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
async def test_longitudinal_trend_analysis_and_topic_clustering(db_session: AsyncSession):
    """Test longitudinal trend analysis across temporal sources and multi-dimensional scoring."""
    inv1 = await _create_test_investigation(db_session, "Neural architecture scaling laws and performance.")
    inv2 = await _create_test_investigation(db_session, "Transformer memory optimization and context length.")

    # Historical source (2021)
    s_old = Source(
        id=uuid.uuid4(),
        investigation_id=inv1.id,
        title="Scaling Laws for Neural Language Models",
        canonical_url="https://arxiv.org/abs/2001.08361",
        original_url="https://arxiv.org/abs/2001.08361",
        source_type="arxiv",
        publication_date="2020-01-23",
    )
    # Recent sources (2024, 2025)
    s_recent1 = Source(
        id=uuid.uuid4(),
        investigation_id=inv1.id,
        title="Scaling Architecture Frontiers 2024",
        canonical_url="https://example.org/scale2024",
        original_url="https://example.org/scale2024",
        source_type="crossref",
        publication_date="2024-05-10",
    )
    s_recent2 = Source(
        id=uuid.uuid4(),
        investigation_id=inv2.id,
        title="Scaling Transformer Long-Context Limits",
        canonical_url="https://example.org/scale2025",
        original_url="https://example.org/scale2025",
        source_type="arxiv",
        publication_date="2025-02-15",
    )
    c1 = Claim(id=uuid.uuid4(), investigation_id=inv1.id, text="Compute scaling follows strict empirical power law.", priority=1)
    c2 = Claim(id=uuid.uuid4(), investigation_id=inv2.id, text="Transformer linear attention eliminates quadratic memory cost.", priority=1)

    db_session.add_all([s_old, s_recent1, s_recent2, c1, c2])
    await db_session.commit()

    # Execute trend analysis
    analysis = await trend_service.analyze_trends(session=db_session)

    assert analysis.id is not None
    assert analysis.total_investigations_analyzed >= 2
    assert analysis.total_sources_analyzed >= 3
    assert analysis.temporal_span_start is not None
    assert analysis.temporal_span_end is not None
    assert len(analysis.topics) >= 1

    topic = analysis.topics[0]
    assert topic.topic_name
    assert topic.classification
    assert topic.activity_score >= 1.0
    assert topic.quality_score >= 1.0
    assert topic.independence_score >= 1.0
    assert topic.summary_narrative
    assert len(analysis.recommendations) >= 1


@pytest.mark.asyncio
async def test_trend_api_routes(db_session: AsyncSession):
    """Test REST API routes for research trend intelligence."""
    inv = await _create_test_investigation(db_session, "Quantum annealing algorithms and optimization benchmarks.")
    source = Source(
        id=uuid.uuid4(),
        investigation_id=inv.id,
        title="Quantum Optimization Survey",
        canonical_url="https://example.org/quantum2024",
        original_url="https://example.org/quantum2024",
        source_type="crossref",
        publication_date="2024-03-01",
    )
    claim = Claim(id=uuid.uuid4(), investigation_id=inv.id, text="Annealing surpasses classical heuristics on TSP.", priority=1)
    db_session.add_all([source, claim])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # POST /research/trends/analyze
        post_res = await client.post("/api/v1/research/trends/analyze", json={})
        assert post_res.status_code == 200
        data = post_res.json()
        assert "topics" in data
        assert "recommendations" in data
        trend_id = data["id"]

        # GET /research/trends/latest
        latest_res = await client.get("/api/v1/research/trends/latest")
        assert latest_res.status_code == 200
        assert latest_res.json()["id"] == trend_id

        # GET /research/trends
        list_res = await client.get("/api/v1/research/trends")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # GET /research/trends/{id}
        get_res = await client.get(f"/api/v1/research/trends/{trend_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == trend_id
