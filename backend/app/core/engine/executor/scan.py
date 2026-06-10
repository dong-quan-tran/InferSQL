# app/core/engine/executor/scan.py
from __future__ import annotations

import pyarrow as pa

from app.core.catalog import DatasetRegistry


class TableScanOperator:
    def __init__(self, registry: DatasetRegistry) -> None:
        self.registry = registry

    def execute(self, table_name: str) -> pa.Table:
        return self.registry.get_table(table_name)