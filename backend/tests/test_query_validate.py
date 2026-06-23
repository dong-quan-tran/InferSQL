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


def test_query_validate_allows_global_count_star(client: TestClient) -> None:
    response = client.post(
        "/query/validate",
        json={"sql": "SELECT COUNT(*) AS row_count FROM prices"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["is_valid"] is True
    assert data["errors"] == []
    assert data["tables"] == ["prices"]
    assert data["has_group_by"] is False


def test_query_validate_allows_non_grouped_column_with_global_aggregate_precheck(
    client: TestClient,
) -> None:
    response = client.post(
        "/query/validate",
        json={"sql": "SELECT symbol, SUM(close) FROM prices"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["is_valid"] is True
    assert data["errors"] == []
    assert data["has_group_by"] is False


def test_query_validate_allows_non_grouped_column_with_grouped_aggregate_precheck(
    client: TestClient,
) -> None:
    response = client.post(
        "/query/validate",
        json={
            "sql": "SELECT symbol, close, SUM(close) FROM prices GROUP BY symbol"
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["errors"] == []
    assert data["has_group_by"] is True


def test_query_validate_rejects_select_star_with_group_by(client: TestClient) -> None:
    response = client.post(
        "/query/validate",
        json={"sql": "SELECT * FROM prices GROUP BY symbol"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["is_valid"] is False
    assert "SELECT * with GROUP BY is not supported right now" in payload["errors"]
    assert payload["has_group_by"] is True


def test_query_execute_rejects_select_star_with_group_by(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT * FROM prices GROUP BY symbol"},
    )

    assert response.status_code == 400
    payload = response.json()

    assert payload["error"]["type"] == "UnsupportedQueryError"
    assert payload["error"]["message"] == "SELECT * with GROUP BY is not supported right now"


def test_group_by_semantics_are_engine_enforced(client: TestClient) -> None:
    sql = "SELECT symbol, close FROM prices GROUP BY symbol"

    validate_response = client.post(
        "/query/validate",
        json={"sql": sql},
    )
    assert validate_response.status_code == 200
    validate_payload = validate_response.json()

    assert validate_payload["is_valid"] is True
    assert validate_payload["errors"] == []

    execute_response = client.post(
        "/query/execute",
        json={"sql": sql},
    )
    assert execute_response.status_code == 400
    execute_payload = execute_response.json()

    assert execute_payload["error"]["type"] == "UnsupportedQueryError"


def test_group_by_aggregate_executes_successfully(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT symbol, SUM(close) AS total_close FROM prices GROUP BY symbol"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "total_close"]
    assert payload["row_count"] == 5
    assert len(payload["rows"]) == 5


def test_validate_join_query_reports_unknown_dataset(client: TestClient) -> None:
    response = client.post(
        "/query/validate",
        json={
            "sql": (
                "SELECT prices.symbol, sectors.sector "
                "FROM prices "
                "JOIN sectors ON prices.symbol = sectors.symbol"
            )
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["is_valid"] is False
    assert "Unknown dataset 'sectors'" in data["errors"]


def test_query_validate_join_is_allowed(client: TestClient) -> None:
    response = client.post(
        "/query/validate",
        json={
            "sql": """
                SELECT p.symbol, n.close
                FROM prices AS p
                JOIN prices_nulls AS n
                  ON p.symbol = n.symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_valid"] is True


def test_query_validate_allows_left_join_with_qualified_columns(client: TestClient) -> None:
    response = client.post(
        "/query/validate",
        json={
            "sql": """
                SELECT p.symbol, n.close AS matched_close
                FROM prices AS p
                LEFT JOIN prices_nulls AS n
                  ON p.symbol = n.symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["is_valid"] is True
    assert payload["errors"] == []
    assert set(payload["tables"]) == {"prices", "prices_nulls"}
    # Columns list is a flat set of referenced column names; exact order is not important.
    assert "symbol" in payload["columns"]
    assert "close" in payload["columns"]


def test_query_validate_join_unknown_alias_column_fails(client: TestClient) -> None:
    response = client.post(
        "/query/validate",
        json={
            "sql": """
                SELECT p.missing_col
                FROM prices AS p
                JOIN prices_nulls AS n
                  ON p.symbol = n.symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_valid"] is False
    assert any("Unknown column 'missing_col'" in error for error in payload["errors"])


def test_query_validate_join_ambiguous_unqualified_column_fails(client: TestClient) -> None:
    response = client.post(
        "/query/validate",
        json={
            "sql": """
                SELECT symbol
                FROM prices AS p
                JOIN prices_nulls AS n
                  ON p.symbol = n.symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_valid"] is False
    assert any("Ambiguous unqualified column 'symbol'" in error for error in payload["errors"])