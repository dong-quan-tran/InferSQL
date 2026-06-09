from app.engine.errors import EmptyQueryError


class QueryValidator:
    def normalize_sql(self, sql: str) -> str:
        return " ".join(sql.strip().split())

    def detect_query_type(self, sql: str) -> str:
        normalized_sql = self.normalize_sql(sql)
        if not normalized_sql:
            return "unknown"

        return normalized_sql.split(" ", 1)[0].upper()

    def validate(self, sql: str) -> dict:
        normalized_sql = self.normalize_sql(sql)

        if not normalized_sql:
            raise EmptyQueryError("SQL must not be empty")

        query_type = self.detect_query_type(normalized_sql)
        errors: list[str] = []

        if query_type != "SELECT":
            errors.append("Only SELECT queries are supported right now")

        return {
            "sql": sql,
            "normalized_sql": normalized_sql,
            "is_valid": len(errors) == 0,
            "query_type": query_type,
            "errors": errors,
        }