from fastapi import APIRouter

from app.api.copilot import router as copilot_router
from app.api.health import router as health_router
from app.api.query import router as query_router

router = APIRouter()
router.include_router(health_router)
router.include_router(query_router)
router.include_router(copilot_router)


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