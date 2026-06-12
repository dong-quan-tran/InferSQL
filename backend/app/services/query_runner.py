# app/services/query_runner.py
from __future__ import annotations

from app.core.catalog import DatasetRegistry
from app.core.engine.executor.service import QueryExecutor


class QueryRunner:
    def __init__(self, dataset_registry: DatasetRegistry) -> None:
        self.query_executor = QueryExecutor(dataset_registry)

    def run(self, physical_plan):
        return self.query_executor.execute(physical_plan)