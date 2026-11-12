import asyncio
import json
import socket
import uuid
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.analysis.service import ROLE_ORDER, run_analysis
from app.events import EventBroker
from app.models import AnalysisAgentExecution, AnalysisJob, Base, Evidence, Investigation, Source
from app.providers.base import ProviderRequestError
from app.providers.limiter import (
    ProviderLimiterKey,
    ProviderQueueTimeoutError,
    provider_concurrency_registry,
)
from app.providers.ollama import OllamaProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.schemas import ProviderConfigRequest, ProviderKind


@pytest_asyncio.fixture
async def isolated_session(tmp_path):
    db_path = tmp_path / "concurrency_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 5})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_limiter():
    provider_concurrency_registry.reset()
    yield
    provider_concurrency_registry.reset()


def _lm_studio_config(*, model: str = "gemma-4-12b-coder-fable5-composer2.5-v1", timeout: float | None = None):
    return ProviderConfigRequest(
        kind=ProviderKind.lm_studio,
        endpoint="http://127.0.0.1:1234",
        model=model,
        allow_local_runtime=True,
        timeout_seconds=timeout,
        retry_count=0,
    )


def _ollama_config(*, model: str = "qwen2.5:7b"):
    return ProviderConfigRequest(
        kind=ProviderKind.ollama,
        endpoint="http://127.0.0.1:11434",
        model=model,
        allow_local_runtime=True,
        retry_count=0,
    )


def _remote_config(*, model: str = "gpt-4o-mini"):
    return ProviderConfigRequest(
        kind=ProviderKind.openai_compatible,
        endpoint="https://api.example.com",
        model=model,
        allow_local_runtime=False,
        retry_count=0,
    )


@pytest.mark.asyncio
async def test_lm_studio_simultaneous_calls_execute_sequentially_and_cap_at_one():
    active = 0
    max_active = 0
    timeline: list[str] = []

    async def fake_request(method: str, path: str, **kwargs):
        nonlocal active, max_active
        idx = len([item for item in timeline if item.startswith("enter:")])
        timeline.append(f"enter:{idx}")
        active += 1
        max_active = max(max_active, active)
        try:
            await asyncio.sleep(0.02)
            req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": json.dumps({"idx": idx})}}], "usage": {}},
                request=req,
            )
        finally:
            active -= 1
            timeline.append(f"exit:{idx}")

    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))]
    p1 = OpenAICompatibleProvider(_lm_studio_config())
    p2 = OpenAICompatibleProvider(_lm_studio_config())
    p3 = OpenAICompatibleProvider(_lm_studio_config())
    p1._client.request = fake_request
    p2._client.request = fake_request
    p3._client.request = fake_request

    try:
        with patch("app.providers.base.socket.getaddrinfo", return_value=loopback):
            results = await asyncio.gather(
                p1.complete([{"role": "user", "content": "one"}]),
                p2.complete([{"role": "user", "content": "two"}]),
                p3.complete([{"role": "user", "content": "three"}]),
            )
        assert max_active == 1
        assert timeline == ["enter:0", "exit:0", "enter:1", "exit:1", "enter:2", "exit:2"]
        assert results[1]["queue_wait_seconds"] >= 0
    finally:
        await asyncio.gather(p1.close(), p2.close(), p3.close())


@pytest.mark.asyncio
async def test_ollama_maximum_active_inference_never_exceeds_one():
    active = 0
    max_active = 0

    async def fake_request(method: str, path: str, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        try:
            await asyncio.sleep(0.02)
            req = httpx.Request(method, f"http://127.0.0.1:11434{path}")
            return httpx.Response(
                200,
                json={"model": "qwen2.5:7b", "message": {"content": "{}"}, "prompt_eval_count": 1, "eval_count": 1},
                request=req,
            )
        finally:
            active -= 1

    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 11434))]
    providers = [OllamaProvider(_ollama_config()) for _ in range(3)]
    for item in providers:
        item._client.request = fake_request

    try:
        with patch("app.providers.base.socket.getaddrinfo", return_value=loopback):
            await asyncio.gather(*(item.complete([{"role": "user", "content": "hi"}]) for item in providers))
        assert max_active == 1
    finally:
        await asyncio.gather(*(item.close() for item in providers))


