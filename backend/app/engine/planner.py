from app.engine.errors import UnsupportedQueryError
from app.engine.validator import QueryValidator


class QueryPlannerService:
    def __init__(self, validator: QueryValidator) -> None:
        self.validator = validator

    def normalize_sql(self, sql: str) -> str:
        return self.validator.normalize_sql(sql)

    def detect_query_type(self, sql: str) -> str:
        return self.validator.detect_query_type(sql)

    def validate(self, sql: str) -> dict:
        return self.validator.validate(sql)

    def plan(self, sql: str) -> dict:
        validation = self.validator.validate(sql)

        if not validation["is_valid"]:
            raise UnsupportedQueryError(validation["errors"][0])

        return {
            "sql": sql,
            "normalized_sql": validation["normalized_sql"],
            "steps": [
                "parse_sql",
                "validate_sql",
                "build_logical_plan",
                "build_physical_plan",
            ],
            "engine": "infersql-planner",
        }