from app.engine.errors import EmptyQueryError, UnsupportedQueryError


class QueryPlannerService:
    def plan(self, sql: str) -> dict:
        normalized_sql = " ".join(sql.strip().split())

        if not normalized_sql:
            raise EmptyQueryError("SQL must not be empty")

        if not normalized_sql.upper().startswith("SELECT "):
            raise UnsupportedQueryError("Only SELECT queries are supported right now")

        return {
            "sql": sql,
            "normalized_sql": normalized_sql,
            "steps": [
                "parse_sql",
                "validate_sql",
                "build_logical_plan",
                "build_physical_plan",
            ],
            "engine": "infersql-planner",
        }


planner_service = QueryPlannerService()