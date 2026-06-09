from pydantic import BaseModel, Field


class QueryPlanRequest(BaseModel):
    sql: str = Field(..., examples=["SELECT symbol, close FROM prices LIMIT 10"])


class QueryPlanResponse(BaseModel):
    sql: str
    normalized_sql: str
    steps: list[str]
    engine: str