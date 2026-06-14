from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request

from app.core.logging import clear_request_id, set_request_id
from app.core.observability import http_request_duration_histogram


access_logger = logging.getLogger("app.access")


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        set_request_id(request_id)

        start = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
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
                "stage": "http",
            },
        )

        clear_request_id()
        return response