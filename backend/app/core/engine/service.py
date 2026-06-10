from app.core.engine.interfaces import QueryPlanner
from app.core.engine.parser import QueryParser
from app.core.engine.physical_planner import QueryPlannerService
from app.core.engine.validator import QueryValidator

query_parser = QueryParser()
query_validator = QueryValidator(parser=query_parser)
planner_service = QueryPlannerService(validator=query_validator)


def get_query_planner() -> QueryPlanner:
    return planner_service