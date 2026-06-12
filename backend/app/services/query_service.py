# app/services/query_service.py
from __future__ import annotations

from time import perf_counter

import pyarrow as pa
from opentelemetry.trace import Status, StatusCode

from app.core.catalog import DatasetNotFoundError, DatasetRegistry
from app.core.engine.executor import QueryExecutor
from app.core.engine.physical_planner import PhysicalPlanner
from app.core.engine.parser import QueryParser
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.observability import (
    query_counter,
    query_duration_histogram,
    query_failure_counter,
    query_phase_duration_histogram,
    query_rows_histogram,
    tracer,
)
from app.schemas.query import (
    DebugInfo,
    QueryExecuteResponse,
    QueryPlanResponse,
    QueryValidationResponse,
)


class QueryService:
    def __init__(self) -> None:
        self.dataset_registry = DatasetRegistry()
        self.physical_planner = PhysicalPlanner()
        self.query_parser = QueryParser()
        self.query_executor = QueryExecutor(self.dataset_registry)
        self._seed_demo_data()

    def validate(
        self,
        *,
        sql: str,
        request_id: str,
        debug: bool,
    ) -> QueryValidationResponse:
        endpoint = "/query/validate"
        query_counter.add(1, attributes={"endpoint": endpoint})

        request_start = perf_counter()

        with tracer.start_as_current_span("query.validate") as span:
            span.set_attribute("request.id", request_id)
            span.set_attribute("query.sql", sql)

            try:
                summarize_start = perf_counter()
                summary = self.query_parser.summarize(sql)
                summarize_duration_ms = (perf_counter() - summarize_start) * 1000
                self._record_phase_duration(endpoint, "summarize", summarize_duration_ms)

                normalized_sql = self.normalize_sql(sql)
                is_valid = summary["query_type"] == "SELECT"
                errors = [] if is_valid else ["Only SELECT queries are supported right now"]

                total_duration_ms = self._record_total_duration(endpoint, request_start)

                span.set_attribute("query.normalized_sql", normalized_sql)
                span.set_attribute("query.type", summary["query_type"])
                span.set_attribute("query.table_count", len(summary["tables"]))
                span.set_attribute("query.column_count", len(summary["columns"]))
                span.set_attribute("query.has_where", summary["has_where"])
                span.set_attribute("query.has_group_by", summary["has_group_by"])
                span.set_attribute("query.has_order_by", summary["has_order_by"])
                span.set_attribute("query.has_limit", summary["has_limit"])
                span.set_attribute("query.is_valid", is_valid)
                span.set_attribute("timing.summarize_ms", round(summarize_duration_ms, 3))
                span.set_attribute("timing.total_ms", round(total_duration_ms, 3))

                if not is_valid:
                    query_failure_counter.add(
                        1,
                        attributes={
                            "endpoint": endpoint,
                            "error.type": "unsupported_query",
                            "query.type": summary["query_type"],
                        },
                    )
                    span.set_attribute("error.type", "unsupported_query")
                    span.set_status(
                        Status(
                            StatusCode.ERROR,
                            "Only SELECT queries are supported right now",
                        )
                    )

                return QueryValidationResponse(
                    sql=sql,
                    normalized_sql=normalized_sql,
                    is_valid=is_valid,
                    query_type=summary["query_type"],
                    errors=errors,
                    tables=summary["tables"],
                    columns=summary["columns"],
                    has_where=summary["has_where"],
                    has_group_by=summary["has_group_by"],
                    has_order_by=summary["has_order_by"],
                    has_limit=summary["has_limit"],
                    debug=self._build_debug_info(
                        request_id=request_id,
                        total_ms=total_duration_ms,
                        debug=debug,
                    ),
                )
            except ValueError as exc:
                self._handle_value_error(
                    endpoint=endpoint,
                    request_start=request_start,
                    span=span,
                    exc=exc,
                )

    def plan(
        self,
        *,
        sql: str,
        request_id: str,
        debug: bool,
    ) -> QueryPlanResponse:
        endpoint = "/query/plan"
        query_counter.add(1, attributes={"endpoint": endpoint})

        request_start = perf_counter()

        with tracer.start_as_current_span("query.plan_request") as span:
            span.set_attribute("request.id", request_id)
            span.set_attribute("query.sql", sql)

            try:
                parse_start = perf_counter()
                with tracer.start_as_current_span("query.parse"):
                    logical_plan = self.query_parser.build_logical_plan(sql)
                parse_duration_ms = (perf_counter() - parse_start) * 1000
                self._record_phase_duration(endpoint, "parse", parse_duration_ms)

                plan_start = perf_counter()
                with tracer.start_as_current_span("query.plan"):
                    physical_plan = self.physical_planner.build(logical_plan)
                plan_duration_ms = (perf_counter() - plan_start) * 1000
                self._record_phase_duration(endpoint, "plan", plan_duration_ms)

                normalized_sql = self.normalize_sql(sql)
                total_duration_ms = self._record_total_duration(endpoint, request_start)

                span.set_attribute("query.normalized_sql", normalized_sql)
                span.set_attribute("plan.engine", "infersql-planner")
                span.set_attribute("plan.step_count", 5)
                span.set_attribute("plan.logical_root", str(logical_plan.node_type))
                span.set_attribute("plan.physical_root", str(physical_plan.node_type))
                span.set_attribute("timing.parse_ms", round(parse_duration_ms, 3))
                span.set_attribute("timing.plan_ms", round(plan_duration_ms, 3))
                span.set_attribute("timing.total_ms", round(total_duration_ms, 3))

                return QueryPlanResponse(
                    sql=sql,
                    normalized_sql=normalized_sql,
                    engine="infersql-planner",
                    steps=[
                        "parse_sql",
                        "extract_query_metadata",
                        "validate_sql",
                        "build_logical_plan",
                        "build_physical_plan",
                    ],
                    logical_plan=logical_plan,
                    physical_plan=physical_plan,
                    debug=self._build_debug_info(
                        request_id=request_id,
                        total_ms=total_duration_ms,
                        parse_ms=parse_duration_ms,
                        plan_ms=plan_duration_ms,
                        debug=debug,
                    ),
                )
            except ValueError as exc:
                self._handle_value_error(
                    endpoint=endpoint,
                    request_start=request_start,
                    span=span,
                    exc=exc,
                )

    def execute(
        self,
        *,
        sql: str,
        request_id: str,
        debug: bool,
    ) -> QueryExecuteResponse:
        endpoint = "/query/execute"
        query_counter.add(1, attributes={"endpoint": endpoint})

        request_start = perf_counter()

        with tracer.start_as_current_span("query.execute") as span:
            span.set_attribute("request.id", request_id)
            span.set_attribute("query.sql", sql)

            try:
                parse_start = perf_counter()
                with tracer.start_as_current_span("query.parse"):
                    logical_plan = self.query_parser.build_logical_plan(sql)
                parse_duration_ms = (perf_counter() - parse_start) * 1000
                self._record_phase_duration(endpoint, "parse", parse_duration_ms)

                plan_start = perf_counter()
                with tracer.start_as_current_span("query.plan"):
                    physical_plan = self.physical_planner.build(logical_plan)
                plan_duration_ms = (perf_counter() - plan_start) * 1000
                self._record_phase_duration(endpoint, "plan", plan_duration_ms)

                execute_start = perf_counter()
                with tracer.start_as_current_span("query.run"):
                    result_table = self.query_executor.execute(physical_plan)
                execute_duration_ms = (perf_counter() - execute_start) * 1000
                self._record_phase_duration(endpoint, "execute", execute_duration_ms)

                normalized_sql = self.normalize_sql(sql)
                total_duration_ms = self._record_total_duration(endpoint, request_start)

                query_rows_histogram.record(
                    result_table.num_rows,
                    attributes={"endpoint": endpoint},
                )

                span.set_attribute("query.normalized_sql", normalized_sql)
                span.set_attribute("query.row_count", result_table.num_rows)
                span.set_attribute("query.column_count", len(result_table.column_names))
                span.set_attribute("timing.parse_ms", round(parse_duration_ms, 3))
                span.set_attribute("timing.plan_ms", round(plan_duration_ms, 3))
                span.set_attribute("timing.execute_ms", round(execute_duration_ms, 3))
                span.set_attribute("timing.total_ms", round(total_duration_ms, 3))

                return QueryExecuteResponse(
                    sql=sql,
                    normalized_sql=normalized_sql,
                    row_count=result_table.num_rows,
                    columns=result_table.column_names,
                    rows=result_table.to_pylist(),
                    logical_plan=logical_plan,
                    physical_plan=physical_plan,
                    debug=self._build_debug_info(
                        request_id=request_id,
                        total_ms=total_duration_ms,
                        parse_ms=parse_duration_ms,
                        plan_ms=plan_duration_ms,
                        execute_ms=execute_duration_ms,
                        debug=debug,
                    ),
                )
            except DatasetNotFoundError as exc:
                total_duration_ms = self._record_total_duration(endpoint, request_start)
                span.set_attribute("timing.total_ms", round(total_duration_ms, 3))
                span.set_attribute("error.type", "dataset_not_found")
                query_failure_counter.add(
                    1,
                    attributes={"endpoint": endpoint, "error.type": "dataset_not_found"},
                )
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise NotFoundError(str(exc)) from exc
            except ValueError as exc:
                self._handle_value_error(
                    endpoint=endpoint,
                    request_start=request_start,
                    span=span,
                    exc=exc,
                )

    @staticmethod
    def normalize_sql(sql: str) -> str:
        return " ".join(sql.split())

    @staticmethod
    def _record_phase_duration(endpoint: str, phase: str, duration_ms: float) -> None:
        query_phase_duration_histogram.record(
            duration_ms,
            attributes={
                "endpoint": endpoint,
                "phase": phase,
            },
        )

    @staticmethod
    def _record_total_duration(endpoint: str, request_start: float) -> float:
        total_duration_ms = (perf_counter() - request_start) * 1000
        query_duration_histogram.record(
            total_duration_ms,
            attributes={"endpoint": endpoint},
        )
        return total_duration_ms

    @staticmethod
    def _build_debug_info(
        *,
        request_id: str,
        total_ms: float,
        debug: bool,
        parse_ms: float | None = None,
        plan_ms: float | None = None,
        execute_ms: float | None = None,
    ) -> DebugInfo | None:
        if not debug:
            return None

        return DebugInfo(
            request_id=request_id,
            total_ms=round(total_ms, 3),
            parse_ms=round(parse_ms, 3) if parse_ms is not None else None,
            plan_ms=round(plan_ms, 3) if plan_ms is not None else None,
            execute_ms=round(execute_ms, 3) if execute_ms is not None else None,
        )

    @staticmethod
    def _handle_value_error(
        *,
        endpoint: str,
        request_start: float,
        span,
        exc: ValueError,
    ) -> None:
        total_duration_ms = QueryService._record_total_duration(endpoint, request_start)
        span.set_attribute("timing.total_ms", round(total_duration_ms, 3))
        span.set_attribute("error.type", "value_error")
        query_failure_counter.add(
            1,
            attributes={"endpoint": endpoint, "error.type": "value_error"},
        )
        span.record_exception(exc)
        span.set_status(Status(StatusCode.ERROR, str(exc)))
        raise BadRequestError(str(exc)) from exc

    def _seed_demo_data(self) -> None:
        if "prices" not in self.dataset_registry.list_tables():
            self.dataset_registry.register_table(
                "prices",
                pa.table(
                    {
                        "symbol": ["AAPL", "MSFT", "NVDA", "AMD", "INTC"],
                        "close": [189.98, 427.12, 1203.00, 166.40, 31.22],
                        "volume": [1000, 1500, 1200, 900, 1100],
                    }
                ),
            )