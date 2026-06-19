from sqlglot import exp
import pytest

from app.core.engine.parser import QueryParser
from app.core.exceptions import InvalidQuerySyntaxError, UnsupportedQueryError


def test_parse_returns_expression() -> None:
    parser = QueryParser()

    expression = parser.parse("SELECT symbol, close FROM prices LIMIT 5")

    assert isinstance(expression, exp.Select)


def test_parse_raises_for_invalid_sql() -> None:
    parser = QueryParser()

    with pytest.raises(InvalidQuerySyntaxError, match="Invalid SQL syntax"):
        parser.parse("SELECT FROM")


def test_validate_select_only_accepts_select() -> None:
    parser = QueryParser()
    expression = parser.parse("SELECT symbol FROM prices")

    parser.validate_select_only(expression)


def test_validate_select_only_rejects_non_select() -> None:
    parser = QueryParser()
    expression = parser.parse("DELETE FROM prices")

    with pytest.raises(
        UnsupportedQueryError,
        match="Only SELECT queries are supported right now",
    ):
        parser.validate_select_only(expression)


def test_summarize_extracts_query_metadata() -> None:
    parser = QueryParser()

    summary = parser.summarize(
        "SELECT symbol, close FROM prices WHERE close > 100 ORDER BY close LIMIT 2"
    )

    assert summary == {
        "query_type": "SELECT",
        "tables": ["prices"],
        "columns": ["close", "symbol"],
        "has_where": True,
        "has_group_by": False,
        "has_order_by": True,
        "has_limit": True,
    }


def test_build_logical_plan_shapes_nodes() -> None:
    parser = QueryParser()

    plan = parser.build_logical_plan(
        "SELECT symbol, close FROM prices WHERE close > 100 LIMIT 2"
    )

    assert plan.node_type == "Limit"
    assert plan.details == {"count": 2}

    project = plan.children[0]
    assert project.node_type == "Project"
    assert project.details["columns"] == ["symbol", "close"]
    assert project.details["projections"] == [
        {"source": "symbol", "output": "symbol"},
        {"source": "close", "output": "close"},
    ]

    filter_node = project.children[0]
    assert filter_node.node_type == "Filter"
    assert filter_node.details["predicate"]["column"] == "close"
    assert filter_node.details["predicate"]["operator"] == ">"
    assert filter_node.details["predicate"]["value"] == 100

    scan = filter_node.children[0]
    assert scan.node_type == "Scan"
    assert scan.details == {"table": "prices"}