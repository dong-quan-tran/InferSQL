# app/core/engine/executor/limit.py
from __future__ import annotations

import pyarrow as pa


class LimitOperator:
    def execute(self, table: pa.Table, limit: int) -> pa.Table:
        return table.slice(0, limit)