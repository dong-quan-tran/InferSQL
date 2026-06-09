from app.engine.interfaces import QueryPlanner
from app.engine.planner import QueryPlannerService
from app.engine.validator import QueryValidator

query_validator = QueryValidator()
planner_service = QueryPlannerService(validator=query_validator)


def get_query_planner() -> QueryPlanner:
    return planner_service