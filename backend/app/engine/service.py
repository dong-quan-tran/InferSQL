from app.engine.interfaces import QueryPlanner
from app.engine.planner import planner_service


def get_query_planner() -> QueryPlanner:
    return planner_service