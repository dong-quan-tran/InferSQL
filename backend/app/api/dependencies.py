from __future__ import annotations

from fastapi import Request

from app.core.catalog.registry import DatasetRegistry
from app.core.engine.parser import QueryParser
from app.core.engine.physical_planner import PhysicalPlanner
from app.core.settings import Settings, get_settings
from app.services.query_compiler import QueryCompiler
from app.services.query_runner import QueryRunner
from app.services.query_service import QueryService


def get_settings_dependency() -> Settings:
    return get_settings()


def get_dataset_registry(request: Request) -> DatasetRegistry:
    return request.app.state.dataset_registry


def get_query_parser(request: Request) -> QueryParser:
    return request.app.state.query_parser


def get_physical_planner(request: Request) -> PhysicalPlanner:
    return request.app.state.physical_planner


def get_query_compiler(request: Request) -> QueryCompiler:
    return request.app.state.query_compiler


def get_query_runner(request: Request) -> QueryRunner:
    return request.app.state.query_runner


def get_query_service(request: Request) -> QueryService:
    return request.app.state.query_service