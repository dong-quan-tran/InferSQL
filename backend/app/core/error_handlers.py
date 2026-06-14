from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import BadRequestError, InferSQLError, NotFoundError


logger = logging.getLogger("app.errors")


def _error_body(
    request: Request,
    message: str,
    error_type: str,
    status_code: int,
) -> dict:
    request_id = getattr(request.state, "request_id", "unknown")
    return {
        "error": {
            "type": error_type,
            "code": error_type.upper(),
            "message": message,
            "status_code": status_code,
            "request_id": request_id,
        }
    }


def _log_exception(
    request: Request,
    exc: Exception,
    status_code: int,
) -> None:
    logger.warning(
        "request failed",
        extra={
            "http_method": request.method,
            "http_path": request.url.path,
            "http_status_code": status_code,
            "error_type": exc.__class__.__name__,
            "error_code": exc.__class__.__name__.upper(),
            "stage": "error",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BadRequestError)
    async def handle_bad_request_error(
        request: Request,
        exc: BadRequestError,
    ) -> JSONResponse:
        status_code = status.HTTP_400_BAD_REQUEST
        _log_exception(request, exc, status_code)
        return JSONResponse(
            status_code=status_code,
            content=_error_body(
                request=request,
                message=exc.message,
                error_type=exc.__class__.__name__,
                status_code=status_code,
            ),
        )

    @app.exception_handler(NotFoundError)
    async def handle_not_found_error(
        request: Request,
        exc: NotFoundError,
    ) -> JSONResponse:
        status_code = status.HTTP_404_NOT_FOUND
        _log_exception(request, exc, status_code)
        return JSONResponse(
            status_code=status_code,
            content=_error_body(
                request=request,
                message=exc.message,
                error_type=exc.__class__.__name__,
                status_code=status_code,
            ),
        )

    @app.exception_handler(InferSQLError)
    async def handle_generic_infersql_error(
        request: Request,
        exc: InferSQLError,
    ) -> JSONResponse:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        _log_exception(request, exc, status_code)
        return JSONResponse(
            status_code=status_code,
            content=_error_body(
                request=request,
                message=str(exc),
                error_type=exc.__class__.__name__,
                status_code=status_code,
            ),
        )