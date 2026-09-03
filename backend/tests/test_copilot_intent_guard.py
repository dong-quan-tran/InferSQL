import pyarrow as pa

from app.core.catalog.registry import (
    DatasetColumnMetadata,
    DatasetMetadata,
    DatasetRegistry,
)
from app.services.copilot_intent_guard import CopilotIntentGuard


def build_registry() -> DatasetRegistry:
    registry = DatasetRegistry()

    registry.register_table(
        "prices",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT"],
                "close": [189.12, 425.27],
            }
        ),
        metadata=DatasetMetadata(
            description="Daily security prices for a small demo universe of stocks.",
            columns={
                "symbol": DatasetColumnMetadata(
                    description="Ticker symbol such as AAPL or MSFT."
                ),
                "close": DatasetColumnMetadata(
                    description="Closing price for the security on the row."
                ),
            },
        ),
    )

    registry.register_table(
        "fundamentals",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT"],
                "market_cap": [2900000000000, 3200000000000],
            }
        ),
        metadata=DatasetMetadata(
            description="Basic company fundamentals for a subset of securities.",
            columns={
                "symbol": DatasetColumnMetadata(
                    description="Ticker symbol shared with prices."
                ),
                "market_cap": DatasetColumnMetadata(
                    description="Approximate market capitalization in USD."
                ),
            },
        ),
    )

    return registry


def test_allows_approved_ticker_alias() -> None:
    decision = CopilotIntentGuard(build_registry()).evaluate("Show ticker and close")

    assert decision.allowed is True
    assert decision.errors == []
    assert decision.matched_aliases["ticker"] == "symbol"


def test_allows_approved_stock_price_alias() -> None:
    decision = CopilotIntentGuard(build_registry()).evaluate(
        "Show stock price for AAPL"
    )

    assert decision.allowed is True
    assert decision.errors == []
    assert decision.matched_aliases["stock price"] == "close"


def test_refuses_unsupported_volume() -> None:
    decision = CopilotIntentGuard(build_registry()).evaluate("Show volume from trades")

    assert decision.allowed is False
    assert decision.clarification_question is None
    assert "volume" in decision.unsupported_terms
    assert "trade" in decision.unsupported_terms
    assert "does not support" in decision.errors[0]


def test_refuses_unsupported_sector() -> None:
    decision = CopilotIntentGuard(build_registry()).evaluate(
        "Show sector for each stock"
    )

    assert decision.allowed is False
    assert decision.clarification_question is None
    assert decision.unsupported_terms == ["sector"]


def test_requests_clarification_for_latest_without_time_column() -> None:
    decision = CopilotIntentGuard(build_registry()).evaluate("Show the latest stock")

    assert decision.allowed is False
    assert decision.ambiguous_terms == ["latest"]
    assert decision.clarification_question is not None
    assert "date or timestamp" in decision.clarification_question


def test_requests_clarification_for_best_performing_without_metric() -> None:
    decision = CopilotIntentGuard(build_registry()).evaluate(
        "Show the best performing stock"
    )

    assert decision.allowed is False
    assert decision.ambiguous_terms == ["best performing"]
    assert decision.clarification_question is not None
    assert "performance" in decision.clarification_question.lower()


def test_requests_clarification_for_underspecified_join() -> None:
    decision = CopilotIntentGuard(build_registry()).evaluate(
        "Join prices with fundamentals"
    )

    assert decision.allowed is False
    assert decision.ambiguous_terms == ["join"]
    assert decision.clarification_question is not None
    assert "which columns" in decision.clarification_question.lower()

def test_blocks_write_intent_requests() -> None:
    guard = CopilotIntentGuard(build_registry())

    requests = {
        "Delete all rows from prices": "delete",
        "Remove MSFT from prices": "remove",
        "Update the closing price for AAPL": "update",
        "Insert a new stock into prices": "insert",
        "Drop the fundamentals table": "drop",
        "Create a new prices table": "create",
        "Truncate prices": "truncate",
    }

    for question, expected_intent in requests.items():
        decision = guard.evaluate(question)

        assert decision.allowed is False, question
        assert decision.clarification_question is None, question
        assert expected_intent in decision.unsupported_terms, question
        assert "read-only analytical queries" in decision.errors[0], question

