from __future__ import annotations

import pyarrow as pa

from app.core.catalog.registry import DatasetRegistry
from app.core.engine.parser import QueryParser
from app.core.settings import get_settings
from app.services.query_compiler import QueryCompiler
from app.services.query_runner import QueryRunner


class QueryService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.dataset_registry = DatasetRegistry()
        self.query_parser = QueryParser()
        self.query_compiler = QueryCompiler()
        self.query_runner = QueryRunner(self.dataset_registry)

        if self.settings.seed_demo_data:
            self._seed_demo_data()

    def validate(self, sql: str, request_id: str | None = None, debug: bool = False):
        normalized_sql = " ".join(sql.strip().split())
        expression = self.query_parser.parse(normalized_sql)
        summary = self.query_parser.summarize(normalized_sql)

        errors: list[str] = []
        is_valid = True

        try:
            self.query_parser.validate_select_only(expression)
        except ValueError as exc:
            is_valid = False
            errors.append(str(exc))

        response = {
            "sql": sql,
            "normalized_sql": normalized_sql,
            "is_valid": is_valid,
            "query_type": summary["query_type"],
            "errors": errors,
            "tables": summary["tables"],
            "columns": summary["columns"],
            "has_where": summary["has_where"],
            "has_group_by": summary["has_group_by"],
            "has_order_by": summary["has_order_by"],
            "has_limit": summary["has_limit"],
        }

        if debug:
            response["debug"] = {
                "request_id": request_id,
                "total_ms": 0.0,
            }

        return response

    def plan(self, sql: str, request_id: str | None = None, debug: bool = False):
        self._validate_referenced_columns(sql)
        compiled = self.query_compiler.compile(sql)

        response = {
            "sql": sql,
            "normalized_sql": compiled.normalized_sql,
            "engine": "infersql-planner",
            "steps": [
                "parse_sql",
                "extract_query_metadata",
                "validate_sql",
                "build_logical_plan",
                "build_physical_plan",
            ],
            "summary": self.query_parser.summarize(sql),
            "logical_plan": compiled.logical_plan.model_dump(),
            "physical_plan": compiled.physical_plan.model_dump(),
        }

        if debug:
            response["debug"] = {"request_id": request_id}

        return response
    
    def execute(
        self,
        sql: str,
        request_id: str | None = None,
        debug: bool = False,
        limit: int = 100,
        offset: int = 0,
    ):
        self._validate_referenced_columns(sql)
        compiled = self.query_compiler.compile(sql)
        result = self.query_runner.run(compiled.physical_plan)

        total_rows = result.num_rows
        # Clamp offset to total_rows so slice() never errors
        safe_offset = min(offset, total_rows)
        safe_limit = max(0, min(limit, total_rows - safe_offset))

        sliced = result.slice(safe_offset, safe_limit)

        rows = sliced.to_pylist()
        columns = list(sliced.column_names)

        response = {
            "sql": sql,
            "normalized_sql": compiled.normalized_sql,
            "engine": "infersql-executor",
            "steps": [
                "parse_sql",
                "build_logical_plan",
                "build_physical_plan",
                "execute_plan",
                "serialize_results",
            ],
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "limit": limit,
            "offset": offset,
            "has_more": safe_offset + safe_limit < total_rows,
            "logical_plan": compiled.logical_plan.model_dump(),
            "physical_plan": compiled.physical_plan.model_dump(),
        }

        if debug:
            response["debug"] = {
                "request_id": request_id,
                "total_ms": 0.0,
            }

        return response

    def validate_query(self, sql: str):
        return self.validate(sql=sql)

    def plan_query(self, sql: str):
        return self.plan(sql=sql)

    def execute_query(self, sql: str):
        return self.execute(sql=sql)

    def _seed_demo_data(self) -> None:
        prices = pa.table(
            {
                "symbol": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"],
                "close": [189.12, 425.27, 1210.54, 176.33, 182.41],
            }
        )
        self.dataset_registry.register_table("prices", prices)

    def _validate_referenced_columns(self, sql: str) -> None:
        summary = self.query_parser.summarize(sql)
        tables = summary["tables"]
        columns = summary["columns"]

        if not tables:
            raise ValueError("Query must reference a table")

        if len(tables) > 1:
            raise ValueError("Only single-table queries are supported right now")

        table_name = tables[0]
        table = self.dataset_registry.get_table(table_name)
        available_columns = set(table.column_names)

        for column in columns:
            normalized_column = column.split(".")[-1]
            if normalized_column not in available_columns:
                raise ValueError(
                    f"Unknown column '{normalized_column}' on dataset '{table_name}'"
                )