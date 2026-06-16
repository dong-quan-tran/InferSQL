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


class CopilotValidationResult(BaseModel):
    is_valid: bool
    normalized_sql: str
    errors: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    query_type: str | None = None
    has_where: bool = False
    has_group_by: bool = False
    has_order_by: bool = False
    has_limit: bool = False


class CopilotRetryStep(BaseModel):
    attempt: int
    candidate: CopilotSqlCandidate
    validation: CopilotValidationResult


class CopilotQueryResponse(BaseModel):
    question: str
    provider: str
    model: str
    candidate: CopilotSqlCandidate
    validation: CopilotValidationResult
    execution: dict | None = None
    attempts: int = 1
    repaired: bool = False
    retry_history: list[CopilotRetryStep] = Field(default_factory=list)


class CopilotHealthResponse(BaseModel):
    provider: Literal["ollama", "remote"]
    model: str
    available: bool