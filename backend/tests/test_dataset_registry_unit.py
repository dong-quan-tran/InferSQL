import pyarrow as pa
import pytest

from app.core.catalog.registry import DatasetNotFoundError, DatasetRegistry


def test_register_get_and_list_tables() -> None:
    registry = DatasetRegistry()
    table = pa.table({"symbol": ["AAPL"], "close": [189.12]})

    registry.register_table("prices", table)

    assert registry.get_table("prices") == table
    assert registry.get("prices") == table
    assert registry.list_tables() == ["prices"]


def test_get_table_raises_for_unknown_dataset() -> None:
    registry = DatasetRegistry()

    with pytest.raises(DatasetNotFoundError, match="Unknown dataset 'missing'"):
        registry.get_table("missing")