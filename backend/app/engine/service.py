class QueryPlannerService:
    def plan(self, sql: str) -> dict:
        normalized_sql = " ".join(sql.strip().split())

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