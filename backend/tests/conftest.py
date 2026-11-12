import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
        test_client.portal.call(engine.dispose)
