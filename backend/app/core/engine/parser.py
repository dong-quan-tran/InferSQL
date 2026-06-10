# app/engine/parser.py
from __future__ import annotations

from typing import Any

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from app.schemas.query import PlanNode


class QueryParser:
    def parse(self, sql: str) -> exp.Expression:
        try:
            return parse_one(sql)
        except ParseError as exc:
            raise ValueError("Invalid SQL syntax") from exc

    def validate_select_only(self, expression: exp.Expression) -> None:
        if not isinstance(expression, exp.Select):
            raise ValueError("Only SELECT queries are supported right now")

    def summarize(self, sql: str) -> dict[str, Any]:
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

    def build_logical_plan(self, sql: str) -> PlanNode:
        expression = self.parse(sql)
        self.validate_select_only(expression)

        table = next(expression.find_all(exp.Table), None)
        if table is None:
            raise ValueError("Query must reference a table")

        select_expressions = expression.expressions or []
        projected_columns = [expr.sql() for expr in select_expressions] or ["*"]

        current_node = PlanNode(
            node_type="Scan",
            details={"table": table.sql()},
            children=[],
        )

        where_clause = expression.args.get("where")
        if where_clause is not None:
            predicate = self._parse_predicate(where_clause.this)
            current_node = PlanNode(
                node_type="Filter",
                details={"predicate": predicate},
                children=[current_node],
            )

        current_node = PlanNode(
            node_type="Project",
            details={"columns": projected_columns},
            children=[current_node],
        )

        limit_clause = expression.args.get("limit")
        if limit_clause is not None and limit_clause.expression is not None:
            limit_value = int(limit_clause.expression.name)
            current_node = PlanNode(
                node_type="Limit",
                details={"count": limit_value},
                children=[current_node],
            )

        return current_node

    def _parse_predicate(self, predicate_expr: exp.Expression) -> dict[str, Any]:
        operator_map: dict[type[exp.Expression], str] = {
            exp.EQ: "=",
            exp.NEQ: "!=",
            exp.GT: ">",
            exp.GTE: ">=",
            exp.LT: "<",
            exp.LTE: "<=",
        }

        for expr_type, operator in operator_map.items():
            if isinstance(predicate_expr, expr_type):
                left = predicate_expr.left
                right = predicate_expr.right

                if not isinstance(left, exp.Column):
                    raise ValueError("Only simple column predicates are supported right now")

                return {
                    "column": left.sql(),
                    "operator": operator,
                    "value": self._extract_literal(right),
                    "sql": predicate_expr.sql(),
                }

        raise ValueError("Only simple WHERE predicates are supported right now")

    def _extract_literal(self, expr: exp.Expression) -> Any:
        if isinstance(expr, exp.Literal):
            if expr.is_string:
                return expr.this

            raw = expr.this
            try:
                if "." in raw:
                    return float(raw)
                return int(raw)
            except ValueError:
                return raw

        raise ValueError("Only literal comparisons are supported right now")