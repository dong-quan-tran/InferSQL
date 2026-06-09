from app.schemas.health import HealthResponse, VersionResponse


def test_health_response_schema() -> None:
    payload = HealthResponse(status="ok")
    assert payload.model_dump() == {"status": "ok"}


def test_version_response_schema() -> None:
    payload = VersionResponse(service="infersql-backend", version="0.1.0")
    assert payload.model_dump() == {
        "service": "infersql-backend",
        "version": "0.1.0",
    }