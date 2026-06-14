from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.catalog.registry import DatasetRegistry
from app.core.engine.parser import QueryParser
from app.core.engine.physical_planner import PhysicalPlanner
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.services.query_compiler import QueryCompiler
from app.services.query_runner import QueryRunner
from app.services.query_service import QueryService


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(json_logs=settings.log_json, log_level=settings.log_level)

    dataset_registry = DatasetRegistry()
    query_parser = QueryParser()
    physical_planner = PhysicalPlanner()
    query_compiler = QueryCompiler(
        query_parser=query_parser,
        physical_planner=physical_planner,
    )
    query_runner = QueryRunner(dataset_registry=dataset_registry)
    query_service = QueryService(
        settings=settings,
        dataset_registry=dataset_registry,
        query_parser=query_parser,
        query_compiler=query_compiler,
        query_runner=query_runner,
    )

    app.state.settings = settings
    app.state.dataset_registry = dataset_registry
    app.state.query_parser = query_parser
    app.state.physical_planner = physical_planner
    app.state.query_compiler = query_compiler
    app.state.query_runner = query_runner
    app.state.query_service = query_service

    logger.info(
        "Starting %s env=%s",
        settings.app_name,
        settings.environment,
    )

    yield

    logger.info(
        "Shutting down %s env=%s",
        settings.app_name,
        settings.environment,
    )