@pytest.mark.asyncio
async def test_unrelated_providers_execute_independently_without_blocking():
    lm_entered = asyncio.Event()
    lm_release = asyncio.Event()
    completion_order: list[str] = []

    async def lm_request(method: str, path: str, **kwargs):
        lm_entered.set()
        await lm_release.wait()
        completion_order.append("lm_studio")
        req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]}, request=req)

    async def ollama_request(method: str, path: str, **kwargs):
        completion_order.append("ollama")
        req = httpx.Request(method, f"http://127.0.0.1:11434{path}")
        return httpx.Response(200, json={"message": {"content": "{}"}}, request=req)

    async def remote_request(method: str, path: str, **kwargs):
        completion_order.append("remote")
        req = httpx.Request(method, f"https://api.example.com{path}")
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]}, request=req)

    lm = OpenAICompatibleProvider(_lm_studio_config())
    ol = OllamaProvider(_ollama_config())
    remote = OpenAICompatibleProvider(_remote_config())
    lm._client.request = lm_request
    ol._client.request = ollama_request
    remote._client.request = remote_request

    def fake_getaddrinfo(host, port, type=0):
        if host == "api.example.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

    try:
        with patch("app.providers.base.socket.getaddrinfo", side_effect=fake_getaddrinfo):
            lm_task = asyncio.create_task(lm.complete([{"role": "user", "content": "slow local"}]))
            await asyncio.wait_for(lm_entered.wait(), timeout=1.0)
            # While lm_studio is blocked mid-inference, ollama and remote must finish immediately.
            await asyncio.gather(
                ol.complete([{"role": "user", "content": "ollama"}]),
                remote.complete([{"role": "user", "content": "remote"}]),
            )
            assert "ollama" in completion_order
            assert "remote" in completion_order
            assert "lm_studio" not in completion_order
            lm_release.set()
            await lm_task
            assert completion_order[-1] == "lm_studio"
    finally:
        await asyncio.gather(lm.close(), ol.close(), remote.close())


@pytest.mark.asyncio
async def test_queue_releases_after_provider_error():
    calls = 0

    async def fake_request(method: str, path: str, **kwargs):
        nonlocal calls
        calls += 1
        req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
        if calls == 1:
            return httpx.Response(500, request=req)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"ok": True})}}]}, request=req)

    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))]
    provider = OpenAICompatibleProvider(_lm_studio_config())
    provider._client.request = fake_request

    try:
        with patch("app.providers.base.socket.getaddrinfo", return_value=loopback):
            first, second = await asyncio.gather(
                provider.complete([{"role": "user", "content": "fail"}]),
                provider.complete([{"role": "user", "content": "succeed"}]),
                return_exceptions=True,
            )
        assert isinstance(first, ProviderRequestError)
        assert isinstance(second, dict)
        assert json.loads(second["content"]) == {"ok": True}
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_queue_and_active_cancellation_release_slots_without_affecting_others():
    key = ProviderLimiterKey("lm_studio", "http://127.0.0.1:1234", "gemma")
    first_entered = asyncio.Event()
    first_release = asyncio.Event()
    second_queued = asyncio.Event()

    async def worker_one():
        async with provider_concurrency_registry.acquire(key, max_concurrency=1):
            first_entered.set()
            await first_release.wait()

    async def on_state_two(state: str, meta: dict):
        if state == "waiting_in_queue":
            second_queued.set()

    async def worker_two():
        async with provider_concurrency_registry.acquire(
            key, max_concurrency=1, on_state_change=on_state_two
        ):
            return "two"

    async def worker_three():
        async with provider_concurrency_registry.acquire(key, max_concurrency=1):
            return "three"

    t1 = asyncio.create_task(worker_one())
    await asyncio.wait_for(first_entered.wait(), timeout=1.0)
    t2 = asyncio.create_task(worker_two())
    await asyncio.wait_for(second_queued.wait(), timeout=1.0)
    t3 = asyncio.create_task(worker_three())
    await asyncio.sleep(0)

    # Cancel queued worker_two while waiting; worker_three remains intact
    t2.cancel()
    with pytest.raises(asyncio.CancelledError):
        await t2

    # Cancel active worker_one; slot must release so worker_three completes
    t1.cancel()
    with pytest.raises(asyncio.CancelledError):
        await t1

    assert await asyncio.wait_for(t3, timeout=1.0) == "three"


