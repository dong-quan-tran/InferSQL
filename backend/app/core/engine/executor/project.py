# app/core/engine/executor/project.py
from __future__ import annotations

import pyarrow as pa


class ProjectOperator:
    def execute(self, table: pa.Table, columns: list[str]) -> pa.Table:
        if columns == ["*"]:
            return table
        return table.select(columns)