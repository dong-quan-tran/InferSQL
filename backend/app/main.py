# app/main.py
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api import router as api_router
from app.core.exceptions import BadRequestError, InferSQLError, NotFoundError
from app.core.observability import http_request_duration_histogram


app = FastAPI(title="InferSQL API")
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
    return response