@pytest.mark.asyncio
async def test_queue_wait_timeout_and_inference_read_timeout_are_separate():
    local_provider = OpenAICompatibleProvider(_lm_studio_config())
    remote_provider = OpenAICompatibleProvider(_remote_config())
    try:
        assert local_provider.inference_timeout_seconds == 300.0
        assert remote_provider.inference_timeout_seconds == 15.0
    finally:
        await asyncio.gather(local_provider.close(), remote_provider.close())

    # Test 1: Expired queued request raises ProviderQueueTimeoutError and does not leak permit.
    key = ProviderLimiterKey("lm_studio", "http://127.0.0.1:1234", "gemma-exp")
    holder_entered = asyncio.Event()
    holder_release = asyncio.Event()

    async def holder():
        async with provider_concurrency_registry.acquire(key, max_concurrency=1):
            holder_entered.set()
            await holder_release.wait()

    async def timed_out_waiter():
        async with provider_concurrency_registry.acquire(key, max_concurrency=1, queue_wait_timeout=0.03):
            return "unexpected"

    t_holder = asyncio.create_task(holder())
    await asyncio.wait_for(holder_entered.wait(), timeout=1.0)
    with pytest.raises(ProviderQueueTimeoutError):
        await timed_out_waiter()

    holder_release.set()
    await t_holder

    # Semaphore must still be fully free (1 available permit) for subsequent work.
    async with provider_concurrency_registry.acquire(key, max_concurrency=1, queue_wait_timeout=0.2) as lease:
        assert lease.wait_seconds < 0.1

    # Test 2: Waiting in queue longer than inference timeout does NOT fail fast inference.
    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))]
    short_infer_provider = OpenAICompatibleProvider(_lm_studio_config(timeout=0.05))
    call_idx = 0

    async def slow_then_fast(method: str, path: str, **kwargs):
        nonlocal call_idx
        call_idx += 1
        req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
        if call_idx == 1:
            await asyncio.sleep(0.08)  # longer than 0.05s, simulated as completed response
        else:
            await asyncio.sleep(0.005)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"call": call_idx})}}]}, request=req)

    short_infer_provider._client.request = slow_then_fast
    try:
        with patch("app.providers.base.socket.getaddrinfo", return_value=loopback):
            res1, res2 = await asyncio.gather(
                short_infer_provider.complete([{"role": "user", "content": "first"}]),
                short_infer_provider.complete([{"role": "user", "content": "second"}]),
            )
        assert res2["queue_wait_seconds"] >= 0.05
    finally:
        await short_infer_provider.close()


@pytest.mark.asyncio
async def test_multi_agent_analysis_tracks_waiting_generating_and_completes_sequentially(isolated_session):
    investigation = Investigation(question="Does concurrency control preserve all analysis agents?", mode="quick")
    isolated_session.add(investigation)
    await isolated_session.flush()
    source = Source(
        investigation_id=investigation.id,
        title="Software study",
        canonical_url="https://example.org/study",
        original_url="https://example.org/study",
        source_type="paper",
        authors_json="[]",
        inclusion_status="included",
    )
    isolated_session.add(source)
    await isolated_session.flush()
    ev = Evidence(
        source_id=source.id,
        exact_text="Concurrency control works reliably across serialized local LLM analysis calls.",
        evidence_type="supporting",
        relevance_score=0.9,
        extraction_method="test",
    )
    isolated_session.add(ev)
    await isolated_session.commit()

    job = AnalysisJob(
        investigation_id=investigation.id,
        status="queued",
        max_debate_rounds=1,
        max_concurrent_agents=4,
        provider_kind="lm_studio",
        default_model="gemma-4-12b-coder-fable5-composer2.5-v1",
    )
    isolated_session.add(job)
    await isolated_session.commit()

    broker = EventBroker()
    active = 0
    max_active = 0
    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))]

    def build_payload(messages):
        sys_msg = messages[0]["content"]
        user_msg = json.loads(messages[1]["content"])
        if "claims array" in sys_msg:
            return {
                "claims": [
                    {
                        "text": "Concurrency control works reliably",
                        "explanation": "Plan",
                        "priority": 1,
                        "search_objectives": ["Concurrency control works reliably"],
                        "evidence_categories": ["supporting", "contradicting"],
                    }
                ]
            }
        if "round_number" in sys_msg:
            return {
                "round_number": 1,
                "moderator_summary": "Debate compared claims.",
                "unresolved_disagreements": [],
                "requested_follow_up": [],
            }
        if "decisions array" in sys_msg:
            cid = user_msg["claims"][0]["claim_id"]
            arg_ids = [item["argument_id"] for item in user_msg["arguments"]]
            return {
                "decisions": [
                    {
                        "claim_id": cid,
                        "decision": "moderately_supported",
                        "explanation": "Evidence matches.",
                        "supporting_argument_ids": arg_ids,
                        "evidence_ids": [str(ev.id)],
                        "unresolved_disagreements": [],
                    }
                ]
            }
        if "sections array" in sys_msg:
            cid = user_msg["claims"][0]["claim_id"]
            return {
                "sections": [
                    {
                        "section_type": "research_question",
                        "title": "Finding",
                        "content": "Completed sequentially.",
                        "claim_ids": [cid],
                        "evidence_ids": [str(ev.id)],
                    }
                ]
            }
        cid = user_msg["claims"][0]["claim_id"]
        role = user_msg["role"]
        arg_type = {
            "advocate": "supporting",
            "skeptic": "contradicting",
            "methodology_auditor": "methodological_criticism",
            "source_intelligence": "source_criticism",
            "citation_genealogy": "source_criticism",
            "temporal_intelligence": "temporal_qualification",
        }[role]
        return {
            "arguments": [
                {
                    "claim_id": cid,
                    "argument_type": arg_type,
                    "text": f"{role} assessment grounded in evidence.",
                    "evidence_ids": [str(ev.id)],
                    "source_ids": [str(source.id)],
                    "evidence_basis": "direct",
                    "reasoning_summary": "Grounded in evidence.",
                    "limitations": ["Mocked local provider"],
                    "confidence": {"level": "moderate", "explanation": "Mocked test check."},
                }
            ]
        }

    async def fake_httpx_request(self, method: str, path: str, **kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        try:
            await asyncio.sleep(0.01)
            payload = build_payload(kwargs["json"]["messages"])
            req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": json.dumps(payload)}}], "usage": {"total_tokens": 10}},
                request=req,
            )
        finally:
            active -= 1

    with (
        patch("app.providers.base.socket.getaddrinfo", return_value=loopback),
        patch.object(httpx.AsyncClient, "request", fake_httpx_request),
    ):
        await run_analysis(
            isolated_session,
            broker,
            job,
            investigation.question,
            provider_config=_lm_studio_config(),
        )

    assert max_active == 1
    assert job.status == "completed"
    executions = list(
        (
            await isolated_session.scalars(
                select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == job.id)
            )
        ).all()
    )
    assert len(executions) == len(ROLE_ORDER) + 3
    assert all(item.status == "completed" for item in executions)

    queued_events = [item for item in broker._history if item.event_type.value == "analysis.agent_queued"]
    started_events = [item for item in broker._history if item.event_type.value == "analysis.agent_started"]
    assert len(queued_events) >= len(ROLE_ORDER)
    assert len(started_events) == len(executions)
    assert all(item.payload.get("status") == "generating" for item in started_events)


