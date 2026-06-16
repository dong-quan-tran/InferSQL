from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_copilot_service
from app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from app.schemas.query import ErrorResponse
from app.services.copilot_service import CopilotService


router = APIRouter()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@router.post(
    "/copilot/query",
    response_model=CopilotQueryResponse,
    response_model_exclude_none=True,
    responses={
        400: {"model": ErrorResponse, "description": "Bad copilot request"},
        500: {"model": ErrorResponse, "description": "Internal copilot error"},
    },
)
def copilot_query(
    payload: CopilotQueryRequest,
    request: Request,
    copilot_service: Annotated[CopilotService, Depends(get_copilot_service)],
) -> CopilotQueryResponse:
    return copilot_service.query(
        question=payload.question,
        execute=payload.execute,
        request_id=_request_id(request),
    )