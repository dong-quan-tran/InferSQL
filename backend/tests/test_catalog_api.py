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