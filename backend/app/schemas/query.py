from typing import Literal

from pydantic import BaseModel, Field, field_validator


class QueryPlanRequest(BaseModel):
    sql: str = Field(..., min_length=1, examples=["SELECT symbol, close FROM prices LIMIT 10"])

    @field_validator("sql")
    @classmethod
    def validate_sql(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("SQL must not be empty")
        return cleaned


class QueryValidationResponse(BaseModel):
    sql: str
    normalized_sql: str
    is_valid: bool
    query_type: str
    errors: list[str]
    tables: list[str]
    columns: list[str]
    has_where: bool
    has_group_by: bool
    has_order_by: bool
    has_limit: bool


class LogicalPlanNode(BaseModel):
    node_type: Literal["Scan", "Filter", "Project", "Limit"]
    details: dict[str, str | list[str] | int]
    children: list["LogicalPlanNode"] = []


class QueryPlanResponse(BaseModel):
    sql: str
    normalized_sql: str
    steps: list[str]
    engine: str
    logical_plan: LogicalPlanNode


LogicalPlanNode.model_rebuild()