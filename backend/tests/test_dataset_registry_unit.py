import pyarrow as pa
import pytest

from app.core.catalog.registry import (
    DatasetColumnMetadata,
    DatasetMetadata,
    DatasetNotFoundError,
    DatasetRegistry,
)


def test_register_and_get_table() -> None:
    registry = DatasetRegistry()
    table = pa.table({"symbol": ["AAPL"], "close": [189.12]})

    registry.register_table("prices", table)

    result = registry.get_table("prices")
    assert result.equals(table)


def test_get_schema_and_describe_table() -> None:
    registry = DatasetRegistry()
    table = pa.table({"symbol": ["AAPL"], "close": [189.12]})
    registry.register_table("prices", table)

    schema = registry.get_schema("prices")
    description = registry.describe_table("prices")

    assert schema.names == ["symbol", "close"]
    assert description["name"] == "prices"
    assert description["description"] is None
    assert description["columns"] == ["symbol", "close"]
    assert description["types"] == {
        "symbol": "string",
        "close": "double",
    }
    assert description["row_count"] == 1
    assert description["column_descriptions"] == {}
    assert description["column_aliases"] == {}
    assert description["column_samples"] == {}


def test_get_missing_table_raises() -> None:
    registry = DatasetRegistry()

    with pytest.raises(DatasetNotFoundError, match="Unknown dataset 'missing'"):
        registry.get_table("missing")


def test_describe_table_includes_metadata_and_samples() -> None:
    registry = DatasetRegistry()
    table = pa.table(
        {
            "symbol": ["AAPL", "MSFT", "AAPL"],
            "close": [189.12, 425.27, 189.12],
        }
    )
    registry.register_table(
        "prices",
        table,
        metadata=DatasetMetadata(
            description="Daily security prices.",
            columns={
                "symbol": DatasetColumnMetadata(description="Ticker symbol."),
                "close": DatasetColumnMetadata(description="Closing price."),
            },
        ),
    )

    description = registry.describe_table(
        "prices",
        include_samples=True,
        sample_limit=2,
    )

    assert description["description"] == "Daily security prices."
    assert description["row_count"] == 3
    assert description["column_descriptions"] == {
        "symbol": "Ticker symbol.",
        "close": "Closing price.",
    }
    assert description["column_samples"]["symbol"] == ["AAPL", "MSFT"]
    assert description["column_samples"]["close"] == [189.12, 425.27]