from fastapi import APIRouter

from app.api.catalog import router as catalog_router
from app.api.copilot import router as copilot_router
from app.api.health import router as health_router
from app.api.query import router as query_router

router = APIRouter()
router.include_router(health_router)
router.include_router(query_router)
router.include_router(copilot_router)
router.include_router(catalog_router)