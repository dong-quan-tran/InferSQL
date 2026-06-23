from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from fastapi.testclient import TestClient


def test_list_datasets_returns_catalog_metadata(client: TestClient) -> None:
    response = client.get("/catalog/datasets")

    assert response.status_code == 200

    data = response.json()
    assert "datasets" in data
    assert len(data["datasets"]) >= 1

    prices = next(item for item in data["datasets"] if item["name"] == "prices")
    assert prices["description"] is not None
    assert prices["row_count"] >= 1

    columns = {column["name"]: column for column in prices["columns"]}
    assert "symbol" in columns
    assert "close" in columns
    assert columns["symbol"]["type"]
    assert columns["close"]["type"]


def test_get_dataset_returns_single_dataset_metadata(client: TestClient) -> None:
    response = client.get("/catalog/datasets/prices")

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "prices"
    assert data["row_count"] >= 1
    assert [column["name"] for column in data["columns"]] == ["symbol", "close"]


def test_get_dataset_returns_404_for_unknown_dataset(client: TestClient) -> None:
    response = client.get("/catalog/datasets/missing_table")

    assert response.status_code == 404

    data = response.json()
    assert data["error"]["type"] == "NotFoundError"
    assert data["error"]["message"] == "Unknown dataset 'missing_table'"


