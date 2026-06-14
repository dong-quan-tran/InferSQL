from app.core.engine.physical_planner import PhysicalPlanner
from app.schemas.query import PlanNode


def test_build_converts_logical_nodes_to_physical_nodes() -> None:
    logical_plan = PlanNode(
        node_type="Limit",
        details={"count": 5},
        children=[
            PlanNode(
                node_type="Project",
                details={"columns": ["symbol", "close"]},
                children=[
                    PlanNode(
                        node_type="Filter",
                        details={
                            "predicate": {
                                "column": "close",
                                "operator": ">",
                                "value": 100,
                            }
                        },
                        children=[
                            PlanNode(
                                node_type="Scan",
                                details={"table": "prices"},
                                children=[],
                            )
                        ],
                    )
                ],
            )
        ],
    )

    planner = PhysicalPlanner()
    physical_plan = planner.build(logical_plan)

    assert physical_plan.node_type == "Limit"
    assert physical_plan.details == {"limit": 5}

    project = physical_plan.children[0]
    assert project.node_type == "Project"

    filter_node = project.children[0]
    assert filter_node.node_type == "Filter"

    scan = filter_node.children[0]
    assert scan.node_type == "TableScan"
    assert scan.details == {"table": "prices"}