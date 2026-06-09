from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_query_plan_returns_expected_shape() -> None:
    response = client.post(
        "/query/plan",
        json={"sql": "SELECT symbol, close FROM prices LIMIT 10"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["sql"] == "SELECT symbol, close FROM prices LIMIT 10"
    assert data["normalized_sql"] == "SELECT symbol, close FROM prices LIMIT 10"
    assert data["engine"] == "infersql-planner"
    assert data["steps"] == [
        "parse_sql",
        "validate_sql",
        "build_logical_plan",
        "build_physical_plan",
    ]


def test_query_plan_normalizes_whitespace() -> None:
    response = client.post(
        "/query/plan",
        json={"sql": " SELECT   symbol,   close   FROM prices   LIMIT 10 "},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["normalized_sql"] == "SELECT symbol, close FROM prices LIMIT 10"


def test_query_plan_rejects_missing_payload() -> None:
    response = client.post("/query/plan", json={})
    assert response.status_code == 422


def test_query_plan_rejects_blank_sql() -> None:
    response = client.post("/query/plan", json={"sql": "   "})
    assert response.status_code == 422
    assert "SQL must not be empty" in str(response.json())


def test_query_plan_rejects_non_select_sql() -> None:
    response = client.post(
        "/query/plan",
        json={"sql": "DELETE FROM prices WHERE symbol = 'AAPL'"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Only SELECT queries are supported right now",
    }