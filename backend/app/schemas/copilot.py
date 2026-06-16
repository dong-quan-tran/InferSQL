from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CopilotQueryRequest(BaseModel):
    question: str
    execute: bool = False


class CopilotSqlCandidate(BaseModel):
    sql: str
    assumptions: list[str] = Field(default_factory=list)
    referenced_tables: list[str] = Field(default_factory=list)
    referenced_columns: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class CopilotQueryResponse(BaseModel):
    question: str
    provider: str
    model: str
    candidate: CopilotSqlCandidate
    validation: dict
    execution: dict | None = None


class CopilotHealthResponse(BaseModel):
    provider: Literal["ollama", "remote"]
    model: str
    available: bool