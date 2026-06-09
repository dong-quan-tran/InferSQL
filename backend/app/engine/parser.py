from sqlglot import exp, parse_one
from sqlglot.errors import ParseError


class QueryParser:
    def parse(self, sql: str) -> exp.Expression:
        return parse_one(sql)

    def summarize(self, sql: str) -> dict:
        expression = self.parse(sql)

        query_type = expression.key.upper()
        tables = sorted({table.sql() for table in expression.find_all(exp.Table)})
        columns = sorted({column.sql() for column in expression.find_all(exp.Column)})

        has_where = expression.args.get("where") is not None
        has_group_by = expression.args.get("group") is not None
        has_order_by = expression.args.get("order") is not None
        has_limit = expression.args.get("limit") is not None

        return {
            "query_type": query_type,
            "tables": tables,
            "columns": columns,
            "has_where": has_where,
            "has_group_by": has_group_by,
            "has_order_by": has_order_by,
            "has_limit": has_limit,
        }

    def is_select(self, sql: str) -> bool:
        expression = self.parse(sql)
        return isinstance(expression, exp.Select)