from contextlib import asynccontextmanager
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.db import engine
from app.main import app


def authed_client() -> TestClient:
    """Helper to return an authenticated TestClient for seeded administrator."""
    test_client = TestClient(app)
    login_res = test_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@neomon.ai", "password": "Password123!"},
    )
    if login_res.status_code == 200:
        token = login_res.json()["session_token"]
        test_client.headers["Authorization"] = f"Bearer {token}"
    return test_client


@asynccontextmanager
async def authed_async_client():
    """Context manager yielding an authenticated AsyncClient for seeded administrator."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post(
            "/api/v1/auth/login",
            json={"email": "admin@neomon.ai", "password": "Password123!"},
        )
        if login_res.status_code == 200:
            token = login_res.json()["session_token"]
            ac.headers["Authorization"] = f"Bearer {token}"
        yield ac


@pytest.fixture
def unauthenticated_client():
    """Client without any authentication headers."""
    with TestClient(app) as test_client:
        yield test_client
        test_client.portal.call(engine.dispose)


@pytest.fixture
def client():
    """Client with valid authentication session for seeded administrator."""
    with authed_client() as test_client:
        yield test_client
        test_client.portal.call(engine.dispose)


@pytest_asyncio.fixture
async def async_client():
    """AsyncClient with valid authentication session for seeded administrator."""
    async with authed_async_client() as ac:
        yield ac
