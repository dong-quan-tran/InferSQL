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
    assert "/query/validate" in data["paths"]
    assert "/query/plan" in data["paths"]
    assert "/query/execute" in data["paths"]


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


def test_query_routes_document_error_responses() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200

    data = response.json()

    validate_post = data["paths"]["/query/validate"]["post"]
    plan_post = data["paths"]["/query/plan"]["post"]
    execute_post = data["paths"]["/query/execute"]["post"]

    assert "400" in validate_post["responses"]
    assert "500" in validate_post["responses"]

    assert "400" in plan_post["responses"]
    assert "404" in plan_post["responses"]
    assert "500" in plan_post["responses"]

    assert "400" in execute_post["responses"]
    assert "404" in execute_post["responses"]
    assert "500" in execute_post["responses"]


def test_error_response_schema_is_present_in_openapi_components() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200

    data = response.json()
    schemas = data["components"]["schemas"]

    assert "ErrorResponse" in schemas
    assert "ErrorDetail" in schemas

    error_response = schemas["ErrorResponse"]
    assert error_response["type"] == "object"
    assert "error" in error_response["properties"]

    error_detail = schemas["ErrorDetail"]
    assert error_detail["type"] == "object"
    assert set(error_detail["properties"].keys()) == {
        "type",
        "code",
        "message",
        "status_code",
        "request_id",
    }