"""Tests for Rate Limiting Middleware and Bucket Enforcement."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.auth.rate_limiter import RateLimiter, get_client_identifier
from app.cache.service import cache_service


def build_mock_request(client_ip: str = "192.168.1.50", forward_for: str = None) -> Request:
    """Construct mock Starlette Request with custom network headers."""
    headers = []
    if forward_for:
        headers.append((b"x-forwarded-for", forward_for.encode()))

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": headers,
        "client": (client_ip, 12345),
    }
    req = Request(scope)
    # Enable test rate limit bypass check
    req.state.force_rate_limit = True
    return req


def test_client_identifier_resolution():
    """Verify IP and X-Forwarded-For resolution."""
    req1 = build_mock_request(client_ip="10.0.0.1")
    assert get_client_identifier(req1) == "ip:10.0.0.1"

    req2 = build_mock_request(client_ip="10.0.0.1", forward_for="203.0.113.195, 10.0.0.1")
    assert get_client_identifier(req2) == "ip:203.0.113.195"


@pytest.mark.asyncio
async def test_rate_limiter_exceed_triggers_429():
    """Verify that requests exceeding configured RPM threshold raise HTTP 429 with Retry-After."""
    # Custom bucket with limit 3 per minute
    limiter = RateLimiter(limit_per_minute=3, bucket="test_bucket")
    req = build_mock_request(client_ip="198.51.100.22")

    # Clear cache key for isolation
    client_id = get_client_identifier(req)

    # 3 allowed requests
    for _ in range(3):
        # Pass header to enable rate limiter under test environment
        scope = dict(req.scope)
        scope["headers"] = [(b"x-enable-rate-limit", b"true")]
        active_req = Request(scope)
        await limiter(active_req)

    # 4th request must be rejected with HTTP 429
    scope = dict(req.scope)
    scope["headers"] = [(b"x-enable-rate-limit", b"true")]
    active_req = Request(scope)

    with pytest.raises(HTTPException) as exc_info:
        await limiter(active_req)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers
    retry_after = int(exc_info.value.headers["Retry-After"])
    assert 1 <= retry_after <= 60
