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
    query_service: Annotated[QueryService, Depends(get_query_service)],
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
    query_service: Annotated[QueryService, Depends(get_query_service)],
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
    query_service: Annotated[QueryService, Depends(get_query_service)],
    debug: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> QueryExecuteResponse:
    return query_service.execute(
        sql=payload.sql,
        request_id=_request_id(request),
        debug=debug,
        limit=limit,
        offset=offset,
    )