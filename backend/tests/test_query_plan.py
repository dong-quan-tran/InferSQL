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
        "extract_query_metadata",
        "validate_sql",
        "build_logical_plan",
        "build_physical_plan",
    ]

    logical_plan = data["logical_plan"]
    assert logical_plan["node_type"] == "Limit"
    assert logical_plan["details"] == {"count": 10}

    project_node = logical_plan["children"][0]
    assert project_node["node_type"] == "Project"
    assert project_node["details"] == {"columns": ["symbol", "close"]}

    scan_node = project_node["children"][0]
    assert scan_node["node_type"] == "Scan"
    assert scan_node["details"] == {"table": "prices"}


def test_query_plan_includes_filter_node_when_where_exists() -> None:
    response = client.post(
        "/query/plan",
        json={"sql": "SELECT symbol FROM prices WHERE close > 100 LIMIT 5"},
    )

    assert response.status_code == 200

    data = response.json()
    logical_plan = data["logical_plan"]

    assert logical_plan["node_type"] == "Limit"
    project_node = logical_plan["children"][0]
    assert project_node["node_type"] == "Project"

    filter_node = project_node["children"][0]
    assert filter_node["node_type"] == "Filter"
    assert filter_node["details"] == {
        "predicate": {
            "column": "close",
            "operator": ">",
            "value": 100,
            "sql": "close > 100",
        }
    }

    scan_node = filter_node["children"][0]
    assert scan_node["node_type"] == "Scan"
    assert scan_node["details"] == {"table": "prices"}


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


def test_query_plan_rejects_invalid_sql_syntax() -> None:
    response = client.post("/query/plan", json={"sql": "SELECT FROM"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid SQL syntax"}