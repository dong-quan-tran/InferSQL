from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_openapi_contains_core_routes() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200

    data = response.json()

    assert "paths" in data
    assert "/health" in data["paths"]
    assert "/version" in data["paths"]


def test_openapi_health_and_version_have_200_response() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200

    data = response.json()

    health_get = data["paths"]["/health"]["get"]
    version_get = data["paths"]["/version"]["get"]

    assert "200" in health_get["responses"]
    assert "200" in version_get["responses"]

    assert "content" in health_get["responses"]["200"]
    assert "content" in version_get["responses"]["200"]

    assert "application/json" in health_get["responses"]["200"]["content"]
    assert "application/json" in version_get["responses"]["200"]["content"]