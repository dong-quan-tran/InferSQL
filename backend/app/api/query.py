# app/api/query.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_query_service
from app.schemas.query import (
    QueryExecuteResponse,
    QueryPlanResponse,
    QueryRequest,
    QueryValidationResponse,
)
from app.services.query_service import QueryService


router = APIRouter()


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
    query_service: Annotated[QueryService, Depends(get_query_service)] = None,
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
    query_service: Annotated[QueryService, Depends(get_query_service)] = None,
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
    query_service: Annotated[QueryService, Depends(get_query_service)] = None,
) -> QueryExecuteResponse:
    return query_service.execute(
        sql=payload.sql,
        request_id=_request_id(request),
        debug=debug,
    )