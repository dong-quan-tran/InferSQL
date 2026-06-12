# app/api/dependencies.py
from __future__ import annotations

from functools import lru_cache

from app.services.query_service import QueryService


@lru_cache
def get_query_service() -> QueryService:
    return QueryService()