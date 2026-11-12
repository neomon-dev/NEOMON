import socket
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.providers.base import ProviderRequestError, validate_provider_endpoint
from app.providers.ollama import OllamaProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.schemas import ProviderConfigRequest, ProviderKind


@pytest.mark.asyncio
async def test_ollama_discovers_models():
    config = ProviderConfigRequest(
        kind=ProviderKind.ollama,
        endpoint="http://localhost:11434",
        allow_local_runtime=True,
    )
    provider = OllamaProvider(config)
    request = httpx.Request("GET", "http://localhost:11434/api/tags")
    response = httpx.Response(200, json={"models": [{"name": "alpha"}, {"name": "beta"}]}, request=request)
    try:
        provider._client.request = AsyncMock(return_value=response)
        assert await provider.discover_models() == ["alpha", "beta"]
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_openai_compatible_returns_structured_completion_metadata():
    config = ProviderConfigRequest(
        kind=ProviderKind.openai_compatible,
        endpoint="https://api.example.com",
        model="remote-model",
    )
    provider = OpenAICompatibleProvider(config)
    request = httpx.Request("POST", "https://api.example.com/v1/chat/completions")
    response = httpx.Response(
        200,
        json={
            "model": "remote-model",
            "choices": [{"message": {"content": '{"arguments": []}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        },
        request=request,
    )
    public_addr = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
    try:
        provider._client.request = AsyncMock(return_value=response)
        with patch("app.providers.base.socket.getaddrinfo", return_value=public_addr):
            result = await provider.complete([{"role": "user", "content": "Return JSON."}])
        assert result["content"] == '{"arguments": []}'
        assert result["usage"]["total_tokens"] == 12
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_ollama_invalid_message_raises_provider_request_error():
    config = ProviderConfigRequest(
        kind=ProviderKind.ollama,
        endpoint="http://localhost:11434",
        model="llama3",
        allow_local_runtime=True,
    )
    provider = OllamaProvider(config)
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    response = httpx.Response(200, json={"message": {"content": None}}, request=request)
    try:
        provider._client.request = AsyncMock(return_value=response)
        with pytest.raises(ProviderRequestError):
            await provider.complete([{"role": "user", "content": "hello"}])
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_provider_ssrf_blocks_metadata_and_private_ips_but_allows_local_runtimes():
    # Local Ollama and LM Studio on localhost are explicitly allowed when allow_local_runtime=True
    await validate_provider_endpoint("http://localhost:11434", ProviderKind.ollama, allow_local_runtime=True)
    await validate_provider_endpoint("http://127.0.0.1:11434", ProviderKind.ollama, allow_local_runtime=True)
    await validate_provider_endpoint("http://127.0.0.1:1234", ProviderKind.lm_studio, allow_local_runtime=True)

    # Localhost/loopback is rejected without explicit local-runtime authorization
    with pytest.raises(ProviderRequestError):
        await validate_provider_endpoint("http://127.0.0.1:11434", ProviderKind.ollama, allow_local_runtime=False)
    with pytest.raises(ProviderRequestError):
        await validate_provider_endpoint("http://127.0.0.1:1234", ProviderKind.lm_studio, allow_local_runtime=False)

    # Unsupported ports on loopback are rejected even with allow_local_runtime=True
    with pytest.raises(ProviderRequestError):
        await validate_provider_endpoint("http://127.0.0.1:8000", ProviderKind.ollama, allow_local_runtime=True)

    # Cloud metadata link-local IP is blocked for all provider kinds
    for kind in (ProviderKind.ollama, ProviderKind.lm_studio, ProviderKind.openai_compatible):
        with pytest.raises(ProviderRequestError):
            await validate_provider_endpoint("http://169.254.169.254/latest/meta-data", kind, allow_local_runtime=True)

    # Arbitrary private network IPs are blocked even with allow_local_runtime=True
    with patch("app.providers.base._get_local_interface_ips", return_value={"192.168.1.10"}):
        await validate_provider_endpoint(
            "http://192.168.1.10:1234/v1",
            ProviderKind.lm_studio,
            allow_local_runtime=True,
        )
        with pytest.raises(ProviderRequestError):
            await validate_provider_endpoint("http://10.0.0.5:11434", ProviderKind.ollama, allow_local_runtime=True)
        with pytest.raises(ProviderRequestError):
            await validate_provider_endpoint("http://192.168.1.50:1234", ProviderKind.lm_studio, allow_local_runtime=True)
        # Ordinary OpenAI-compatible provider never bypasses SSRF checks even if allow_local_runtime=True
        with pytest.raises(ProviderRequestError):
            await validate_provider_endpoint(
                "http://127.0.0.1:1234/v1",
                ProviderKind.openai_compatible,
                allow_local_runtime=True,
            )


@pytest.mark.asyncio
async def test_provider_ssrf_blocks_dns_rebinding_and_redirects():
    # DNS rebinding: localhost resolving to non-loopback private IP is rejected
    rebound_private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 11434))]
    with patch("app.providers.base.socket.getaddrinfo", return_value=rebound_private):
        with pytest.raises(ProviderRequestError):
            await validate_provider_endpoint("http://localhost:11434", ProviderKind.ollama, allow_local_runtime=True)

    # DNS rebinding: public domain resolving to loopback is rejected
    rebound_loopback = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
    with patch("app.providers.base.socket.getaddrinfo", return_value=rebound_loopback):
        with pytest.raises(ProviderRequestError):
            await validate_provider_endpoint("https://api.example.com", ProviderKind.openai_compatible)

    # Redirects to unauthorized private destinations are rejected
    config = ProviderConfigRequest(
        kind=ProviderKind.openai_compatible,
        endpoint="https://api.example.com",
        model="remote-model",
    )
    provider = OpenAICompatibleProvider(config)
    public_addr = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    request = httpx.Request("GET", "https://api.example.com/v1/models")
    redirect_response = httpx.Response(
        302,
        headers={"location": "http://169.254.169.254/latest/meta-data"},
        request=request,
    )
    try:
        provider._client.request = AsyncMock(return_value=redirect_response)
        with patch("app.providers.base.socket.getaddrinfo", return_value=public_addr):
            with pytest.raises(ProviderRequestError):
                await provider.discover_models()
    finally:
        await provider.close()


def test_provider_test_and_analysis_use_consistent_local_runtime_validation(client):
    # Without allow_local_runtime=True, /providers/test rejects loopback
    test_resp = client.post(
        "/api/v1/providers/test",
        json={
            "kind": "lm_studio",
            "endpoint": "http://127.0.0.1:1234/v1",
            "allow_local_runtime": False,
        },
    )
    assert test_resp.status_code == 422
    assert test_resp.json()["error"] == "invalid_provider_endpoint"

    # With allow_local_runtime=True, /providers/test accepts explicitly authorized LM Studio endpoint
    with patch("app.routers.providers.create_provider") as create_provider:
        provider = create_provider.return_value
        provider.test_connection = AsyncMock(
            return_value={
                "kind": "lm_studio",
                "endpoint": "http://127.0.0.1:1234/v1",
                "connected": True,
                "models": ["qwen2.5-7b"],
                "api_key_configured": False,
            }
        )
        provider.close = AsyncMock()
        ok_resp = client.post(
            "/api/v1/providers/test",
            json={
                "kind": "lm_studio",
                "endpoint": "http://127.0.0.1:1234/v1",
                "allow_local_runtime": True,
            },
        )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["connected"] is True
    assert ok_resp.json()["models"] == ["qwen2.5-7b"]
