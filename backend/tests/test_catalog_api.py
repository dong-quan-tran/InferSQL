from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from fastapi.testclient import TestClient

from app.main import app


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



client = TestClient(app)


def test_ingest_csv_registers_dataset(tmp_path: Path) -> None:
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


def test_ingest_parquet_registers_dataset(tmp_path: Path) -> None:
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


def test_upload_csv_registers_dataset(tmp_path: Path) -> None:
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


def test_upload_parquet_registers_dataset(tmp_path: Path) -> None:
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