from app.engine.interfaces import QueryPlanner
from app.engine.parser import QueryParser
from app.engine.planner import QueryPlannerService
from app.engine.validator import QueryValidator

query_parser = QueryParser()
query_validator = QueryValidator(parser=query_parser)
planner_service = QueryPlannerService(validator=query_validator)


def get_query_planner() -> QueryPlanner:
    return planner_service