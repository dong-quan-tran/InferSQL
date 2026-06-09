from sqlglot import exp, parse_one


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

    def build_logical_plan(self, sql: str) -> dict:
        expression = self.parse(sql)

        table = next(expression.find_all(exp.Table), None)
        if table is None:
            raise ValueError("Query must reference a table")

        select_expressions = expression.expressions or []
        projected_columns = [expr.sql() for expr in select_expressions] or ["*"]

        current_node = {
            "node_type": "Scan",
            "details": {
                "table": table.sql(),
            },
            "children": [],
        }

        where_clause = expression.args.get("where")
        if where_clause is not None:
            current_node = {
                "node_type": "Filter",
                "details": {
                    "predicate": where_clause.this.sql(),
                },
                "children": [current_node],
            }

        current_node = {
            "node_type": "Project",
            "details": {
                "columns": projected_columns,
            },
            "children": [current_node],
        }

        limit_clause = expression.args.get("limit")
        if limit_clause is not None and limit_clause.expression is not None:
            limit_value = int(limit_clause.expression.name)
            current_node = {
                "node_type": "Limit",
                "details": {
                    "count": limit_value,
                },
                "children": [current_node],
            }

        return current_node