from __future__ import annotations

import logging

import pyarrow as pa
from sqlglot import exp

from app.core.catalog.registry import DatasetNotFoundError, DatasetRegistry
from app.core.engine.parser import QueryParser
from app.core.exceptions import (
    EmptyQueryError,
    InvalidQuerySyntaxError,
    UnknownColumnError,
    UnknownDatasetError,
    UnsupportedQueryError,
)
from app.core.settings import Settings
from app.schemas.query import SchemaReferenceSummary, ValidationSummary
from app.services.query_compiler import QueryCompiler
from app.services.query_runner import QueryRunner


logger = logging.getLogger(__name__)


class QueryService:
    def __init__(
        self,
        settings: Settings,
        dataset_registry: DatasetRegistry,
        query_parser: QueryParser,
        query_compiler: QueryCompiler,
        query_runner: QueryRunner,
    ) -> None:
        self.settings = settings
        self.dataset_registry = dataset_registry
        self.query_parser = query_parser
        self.query_compiler = query_compiler
        self.query_runner = query_runner

        if self.settings.seed_demo_data and "prices" not in self.dataset_registry.list_tables():
            self._seed_demo_data()

    def validate(self, sql: str, request_id: str | None = None, debug: bool = False):
        normalized_sql = " ".join(sql.strip().split())

        logger.info(
            "validating query",
            extra={"stage": "validate", "dataset": None},
        )

        expression = self.query_parser.parse(normalized_sql)
        summary_dict = self.query_parser.summarize(normalized_sql)

        summary = ValidationSummary(
            normalized_sql=normalized_sql,
            query_type=summary_dict["query_type"],
            tables=summary_dict["tables"],
            columns=summary_dict["columns"],
            has_where=summary_dict["has_where"],
            has_group_by=summary_dict["has_group_by"],
            has_order_by=summary_dict["has_order_by"],
            has_limit=summary_dict["has_limit"],
        )

        try:
            self.query_parser.validate_select_only(expression)
            self._validate_referenced_schema(normalized_sql)
        except (
            EmptyQueryError,
            InvalidQuerySyntaxError,
            UnsupportedQueryError,
            UnknownDatasetError,
            UnknownColumnError,
        ) as exc:
            summary.is_valid = False
            summary.errors.append(str(exc))

            logger.info(
                "query validation failed",
                extra={
                    "stage": "validate",
                    "dataset": summary.tables[0] if summary.tables else None,
                    "error_code": exc.__class__.__name__.upper(),
                },
            )

        response = {
            "sql": sql,
            "normalized_sql": summary.normalized_sql,
            "is_valid": summary.is_valid,
            "query_type": summary.query_type,
            "errors": summary.errors,
            "tables": summary.tables,
            "columns": summary.columns,
            "has_where": summary.has_where,
            "has_group_by": summary.has_group_by,
            "has_order_by": summary.has_order_by,
            "has_limit": summary.has_limit,
        }

        if debug:
            response["debug"] = {
                "request_id": request_id or "unknown",
                "total_ms": 0.0,
            }

        return response

    def plan(self, sql: str, request_id: str | None = None, debug: bool = False):
        logger.info(
            "planning query",
            extra={"stage": "plan", "dataset": None},
        )

        self._validate_referenced_schema(sql)
        compiled = self.query_compiler.compile(sql)

        dataset = None
        scan_node = self._find_node(compiled.logical_plan, "Scan")
        if scan_node is not None:
            dataset = scan_node.details.get("table")

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
            "logical_plan": compiled.logical_plan.model_dump(),
            "physical_plan": compiled.physical_plan.model_dump(),
        }

        logger.info(
            "query planned",
            extra={"stage": "plan", "dataset": dataset},
        )

        if debug:
            response["debug"] = {
                "request_id": request_id or "unknown",
                "total_ms": 0.0,
            }

        return response

    def execute(
        self,
        sql: str,
        request_id: str | None = None,
        debug: bool = False,
        limit: int = 100,
        offset: int = 0,
    ):
        logger.info(
            "executing query",
            extra={"stage": "execute", "dataset": None},
        )

        self._validate_referenced_schema(sql)
        compiled = self.query_compiler.compile(sql)
        execution_result = self.query_runner.run(
            compiled.physical_plan,
            limit=limit,
            offset=offset,
        )

        dataset = None
        scan_node = self._find_node(compiled.logical_plan, "Scan")
        if scan_node is not None:
            dataset = scan_node.details.get("table")

        logger.info(
            "query executed",
            extra={"stage": "execute", "dataset": dataset},
        )

        response = {
            "sql": sql,
            "normalized_sql": compiled.normalized_sql,
            "row_count": execution_result.row_count,
            "columns": execution_result.columns,
            "rows": execution_result.rows,
            "logical_plan": compiled.logical_plan.model_dump(),
            "physical_plan": compiled.physical_plan.model_dump(),
        }

        if debug:
            response["debug"] = {
                "request_id": request_id or "unknown",
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
        from app.core.catalog.registry import DatasetColumnMetadata, DatasetMetadata

        prices_metadata = DatasetMetadata(
            description="Daily security prices for a small demo universe of stocks.",
            columns={
                "symbol": DatasetColumnMetadata(
                    description="Ticker symbol such as AAPL, MSFT, NVDA, GOOGL, or AMZN."
                ),
                "close": DatasetColumnMetadata(
                    description="Closing price for the security on the row."
                ),
            },
        )

        prices = pa.table(
            {
                "symbol": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"],
                "close": [189.12, 425.27, 1210.54, 176.33, 182.41],
            }
        )
        self.dataset_registry.register_table(
            "prices",
            prices,
            metadata=prices_metadata,
        )

        prices_nulls = pa.table(
            {
                "symbol": ["AAPL", "MSFT", "NVDA"],
                "close": [150.0, None, 120.0],
            }
        )
        self.dataset_registry.register_table(
            "prices_nulls",
            prices_nulls,
            metadata=DatasetMetadata(
                description="Demo prices table with null close values for ORDER BY behavior tests.",
                columns={
                    "symbol": DatasetColumnMetadata(
                        description="Ticker symbol such as AAPL, MSFT, or NVDA."
                    ),
                    "close": DatasetColumnMetadata(
                        description="Closing price for the security on the row; may be null in this demo fixture."
                    ),
                },
            ),
        )

    def _validate_referenced_schema(self, sql: str) -> SchemaReferenceSummary:
        normalized_sql = " ".join(sql.strip().split())
        if not normalized_sql:
            raise EmptyQueryError("SQL must not be empty")

        expression = self.query_parser.parse(normalized_sql)
        self.query_parser.validate_select_only(expression)

        summary = self.query_parser.summarize(normalized_sql)
        tables = summary["tables"]
        columns = summary["columns"]

        if not tables:
            raise UnsupportedQueryError("Query must reference a dataset")

        if self.query_parser.has_join(expression):
            raise UnsupportedQueryError(
                "JOIN queries are not supported right now"
            )

        if len(tables) > 1:
            raise UnsupportedQueryError(
                "Only single-table queries are supported right now"
            )

        dataset_name = tables[0]

        try:
            schema = self.dataset_registry.get_schema(dataset_name)
        except DatasetNotFoundError as exc:
            raise UnknownDatasetError(f"Unknown dataset '{dataset_name}'") from exc

        available_columns = [field.name for field in schema]
        available_column_set = set(available_columns)

        for column in columns:
            if column == "*":
                continue
            if column not in available_column_set:
                raise UnknownColumnError(
                    f"Unknown column '{column}' on dataset '{dataset_name}'"
                )

        group = expression.args.get("group")
        select_expressions = expression.expressions or []

        group_by_cols: set[str] = set()
        if group is not None:
            for group_expr in group.expressions:
                if isinstance(group_expr, exp.Column):
                    group_by_cols.add(group_expr.name)
                else:
                    raise UnsupportedQueryError(
                        "Only plain column expressions are supported in GROUP BY right now"
                    )

        aggregate_nodes = (exp.Count, exp.Sum, exp.Avg)
        has_aggregate = False
        non_agg_columns: set[str] = set()

        for item in select_expressions:
            if isinstance(item, exp.Star):
                if group is not None:
                    raise UnsupportedQueryError(
                        "SELECT * with GROUP BY is not supported right now"
                    )
                continue

            target = item.this if isinstance(item, exp.Alias) else item

            if isinstance(target, aggregate_nodes):
                has_aggregate = True
                continue

            if isinstance(target, exp.Column):
                non_agg_columns.add(target.name)
                continue

            if group is not None:
                raise UnsupportedQueryError(
                    "Only plain columns and simple aggregates are supported in grouped SELECT lists right now"
                )

        if has_aggregate and group is None and non_agg_columns:
            column_list = ", ".join(f"'{name}'" for name in sorted(non_agg_columns))
            raise UnsupportedQueryError(
                f"Columns {column_list} must appear in GROUP BY or be aggregated"
            )

        if group is not None:
            missing = sorted(non_agg_columns.difference(group_by_cols))
            if missing:
                missing_list = ", ".join(f"'{name}'" for name in missing)
                raise UnsupportedQueryError(
                    f"Columns {missing_list} must appear in GROUP BY or be aggregated"
                )

        return SchemaReferenceSummary(
            dataset_name=dataset_name,
            columns=columns,
            available_columns=available_columns,
        )

    def _find_node(self, node, node_type: str):
        if node.node_type == node_type:
            return node

        for child in node.children:
            match = self._find_node(child, node_type)
            if match is not None:
                return match

        return None