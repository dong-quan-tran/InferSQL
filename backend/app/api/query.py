# app/api/query.py
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.schemas.query import (
    QueryExecuteResponse,
    QueryPlanResponse,
    QueryRequest,
    QueryValidationResponse,
)
from app.services.query_service import QueryService


router = APIRouter()
query_service = QueryService()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@router.post(
    "/query/validate",
    response_model=QueryValidationResponse,
    response_model_exclude_none=True,
)
def validate_query(
    payload: QueryRequest,
    request: Request,
    debug: bool = Query(False),
) -> QueryValidationResponse:
    return query_service.validate(
        sql=payload.sql,
        request_id=_request_id(request),
        debug=debug,
    )


@router.post(
    "/query/plan",
    response_model=QueryPlanResponse,
    response_model_exclude_none=True,
)
def plan_query(
    payload: QueryRequest,
    request: Request,
    debug: bool = Query(False),
) -> QueryPlanResponse:
    return query_service.plan(
        sql=payload.sql,
        request_id=_request_id(request),
        debug=debug,
    )


@router.post(
    "/query/execute",
    response_model=QueryExecuteResponse,
    response_model_exclude_none=True,
)
def execute_query(
    payload: QueryRequest,
    request: Request,
    debug: bool = Query(False),
) -> QueryExecuteResponse:
    return query_service.execute(
        sql=payload.sql,
        request_id=_request_id(request),
        debug=debug,
    )