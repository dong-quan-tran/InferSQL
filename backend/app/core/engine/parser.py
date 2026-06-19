from __future__ import annotations

from typing import Any

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

        group = expression.args.get("group")
        select_expressions = expression.expressions or []

        aggregates: list[dict[str, str]] = []
        group_keys: list[str] = []

        if group is not None:
            for group_expr in group.expressions:
                if isinstance(group_expr, exp.Column):
                    group_keys.append(group_expr.name)
                else:
                    group_keys.append(group_expr.sql())

        def _aggregate_arg(node: exp.Expression):
            arg = getattr(node, "this", None)
            if arg is not None:
                return arg
            expressions = getattr(node, "expressions", None) or []
            return expressions[0] if expressions else None

        for item in select_expressions:
            if isinstance(item, exp.Alias):
                target = item.this
                alias = item.alias
            else:
                target = item
                alias = None

            func_name: str | None = None
            column_name: str | None = None

            if isinstance(target, exp.Count):
                func_name = "COUNT"
                arg = _aggregate_arg(target)
                if isinstance(arg, exp.Star) or arg is None:
                    column_name = "*"
                elif isinstance(arg, exp.Column):
                    column_name = arg.name
                else:
                    column_name = arg.sql()

            elif isinstance(target, exp.Sum):
                func_name = "SUM"
                arg = _aggregate_arg(target)
                if isinstance(arg, exp.Column):
                    column_name = arg.name
                else:
                    column_name = arg.sql() if arg is not None else "*"

            elif isinstance(target, exp.Avg):
                func_name = "AVG"
                arg = _aggregate_arg(target)
                if isinstance(arg, exp.Column):
                    column_name = arg.name
                else:
                    column_name = arg.sql() if arg is not None else "*"

            if func_name is not None:
                default_alias = (
                    "count"
                    if func_name == "COUNT" and column_name == "*"
                    else f"{func_name.lower()}_{column_name}"
                )
                aggregates.append(
                    {
                        "func": func_name,
                        "column": column_name or "*",
                        "alias": alias or default_alias,
                    }
                )

        if aggregates or group_keys:
            current = PlanNode(
                node_type="Aggregate",
                details={
                    "group_keys": group_keys,
                    "aggregates": aggregates,
                },
                children=[current],
            )

        columns: list[str] = []
        projections: list[dict[str, str]] = []
        for item in select_expressions:
            if isinstance(item, exp.Star):
                projections.append({"source": "*", "output": "*"})
            elif isinstance(item, exp.Column):
                projections.append({"source": item.name, "output": item.name})
            elif isinstance(item, exp.Alias):
                target = item.this
                if isinstance(target, exp.Column):
                    projections.append({"source": target.name, "output": item.alias})
                else:
                    projections.append({"source": item.alias, "output": item.alias})
            else:
                projections.append({"source": item.sql(), "output": item.sql()})

        current = PlanNode(
            node_type="Project",
            details={
                "columns": [projection["output"] for projection in projections],
                "projections": projections,
            },
            children=[current],
        )

        order = expression.args.get("order")
        if order is not None and order.expressions:
            sort_keys: list[dict[str, Any]] = []
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
    
    def has_join(self, expression: exp.Expression) -> bool:
        return any(True for _ in expression.find_all(exp.Join))