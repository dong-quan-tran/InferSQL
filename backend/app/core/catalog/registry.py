from __future__ import annotations

import pyarrow as pa


class DatasetNotFoundError(Exception):
    pass


class DatasetRegistry:
    def __init__(self) -> None:
        self._tables: dict[str, pa.Table] = {}

    def register_table(self, name: str, table: pa.Table) -> None:
        self._tables[name] = table

    def get_table(self, name: str) -> pa.Table:
        try:
            return self._tables[name]
        except KeyError as exc:
            raise DatasetNotFoundError(f"Unknown dataset '{name}'") from exc

    def get_schema(self, name: str) -> pa.Schema:
        return self.get_table(name).schema

    def describe_table(self, name: str) -> dict:
        schema = self.get_schema(name)
        return {
            "name": name,
            "columns": [field.name for field in schema],
            "types": {field.name: str(field.type) for field in schema},
        }

    def list_tables(self) -> list[str]:
        return sorted(self._tables.keys())