import atexit
import os
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure test environment
os.environ.setdefault("NEOMON_ENVIRONMENT", "test")

# Isolated SQLite database setup for tests
_SESSION_TEMP_DB: Path | None = None
_BASELINE_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "test_database.db",
    Path(__file__).resolve().parents[1] / "backups" / "recovery_experiments" / "neomon_recovered.db",
]

# If NEOMON_DATABASE_URL is not explicitly set, create an isolated disposable test copy
if "NEOMON_DATABASE_URL" not in os.environ:
    baseline_path = next((p for p in _BASELINE_CANDIDATES if p.exists()), None)
    if baseline_path:
        temp_dir = Path(tempfile.gettempdir())
        _SESSION_TEMP_DB = temp_dir / f"neomon_test_{os.getpid()}_{uuid.uuid4().hex[:8]}.db"
        shutil.copyfile(baseline_path, _SESSION_TEMP_DB)
        os.environ["NEOMON_DATABASE_URL"] = f"sqlite+aiosqlite:///{_SESSION_TEMP_DB.as_posix()}"

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.db import engine
from app.main import app


def _cleanup_temp_db():
    global _SESSION_TEMP_DB
    if _SESSION_TEMP_DB and _SESSION_TEMP_DB.exists():
        for f in [
            _SESSION_TEMP_DB,
            _SESSION_TEMP_DB.with_name(_SESSION_TEMP_DB.name + "-wal"),
            _SESSION_TEMP_DB.with_name(_SESSION_TEMP_DB.name + "-shm"),
        ]:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass


atexit.register(_cleanup_temp_db)


def pytest_sessionfinish(session, exitstatus):
    """Clean up the isolated test database and temporary SQLite WAL files."""
    import asyncio
    try:
        from app.db import engine
        asyncio.run(engine.dispose())
    except Exception:
        pass
    _cleanup_temp_db()


def authed_client() -> TestClient:
    """Helper to return an authenticated TestClient for seeded administrator."""
    test_client = TestClient(app)
    login_res = test_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@neomon.ai", "password": "Password123!"},
    )
    assert login_res.status_code == 200, f"authed_client login failed: {login_res.status_code} - {login_res.text}"
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
        assert login_res.status_code == 200, f"authed_async_client login failed: {login_res.status_code} - {login_res.text}"
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