def test_ingest_csv_registers_dataset(client: TestClient, tmp_path: Path) -> None:
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text(
        "symbol,close\nAAPL,189.12\nMSFT,425.27\n",
        encoding="utf-8",
    )

    response = client.post(
        "/catalog/ingest",
        json={
            "name": "prices_csv",
            "path": str(csv_path),
            "description": "CSV prices dataset",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "prices_csv"
    assert data["row_count"] == 2
    assert "loaded_at" in data
    assert data["source_path"].endswith("prices.csv")
    assert data["description"] == "CSV prices dataset"


def test_ingest_parquet_registers_dataset(client: TestClient, tmp_path: Path) -> None:
    parquet_path = tmp_path / "fundamentals.parquet"
    table = pa.table(
        {
            "symbol": ["AAPL", "MSFT"],
            "market_cap": [3.1, 3.0],
        }
    )
    pq.write_table(table, parquet_path)

    response = client.post(
        "/catalog/ingest",
        json={
            "name": "fundamentals_parquet",
            "path": str(parquet_path),
            "description": "Parquet fundamentals dataset",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "fundamentals_parquet"
    assert data["row_count"] == 2
    assert "loaded_at" in data
    assert data["source_path"].endswith("fundamentals.parquet")
    assert data["description"] == "Parquet fundamentals dataset"


def test_upload_csv_registers_dataset(client: TestClient) -> None:
    response = client.post(
        "/catalog/upload",
        data={
            "name": "uploaded_prices",
            "description": "Uploaded CSV dataset",
        },
        files={
            "file": (
                "prices.csv",
                b"symbol,close\nAAPL,189.12\nMSFT,425.27\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "uploaded_prices"
    assert data["row_count"] == 2
    assert data["description"] == "Uploaded CSV dataset"
    assert data["source_path"] is not None


def test_upload_parquet_registers_dataset(client: TestClient, tmp_path: Path) -> None:
    parquet_path = tmp_path / "upload.parquet"
    table = pa.table(
        {
            "symbol": ["AAPL", "MSFT"],
            "market_cap": [3.1, 3.0],
        }
    )
    pq.write_table(table, parquet_path)

    response = client.post(
        "/catalog/upload",
        data={
            "name": "uploaded_fundamentals",
            "description": "Uploaded Parquet dataset",
        },
        files={
            "file": (
                "fundamentals.parquet",
                parquet_path.read_bytes(),
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "uploaded_fundamentals"
    assert data["row_count"] == 2
    assert data["description"] == "Uploaded Parquet dataset"
    assert data["source_path"] is not None


def test_ingest_rejects_duplicate_dataset_name_by_default(
    client: TestClient, tmp_path: Path
) -> None:
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text(
        "symbol,close\nAAPL,189.12\nMSFT,425.27\n",
        encoding="utf-8",
    )

    first = client.post(
        "/catalog/ingest",
        json={
            "name": "duplicate_prices",
            "path": str(csv_path),
            "description": "First load",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/catalog/ingest",
        json={
            "name": "duplicate_prices",
            "path": str(csv_path),
            "description": "Second load",
        },
    )

    assert second.status_code == 409
    data = second.json()
    assert data["error"]["type"] == "ConflictError"
    assert data["error"]["message"] == "Dataset 'duplicate_prices' already exists"


def test_ingest_allows_overwrite_when_requested(
    client: TestClient, tmp_path: Path
) -> None:
    first_csv = tmp_path / "first.csv"
    first_csv.write_text(
        "symbol,close\nAAPL,189.12\nMSFT,425.27\n",
        encoding="utf-8",
    )

    second_csv = tmp_path / "second.csv"
    second_csv.write_text(
        "symbol,close\nNVDA,1210.54\n",
        encoding="utf-8",
    )

    first = client.post(
        "/catalog/ingest",
        json={
            "name": "overwrite_prices",
            "path": str(first_csv),
            "description": "Initial version",
        },
    )
    assert first.status_code == 200
    assert first.json()["row_count"] == 2

    second = client.post(
        "/catalog/ingest?overwrite=true",
        json={
            "name": "overwrite_prices",
            "path": str(second_csv),
            "description": "Replacement version",
        },
    )

    assert second.status_code == 200
    data = second.json()
    assert data["name"] == "overwrite_prices"
    assert data["row_count"] == 1
    assert data["description"] == "Replacement version"


def test_ingested_csv_dataset_is_queryable_via_execute(
    client: TestClient, tmp_path: Path
) -> None:
    csv_path = tmp_path / "queryable_prices.csv"
    csv_path.write_text(
        "symbol,close\nAAPL,189.12\nMSFT,425.27\n",
        encoding="utf-8",
    )

    ingest_response = client.post(
        "/catalog/ingest",
        json={
            "name": "queryable_prices",
            "path": str(csv_path),
            "description": "Queryable CSV dataset",
        },
    )
    assert ingest_response.status_code == 200

    query_response = client.post(
        "/query/execute",
        json={"sql": "SELECT symbol, close FROM queryable_prices ORDER BY symbol"},
    )
    assert query_response.status_code == 200

    payload = query_response.json()
    assert payload["columns"] == ["symbol", "close"]
    assert payload["row_count"] == 2
    assert payload["rows"] == [
        {"symbol": "AAPL", "close": 189.12},
        {"symbol": "MSFT", "close": 425.27},
    ]


def test_ingest_rejects_missing_file_path(
    client: TestClient, tmp_path: Path
) -> None:
    missing_path = tmp_path / "missing.csv"

    response = client.post(
        "/catalog/ingest",
        json={
            "name": "missing_prices",
            "path": str(missing_path),
            "description": "Missing file",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["type"] == "ValidationError"


def test_ingest_rejects_malformed_csv(client: TestClient, tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_bytes(b"\x00\x01\x02not-a-real-csv")

    response = client.post(
        "/catalog/ingest",
        json={
            "name": "bad_csv",
            "path": str(csv_path),
            "description": "Bad CSV",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["type"] == "ValidationError"


def test_ingest_rejects_invalid_parquet(client: TestClient, tmp_path: Path) -> None:
    parquet_path = tmp_path / "bad.parquet"
    parquet_path.write_text("not a parquet file", encoding="utf-8")

    response = client.post(
        "/catalog/ingest",
        json={
            "name": "bad_parquet",
            "path": str(parquet_path),
            "description": "Bad parquet",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["type"] == "ValidationError"