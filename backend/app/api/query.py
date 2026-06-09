from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.engine.errors import EmptyQueryError, UnsupportedQueryError
from app.engine.interfaces import QueryPlanner
from app.engine.service import get_query_planner
from app.schemas.query import (
    QueryPlanRequest,
    QueryPlanResponse,
    QueryValidationResponse,
)

router = APIRouter(tags=["query"])

QueryPlannerDependency = Annotated[QueryPlanner, Depends(get_query_planner)]


@router.post("/query/validate", response_model=QueryValidationResponse)
def validate_query(
    payload: QueryPlanRequest,
    planner: QueryPlannerDependency,
) -> QueryValidationResponse:
    try:
        result = planner.validate(payload.sql)
    except EmptyQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return QueryValidationResponse(**result)


@router.post("/query/plan", response_model=QueryPlanResponse)
def plan_query(
    payload: QueryPlanRequest,
    planner: QueryPlannerDependency,
) -> QueryPlanResponse:
    try:
        result = planner.plan(payload.sql)
    except EmptyQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except UnsupportedQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return QueryPlanResponse(**result)