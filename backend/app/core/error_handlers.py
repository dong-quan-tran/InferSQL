# app/core/error_handlers.py
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import BadRequestError, InferSQLError, NotFoundError

error_logger = logging.getLogger("app.error")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BadRequestError)
    async def bad_request_error_handler(request: Request, exc: BadRequestError):
        error_logger.warning(
            "request failed with bad request error",
            extra={
                "error_type": "bad_request",
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status_code": 400,
            },
        )
        return JSONResponse(
            status_code=400,
            content={"detail": exc.message},
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        error_logger.warning(
            "request failed with not found error",
            extra={
                "error_type": "not_found",
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status_code": 404,
            },
        )
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message},
        )

    @app.exception_handler(InferSQLError)
    async def generic_infersql_error_handler(request: Request, exc: InferSQLError):
        error_logger.error(
            "request failed with internal application error",
            extra={
                "error_type": "infersql_error",
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status_code": 500,
            },
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )