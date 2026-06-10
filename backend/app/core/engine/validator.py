from sqlglot.errors import ParseError

from app.core.engine.errors import EmptyQueryError, QueryParseError
from app.core.engine.parser import QueryParser


class QueryValidator:
    def __init__(self, parser: QueryParser) -> None:
        self.parser = parser

    def normalize_sql(self, sql: str) -> str:
        return " ".join(sql.strip().split())

    def validate(self, sql: str) -> dict:
        normalized_sql = self.normalize_sql(sql)

        if not normalized_sql:
            raise EmptyQueryError("SQL must not be empty")

        try:
            summary = self.parser.summarize(normalized_sql)
        except ParseError as exc:
            raise QueryParseError("Invalid SQL syntax") from exc

        errors: list[str] = []

        if summary["query_type"] != "SELECT":
            errors.append("Only SELECT queries are supported right now")

        return {
            "sql": sql,
            "normalized_sql": normalized_sql,
            "is_valid": len(errors) == 0,
            "query_type": summary["query_type"],
            "errors": errors,
            "tables": summary["tables"],
            "columns": summary["columns"],
            "has_where": summary["has_where"],
            "has_group_by": summary["has_group_by"],
            "has_order_by": summary["has_order_by"],
            "has_limit": summary["has_limit"],
        }