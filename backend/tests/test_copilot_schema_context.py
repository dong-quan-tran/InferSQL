from __future__ import annotations

import pyarrow as pa

from app.core.catalog.registry import (
    DatasetColumnMetadata,
    DatasetMetadata,
    DatasetRegistry,
)
from app.services.copilot_schema_context import CopilotSchemaContextBuilder


def test_schema_context_builder_includes_table_and_columns() -> None:
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
            description="Daily security prices for a demo stock universe.",
            columns={
                "symbol": DatasetColumnMetadata(
                    description="Ticker symbol such as AAPL or MSFT."
                ),
                "close": DatasetColumnMetadata(
                    description="Closing price for the security."
                ),
            },
        ),
    )

    builder = CopilotSchemaContextBuilder(registry)
    context = builder.build()

    assert "Table: prices" in context
    assert "Description: Daily security prices for a demo stock universe." in context
    assert "- symbol:" in context
    assert "- close:" in context
    assert "Ticker symbol such as AAPL or MSFT." in context
    assert "Closing price for the security." in context


def test_schema_context_builder_includes_sample_values_by_default() -> None:
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
            description="Daily security prices.",
            columns={
                "symbol": DatasetColumnMetadata(description="Ticker symbol."),
                "close": DatasetColumnMetadata(description="Closing price."),
            },
        ),
    )

    builder = CopilotSchemaContextBuilder(registry)
    context = builder.build()

    assert "examples:" in context
    assert "'AAPL'" in context or '"AAPL"' in context


def test_schema_context_builder_can_disable_samples() -> None:
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
            description="Daily security prices.",
            columns={
                "symbol": DatasetColumnMetadata(description="Ticker symbol."),
                "close": DatasetColumnMetadata(description="Closing price."),
            },
        ),
    )

    builder = CopilotSchemaContextBuilder(
        registry,
        include_samples=False,
    )
    context = builder.build()

    assert "examples:" not in context


def test_schema_context_builder_can_limit_to_selected_tables() -> None:
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
            description="Daily security prices.",
            columns={
                "symbol": DatasetColumnMetadata(description="Ticker symbol."),
                "close": DatasetColumnMetadata(description="Closing price."),
            },
        ),
    )
    registry.register_table(
        "fundamentals",
        pa.table(
            {
                "symbol": ["AAPL", "MSFT"],
                "market_cap": [3.1, 3.0],
            }
        ),
        metadata=DatasetMetadata(
            description="Company fundamentals.",
            columns={
                "symbol": DatasetColumnMetadata(description="Ticker symbol."),
                "market_cap": DatasetColumnMetadata(description="Market capitalization."),
            },
        ),
    )

    builder = CopilotSchemaContextBuilder(registry)
    context = builder.build(table_names=["prices"])

    assert "Table: prices" in context
    assert "Table: fundamentals" not in context

def test_schema_context_builder_includes_alias_hints() -> None:
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
            description="Daily security prices for a demo stock universe.",
            columns={
                "symbol": DatasetColumnMetadata(
                    description="Ticker symbol such as AAPL or MSFT."
                ),
                "close": DatasetColumnMetadata(
                    description="Closing price for the security."
                ),
            },
        ),
    )

    builder = CopilotSchemaContextBuilder(registry)
    context = builder.build()

    assert "aliases:" in context
    assert "ticker" in context
    assert "stock symbol" in context
    assert "close price" in context
    assert "closing price" in context