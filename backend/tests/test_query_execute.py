# tests/test_query_execute.py
from fastapi.testclient import TestClient


def test_query_execute_returns_rows(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT symbol, close FROM prices WHERE close > 100 LIMIT 2"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["sql"] == "SELECT symbol, close FROM prices WHERE close > 100 LIMIT 2"
    assert data["normalized_sql"] == "SELECT symbol, close FROM prices WHERE close > 100 LIMIT 2"
    assert data["columns"] == ["symbol", "close"]
    assert data["row_count"] == 2
    assert len(data["rows"]) == 2
    assert all("symbol" in row for row in data["rows"])
    assert all("close" in row for row in data["rows"])

    assert data["logical_plan"]["node_type"] == "Limit"
    assert data["physical_plan"]["node_type"] == "Limit"


def test_query_execute_rejects_non_select(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "DELETE FROM prices WHERE symbol = 'AAPL'"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Only SELECT queries are supported right now",
    }


def test_query_execute_rejects_unknown_column(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT nope FROM prices LIMIT 5"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Unknown column 'nope' on dataset 'prices'",
    }