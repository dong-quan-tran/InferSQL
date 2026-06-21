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
    assert response.json()["error"]["type"] == "UnsupportedQueryError"
    assert response.json()["error"]["message"] == "Only SELECT queries are supported right now"


def test_query_execute_rejects_unknown_column(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT nope FROM prices LIMIT 5"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["type"] == "UnknownColumnError"
    assert response.json()["error"]["message"] == "Unknown column 'nope' on dataset 'prices'"


def test_query_execute_rejects_unknown_dataset(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT symbol FROM missing_table LIMIT 5"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["type"] == "UnknownDatasetError"
    assert response.json()["error"]["message"] == "Unknown dataset 'missing_table'"


def test_query_execute_orders_rows_ascending(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT symbol, close FROM prices ORDER BY close LIMIT 3"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["columns"] == ["symbol", "close"]
    assert data["row_count"] == 3

    closes = [row["close"] for row in data["rows"]]
    assert closes == sorted(closes)

    assert data["logical_plan"]["node_type"] == "Limit"
    assert data["physical_plan"]["node_type"] == "Limit"

    sort_node = data["logical_plan"]["children"][0]
    assert sort_node["node_type"] == "Sort"
    assert sort_node["details"] == {
        "keys": [{"column": "close", "direction": "ASC"}]
    }


def test_query_execute_orders_rows_descending(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT symbol, close FROM prices ORDER BY close DESC LIMIT 3"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["columns"] == ["symbol", "close"]
    assert data["row_count"] == 3

    closes = [row["close"] for row in data["rows"]]
    assert closes == sorted(closes, reverse=True)

    sort_node = data["logical_plan"]["children"][0]
    assert sort_node["node_type"] == "Sort"
    assert sort_node["details"] == {
        "keys": [{"column": "close", "direction": "DESC"}]
    }


def test_query_execute_orders_rows_after_filter(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close DESC LIMIT 2"
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["columns"] == ["symbol", "close"]
    assert data["row_count"] == 2

    closes = [row["close"] for row in data["rows"]]
    assert closes == sorted(closes, reverse=True)
    assert all(value > 100 for value in closes)


def test_query_execute_global_count_star(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT COUNT(*) AS row_count FROM prices"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["columns"] == ["row_count"]
    assert data["row_count"] == 1
    assert len(data["rows"]) == 1
    assert data["rows"][0]["row_count"] == 5  # seeded demo table has 5 rows


def test_query_execute_grouped_sum_by_symbol(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": "SELECT symbol, SUM(close) AS total_close FROM prices GROUP BY symbol"
        },
    )

    assert response.status_code == 200

    data = response.json()
    # One row per symbol, same as number of input rows in demo data.
    assert data["row_count"] == 5
    assert data["columns"] == ["symbol", "total_close"]
    assert len(data["rows"]) == 5

    # Each symbol appears exactly once.
    rows = data["rows"]
    symbols = {row["symbol"] for row in rows}
    assert symbols == {"AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"}

    # Totals match seeded demo prices exactly.
    totals_by_symbol = {row["symbol"]: row["total_close"] for row in rows}
    assert totals_by_symbol == {
        "AAPL": 189.12,
        "MSFT": 425.27,
        "NVDA": 1210.54,
        "GOOGL": 176.33,
        "AMZN": 182.41,
    }


def test_query_execute_respects_simple_alias(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT close AS price FROM prices LIMIT 1"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["columns"] == ["price"]
    assert data["row_count"] == 1
    assert len(data["rows"]) == 1
    row = data["rows"][0]
    assert "price" in row
    assert "close" not in row


def test_query_execute_alias_with_filter(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT close AS price FROM prices WHERE close > 100 LIMIT 2"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["columns"] == ["price"]
    assert data["row_count"] == 2
    assert len(data["rows"]) == 2
    for row in data["rows"]:
        assert "price" in row
        assert "close" not in row
        assert row["price"] > 100


def test_query_execute_grouped_aggregate_aliases(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": "SELECT symbol, SUM(close) AS total_close FROM prices GROUP BY symbol"
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["columns"] == ["symbol", "total_close"]
    assert data["row_count"] == 5

    rows = data["rows"]
    symbols = {row["symbol"] for row in rows}
    assert symbols == {"AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"}

    # Aliasing behavior: output uses alias, not raw expression.
    for row in rows:
        assert "total_close" in row
        assert "SUM(close)" not in row
        assert isinstance(row["total_close"], (int, float))


def test_query_execute_order_by_sorts_nulls_last(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT symbol, close FROM prices_nulls ORDER BY close LIMIT 10"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["columns"] == ["symbol", "close"]

    rows = data["rows"]
    assert [row["close"] for row in rows[:-1]] == sorted(
        [row["close"] for row in rows[:-1]]
    )
    assert rows[-1]["close"] is None


def test_query_execute_inner_join_returns_matching_rows(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT p.symbol, p.close AS left_close, n.close AS right_close
                FROM prices AS p
                JOIN prices_nulls AS n
                  ON p.symbol = n.symbol
                ORDER BY p.symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "left_close", "right_close"]
    assert payload["row_count"] == 3
    assert payload["rows"] == [
        {"symbol": "AAPL", "left_close": 189.12, "right_close": 150.0},
        {"symbol": "MSFT", "left_close": 425.27, "right_close": None},
        {"symbol": "NVDA", "left_close": 1210.54, "right_close": 120.0},
    ]


def test_query_execute_left_join_preserves_unmatched_rows(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT p.symbol, n.close AS matched_close
                FROM prices AS p
                LEFT JOIN prices_nulls AS n
                  ON p.symbol = n.symbol
                ORDER BY p.symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "matched_close"]
    assert payload["row_count"] == 5
    assert payload["rows"] == [
        {"symbol": "AAPL", "matched_close": 150.0},
        {"symbol": "AMZN", "matched_close": None},
        {"symbol": "GOOGL", "matched_close": None},
        {"symbol": "MSFT", "matched_close": None},
        {"symbol": "NVDA", "matched_close": 120.0},
    ]


def test_query_execute_unknown_join_alias_returns_404(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT x.symbol
                FROM prices AS p
                JOIN prices_nulls AS n
                  ON p.symbol = n.symbol
            """
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "UNKNOWNDATASETERROR"
    assert "Unknown dataset or alias 'x'" in payload["error"]["message"]


def test_query_execute_ambiguous_unqualified_column_returns_400(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol
                FROM prices AS p
                JOIN prices_nulls AS n
                  ON p.symbol = n.symbol
            """
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTEDQUERYERROR"
    assert "Ambiguous unqualified column 'symbol'" in payload["error"]["message"]

def test_query_execute_select_from_prices_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT FROM prices"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTEDQUERYERROR"
    assert "select at least one column" in payload["error"]["message"]


def test_query_execute_unknown_column_returns_400(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT missing_column FROM prices"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNKNOWNCOLUMNERROR"
    assert "Unknown column 'missing_column'" in payload["error"]["message"]


def test_query_execute_malformed_subquery_returns_unsupported(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol
                FROM prices
                WHERE symbol IN (SELECT FROM prices_nulls)
            """
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTEDQUERYERROR"


def test_query_execute_invalid_union_shape_returns_unsupported(client: TestClient) -> None:
    # Different column counts between the two SELECT branches.
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol FROM prices
                UNION ALL
                SELECT symbol, close FROM prices
            """
        },
    )

    # DataFusion typically surfaces this as a planning/schema error; we map to UNSUPPORTEDQUERYERROR.
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTEDQUERYERROR"