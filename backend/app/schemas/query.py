from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    sql: str

    @field_validator("sql")
    @classmethod
    def validate_sql_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("SQL must not be empty")
        return value


class PlanNode(BaseModel):
    node_type: str
    details: dict[str, Any] = Field(default_factory=dict)
    children: list["PlanNode"] = Field(default_factory=list)


class DebugInfo(BaseModel):
    request_id: str
    total_ms: float
    parse_ms: float | None = None
    plan_ms: float | None = None
    execute_ms: float | None = None


class ErrorDetail(BaseModel):
    type: str
    code: str
    message: str
    status_code: int
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SchemaReferenceSummary(BaseModel):
    dataset_name: str
    columns: list[str]
    available_columns: list[str]


class ValidationSummary(BaseModel):
    normalized_sql: str
    query_type: str | None = None
    tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    has_where: bool = False
    has_group_by: bool = False
    has_order_by: bool = False
    has_limit: bool = False
    is_valid: bool = True
    errors: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    row_count: int
    columns: list[str]
    rows: list[dict[str, Any]]


class QueryValidationResponse(BaseModel):
    sql: str
    normalized_sql: str
    is_valid: bool
    query_type: str | None = None
    errors: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    has_where: bool = False
    has_group_by: bool = False
    has_order_by: bool = False
    has_limit: bool = False
    debug: DebugInfo | None = None


class QueryPlanResponse(BaseModel):
    sql: str
    normalized_sql: str
    engine: str
    steps: list[str]
    logical_plan: PlanNode
    physical_plan: PlanNode
    debug: DebugInfo | None = None


class QueryExecuteResponse(BaseModel):
    sql: str
    normalized_sql: str
    row_count: int
    columns: list[str]
    rows: list[dict[str, Any]]
    logical_plan: PlanNode
    physical_plan: PlanNode
    debug: DebugInfo | None = None


PlanNode.model_rebuild()