from typing import Protocol


class QueryPlanner(Protocol):
    def normalize_sql(self, sql: str) -> str:
        ...

    def detect_query_type(self, sql: str) -> str:
        ...

    def validate(self, sql: str) -> dict:
        ...

    def plan(self, sql: str) -> dict:
        ...