# app/core/catalog/registry.py
from __future__ import annotations

from dataclasses import dataclass, field

import pyarrow as pa


class DatasetNotFoundError(KeyError):
    pass


@dataclass
class DatasetRegistry:
    _tables: dict[str, pa.Table] = field(default_factory=dict)

    def register_table(self, name: str, table: pa.Table) -> None:
        self._tables[name.lower()] = table

    def get_table(self, name: str) -> pa.Table:
        key = name.lower()
        if key not in self._tables:
            raise DatasetNotFoundError(f"Dataset '{name}' is not registered")
        return self._tables[key]

    def list_tables(self) -> list[str]:
        return sorted(self._tables.keys())