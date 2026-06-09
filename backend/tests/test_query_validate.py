from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_query_validate_accepts_select_sql() -> None:
    response = client.post(
        "/query/validate",
        json={"sql": "SELECT symbol, close FROM prices LIMIT 10"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sql": "SELECT symbol, close FROM prices LIMIT 10",
        "normalized_sql": "SELECT symbol, close FROM prices LIMIT 10",
        "is_valid": True,
        "query_type": "SELECT",
        "errors": [],
    }


def test_query_validate_normalizes_whitespace() -> None:
    response = client.post(
        "/query/validate",
        json={"sql": " SELECT   symbol,   close   FROM prices   LIMIT 10 "},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["normalized_sql"] == "SELECT symbol, close FROM prices LIMIT 10"
    assert data["is_valid"] is True


def test_query_validate_reports_unsupported_query() -> None:
    response = client.post(
        "/query/validate",
        json={"sql": "DELETE FROM prices WHERE symbol = 'AAPL'"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sql": "DELETE FROM prices WHERE symbol = 'AAPL'",
        "normalized_sql": "DELETE FROM prices WHERE symbol = 'AAPL'",
        "is_valid": False,
        "query_type": "DELETE",
        "errors": ["Only SELECT queries are supported right now"],
    }


def test_query_validate_rejects_blank_sql() -> None:
    response = client.post("/query/validate", json={"sql": "   "})
    assert response.status_code == 422