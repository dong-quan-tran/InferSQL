from fastapi.testclient import TestClient


def test_registry_is_source_of_truth_for_catalog_list(client: TestClient) -> None:
    registry = client.app.state.dataset_registry

    response = client.get("/catalog/datasets")
    assert response.status_code == 200

    payload = response.json()
    datasets = {item["name"]: item for item in payload["datasets"]}

    for table_name in registry.list_tables():
        described = registry.describe_table(table_name, include_samples=False)
        assert table_name in datasets

        api_dataset = datasets[table_name]
        assert api_dataset["name"] == described["name"]
        assert api_dataset["description"] == described["description"]
        assert api_dataset["row_count"] == described["row_count"]
        assert api_dataset["source_path"] == described["source_path"]
        assert api_dataset["loaded_at"] == described["loaded_at"]

        api_columns = {column["name"]: column for column in api_dataset["columns"]}
        assert set(api_columns) == set(described["columns"])

        for column_name in described["columns"]:
            assert api_columns[column_name]["type"] == described["types"][column_name]
            assert api_columns[column_name]["description"] == described["column_descriptions"].get(
                column_name
            )


def test_registry_is_source_of_truth_for_catalog_detail(client: TestClient) -> None:
    registry = client.app.state.dataset_registry

    described = registry.describe_table("prices", include_samples=True, sample_limit=3)

    response = client.get("/catalog/datasets/prices")
    assert response.status_code == 200

    payload = response.json()
    assert payload["name"] == described["name"]
    assert payload["description"] == described["description"]
    assert payload["row_count"] == described["row_count"]
    assert payload["source_path"] == described["source_path"]
    assert payload["loaded_at"] == described["loaded_at"]
    assert payload["column_aliases"] == described["column_aliases"]
    assert payload["column_samples"] == described["column_samples"]

    api_columns = {column["name"]: column for column in payload["columns"]}
    assert set(api_columns) == set(described["columns"])

    for column_name in described["columns"]:
        assert api_columns[column_name]["type"] == described["types"][column_name]
        assert api_columns[column_name]["description"] == described["column_descriptions"].get(
            column_name
        )


def test_registry_schema_matches_query_execution_columns(client: TestClient) -> None:
    registry = client.app.state.dataset_registry
    schema = registry.get_schema("prices")

    response = client.post(
        "/query/execute",
        json={"sql": "SELECT * FROM prices LIMIT 1"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["columns"] == [field.name for field in schema]
    assert payload["row_count"] == 1


def test_registry_types_match_catalog_detail(client: TestClient) -> None:
    registry = client.app.state.dataset_registry
    schema = registry.get_schema("prices")

    response = client.get("/catalog/datasets/prices")
    assert response.status_code == 200

    payload = response.json()
    api_types = {column["name"]: column["type"] for column in payload["columns"]}
    registry_types = {field.name: str(field.type) for field in schema}

    assert api_types == registry_types