@pytest.mark.asyncio
async def test_cancelling_queued_multi_agent_analysis_marks_executions_cancelled_and_releases_slot(isolated_session):
    investigation = Investigation(question="Does cancelling queued analysis clean up state?", mode="quick")
    isolated_session.add(investigation)
    await isolated_session.flush()
    source = Source(
        investigation_id=investigation.id,
        title="Software study",
        canonical_url="https://example.org/study-cancel",
        original_url="https://example.org/study-cancel",
        source_type="paper",
        authors_json="[]",
        inclusion_status="included",
    )
    isolated_session.add(source)
    await isolated_session.flush()
    ev = Evidence(
        source_id=source.id,
        exact_text="Cancelled queued analysis releases the provider slot.",
        evidence_type="supporting",
        relevance_score=0.9,
        extraction_method="test",
    )
    isolated_session.add(ev)
    await isolated_session.commit()

    job = AnalysisJob(
        investigation_id=investigation.id,
        status="queued",
        max_debate_rounds=1,
        max_concurrent_agents=3,
        provider_kind="lm_studio",
        default_model="gemma-4-12b-coder-fable5-composer2.5-v1",
    )
    isolated_session.add(job)
    await isolated_session.commit()

    broker = EventBroker()
    role_entered = asyncio.Event()
    role_block = asyncio.Event()
    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))]

    async def fake_httpx_request(self, method: str, path: str, **kwargs):
        sys_msg = kwargs["json"]["messages"][0]["content"]
        req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
        if "claims array" in sys_msg:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "claims": [
                                            {
                                                "text": "Cancelled queued analysis",
                                                "explanation": "Plan",
                                                "priority": 1,
                                                "search_objectives": ["Cancelled queued analysis"],
                                                "evidence_categories": ["supporting"],
                                            }
                                        ]
                                    }
                                )
                            }
                        }
                    ]
                },
                request=req,
            )
        role_entered.set()
        await role_block.wait()
        return httpx.Response(500, request=req)

    with (
        patch("app.providers.base.socket.getaddrinfo", return_value=loopback),
        patch.object(httpx.AsyncClient, "request", fake_httpx_request),
    ):
        task = asyncio.create_task(
            run_analysis(
                isolated_session,
                broker,
                job,
                investigation.question,
                provider_config=_lm_studio_config(),
            )
        )
        await asyncio.wait_for(role_entered.wait(), timeout=2.0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    executions = list(
        (
            await isolated_session.scalars(
                select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == job.id)
            )
        ).all()
    )
    assert any(item.status == "cancelled" for item in executions)
    assert not any(item.status in {"waiting_in_queue", "generating", "running", "queued"} for item in executions)
    key = ProviderLimiterKey("lm_studio", "http://127.0.0.1:1234", "gemma-4-12b-coder-fable5-composer2.5-v1")
    async with provider_concurrency_registry.acquire(key, max_concurrency=1, queue_wait_timeout=0.2):
        pass
