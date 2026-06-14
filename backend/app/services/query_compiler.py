from __future__ import annotations

from dataclasses import dataclass

from app.core.engine.parser import QueryParser
from app.core.engine.physical_planner import PhysicalPlanner
from app.schemas.query import PlanNode


@dataclass
class CompiledQuery:
    normalized_sql: str
    logical_plan: PlanNode
    physical_plan: PlanNode


class QueryCompiler:
    def __init__(self) -> None:
        self.query_parser = QueryParser()
        self.physical_planner = PhysicalPlanner()

    def compile(self, sql: str) -> CompiledQuery:
        normalized_sql = " ".join(sql.strip().split())

        expression = self.query_parser.parse(normalized_sql)
        self.query_parser.validate_select_only(expression)

        logical_plan = self.query_parser.build_logical_plan(normalized_sql)
        physical_plan = self.physical_planner.build(logical_plan)

        return CompiledQuery(
            normalized_sql=normalized_sql,
            logical_plan=logical_plan,
            physical_plan=physical_plan,
        )