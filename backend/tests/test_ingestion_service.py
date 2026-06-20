from __future__ import annotations

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app.core.catalog.registry import DatasetRegistry
from app.services.ingestion_service import (
    DatasetIngestionService,
    UnsupportedDatasetFormatError,
)


def test_load_csv_registers_table_with_metadata(tmp_path) -> None:
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text(
        "symbol,close\nAAPL,189.12\nMSFT,425.27\n",
        encoding="utf-8",
    )

    registry = DatasetRegistry()
    service = DatasetIngestionService(registry)

    result = service.load_file(
        name="prices",
        path=str(csv_path),
        description="Daily security prices from CSV.",
    )

    assert result["name"] == "prices"
    assert result["row_count"] == 2
    assert result["source_path"] == str(csv_path)
    assert result["loaded_at"] is not None
    assert result["description"] == "Daily security prices from CSV."

    table = registry.get_table("prices")
    assert table.num_rows == 2
    assert table.column_names == ["symbol", "close"]


def test_load_parquet_registers_table_with_metadata(tmp_path) -> None:
    parquet_path = tmp_path / "fundamentals.parquet"
    table = pa.table(
        {
            "symbol": ["AAPL", "MSFT"],
            "market_cap": [3.1, 3.0],
        }
    )
    pq.write_table(table, parquet_path)

    registry = DatasetRegistry()
    service = DatasetIngestionService(registry)

    result = service.load_file(
        name="fundamentals",
        path=str(parquet_path),
        description="Company fundamentals from Parquet.",
    )

    assert result["name"] == "fundamentals"
    assert result["row_count"] == 2
    assert result["source_path"] == str(parquet_path)
    assert result["loaded_at"] is not None
    assert result["description"] == "Company fundamentals from Parquet."

    loaded = registry.get_table("fundamentals")
    assert loaded.num_rows == 2
    assert loaded.column_names == ["symbol", "market_cap"]


def test_load_file_rejects_unsupported_extension(tmp_path) -> None:
    json_path = tmp_path / "prices.json"
    json_path.write_text('{"hello": "world"}', encoding="utf-8")

    registry = DatasetRegistry()
    service = DatasetIngestionService(registry)

    with pytest.raises(UnsupportedDatasetFormatError):
        service.load_file(name="prices", path=str(json_path))