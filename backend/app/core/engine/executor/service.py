from __future__ import annotations

import pyarrow as pa

from app.core.catalog import DatasetRegistry
from app.schemas.query import PlanNode

from .filter import FilterOperator
from .limit import LimitOperator
from .project import ProjectOperator
from .scan import TableScanOperator
from .sort import SortOperator


class QueryExecutor:
    def __init__(self, registry: DatasetRegistry) -> None:
        self.scan = TableScanOperator(registry)
        self.filter = FilterOperator()
        self.project = ProjectOperator()
        self.sort = SortOperator()
        self.limit = LimitOperator()

    def execute(self, plan: PlanNode) -> pa.Table:
        if plan.node_type == "TableScan":
            return self.scan.execute(plan.details["table"])

        if len(plan.children) != 1:
            raise ValueError(f"{plan.node_type} expects exactly one child")

        input_table = self.execute(plan.children[0])

        if plan.node_type == "Filter":
            predicate = plan.details["predicate"]
            return self.filter.execute(
                input_table,
                column=predicate["column"],
                operator=predicate["operator"],
                value=predicate["value"],
            )

        if plan.node_type == "Project":
            return self.project.execute(input_table, plan.details["columns"])

        if plan.node_type == "Sort":
            return self.sort.execute(input_table, plan.details["keys"])

        if plan.node_type == "Limit":
            return self.limit.execute(input_table, plan.details["limit"])

        raise ValueError(f"Unsupported physical operator: {plan.node_type}")