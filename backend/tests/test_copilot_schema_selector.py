from __future__ import annotations

import pyarrow as pa

from app.core.catalog.registry import (
    DatasetColumnMetadata,
    DatasetMetadata,
    DatasetRegistry,
)
from app.services.copilot_schema_selector import CopilotSchemaSelector


def build_registry() -> DatasetRegistry:
    registry = DatasetRegistry()

    registry.register_table(
        "prices",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT", "NVDA"],
                "close": [189.12, 425.27, 1210.54],
            }
        ),
        metadata=DatasetMetadata(
            description="Daily stock prices for a demo universe.",
            columns={
                "symbol": DatasetColumnMetadata(description="Ticker symbol."),
                "close": DatasetColumnMetadata(description="Closing stock price."),
            },
        ),
    )

    registry.register_table(
        "fundamentals",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT", "NVDA"],
                "market_cap": [3.1, 3.0, 2.8],
            }
        ),
        metadata=DatasetMetadata(
            description="Company fundamentals and valuation metrics.",
            columns={
                "symbol": DatasetColumnMetadata(description="Ticker symbol."),
                "market_cap": DatasetColumnMetadata(description="Market capitalization."),
            },
        ),
    )

    return registry


def test_select_tables_prefers_prices_for_price_question() -> None:
    registry = build_registry()
    selector = CopilotSchemaSelector(registry)

    selected = selector.select_tables("Show stock prices for AAPL")

    assert selected[0] == "prices"


def test_select_tables_prefers_fundamentals_for_market_cap_question() -> None:
    registry = build_registry()
    selector = CopilotSchemaSelector(registry)

    selected = selector.select_tables("Show market cap for MSFT")

    assert selected[0] == "fundamentals"


def test_select_tables_falls_back_to_all_tables_when_no_overlap() -> None:
    registry = build_registry()
    selector = CopilotSchemaSelector(registry)

    selected = selector.select_tables("Completely unrelated phrasing")

    assert selected == ["fundamentals", "prices"]