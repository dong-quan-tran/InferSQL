# app/api/query.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
import pyarrow as pa
from opentelemetry.trace import Status, StatusCode

from app.core.catalog import DatasetNotFoundError, DatasetRegistry
from app.core.engine.executor import QueryExecutor
from app.core.engine.physical_planner import PhysicalPlanner
from app.core.engine.parser import QueryParser
from app.core.observability import (
    query_counter,
    query_duration_histogram,
    query_failure_counter,
    tracer,
)
from app.schemas.query import (
    QueryExecuteResponse,
    QueryPlanResponse,
    QueryRequest,
    QueryValidationResponse,
)

router = APIRouter()

dataset_registry = DatasetRegistry()
physical_planner = PhysicalPlanner()
query_parser = QueryParser()


def normalize_sql(sql: str) -> str:
    return " ".join(sql.split())


def _request_id(request: Request | None) -> str:
    if request is None:
        return "unknown"
    return getattr(request.state, "request_id", "unknown")


def seed_demo_data() -> None:
    if "prices" not in dataset_registry.list_tables():
        dataset_registry.register_table(
            "prices",
            pa.table(
                {
                    "symbol": ["AAPL", "MSFT", "NVDA", "AMD", "INTC"],
                    "close": [189.98, 427.12, 1203.00, 166.40, 31.22],
                    "volume": [1000, 1500, 1200, 900, 1100],
                }
            ),
        )


seed_demo_data()


@router.post("/query/validate", response_model=QueryValidationResponse)
def validate_query(payload: QueryRequest, request: Request) -> QueryValidationResponse:
    query_counter.add(
        1,
        attributes={"endpoint": "/query/validate"},
    )

    with tracer.start_as_current_span("query.validate") as span:
        span.set_attribute("request.id", _request_id(request))
        span.set_attribute("query.sql", payload.sql)

        try:
            summary = query_parser.summarize(payload.sql)
            normalized_sql = normalize_sql(payload.sql)

            is_valid = summary["query_type"] == "SELECT"
            errors = [] if is_valid else ["Only SELECT queries are supported right now"]

            span.set_attribute("query.normalized_sql", normalized_sql)
            span.set_attribute("query.type", summary["query_type"])
            span.set_attribute("query.table_count", len(summary["tables"]))
            span.set_attribute("query.column_count", len(summary["columns"]))
            span.set_attribute("query.has_where", summary["has_where"])
            span.set_attribute("query.has_group_by", summary["has_group_by"])
            span.set_attribute("query.has_order_by", summary["has_order_by"])
            span.set_attribute("query.has_limit", summary["has_limit"])
            span.set_attribute("query.is_valid", is_valid)

            if not is_valid:
                query_failure_counter.add(
                    1,
                    attributes={
                        "endpoint": "/query/validate",
                        "error.type": "unsupported_query",
                        "query.type": summary["query_type"],
                    },
                )

            return QueryValidationResponse(
                sql=payload.sql,
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
            )
        except ValueError as exc:
            query_failure_counter.add(
                1,
                attributes={"endpoint": "/query/validate", "error.type": "value_error"},
            )
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/query/plan", response_model=QueryPlanResponse)
def plan_query(payload: QueryRequest, request: Request) -> QueryPlanResponse:
    query_counter.add(
        1,
        attributes={"endpoint": "/query/plan"},
    )

    with tracer.start_as_current_span("query.plan_request") as span:
        span.set_attribute("request.id", _request_id(request))
        span.set_attribute("query.sql", payload.sql)

        try:
            with tracer.start_as_current_span("query.parse"):
                logical_plan = query_parser.build_logical_plan(payload.sql)

            with tracer.start_as_current_span("query.plan"):
                physical_plan = physical_planner.build(logical_plan)

            normalized_sql = normalize_sql(payload.sql)

            span.set_attribute("query.normalized_sql", normalized_sql)
            span.set_attribute("plan.engine", "infersql-planner")
            span.set_attribute("plan.step_count", 5)
            span.set_attribute("plan.logical_root", logical_plan.node_type)
            span.set_attribute("plan.physical_root", physical_plan.node_type)

            return QueryPlanResponse(
                sql=payload.sql,
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
            )
        except ValueError as exc:
            query_failure_counter.add(
                1,
                attributes={"endpoint": "/query/plan", "error.type": "value_error"},
            )
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/query/execute", response_model=QueryExecuteResponse)
def execute_query(payload: QueryRequest, request: Request) -> QueryExecuteResponse:
    query_counter.add(
        1,
        attributes={"endpoint": "/query/execute"},
    )

    with tracer.start_as_current_span("query.execute") as span:
        span.set_attribute("request.id", _request_id(request))
        span.set_attribute("query.sql", payload.sql)

        try:
            with tracer.start_as_current_span("query.parse"):
                logical_plan = query_parser.build_logical_plan(payload.sql)

            with tracer.start_as_current_span("query.plan"):
                physical_plan = physical_planner.build(logical_plan)

            with tracer.start_as_current_span("query.run"):
                executor = QueryExecutor(dataset_registry)
                result_table = executor.execute(physical_plan)

            normalized_sql = normalize_sql(payload.sql)

            span.set_attribute("query.normalized_sql", normalized_sql)
            span.set_attribute("query.row_count", result_table.num_rows)
            span.set_attribute("query.column_count", len(result_table.column_names))
            span.set_attribute("query.table_name", "prices")

            return QueryExecuteResponse(
                sql=payload.sql,
                normalized_sql=normalized_sql,
                row_count=result_table.num_rows,
                columns=result_table.column_names,
                rows=result_table.to_pylist(),
                logical_plan=logical_plan,
                physical_plan=physical_plan,
            )
        except DatasetNotFoundError as exc:
            query_failure_counter.add(
                1,
                attributes={"endpoint": "/query/execute", "error.type": "dataset_not_found"},
            )
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            query_failure_counter.add(
                1,
                attributes={"endpoint": "/query/execute", "error.type": "value_error"},
            )
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise HTTPException(status_code=400, detail=str(exc)) from exc