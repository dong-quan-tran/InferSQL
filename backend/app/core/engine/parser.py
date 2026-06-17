from __future__ import annotations

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from app.core.exceptions import InvalidQuerySyntaxError, UnsupportedQueryError
from app.schemas.query import PlanNode


class QueryParser:
    def parse(self, sql: str) -> exp.Expression:
        try:
            return parse_one(sql)
        except ParseError as exc:
            raise InvalidQuerySyntaxError("Invalid SQL syntax") from exc

    def validate_select_only(self, expression: exp.Expression) -> None:
        if not isinstance(expression, exp.Select):
            raise UnsupportedQueryError("Only SELECT queries are supported right now")

    def summarize(self, sql: str) -> dict:
        expression = self.parse(sql)

        tables = sorted({table.name for table in expression.find_all(exp.Table)})
        columns = sorted(
            {
                column.alias_or_name
                for column in expression.find_all(exp.Column)
                if column.alias_or_name
            }
        )

        where = expression.args.get("where")
        group = expression.args.get("group")
        order = expression.args.get("order")
        limit = expression.args.get("limit")

        return {
            "query_type": expression.key.upper(),
            "tables": tables,
            "columns": columns,
            "has_where": where is not None,
            "has_group_by": group is not None,
            "has_order_by": order is not None,
            "has_limit": limit is not None,
        }

    def build_logical_plan(self, sql: str) -> PlanNode:
        expression = self.parse(sql)
        self.validate_select_only(expression)

        from_clause = expression.args.get("from_")
        if from_clause is None or from_clause.this is None:
            raise InvalidQuerySyntaxError("Invalid SQL syntax")

        table = from_clause.this.name
        current = PlanNode(
            node_type="Scan",
            details={"table": table},
            children=[],
        )

        where = expression.args.get("where")
        if where is not None:
            predicate = where.this
            current = PlanNode(
                node_type="Filter",
                details={
                    "predicate": {
                        "column": predicate.left.name,
                        "operator": predicate.__class__.__name__.upper(),
                        "value": self._literal_value(predicate.right),
                        "sql": predicate.sql(),
                    }
                },
                children=[current],
            )

            operator_map = {
                "GT": ">",
                "GTE": ">=",
                "LT": "<",
                "LTE": "<=",
                "EQ": "=",
                "NEQ": "!=",
            }
            current.details["predicate"]["operator"] = operator_map.get(
                current.details["predicate"]["operator"],
                current.details["predicate"]["operator"],
            )

        select_expressions = expression.expressions or []
        columns = []
        for item in select_expressions:
            if isinstance(item, exp.Star):
                columns.append("*")
            elif isinstance(item, exp.Column):
                columns.append(item.name)
            else:
                columns.append(item.sql())

        current = PlanNode(
            node_type="Project",
            details={"columns": columns},
            children=[current],
        )

        order = expression.args.get("order")
        if order is not None and order.expressions:
            sort_keys = []
            for ordered in order.expressions:
                if not isinstance(ordered, exp.Ordered):
                    continue

                sort_expr = ordered.this
                if isinstance(sort_expr, exp.Column):
                    column_name = sort_expr.name
                else:
                    column_name = sort_expr.sql()

                sort_keys.append(
                    {
                        "column": column_name,
                        "direction": "DESC" if ordered.args.get("desc") else "ASC",
                    }
                )

            current = PlanNode(
                node_type="Sort",
                details={"keys": sort_keys},
                children=[current],
            )

        limit = expression.args.get("limit")
        if limit is not None and limit.expression is not None:
            current = PlanNode(
                node_type="Limit",
                details={"count": int(limit.expression.name)},
                children=[current],
            )

        return current

    def _literal_value(self, node):
        if isinstance(node, exp.Literal):
            if node.is_string:
                return node.this
            try:
                if "." in node.this:
                    return float(node.this)
                return int(node.this)
            except ValueError:
                return node.this
        return node.sql()