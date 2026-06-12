# app/services/query_compiler.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.engine.parser import QueryParser
from app.core.engine.physical_planner import PhysicalPlanner


@dataclass
class QueryMetadata:
    query_type: str
    tables: list[str]
    columns: list[str]
    has_where: bool
    has_group_by: bool
    has_order_by: bool
    has_limit: bool


@dataclass
class CompiledQuery:
    sql: str
    normalized_sql: str
    query_metadata: QueryMetadata
    logical_plan: Any
    physical_plan: Any


class QueryCompiler:
    def __init__(self) -> None:
        self.query_parser = QueryParser()
        self.physical_planner = PhysicalPlanner()

    def compile(self, sql: str) -> CompiledQuery:
        normalized_sql = " ".join(sql.strip().split())

        expression = self.query_parser.parse(normalized_sql)
        self.query_parser.validate_select_only(expression)

        summary = self.query_parser.summarize(normalized_sql)
        logical_plan = self.query_parser.build_logical_plan(normalized_sql)
        physical_plan = self.physical_planner.build(logical_plan)

        query_metadata = QueryMetadata(
            query_type=summary["query_type"],
            tables=summary["tables"],
            columns=summary["columns"],
            has_where=summary["has_where"],
            has_group_by=summary["has_group_by"],
            has_order_by=summary["has_order_by"],
            has_limit=summary["has_limit"],
        )

        return CompiledQuery(
            sql=sql,
            normalized_sql=normalized_sql,
            query_metadata=query_metadata,
            logical_plan=logical_plan,
            physical_plan=physical_plan,
        )