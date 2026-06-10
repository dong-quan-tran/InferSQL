# app/api/query.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
import pyarrow as pa

from app.core.catalog import DatasetNotFoundError, DatasetRegistry
from app.core.engine.executor import QueryExecutor
from app.core.engine.physical_planner import PhysicalPlanner
from app.core.engine.parser import QueryParser
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
def validate_query(payload: QueryRequest) -> QueryValidationResponse:
    try:
        summary = query_parser.summarize(payload.sql)

        is_valid = summary["query_type"] == "SELECT"
        errors = [] if is_valid else ["Only SELECT queries are supported right now"]

        return QueryValidationResponse(
            sql=payload.sql,
            normalized_sql=normalize_sql(payload.sql),
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    

@router.post("/query/plan", response_model=QueryPlanResponse)
def plan_query(payload: QueryRequest) -> QueryPlanResponse:
    try:
        logical_plan = query_parser.build_logical_plan(payload.sql)
        physical_plan = physical_planner.build(logical_plan)

        return QueryPlanResponse(
            sql=payload.sql,
            normalized_sql=normalize_sql(payload.sql),
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/query/execute", response_model=QueryExecuteResponse)
def execute_query(payload: QueryRequest) -> QueryExecuteResponse:
    try:
        logical_plan = query_parser.build_logical_plan(payload.sql)
        physical_plan = physical_planner.build(logical_plan)

        executor = QueryExecutor(dataset_registry)
        result_table = executor.execute(physical_plan)

        return QueryExecuteResponse(
            sql=payload.sql,
            normalized_sql=normalize_sql(payload.sql),
            row_count=result_table.num_rows,
            columns=result_table.column_names,
            rows=result_table.to_pylist(),
            logical_plan=logical_plan,
            physical_plan=physical_plan,
        )
    except DatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc