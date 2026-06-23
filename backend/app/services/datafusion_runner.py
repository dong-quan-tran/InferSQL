from __future__ import annotations

from typing import Any

import pyarrow as pa
from datafusion import SessionContext

from app.core.catalog.registry import DatasetRegistry
from app.schemas.query import ExecutionResult


class DataFusionRunner:
    def __init__(self, dataset_registry: DatasetRegistry) -> None:
        self.dataset_registry = dataset_registry

    def _build_context(self) -> SessionContext:
        ctx = SessionContext()

        for table_name in self.dataset_registry.list_tables():
            table = self.dataset_registry.get_table(table_name)
            ctx.register_record_batches(table_name, [table.to_batches()])

        return ctx

    def _collect_table(self, sql: str) -> pa.Table:
        ctx = self._build_context()
        dataframe = ctx.sql(sql)
        batches = dataframe.collect()

        if not batches:
            return pa.table({})

        return pa.Table.from_batches(batches)

    def run_table(self, sql: str) -> pa.Table:
        return self._collect_table(sql)

    def explain(self, sql: str, verbose: bool = True) -> list[dict[str, Any]]:
        explain_sql = f"EXPLAIN {'VERBOSE ' if verbose else ''}{sql}"
        table = self._collect_table(explain_sql)

        if table.num_rows == 0:
            return []

        return table.to_pylist()

    def run(
        self,
        sql: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> ExecutionResult:
        result = self.run_table(sql)

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