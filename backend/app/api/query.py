from fastapi import APIRouter, HTTPException, status

from app.engine.errors import EmptyQueryError, UnsupportedQueryError
from app.engine.service import planner_service
from app.schemas.query import QueryPlanRequest, QueryPlanResponse

router = APIRouter(tags=["query"])


@router.post("/query/plan", response_model=QueryPlanResponse)
def plan_query(payload: QueryPlanRequest) -> QueryPlanResponse:
    try:
        result = planner_service.plan(payload.sql)
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