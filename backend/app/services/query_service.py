from __future__ import annotations

import logging
import re

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
from app.schemas.query import PlanNode, SchemaReferenceSummary, ValidationSummary
from app.services.datafusion_runner import DataFusionRunner
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
        self.datafusion_runner = DataFusionRunner(dataset_registry)

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

        normalized_sql = " ".join(sql.strip().split())
        if not normalized_sql:
            raise EmptyQueryError("SQL must not be empty")

        expression = self.query_parser.parse(normalized_sql)
        self.query_parser.validate_select_only(expression)

        self._validate_referenced_schema(normalized_sql)
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

        normalized_sql = " ".join(sql.strip().split())
        if not normalized_sql:
            raise EmptyQueryError("SQL must not be empty")

        expression = self.query_parser.parse(normalized_sql)
        self.query_parser.validate_select_only(expression)

        self._validate_referenced_schema(normalized_sql)

        try:
            execution_result = self.datafusion_runner.run(
                normalized_sql,
                limit=limit,
                offset=offset,
            )
        except (
            InvalidQuerySyntaxError,
            UnknownDatasetError,
            UnknownColumnError,
            UnsupportedQueryError,
        ):
            raise
        except Exception as exc:
            raise self._map_datafusion_error(exc) from exc

        compiled = self.query_compiler.compile(sql)
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
            "normalized_sql": normalized_sql,
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

        tables = self._extract_referenced_tables(expression)
        if not tables:
            raise UnsupportedQueryError("Query must reference a dataset")

        alias_to_table = self._build_alias_to_table_map(expression)
        available_columns_by_table = self._load_available_columns_by_table(tables)

        self._validate_columns(expression, alias_to_table, available_columns_by_table)

        if len(tables) == 1:
            dataset_name = tables[0]
            available_columns = sorted(available_columns_by_table[dataset_name])
            self._validate_single_table_grouping(expression, dataset_name, available_columns)
            return SchemaReferenceSummary(
                dataset_name=dataset_name,
                columns=self._extract_column_names(expression),
                available_columns=available_columns,
            )

        return SchemaReferenceSummary(
            dataset_name="__multiple__",
            columns=self._extract_column_names(expression),
            available_columns=sorted(
                {
                    column_name
                    for column_names in available_columns_by_table.values()
                    for column_name in column_names
                }
            ),
        )

    def _extract_referenced_tables(self, expression: exp.Expression) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for table in expression.find_all(exp.Table):
            name = table.name
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)

        return names

    def _build_alias_to_table_map(self, expression: exp.Expression) -> dict[str, str]:
        alias_to_table: dict[str, str] = {}

        for table in expression.find_all(exp.Table):
            table_name = table.name
            if not table_name:
                continue

            alias_to_table[table_name] = table_name

            alias = table.alias_or_name
            if alias:
                alias_to_table[alias] = table_name

        return alias_to_table

    def _load_available_columns_by_table(self, tables: list[str]) -> dict[str, set[str]]:
        available_columns_by_table: dict[str, set[str]] = {}

        for dataset_name in tables:
            try:
                schema = self.dataset_registry.get_schema(dataset_name)
            except DatasetNotFoundError as exc:
                raise UnknownDatasetError(f"Unknown dataset '{dataset_name}'") from exc

            available_columns_by_table[dataset_name] = {field.name for field in schema}

        return available_columns_by_table

    def _validate_columns(
        self,
        expression: exp.Expression,
        alias_to_table: dict[str, str],
        available_columns_by_table: dict[str, set[str]],
    ) -> None:
        for column in expression.find_all(exp.Column):
            column_name = column.name
            if not column_name or column_name == "*":
                continue

            table_alias = column.table

            if table_alias:
                dataset_name = alias_to_table.get(table_alias)
                if dataset_name is None:
                    raise UnknownDatasetError(
                        f"Unknown dataset or alias '{table_alias}'"
                    )

                if column_name not in available_columns_by_table[dataset_name]:
                    raise UnknownColumnError(
                        f"Unknown column '{column_name}' on dataset '{dataset_name}'"
                    )

                continue

            matching_datasets = [
                dataset_name
                for dataset_name, column_names in available_columns_by_table.items()
                if column_name in column_names
            ]

            if not matching_datasets:
                if len(available_columns_by_table) == 1:
                    dataset_name = next(iter(available_columns_by_table))
                    raise UnknownColumnError(
                        f"Unknown column '{column_name}' on dataset '{dataset_name}'"
                    )
                raise UnknownColumnError(f"Unknown column '{column_name}'")

            if len(matching_datasets) > 1 and len(available_columns_by_table) > 1:
                dataset_list = ", ".join(sorted(matching_datasets))
                raise UnsupportedQueryError(
                    f"Ambiguous unqualified column '{column_name}' referenced across datasets: {dataset_list}"
                )

    def _extract_column_names(self, expression: exp.Expression) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for column in expression.find_all(exp.Column):
            column_name = column.name
            if not column_name or column_name in seen:
                continue
            seen.add(column_name)
            names.append(column_name)

        return names

    def _validate_single_table_grouping(
        self,
        expression: exp.Expression,
        dataset_name: str,
        available_columns: list[str],
    ) -> None:
        del dataset_name, available_columns

        group = expression.args.get("group")
        select_expressions = expression.expressions or []

        if not select_expressions:
            raise UnsupportedQueryError(
                "Query must select at least one column or expression"
            )

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

    def _extract_quoted_identifier(self, message: str) -> str | None:
        patterns = [
            r"'([^']+)'",
            r'"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1)
        return None

    def _map_datafusion_error(self, exc: Exception) -> Exception:
        message = str(exc or "").strip()
        lowered = message.lower()

        if (
            "sql parser error" in lowered
            or "parser error" in lowered
            or "parse error" in lowered
            or "syntax error" in lowered
        ):
            return InvalidQuerySyntaxError(message)

        if (
            "no table named" in lowered
            or "table not found" in lowered
            or "unresolved table" in lowered
            or "unknown table" in lowered
        ):
            ident = self._extract_quoted_identifier(message)
            if ident:
                return UnknownDatasetError(f"Unknown dataset '{ident}'")
            return UnknownDatasetError(message)

        if (
            "ambiguous reference to unqualified field" in lowered
            or ("ambiguous" in lowered and "column" in lowered)
            or ("ambiguous" in lowered and "field" in lowered)
        ):
            return UnsupportedQueryError(message)

        if (
            "field not found" in lowered
            or "no field named" in lowered
            or "schema error" in lowered
            or "schemaerror(fieldnotfound" in lowered
            or "unqualified_field_not_found" in lowered
            or "unresolved column" in lowered
            or "could not be resolved from available columns" in lowered
        ):
            ident = self._extract_quoted_identifier(message)
            if ident:
                return UnknownColumnError(f"Unknown column '{ident}'")
            return UnknownColumnError(message)

        if (
            "not implemented" in lowered
            or "this feature is not implemented" in lowered
            or "unsupported logical plan" in lowered
            or "unsupported function" in lowered
            or "unsupported syntax" in lowered
            or "planning error" in lowered
            or "error during planning" in lowered
            or "failed to optimize plan" in lowered
            or "wrong number of columns in set expression" in lowered
            or "incompatible types" in lowered
            or "non-aggregate expressions" in lowered
        ):
            return UnsupportedQueryError(message)

        return UnsupportedQueryError(f"DataFusion execution error: {message}")

    def _find_node(self, node: PlanNode, node_type: str):
        if node.node_type == node_type:
            return node

        for child in node.children:
            match = self._find_node(child, node_type)
            if match is not None:
                return match

        return None