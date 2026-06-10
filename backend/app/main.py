from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api import router as api_router
from app.core.observability import query_duration_histogram

app = FastAPI(title="InferSQL API")
app.include_router(api_router)

FastAPIInstrumentor.instrument_app(app)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    response.headers["X-Request-Id"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.3f}"

    query_duration_histogram.record(
        duration_ms,
        attributes={
            "http.method": request.method,
            "http.route": request.url.path,
        },
    )
    return response