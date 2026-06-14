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

    def get(self, name: str) -> pa.Table:
        return self.get_table(name)