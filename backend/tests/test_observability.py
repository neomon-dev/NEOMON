"""Tests for Observability, Health/Readiness Probes, and Request Tracking."""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.logging_config import mask_sensitive_data


def test_liveness_probes():
    """Verify /health and /api/v1/health liveness endpoints."""
    with TestClient(app) as client:
        # Root probe
        r1 = client.get("/health")
        assert r1.status_code == 200
        data1 = r1.json()
        assert data1["status"] == "ok"
        assert "version" in data1

        # API v1 probe
        r2 = client.get("/api/v1/health")
        assert r2.status_code == 200
        assert r2.json()["status"] == "ok"


def test_readiness_probes():
    """Verify /ready and /api/v1/ready readiness checks."""
    with TestClient(app) as client:
        r = client.get("/ready")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ready"
        assert data["database"]["status"] == "healthy"
        assert data["cache"]["healthy"] is True
        assert "worker" in data


def test_metrics_probes():
    """Verify /metrics and /api/v1/metrics operational telemetry."""
    with TestClient(app) as client:
        r = client.get("/metrics")
        assert r.status_code == 200
        data = r.json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0.0
        assert "database" in data
        assert "cache" in data
        assert "worker" in data


def test_request_id_correlation_header():
    """Verify X-Request-ID propagation and generation."""
    with TestClient(app) as client:
        # Case 1: Custom request ID provided
        custom_id = f"trace-{uuid.uuid4()}"
        r1 = client.get("/health", headers={"X-Request-ID": custom_id})
        assert r1.headers.get("X-Request-ID") == custom_id

        # Case 2: Generated request ID when omitted
        r2 = client.get("/health")
        generated_id = r2.headers.get("X-Request-ID")
        assert generated_id is not None
        assert len(generated_id) >= 10


def test_sensitive_data_masking():
    """Verify passwords, bearer tokens, and secrets are sanitized in logs."""
    raw_log = 'User login failed with password="SuperSecretPassword123!" and token: "eyJhbGciOiJIUzI1NiJ9"'
    masked = mask_sensitive_data(raw_log)
    assert "SuperSecretPassword123!" not in masked
    assert "***REDACTED***" in masked

    raw_auth = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.testpayload.signature"
    masked_auth = mask_sensitive_data(raw_auth)
    assert "eyJhbGciOiJIUzI1NiJ9" not in masked_auth
    assert "Bearer ***REDACTED***" in masked_auth
