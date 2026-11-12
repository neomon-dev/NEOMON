import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.analysis.protocol import DecisionPayload
from app.analysis.service import (
    _build_fallback_report_sections,
    compute_analysis_coverage,
)
from app.models import AdjudicationDecision, AgentArgument, AnalysisAgentExecution, AnalysisJob, Base, Claim, Evidence, Investigation, Source
from app.providers.limiter import (
    ProviderConcurrencyRegistry,
    ProviderLimiterKey,
    ProviderQueueFullError,
    ProviderQueueTimeoutError,
    provider_concurrency_registry,
)
from app.schemas import AnalysisCoverageSummary


@pytest_asyncio.fixture
async def session(tmp_path):
    db_path = tmp_path / "reliability_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 5})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_registry():
    provider_concurrency_registry.reset()
    yield
    provider_concurrency_registry.reset()


@pytest.mark.asyncio
async def test_bounded_queue_rejects_when_full():
    registry = ProviderConcurrencyRegistry()
    key = ProviderLimiterKey("lm_studio", "http://127.0.0.1:1234", "test-model")

    async with registry.acquire(key, max_concurrency=1, max_queue_size=2) as lease1:
        assert lease1.queue_position == 1

        async def _waiter(wait_timeout: float = 2.0):
            async with registry.acquire(
                key, max_concurrency=1, queue_wait_timeout=wait_timeout, max_queue_size=2
            ):
                await asyncio.sleep(0.01)

        t1 = asyncio.create_task(_waiter())
        t2 = asyncio.create_task(_waiter())
        await asyncio.sleep(0.02)

        stats = registry.get_queue_stats(key)
        assert stats["waiting"] == 2
        assert stats["active"] == 1

        with pytest.raises(ProviderQueueFullError) as exc_info:
            async with registry.acquire(key, max_concurrency=1, max_queue_size=2):
                pass
        assert "capacity" in str(exc_info.value).lower()

        t1.cancel()
        t2.cancel()


@pytest.mark.asyncio
async def test_queue_wait_timeout_vs_inference_timeout():
    registry = ProviderConcurrencyRegistry()
    key = ProviderLimiterKey("lm_studio", "http://127.0.0.1:1234", "test-model")

    async with registry.acquire(key, max_concurrency=1) as lease1:
        assert lease1.queue_position == 1

        with pytest.raises(ProviderQueueTimeoutError) as exc_info:
            async with registry.acquire(key, max_concurrency=1, queue_wait_timeout=0.05):
                pass
        msg = str(exc_info.value).lower()
        assert "timed out waiting" in msg
        assert "provider queue" in msg


@pytest.mark.asyncio
async def test_queue_position_telemetry_reports_accurate_ordering():
    registry = ProviderConcurrencyRegistry()
    key = ProviderLimiterKey("lm_studio", "http://127.0.0.1:1234", "test-model")

    events: list[tuple[str, dict]] = []

    async def listener(state: str, details: dict):
        events.append((state, details))

    async with registry.acquire(key, max_concurrency=1, on_state_change=listener) as l1:
        assert l1.queue_position == 1

        async def _queued_task():
            async with registry.acquire(key, max_concurrency=1, queue_wait_timeout=2.0, on_state_change=listener) as l2:
                assert l2.queue_position >= 1
                await asyncio.sleep(0.01)

        t_queued = asyncio.create_task(_queued_task())
        await asyncio.sleep(0.02)

        stats = registry.get_queue_stats(key)
        assert stats["waiting"] == 1
        assert stats["active"] == 1

    await t_queued
    states = [s for s, _ in events]
    assert "waiting_in_queue" in states
    assert "generating" in states


def test_fallback_report_sections_generation():
    cid = uuid.uuid4()
    claim = Claim(
        id=cid,
        investigation_id=uuid.uuid4(),
        text="Quantum computing breaks RSA-2048 encryption.",
        status="debated",
    )
    decision = DecisionPayload(
        claim_id=cid,
        decision="contradictory",
        explanation="Current quantum architectures lack sufficient logical qubits.",
        supporting_argument_ids=[],
        evidence_ids=[],
        unresolved_disagreements=["Fault-tolerant error threshold"],
    )

    eid = uuid.uuid4()
    evidence_item = Evidence(
        id=eid,
        source_id=uuid.uuid4(),
        exact_text="RSA-2048 remains unbroken by current hardware.",
        evidence_type="direct",
        relevance_score=0.9,
        extraction_method="heuristic",
    )

    sections = _build_fallback_report_sections(
        question="Is RSA-2048 vulnerable to quantum computers today?",
        claims=[claim],
        decisions=[decision],
        evidence=[evidence_item],
        sources={},
        documents={},
        warnings=["LLM report generator failed: HTTP 500"],
        provenance_for_fn=lambda ids: [],
    )

    assert len(sections) == 18
    section_types = [s.section_type for s in sections]
    assert "executive_summary" in section_types
    assert "claim_by_claim_assessment" in section_types
    assert "limitations" in section_types

    exec_summary = next(s for s in sections if s.section_type == "executive_summary")
    assert "1 atomic claim(s)" in exec_summary.content
    assert "LLM report generator failed: HTTP 500" in exec_summary.content


def test_compute_analysis_coverage_calculates_rates_and_flags():
    inv_id = uuid.uuid4()
    job_id = uuid.uuid4()
    c1 = Claim(
        id=uuid.uuid4(),
        investigation_id=inv_id,
        text="Claim A",
        status="supported",
        priority=1,
        explanation="Test explanation",
    )
    c2 = Claim(
        id=uuid.uuid4(),
        investigation_id=inv_id,
        text="Claim B",
        status="unverified",
        priority=2,
        explanation="Test explanation",
    )
    executions = [
        AnalysisAgentExecution(
            id=uuid.uuid4(),
            job_id=job_id,
            agent_identifier="intelligence_planner",
            status="completed",
        ),
        AnalysisAgentExecution(
            id=uuid.uuid4(),
            job_id=job_id,
            agent_identifier="advocate",
            status="completed",
        ),
        AnalysisAgentExecution(
            id=uuid.uuid4(),
            job_id=job_id,
            agent_identifier="skeptic",
            status="completed",
        ),
    ]
    dec = AdjudicationDecision(
        id=uuid.uuid4(),
        job_id=job_id,
        claim_id=c1.id,
        decision="supported",
        explanation="Strong consensus",
        evidence_ids_json="[]",
        supporting_argument_ids_json="[]",
        unresolved_disagreements_json="[]",
    )

    coverage = compute_analysis_coverage(
        claims=[c1, c2],
        executions=executions,
        arguments=[],
        decisions=[dec],
        evidence=[],
    )
    assert isinstance(coverage, AnalysisCoverageSummary)
    assert coverage.claims_total == 2
    assert coverage.claims_evaluated == 1
    assert len(coverage.required_agents) == 10
    assert len(coverage.completed_agents) == 3
    assert coverage.is_partially_completed is True
    assert 0.0 < coverage.coverage_percentage < 100.0
