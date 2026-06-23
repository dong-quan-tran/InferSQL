from __future__ import annotations

import logging
import re
import time

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

    def _build_debug_info(
        self,
        *,
        request_id: str | None,
        total_ms: float,
        stage: str,
        engine: str | None,
        error_origin: str | None = None,
        features: list[str] | None = None,
    ) -> dict:
        return {
            "request_id": request_id or "unknown",
            "total_ms": total_ms,
            "stage": stage,
            "engine": engine,
            "error_origin": error_origin,
            "features": features or [],
        }

    def _has_top_level_derived_from(self, expression: exp.Expression) -> bool:
        if not isinstance(expression, exp.Select):
            return False

        from_clause = expression.args.get("from_")
        if from_clause is None or from_clause.this is None:
            return False

        return isinstance(from_clause.this, exp.Subquery)

    def _build_datafusion_plan_response(
        self,
        sql: str,
        normalized_sql: str,
        explain_rows: list[dict],
    ) -> dict:
        logical_lines: list[str] = []
        physical_lines: list[str] = []

        for row in explain_rows:
            plan_type = str(row.get("plan_type", ""))
            plan_value = str(row.get("plan", ""))

            if not plan_value:
                continue

            lowered = plan_type.lower()
            if "logical" in lowered:
                logical_lines.append(plan_value)
            elif "physical" in lowered:
                physical_lines.append(plan_value)

        return {
            "sql": sql,
            "normalized_sql": normalized_sql,
            "engine": "datafusion",
            "steps": [
                "parse_sql",
                "extract_query_metadata",
                "validate_sql",
                "build_engine_plan",
            ],
            "logical_plan": {
                "node_type": "DataFusionLogicalPlan",
                "details": {"lines": logical_lines},
                "children": [],
            },
            "physical_plan": {
                "node_type": "DataFusionPhysicalPlan",
                "details": {"lines": physical_lines},
                "children": [],
            },
        }

    def _validate_referenced_tables_exist(self, sql: str) -> list[str]:
        normalized_sql = " ".join(sql.strip().split())
        if not normalized_sql:
            raise EmptyQueryError("SQL must not be empty")

        expression = self.query_parser.parse(normalized_sql)
        tables = self._extract_referenced_tables(expression)

        if not tables and not self._has_top_level_derived_from(expression):
            raise UnsupportedQueryError("Query must reference a dataset")

        for dataset_name in tables:
            try:
                self.dataset_registry.get_schema(dataset_name)
            except DatasetNotFoundError as exc:
                raise UnknownDatasetError(f"Unknown dataset '{dataset_name}'") from exc

        return tables

    def _plan_with_datafusion(
        self,
        sql: str,
        normalized_sql: str,
    ) -> dict:
        try:
            explain_rows = self.datafusion_runner.explain(normalized_sql, verbose=True)
        except (
            InvalidQuerySyntaxError,
            UnknownDatasetError,
            UnknownColumnError,
            UnsupportedQueryError,
        ):
            raise
        except BaseException as exc:
            raise self._map_datafusion_error(exc) from exc

        return self._build_datafusion_plan_response(
            sql=sql,
            normalized_sql=normalized_sql,
            explain_rows=explain_rows,
        )

    # -------------------------------------------------------------------------
    # Feature detection helpers
    # -------------------------------------------------------------------------

    def _has_joins(self, expression: exp.Expression) -> bool:
        return expression.find(exp.Join) is not None

    def _has_set_ops(self, expression: exp.Expression) -> bool:
        return (
            expression.find(exp.Union) is not None
            or expression.find(exp.Intersect) is not None
            or expression.find(exp.Except) is not None
        )

    def _has_window_functions(self, expression: exp.Expression) -> bool:
        return expression.find(exp.Window) is not None

    def _compute_features(self, expression: exp.Expression) -> list[str]:
        features: list[str] = []
        if self._has_joins(expression):
            features.append("join")
        if self._has_set_ops(expression):
            features.append("set_op")
        if self._has_window_functions(expression):
            features.append("window")
        if self._has_top_level_derived_from(expression):
            features.append("derived_from")
        return features

    # -------------------------------------------------------------------------
    # Shared analysis
    # -------------------------------------------------------------------------

    def _analyze_query(
        self,
        sql: str,
    ) -> tuple[exp.Expression, ValidationSummary]:
        """
        Normalizes SQL, parses, extracts metadata, and applies product-level
        validation (select-only + schema/column checks). This is the single
        precheck path for validate/plan/execute.
        """
        normalized_sql = " ".join(sql.strip().split())
        if not normalized_sql:
            raise EmptyQueryError("SQL must not be empty")

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

        return expression, summary

    # -------------------------------------------------------------------------
    # Public operations
    # -------------------------------------------------------------------------

    def validate(self, sql: str, request_id: str | None = None, debug: bool = False):
        start_time = time.perf_counter()

        logger.info(
            "validating query",
            extra={"stage": "validate", "dataset": None},
        )

        expression, summary = self._analyze_query(sql)
        features = self._compute_features(expression)
        del expression

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

        total_ms = (time.perf_counter() - start_time) * 1000.0

        if debug:
            response["debug"] = self._build_debug_info(
                request_id=request_id,
                total_ms=total_ms,
                stage="validate",
                engine=None,
                features=features,
            )

        return response

    def plan(self, sql: str, request_id: str | None = None, debug: bool = False):
        start_time = time.perf_counter()

        logger.info(
            "planning query",
            extra={"stage": "plan", "dataset": None},
        )

        normalized_sql = " ".join(sql.strip().split())
        if not normalized_sql:
            raise EmptyQueryError("SQL must not be empty")

        expression = self.query_parser.parse(normalized_sql)
        self.query_parser.validate_select_only(expression)
        features = self._compute_features(expression)

        # Broad SQL with a top-level derived table in FROM should bypass
        # product schema validation and be delegated directly to DataFusion.
        if self._has_top_level_derived_from(expression):
            response = self._plan_with_datafusion(
                sql=sql,
                normalized_sql=normalized_sql,
            )

            logger.info(
                "query planned",
                extra={"stage": "plan", "dataset": None},
            )

            total_ms = (time.perf_counter() - start_time) * 1000.0

            if debug:
                response["debug"] = self._build_debug_info(
                    request_id=request_id,
                    total_ms=total_ms,
                    stage="plan",
                    engine="datafusion",
                    features=features,
                )

            return response

        _, summary = self._analyze_query(sql)

        if not summary.is_valid and summary.errors:
            message = summary.errors[0]
            if "Invalid SQL syntax" in message:
                raise InvalidQuerySyntaxError(message)
            if message.startswith("Unknown dataset"):
                raise UnknownDatasetError(message)
            if message.startswith("Unknown column"):
                raise UnknownColumnError(message)
            raise UnsupportedQueryError(message)

        if self._supports_custom_planner(expression):
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

            total_ms = (time.perf_counter() - start_time) * 1000.0

            if debug:
                response["debug"] = self._build_debug_info(
                    request_id=request_id,
                    total_ms=total_ms,
                    stage="plan",
                    engine="infersql-planner",
                    features=features,
                )

            return response

        self._validate_referenced_tables_exist(normalized_sql)

        response = self._plan_with_datafusion(
            sql=sql,
            normalized_sql=normalized_sql,
        )

        logger.info(
            "query planned",
            extra={"stage": "plan", "dataset": None},
        )

        total_ms = (time.perf_counter() - start_time) * 1000.0

        if debug:
            response["debug"] = self._build_debug_info(
                request_id=request_id,
                total_ms=total_ms,
                stage="plan",
                engine="datafusion",
                features=features,
            )

        return response

    def execute(
        self,
        sql: str,
        request_id: str | None = None,
        debug: bool = False,
        limit: int = 100,
        offset: int = 0,
    ):
        start_time = time.perf_counter()

        logger.info(
            "executing query",
            extra={"stage": "execute", "dataset": None},
        )

        expression, summary = self._analyze_query(sql)

        if not summary.is_valid and summary.errors:
            message = summary.errors[0]
            if "Invalid SQL syntax" in message:
                raise InvalidQuerySyntaxError(message)
            if message.startswith("Unknown dataset"):
                raise UnknownDatasetError(message)
            if message.startswith("Unknown column"):
                raise UnknownColumnError(message)
            raise UnsupportedQueryError(message)

        normalized_sql = summary.normalized_sql

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
        except BaseException as exc:
            raise self._map_datafusion_error(exc) from exc

        compiled = None
        dataset = None
        if self._supports_custom_planner(expression):
            compiled = self.query_compiler.compile(sql)
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
            "logical_plan": compiled.logical_plan.model_dump() if compiled else None,
            "physical_plan": compiled.physical_plan.model_dump() if compiled else None,
        }

        total_ms = (time.perf_counter() - start_time) * 1000.0

        if debug:
            features = self._compute_features(expression)
            response["debug"] = self._build_debug_info(
                request_id=request_id,
                total_ms=total_ms,
                stage="execute",
                engine="datafusion",
                features=features,
            )

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
        self._validate_select_lists(expression)

        tables = self._extract_referenced_tables(expression)
        has_derived_from = self._has_top_level_derived_from(expression)

        if not tables and not has_derived_from:
            raise UnsupportedQueryError("Query must reference a dataset")

        alias_to_table = self._build_alias_to_table_map(expression)
        available_columns_by_table = self._load_available_columns_by_table(tables) if tables else {}

        self._validate_columns(expression, alias_to_table, available_columns_by_table)

        if (
            len(tables) == 1
            and isinstance(expression, exp.Select)
            and not has_derived_from
            and expression.find(exp.Subquery) is None
            and not self._has_set_operation(expression)
        ):
            dataset_name = tables[0]
            available_columns = sorted(available_columns_by_table[dataset_name])
            self._validate_single_table_grouping(expression, dataset_name, available_columns)
            return SchemaReferenceSummary(
                dataset_name=dataset_name,
                columns=self._extract_column_names(expression),
                available_columns=available_columns,
            )

        merged_columns = sorted(
            {
                column_name
                for column_names in available_columns_by_table.values()
                for column_name in column_names
            }
        )

        return SchemaReferenceSummary(
            dataset_name="__derived__" if has_derived_from and not tables else (
                "__multiple__" if len(tables) > 1 else (tables[0] if tables else "__derived__")
            ),
            columns=self._extract_column_names(expression),
            available_columns=merged_columns,
        )

    def _extract_referenced_tables(self, expression: exp.Expression) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        for table in expression.find_all(exp.Table):
            if self._is_derived_alias_table(table):
                continue

            name = table.name
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)

        return names

    def _build_alias_to_table_map(self, expression: exp.Expression) -> dict[str, str]:
        alias_to_table: dict[str, str] = {}

        for table in expression.find_all(exp.Table):
            if self._is_derived_alias_table(table):
                continue

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
        derived_aliases = {
            subquery.alias_or_name
            for subquery in expression.find_all(exp.Subquery)
            if subquery.alias_or_name
        }

        for column in expression.find_all(exp.Column):
            column_name = column.name
            if not column_name or column_name == "*":
                continue

            table_alias = column.table

            if table_alias:
                if table_alias in derived_aliases:
                    continue

                dataset_name = alias_to_table.get(table_alias)
                if dataset_name is None:
                    raise UnknownDatasetError(f"Unknown dataset or alias '{table_alias}'")

                if column_name not in available_columns_by_table[dataset_name]:
                    raise UnknownColumnError(
                        f"Unknown column '{column_name}' on dataset '{dataset_name}'"
                    )

                continue

            if self._column_is_within_subquery_scope(column):
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
        # Tiny product guardrail only:
        # disallow SELECT * with GROUP BY for single-table queries.
        #
        # All other grouped-query semantics are delegated to DataFusion.
        del dataset_name, available_columns

        if not isinstance(expression, exp.Select):
            return

        group = expression.args.get("group")
        if group is None:
            return

        select_expressions = expression.expressions or []
        if not select_expressions:
            return

        for item in select_expressions:
            if isinstance(item, exp.Star):
                raise UnsupportedQueryError(
                    "SELECT * with GROUP BY is not supported right now"
                )

            target = item.this if isinstance(item, exp.Alias) else item

            if isinstance(target, exp.Star):
                raise UnsupportedQueryError(
                    "SELECT * with GROUP BY is not supported right now"
                )

    def _validate_select_lists(self, expression: exp.Expression) -> None:
        for select in expression.find_all(exp.Select):
            select_expressions = select.expressions or []
            if not select_expressions:
                raise UnsupportedQueryError(
                    "Query must select at least one column or expression"
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

    def _map_datafusion_error(self, exc: BaseException) -> Exception:
        message = str(exc or "").strip()
        lowered = message.lower()

        if "panic" in lowered or exc.__class__.__name__ == "PanicException":
            return UnsupportedQueryError("DataFusion execution error")

        if (
            "sql parser error" in lowered
            or "parser error" in lowered
            or "parse error" in lowered
            or "syntax error" in lowered
        ):
            return InvalidQuerySyntaxError("Invalid SQL syntax")

        if (
            "no table named" in lowered
            or "table not found" in lowered
            or "unresolved table" in lowered
            or "unknown table" in lowered
        ):
            ident = self._extract_quoted_identifier(message)
            if ident:
                return UnknownDatasetError(f"Unknown dataset '{ident}'")
            return UnknownDatasetError("Unknown dataset")

        if (
            "ambiguous reference to unqualified field" in lowered
            or ("ambiguous" in lowered and "column" in lowered)
            or ("ambiguous" in lowered and "field" in lowered)
        ):
            return UnsupportedQueryError("Ambiguous column reference")

        if (
            "field not found" in lowered
            or "no field named" in lowered
            or "schemaerror(fieldnotfound" in lowered
            or "unqualified_field_not_found" in lowered
            or "unresolved column" in lowered
            or "could not be resolved from available columns" in lowered
        ):
            ident = self._extract_quoted_identifier(message)
            if ident:
                return UnknownColumnError(f"Unknown column '{ident}'")
            return UnknownColumnError("Unknown column")

        if "union queries must have the same number of columns" in lowered:
            return UnsupportedQueryError("UNION queries must have the same number of columns")

        if "invalid subquery" in lowered or ("subquery" in lowered and "not supported" in lowered):
            return UnsupportedQueryError("Unsupported subquery shape")

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
            return UnsupportedQueryError("Query is not supported by the execution engine")

        return UnsupportedQueryError("DataFusion execution error")

    def _find_node(self, node: PlanNode, node_type: str):
        if node.node_type == node_type:
            return node

        for child in node.children:
            match = self._find_node(child, node_type)
            if match is not None:
                return match

        return None

    def _is_derived_alias_table(self, table: exp.Table) -> bool:
        parent = table.parent
        while parent is not None:
            if isinstance(parent, exp.Subquery):
                return True
            parent = parent.parent
        return False

    def _is_derived_alias_name(self, expression: exp.Expression, alias_name: str) -> bool:
        for subquery in expression.find_all(exp.Subquery):
            alias = subquery.alias_or_name
            if alias == alias_name:
                return True
        return False

    def _column_is_within_subquery_scope(self, column: exp.Column) -> bool:
        parent = column.parent
        while parent is not None:
            if isinstance(parent, exp.Subquery):
                from_or_join_parent = parent.parent
                if isinstance(from_or_join_parent, (exp.From, exp.Join)):
                    return False
                return True
            parent = parent.parent
        return False

    def _has_set_operation(self, expression: exp.Expression) -> bool:
        return expression.find(exp.Union) is not None

    def _supports_custom_planner(self, expression: exp.Expression) -> bool:
        if not isinstance(expression, exp.Select):
            return False

        if expression.find(exp.Subquery) is not None:
            return False

        if expression.find(exp.Join) is not None:
            return False

        if expression.find(exp.Union) is not None:
            return False

        if expression.find(exp.Intersect) is not None:
            return False

        if expression.find(exp.Except) is not None:
            return False

        where = expression.args.get("where")
        if where is not None and not isinstance(
            where.this,
            (exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE),
        ):
            return False

        return True