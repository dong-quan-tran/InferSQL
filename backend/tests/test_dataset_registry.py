# tests/test_dataset_registry.py
import pyarrow as pa

from app.core.catalog import DatasetRegistry


def test_register_and_get_table():
    registry = DatasetRegistry()
    table = pa.table({"a": [1, 2, 3]})

    registry.register_table("demo", table)

    fetched = registry.get_table("demo")
    assert fetched.num_rows == 3
    assert fetched.column_names == ["a"]