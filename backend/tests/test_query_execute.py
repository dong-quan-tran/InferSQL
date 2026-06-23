from fastapi.testclient import TestClient


# Basic execution and shape


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


# Ordering, limits, and nulls


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


# Aggregations and GROUP BY / HAVING


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


def test_query_execute_having_filters_grouped_rows(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol, SUM(close) AS total_close
                FROM prices
                GROUP BY symbol
                HAVING SUM(close) > 200
                ORDER BY symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "total_close"]
    assert payload["row_count"] == 2
    assert payload["rows"] == [
        {"symbol": "MSFT", "total_close": 425.27},
        {"symbol": "NVDA", "total_close": 1210.54},
    ]


def test_query_execute_invalid_having_non_grouped_column_engine_rejected(
    client: TestClient,
) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol, SUM(close) AS total_close
                FROM prices
                GROUP BY symbol
                HAVING close > 200
            """
        },
    )

    # DataFusion should surface this as an aggregate/group-by semantic error;
    # we normalize to an UnsupportedQueryError.
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTEDQUERYERROR"
    assert payload["error"]["type"] == "UnsupportedQueryError"


def test_query_execute_having_without_group_by_relies_on_engine(
    client: TestClient,
) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol, SUM(close) AS total_close
                FROM prices
                HAVING SUM(close) > 200
            """
        },
    )

    if response.status_code == 200:
        payload = response.json()
        assert payload["columns"] == ["symbol", "total_close"]
        # Depending on engine behavior, the row_count/rows may vary;
        # we only assert the basic shape.
        assert payload["row_count"] >= 1
    else:
        assert response.status_code == 400
        payload = response.json()
        assert payload["error"]["code"] in (
            "UNSUPPORTEDQUERYERROR",
            "INVALIDQUERYSYNTAXERROR",
        )


# Aliases and expressions


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


def test_query_execute_arithmetic_expression_in_select(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol, close, close + 1 AS close_plus
                FROM prices
                ORDER BY symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "close", "close_plus"]
    rows = payload["rows"]
    assert len(rows) == 5

    # Verify arithmetic expression is evaluated correctly per row.
    for row in rows:
        assert isinstance(row["close"], (int, float))
        assert isinstance(row["close_plus"], (int, float))
        assert row["close_plus"] == row["close"] + 1


