import json
import logging
import socket
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.analysis.protocol import PlannerPayload
from app.analysis.service import _optional_llm_json, run_analysis
from app.events import EventBroker
from app.models import AnalysisJob, Base, Investigation
from app.providers.base import ProviderRequestError
from app.providers.limiter import provider_concurrency_registry
from app.providers.ollama import OllamaProvider
from app.providers.openai_compatible import OpenAICompatibleProvider, sanitize_json_schema
from app.schemas import ProviderConfigRequest, ProviderKind


@pytest.fixture(autouse=True)
def _reset_limiter():
    provider_concurrency_registry.reset()
    yield
    provider_concurrency_registry.reset()


@pytest_asyncio.fixture
async def isolated_session(tmp_path):
    db_path = tmp_path / "structured_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 5})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _lm_config():
    return ProviderConfigRequest(
        kind=ProviderKind.lm_studio,
        endpoint="http://127.0.0.1:1234",
        model="gemma-4-12B-coder-fable5-composer2.5-v1",
        allow_local_runtime=True,
        retry_count=0,
    )


def _remote_config():
    return ProviderConfigRequest(
        kind=ProviderKind.openai_compatible,
        endpoint="https://api.example.com",
        model="remote-json-model",
        api_key="sk-secret-do-not-log",
        allow_local_runtime=False,
        retry_count=0,
    )


def test_sanitize_json_schema_inlines_defs_and_removes_uuid_format():
    cleaned = sanitize_json_schema(PlannerPayload.model_json_schema())
    serialized = json.dumps(cleaned)
    assert "$defs" not in serialized
    assert "$ref" not in serialized
    assert '"format": "uuid"' not in serialized
    assert cleaned["type"] == "object"
    assert cleaned["additionalProperties"] is False


@pytest.mark.asyncio
async def test_http_400_error_body_visibility_and_bearer_redaction(caplog):
    config = _remote_config()
    provider = OpenAICompatibleProvider(config)
    public_addr = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    req = httpx.Request("POST", "https://api.example.com/v1/chat/completions")
    err_response = httpx.Response(
        400,
        json={
            "error": {
                "message": "Invalid model request with Bearer super-secret-token-value",
                "type": "invalid_request_error",
            }
        },
        request=req,
    )
    try:
        provider._client.request = AsyncMock(return_value=err_response)
        with (
            patch("app.providers.base.socket.getaddrinfo", return_value=public_addr),
            caplog.at_level(logging.WARNING),
        ):
            with pytest.raises(ProviderRequestError) as exc_info:
                await provider.complete([{"role": "user", "content": "hi"}])
        msg = str(exc_info.value)
        assert "HTTP 400" in msg
        assert "Invalid model request" in msg
        assert "invalid_request_error" in msg
        assert "super-secret-token-value" not in msg
        assert "sk-secret-do-not-log" not in caplog.text
        assert "remote-json-model" in caplog.text
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_lm_studio_never_sends_json_object_and_falls_back_from_json_schema_400():
    provider = OpenAICompatibleProvider(_lm_config())
    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))]
    recorded_bodies: list[dict] = []

    async def fake_request(method: str, path: str, **kwargs):
        body = kwargs["json"]
        recorded_bodies.append(body)
        req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
        if "response_format" in body:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": "'response_format.type' must be 'json_schema' or 'text'",
                        "type": "invalid_request_error",
                    }
                },
                request=req,
            )
        return httpx.Response(
            200,
            json={
                "model": "gemma-4-12B-coder-fable5-composer2.5-v1",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "claims": [
                                        {
                                            "text": "LM Studio fallback returns valid planner claims.",
                                            "explanation": "Tested fallback path.",
                                            "priority": 1,
                                            "search_objectives": ["LM Studio structured output"],
                                            "evidence_categories": ["supporting"],
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ],
                "usage": {"total_tokens": 25},
            },
            request=req,
        )

    try:
        provider._client.request = fake_request
        with patch("app.providers.base.socket.getaddrinfo", return_value=loopback):
            payload, usage, error = await _optional_llm_json(
                provider,
                None,
                "Plan claims.",
                "How does fallback work?",
                response_model=PlannerPayload,
                stage_name="intelligence_planner",
            )
            assert error is None
            assert payload is not None
            assert len(payload["claims"]) == 1
            assert usage["total_tokens"] == 25
            # Second call skips json_schema because capability was cached False.
            payload2, _, error2 = await _optional_llm_json(
                provider,
                None,
                "Plan claims.",
                "Second question?",
                response_model=PlannerPayload,
                stage_name="intelligence_planner",
            )
            assert error2 is None
            assert payload2 is not None
        assert recorded_bodies[0]["response_format"]["type"] == "json_schema"
        assert "response_format" not in recorded_bodies[1]
        assert "response_format" not in recorded_bodies[2]
        assert all(
            body.get("response_format", {}).get("type") != "json_object" for body in recorded_bodies
        )
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_markdown_fenced_json_and_bounded_validation_correction():
    provider = OpenAICompatibleProvider(_lm_config())
    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))]
    attempts = 0

    async def fake_request(method: str, path: str, **kwargs):
        nonlocal attempts
        attempts += 1
        req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
        if attempts == 1:
            # Missing required search_objectives/evidence_categories -> fails PlannerPayload validation
            bad = {"claims": [{"text": "Invalid partial claim", "explanation": "Missing fields", "priority": 1}]}
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(bad)}}]}, request=req)
        corrected = (
            "```json\n"
            + json.dumps(
                {
                    "claims": [
                        {
                            "text": "Corrected claim satisfies full Pydantic schema.",
                            "explanation": "Fixed on bounded retry.",
                            "priority": 1,
                            "search_objectives": ["Schema validation retry"],
                            "evidence_categories": ["supporting"],
                        }
                    ]
                }
            )
            + "\n```"
        )
        return httpx.Response(200, json={"choices": [{"message": {"content": corrected}}]}, request=req)

    try:
        provider._client.request = fake_request
        with patch("app.providers.base.socket.getaddrinfo", return_value=loopback):
            payload, _, error = await _optional_llm_json(
                provider,
                None,
                "Plan claims.",
                "Test retry",
                response_model=PlannerPayload,
                stage_name="intelligence_planner",
            )
        assert error is None
        assert payload is not None
        assert attempts == 2
        assert payload["claims"][0]["text"] == "Corrected claim satisfies full Pydantic schema."
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_invalid_json_and_fabricated_validation_failure_stop_after_bounded_retry():
    provider = OpenAICompatibleProvider(_lm_config())
    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))]
    attempts = 0

    async def always_invalid(method: str, path: str, **kwargs):
        nonlocal attempts
        attempts += 1
        req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Not valid JSON output at all"}}]},
            request=req,
        )

    try:
        provider._client.request = always_invalid
        with patch("app.providers.base.socket.getaddrinfo", return_value=loopback):
            payload, _, error = await _optional_llm_json(
                provider,
                None,
                "Plan claims.",
                "Bad output",
                response_model=PlannerPayload,
                stage_name="intelligence_planner",
            )
        assert payload is None
        assert error is not None
        assert attempts == 2  # initial + 1 bounded correction attempt only
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_planner_analysis_surfaces_stage_model_and_http_400_detail(isolated_session):
    investigation = Investigation(question="Why did LM Studio return HTTP 400?", mode="quick")
    isolated_session.add(investigation)
    await isolated_session.flush()
    job = AnalysisJob(
        investigation_id=investigation.id,
        status="queued",
        provider_kind="lm_studio",
        default_model="gemma-4-12B-coder-fable5-composer2.5-v1",
    )
    isolated_session.add(job)
    await isolated_session.commit()

    broker = EventBroker()
    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))]

    async def always_400(self, method: str, path: str, **kwargs):
        req = httpx.Request(method, f"http://127.0.0.1:1234{path}")
        return httpx.Response(
            400,
            json={"error": {"message": "Context length exceeded for model", "type": "invalid_request_error"}},
            request=req,
        )

    with (
        patch("app.providers.base.socket.getaddrinfo", return_value=loopback),
        patch.object(httpx.AsyncClient, "request", always_400),
    ):
        await run_analysis(isolated_session, broker, job, investigation.question, provider_config=_lm_config())

    assert job.status == "failed"
    assert job.error_message is not None
    assert "HTTP 400" in job.error_message
    assert "Context length exceeded for model" in job.error_message
    assert "intelligence_planner" in job.error_message
    assert "gemma-4-12B-coder-fable5-composer2.5-v1" in job.error_message


@pytest.mark.asyncio
async def test_remote_openai_compatible_and_ollama_compatibility():
    remote = OpenAICompatibleProvider(_remote_config())
    public_addr = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    remote_bodies: list[dict] = []

    async def remote_request(method: str, path: str, **kwargs):
        body = kwargs["json"]
        remote_bodies.append(body)
        req = httpx.Request(method, f"https://api.example.com{path}")
        if body.get("response_format", {}).get("type") == "json_schema":
            return httpx.Response(400, json={"error": {"message": "json_schema not supported"}}, request=req)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]}, request=req)

    ollama = OllamaProvider(
        ProviderConfigRequest(
            kind=ProviderKind.ollama,
            endpoint="http://127.0.0.1:11434",
            model="qwen2.5:7b",
            allow_local_runtime=True,
            retry_count=0,
        )
    )
    loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 11434))]

    async def ollama_request(method: str, path: str, **kwargs):
        req = httpx.Request(method, f"http://127.0.0.1:11434{path}")
        return httpx.Response(200, json={"message": {"content": '{"ok": true}'}}, request=req)

    try:
        remote._client.request = remote_request
        ollama._client.request = ollama_request
        with patch("app.providers.base.socket.getaddrinfo", return_value=public_addr):
            res = await remote.complete(
                [{"role": "user", "content": "hi"}],
                response_schema=PlannerPayload.model_json_schema(),
            )
            assert res["response_format_mode"] == "json_object"
            assert remote_bodies[0]["response_format"]["type"] == "json_schema"
            assert remote_bodies[1]["response_format"]["type"] == "json_object"

        with patch("app.providers.base.socket.getaddrinfo", return_value=loopback):
            ol_res = await ollama.complete([{"role": "user", "content": "hi"}])
            assert ol_res["content"] == '{"ok": true}'
    finally:
        await remote.close()
        await ollama.close()
