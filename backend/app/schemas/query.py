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


class QueryPlanResponse(BaseModel):
    sql: str
    normalized_sql: str
    steps: list[str]
    engine: str