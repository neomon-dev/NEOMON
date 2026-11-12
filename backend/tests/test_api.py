from unittest.mock import AsyncMock, patch


def test_health_is_versioned_and_explicit(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["demo_mode"] is True


def test_agents_expose_all_twelve_foundation_agents(client):
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert len(response.json()) == 12
    assert all(agent["demo_mode"] is True for agent in response.json())


def test_provider_validation_rejects_non_http_endpoint(client):
    response = client.post(
        "/api/v1/providers/test",
        json={"kind": "ollama", "endpoint": "localhost:11434"},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_provider_test_redacts_api_key_and_returns_provider_status(client):
    with patch(
        "app.routers.providers.create_provider"
    ) as create_provider:
        provider = create_provider.return_value
        provider.test_connection = AsyncMock(
            return_value={
                "kind": "ollama",
                "endpoint": "http://localhost:11434",
                "connected": True,
                "models": ["local-model"],
                "api_key_configured": True,
            }
        )
        provider.close = AsyncMock()
        response = client.post(
            "/api/v1/providers/test",
            json={
                "kind": "ollama",
                "endpoint": "http://localhost:11434",
                "api_key": "secret-value",
                "allow_local_runtime": True,
            },
        )
    assert response.status_code == 200
    assert "secret-value" not in response.text
    assert response.json()["api_key_configured"] is True


def test_cors_is_allowlisted(client):
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
