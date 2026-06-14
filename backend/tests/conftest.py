import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as client:
        yield client