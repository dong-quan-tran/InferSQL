# app/core/lifespan.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.services.query_service import QueryService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(json_logs=settings.log_json, log_level=settings.log_level)

    app.state.query_service = QueryService()

    logger.info(
        "Starting %s env=%s",
        settings.app_name,
        settings.environment,
    )

    yield

    logger.info(
        "Shutting down %s env=%s",
        settings.app_name,
        settings.environment,
    )