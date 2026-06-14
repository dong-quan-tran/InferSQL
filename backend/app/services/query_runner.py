from __future__ import annotations

import pyarrow as pa

from app.core.catalog.registry import DatasetRegistry
from app.core.engine.executor.service import QueryExecutor
from app.schemas.query import ExecutionResult


class QueryRunner:
    def __init__(self, dataset_registry: DatasetRegistry) -> None:
        self.query_executor = QueryExecutor(dataset_registry)

    def run_table(self, physical_plan) -> pa.Table:
        return self.query_executor.execute(physical_plan)

    def run(self, physical_plan, limit: int | None = None, offset: int = 0) -> ExecutionResult:
        result = self.run_table(physical_plan)

        total_rows = result.num_rows
        safe_offset = min(offset, total_rows)
        if limit is None:
            safe_limit = total_rows - safe_offset
        else:
            safe_limit = max(0, min(limit, total_rows - safe_offset))

        sliced = result.slice(safe_offset, safe_limit)

        return ExecutionResult(
            row_count=sliced.num_rows,
            columns=list(sliced.column_names),
            rows=sliced.to_pylist(),
        )