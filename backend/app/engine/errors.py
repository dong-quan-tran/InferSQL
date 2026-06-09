class QueryPlanningError(Exception):
    pass


class EmptyQueryError(QueryPlanningError):
    pass


class UnsupportedQueryError(QueryPlanningError):
    pass