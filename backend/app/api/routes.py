from fastapi import APIRouter, HTTPException, status

from app.core.engine.errors import EmptyQueryError, UnsupportedQueryError
from app.core.engine.service import planner_service
from app.schemas.health import HealthResponse, VersionResponse
from app.schemas.query import QueryPlanRequest, QueryPlanResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(service="infersql-backend", version="0.1.0")


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