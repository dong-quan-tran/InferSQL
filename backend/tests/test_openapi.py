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
    assert {
        "type",
        "code",
        "message",
        "status_code",
        "request_id",
    }.issubset(set(error_detail["properties"].keys()))

def test_query_routes_have_summaries_and_descriptions() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200

    data = response.json()

    validate_post = data["paths"]["/query/validate"]["post"]
    plan_post = data["paths"]["/query/plan"]["post"]
    execute_post = data["paths"]["/query/execute"]["post"]

    assert validate_post["summary"] == "Validate a SQL query"
    assert "validates a sql query" in validate_post["description"].lower()

    assert plan_post["summary"] == "Build a query plan"
    assert "logical and physical plan" in plan_post["description"].lower()

    assert execute_post["summary"] == "Execute a SQL query"
    assert "limit" in execute_post["description"].lower()
    assert "offset" in execute_post["description"].lower()


def test_error_response_schema_documents_optional_debug_metadata() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200

    data = response.json()
    schemas = data["components"]["schemas"]

    assert "ErrorResponse" in schemas
    assert "ErrorDetail" in schemas

    error_detail = schemas["ErrorDetail"]
    properties = error_detail["properties"]

    assert "debug" in properties

    debug_schema = properties["debug"]
    assert "anyOf" in debug_schema or "$ref" in debug_schema