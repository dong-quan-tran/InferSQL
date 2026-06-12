# app/main.py
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api import router as api_router
from app.core.exceptions import BadRequestError, InferSQLError, NotFoundError
from app.core.logging import configure_logging, set_request_id
from app.core.observability import http_request_duration_histogram
from app.core.settings import get_settings

logger = logging.getLogger(__name__)
access_logger = logging.getLogger("app.access")

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(json_logs=settings.log_json, log_level=settings.log_level)

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


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router)

    FastAPIInstrumentor.instrument_app(app)

    @app.exception_handler(BadRequestError)
    async def bad_request_error_handler(request: Request, exc: BadRequestError):
        return JSONResponse(
            status_code=400,
            content={"detail": exc.message},
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message},
        )

    @app.exception_handler(InferSQLError)
    async def generic_infersql_error_handler(request: Request, exc: InferSQLError):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        set_request_id(request_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-Id"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.3f}"

        http_request_duration_histogram.record(
            duration_ms,
            attributes={
                "http.method": request.method,
                "http.target": request.url.path,
            },
        )

        access_logger.info(
            "request completed",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status_code": response.status_code,
                "duration_ms": round(duration_ms, 3),
                "client_ip": request.client.host if request.client else None,
            },
        )

        return response

    return app


app = create_app()