def test_query_execute_order_by_select_alias_is_currently_rejected(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol, close, close + 1 AS close_plus
                FROM prices
                ORDER BY close_plus DESC
            """
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNKNOWNCOLUMNERROR"
    assert "Unknown column 'close_plus'" in payload["error"]["message"]


def test_query_execute_orders_by_raw_expression(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol, close
                FROM prices
                ORDER BY close * 2 DESC
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "close"]
    rows = payload["rows"]

    closes = [row["close"] for row in rows]
    # Ordering by close * 2 should be equivalent to ordering by close.
    assert closes == sorted(closes, reverse=True)


def test_query_execute_expression_in_where(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol, close
                FROM prices
                WHERE close + 10 > 200
                ORDER BY symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "close"]
    rows = payload["rows"]
    symbols = [row["symbol"] for row in rows]
    closes = [row["close"] for row in rows]

    # WHERE clause should be enforced based on the expression.
    assert all(close + 10 > 200 for close in closes)
    # With seeded data, that means close > 190; only MSFT and NVDA qualify.
    assert symbols == ["MSFT", "NVDA"]


# Joins and ambiguity


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


# Subqueries


def test_query_execute_select_from_prices_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT FROM prices"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTEDQUERYERROR"
    assert "select at least one column" in payload["error"]["message"]


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
    assert payload["error"]["message"] in (
        "Query must select at least one column or expression",
        "Unsupported subquery shape",
        "DataFusion execution error",
        "Query is not supported by the execution engine",
    )


def test_query_execute_in_subquery_returns_rows(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol
                FROM prices
                WHERE symbol IN (
                    SELECT symbol
                    FROM prices_nulls
                )
                ORDER BY symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol"]
    assert payload["row_count"] == 3
    assert payload["rows"] == [
        {"symbol": "AAPL"},
        {"symbol": "MSFT"},
        {"symbol": "NVDA"},
    ]


def test_query_execute_scalar_subquery_in_select(client: TestClient) -> None:
    # Expect the same global max(close) value repeated for each row.
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT
                  symbol,
                  close,
                  (SELECT MAX(close) FROM prices) AS max_close
                FROM prices
                ORDER BY symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "close", "max_close"]
    assert payload["row_count"] == 5
    rows = payload["rows"]

    # Symbols are sorted alphabetically.
    assert [row["symbol"] for row in rows] == ["AAPL", "AMZN", "GOOGL", "MSFT", "NVDA"]

    # max_close should be the same for every row, and equal to the max of close.
    max_close_values = {row["max_close"] for row in rows}
    assert len(max_close_values) == 1
    (max_close,) = max_close_values

    closes = [row["close"] for row in rows]
    assert max_close == max(closes)


def test_query_execute_scalar_subquery_in_where(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol, close
                FROM prices
                WHERE close > (
                  SELECT AVG(close) FROM prices
                )
                ORDER BY symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "close"]
    rows = payload["rows"]
    symbols = [row["symbol"] for row in rows]
    closes = [row["close"] for row in rows]

    # Manually compute the average to assert correctness.
    response_all = client.post(
        "/query/execute",
        json={"sql": "SELECT symbol, close FROM prices"},
    )
    assert response_all.status_code == 200
    all_closes = [row["close"] for row in response_all.json()["rows"]]
    avg_close = sum(all_closes) / len(all_closes)

    assert all(close > avg_close for close in closes)

    # With the seeded demo data, only NVDA is above the global average close.
    assert symbols == ["NVDA"]


# Set operations


def test_query_execute_union_all_returns_all_rows(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol
                FROM prices_nulls
                UNION ALL
                SELECT symbol
                FROM prices_nulls
                ORDER BY symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol"]
    assert payload["row_count"] == 6
    assert payload["rows"] == [
        {"symbol": "AAPL"},
        {"symbol": "AAPL"},
        {"symbol": "MSFT"},
        {"symbol": "MSFT"},
        {"symbol": "NVDA"},
        {"symbol": "NVDA"},
    ]


def test_query_execute_union_deduplicates_rows(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol
                FROM prices_nulls
                UNION
                SELECT symbol
                FROM prices_nulls
                ORDER BY symbol
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol"]
    assert payload["row_count"] == 3
    assert payload["rows"] == [
        {"symbol": "AAPL"},
        {"symbol": "MSFT"},
        {"symbol": "NVDA"},
    ]


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
    assert payload["error"]["message"] in (
        "UNION queries must have the same number of columns",
        "Query is not supported by the execution engine",
    )


# Engine delegation / grouped semantics edge cases


def test_query_execute_grouped_expression_is_engine_rejected(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT symbol, close + 1 AS close_plus
                FROM prices
                GROUP BY symbol
            """
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTEDQUERYERROR"
    assert payload["error"]["type"] == "UnsupportedQueryError"


def test_query_execute_aggregate_with_non_grouped_expression_relies_on_engine(
    client: TestClient,
) -> None:
    # No GROUP BY, but both aggregate and non-aggregate expression present.
    # We want DataFusion to decide semantics rather than product validator blocking it prematurely.
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT SUM(close) AS total_close, close + 1 AS close_plus
                FROM prices
            """
        },
    )

    # Depending on DataFusion version, this may either succeed or fail with a semantic error.
    # For now, we only assert that if it fails, we return a structured 400 with a known error code.
    if response.status_code == 200:
        payload = response.json()
        assert "total_close" in payload["columns"]
    else:
        assert response.status_code == 400
        payload = response.json()
        assert payload["error"]["code"] in (
            "UNSUPPORTEDQUERYERROR",
            "UNKNOWNCOLUMNERROR",
            "INVALIDQUERYSYNTAXERROR",
        )


# Error normalization and debug metadata


def test_query_execute_unknown_dataset_returns_normalized_error(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT symbol FROM missing_table LIMIT 5"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "UNKNOWNDATASETERROR"
    assert payload["error"]["message"] == "Unknown dataset 'missing_table'"


def test_query_execute_unknown_column_returns_normalized_error(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={"sql": "SELECT missing_column FROM prices"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "UNKNOWNCOLUMNERROR"
    assert "Unknown column 'missing_column'" in payload["error"]["message"]


def test_query_execute_debug_metadata_includes_timings_and_engine(client: TestClient) -> None:
    response = client.post(
        "/query/execute?debug=true",
        json={"sql": "SELECT symbol, close FROM prices LIMIT 2"},
    )

    assert response.status_code == 200
    payload = response.json()
    debug = payload.get("debug")
    assert debug is not None
    assert debug["stage"] == "execute"
    assert debug["engine"] == "datafusion"
    assert isinstance(debug["total_ms"], (int, float))


# Simple unknown-column / dataset tests (non-normalized-shape legacy ones)


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


# Window functions


def test_query_execute_window_row_number_over_partition(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT
                    symbol,
                    close,
                    ROW_NUMBER() OVER (
                        PARTITION BY symbol
                        ORDER BY close
                    ) AS row_number
                FROM prices
                ORDER BY symbol, close
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "close", "row_number"]
    rows = payload["rows"]
    assert rows, "expected at least one row"

    current_symbol = None
    current_row_number = 0

    for row in rows:
        symbol = row["symbol"]
        rn = row["row_number"]

        if symbol != current_symbol:
            current_symbol = symbol
            current_row_number = 1
        else:
            current_row_number += 1

        assert rn == current_row_number


def test_query_execute_window_lag_over_order_by(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT
                    symbol,
                    close,
                    LAG(close, 1) OVER (
                        PARTITION BY symbol
                        ORDER BY close
                    ) AS prev_close
                FROM prices
                ORDER BY symbol, close
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "close", "prev_close"]
    rows = payload["rows"]
    assert rows, "expected at least one row"

    # With one row per symbol in the demo dataset,
    # each partition has a single row, so prev_close should always be NULL.
    for row in rows:
        assert row["prev_close"] is None


def test_query_execute_window_sum_over_running_total(client: TestClient) -> None:
    response = client.post(
        "/query/execute",
        json={
            "sql": """
                SELECT
                    symbol,
                    close,
                    SUM(close) OVER (
                        PARTITION BY symbol
                        ORDER BY close
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS running_close
                FROM prices
                ORDER BY symbol, close
            """
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["columns"] == ["symbol", "close", "running_close"]
    rows = payload["rows"]
    assert rows, "expected at least one row"

    # Because there is a single row per symbol in the demo data,
    # running_close should equal close for every row.
    for row in rows:
        assert row["running_close"] == row["close"]