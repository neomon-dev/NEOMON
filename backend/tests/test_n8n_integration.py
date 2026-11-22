import uuid
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionFactory
from app.models import Investigation


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_n8n_status_endpoint(client: TestClient):
    # Register user
    unique_email = f"n8n_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "SecurePassword123!",
            "display_name": "n8n Tester",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["session_token"]

    status_res = client.get(
        "/api/v1/integrations/n8n/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_res.status_code == 200
    data = status_res.json()
    assert "status" in data
    assert "configured" in data
    assert "version" in data


def test_n8n_monitoring_crud_lifecycle(client: TestClient):
    unique_email = f"monitor_{uuid.uuid4().hex[:8]}@neomon.ai"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "SecurePassword123!",
            "display_name": "Monitor Tester",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    token = reg_data["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Retrieve workspace id
    ws_res = client.get("/api/v1/workspaces", headers=headers)
    assert ws_res.status_code == 200
    workspace_id = ws_res.json()[0]["id"]

    # Create an investigation with mocked background retrieval
    with patch("app.routers.research.run_investigation", return_value=([], [])):
        inv_res = client.post(
            "/api/v1/research/investigations",
            headers=headers,
            json={"question": "What are next-generation electrolyte breakthroughs for sodium-ion batteries?", "workspace_id": workspace_id},
        )
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["investigation"]["id"]

    # 1. Create monitoring config
    create_res = client.post(
        "/api/v1/monitoring",
        headers=headers,
        json={
            "workspace_id": workspace_id,
            "investigation_id": inv_id,
            "name": "Sodium Battery Breakthroughs",
            "query_keywords": "sodium battery, solid electrolyte, ionic conductivity",
            "interval_minutes": 60,
            "max_new_sources_per_run": 5,
        },
    )
    assert create_res.status_code == 201
    cfg = create_res.json()
    config_id = cfg["id"]
    assert cfg["name"] == "Sodium Battery Breakthroughs"
    assert cfg["is_active"] is True

    # 2. List monitoring configs
    list_res = client.get(
        f"/api/v1/monitoring?workspace_id={workspace_id}",
        headers=headers,
    )
    assert list_res.status_code == 200
    configs = list_res.json()
    assert len(configs) >= 1
    assert any(c["id"] == config_id for c in configs)

    # 3. Update monitoring config
    update_res = client.patch(
        f"/api/v1/monitoring/{config_id}",
        headers=headers,
        json={"is_active": False, "interval_minutes": 120},
    )
    assert update_res.status_code == 200
    assert update_res.json()["is_active"] is False
    assert update_res.json()["interval_minutes"] == 120

    # 4. Trigger monitoring run manually
    trigger_res = client.post(
        f"/api/v1/monitoring/{config_id}/trigger",
        headers=headers,
        json={"idempotency_key": f"test_idem_{uuid.uuid4().hex[:8]}"},
    )
    assert trigger_res.status_code == 200
    run_data = trigger_res.json()
    assert run_data["status"] == "completed"

    # 5. Delete monitoring config
    del_res = client.delete(
        f"/api/v1/monitoring/{config_id}",
        headers=headers,
    )
    assert del_res.status_code == 204


def test_n8n_service_event_callback_validation(client: TestClient):
    # Service call requires valid Bearer token
    unauth_res = client.post(
        "/api/v1/integrations/n8n/events",
        json={"event_type": "monitoring.trigger", "payload": {}},
    )
    assert unauth_res.status_code in {401, 403}

    # With service token
    auth_res = client.post(
        "/api/v1/integrations/n8n/events",
        headers={"Authorization": "Bearer neomon_n8n_s2s_default_secret"},
        json={"event_type": "notification.callback", "payload": {"status": "delivered"}},
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["status"] == "accepted"
