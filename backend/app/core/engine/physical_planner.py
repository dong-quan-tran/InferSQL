# app/core/engine/physical_planner.py
from __future__ import annotations

from app.schemas.query import PlanNode

LOGICAL_TO_PHYSICAL = {
    "Scan": "TableScan",
    "Filter": "Filter",
    "Project": "Project",
    "Limit": "Limit",
}


class PhysicalPlanner:
    def build(self, logical_plan: PlanNode) -> PlanNode:
        return self._convert_node(logical_plan)

    def _convert_node(self, node: PlanNode) -> PlanNode:
        details = dict(node.details)

        if node.node_type == "Limit" and "count" in details:
            details = {"limit": details["count"]}

        return PlanNode(
            node_type=LOGICAL_TO_PHYSICAL.get(node.node_type, node.node_type),
            details=details,
            children=[self._convert_node(child) for child in node.children],
        )