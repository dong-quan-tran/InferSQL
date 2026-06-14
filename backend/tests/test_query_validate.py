from fastapi.testclient import TestClient


def test_query_validate_accepts_select_sql(client: TestClient) -> None:
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
        "tables": ["prices"],
        "columns": ["close", "symbol"],
        "has_where": False,
        "has_group_by": False,
        "has_order_by": False,
        "has_limit": True,
    }


def test_query_validate_normalizes_whitespace(client: TestClient) -> None:
    response = client.post(
        "/query/validate",
        json={"sql": " SELECT   symbol,   close   FROM prices   LIMIT 10 "},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["normalized_sql"] == "SELECT symbol, close FROM prices LIMIT 10"
    assert data["is_valid"] is True
    assert data["tables"] == ["prices"]


def test_query_validate_reports_unsupported_query(client: TestClient) -> None:
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
        "tables": ["prices"],
        "columns": ["symbol"],
        "has_where": True,
        "has_group_by": False,
        "has_order_by": False,
        "has_limit": False,
    }


def test_query_validate_rejects_blank_sql(client: TestClient) -> None:
    response = client.post("/query/validate", json={"sql": "   "})
    assert response.status_code == 422


def test_query_validate_rejects_invalid_sql_syntax(client: TestClient) -> None:
    response = client.post("/query/validate", json={"sql": "SELECT FROM"})
    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Invalid SQL syntax"


def test_query_validate_rejects_unknown_column(client: TestClient) -> None:
    response = client.post(
        "/query/validate",
        json={"sql": "SELECT nope FROM prices LIMIT 5"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["is_valid"] is False
    assert data["errors"] == ["Unknown column 'nope' on dataset 'prices'"]
    assert data["tables"] == ["prices"]
    assert data["columns"] == ["nope"]