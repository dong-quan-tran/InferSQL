from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_query_service
from app.schemas.query import (
    ErrorResponse,
    QueryExecuteResponse,
    QueryPlanResponse,
    QueryRequest,
    QueryValidationResponse,
)
from app.services.query_service import QueryService

router = APIRouter()

ERROR_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "Bad request, invalid SQL syntax, or unsupported query shape",
    },
    404: {
        "model": ErrorResponse,
        "description": "Referenced dataset not found",
    },
    500: {
        "model": ErrorResponse,
        "description": "Internal InferSQL error or execution engine failure",
    },
}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _set_request_debug(request: Request, debug: bool) -> None:
    request.state.debug = debug


@router.post(
    "/query/validate",
    response_model=QueryValidationResponse,
    response_model_exclude_none=True,
    summary="Validate a SQL query",
    description=(
        "Parses and validates a SQL query without executing it. "
        "Returns normalized SQL, referenced tables and columns, query-shape flags, "
        "and validation errors when present. "
        "When `debug=true`, the response may include diagnostic metadata."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Bad request, invalid SQL syntax, or unsupported query shape",
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal InferSQL error",
        },
    },
)
def validate_query(
    payload: QueryRequest,
    request: Request,
    query_service: Annotated[QueryService, Depends(get_query_service)],
    debug: bool = Query(False, description="Include diagnostic metadata in the response"),
) -> QueryValidationResponse:
    _set_request_debug(request, debug)
    return query_service.validate(
        sql=payload.sql,
        request_id=_request_id(request),
        debug=debug,
    )


@router.post(
    "/query/plan",
    response_model=QueryPlanResponse,
    response_model_exclude_none=True,
    summary="Build a query plan",
    description=(
        "Builds a logical and physical plan for a SQL query without returning result rows. "
        "Uses the custom planner when supported and falls back to the execution engine planner "
        "for broader SQL shapes. When `debug=true`, the response may include diagnostic metadata."
    ),
    responses=ERROR_RESPONSES,
)
def plan_query(
    payload: QueryRequest,
    request: Request,
    query_service: Annotated[QueryService, Depends(get_query_service)],
    debug: bool = Query(False, description="Include diagnostic metadata in the response"),
) -> QueryPlanResponse:
    _set_request_debug(request, debug)
    return query_service.plan(
        sql=payload.sql,
        request_id=_request_id(request),
        debug=debug,
    )


@router.post(
    "/query/execute",
    response_model=QueryExecuteResponse,
    response_model_exclude_none=True,
    summary="Execute a SQL query",
    description=(
        "Executes a SQL query and returns result rows. "
        "Supports result pagination through `limit` and `offset`. "
        "When `debug=true`, the response or error body may include diagnostic metadata."
    ),
    responses=ERROR_RESPONSES,
)
def execute_query(
    payload: QueryRequest,
    request: Request,
    query_service: Annotated[QueryService, Depends(get_query_service)],
    debug: bool = Query(False, description="Include diagnostic metadata in the response"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip before returning results"),
) -> QueryExecuteResponse:
    _set_request_debug(request, debug)
    return query_service.execute(
        sql=payload.sql,
        request_id=_request_id(request),
        debug=debug,
        limit=limit,
        offset=offset,
    )