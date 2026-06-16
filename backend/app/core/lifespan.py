from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.catalog.registry import DatasetRegistry
from app.core.engine.parser import QueryParser
from app.core.engine.physical_planner import PhysicalPlanner
from app.core.logging import configure_logging
from app.core.settings import Settings, get_settings
from app.services.copilot_service import CopilotService
from app.services.llm.ollama_provider import OllamaLLMProvider
from app.services.llm.remote_provider import RemoteLLMProvider
from app.services.query_compiler import QueryCompiler
from app.services.query_runner import QueryRunner
from app.services.query_service import QueryService

logger = logging.getLogger(__name__)


def build_query_service(settings: Settings) -> QueryService:
    dataset_registry = DatasetRegistry()
    query_parser = QueryParser()
    physical_planner = PhysicalPlanner()
    query_compiler = QueryCompiler(
        query_parser=query_parser,
        physical_planner=physical_planner,
    )
    query_runner = QueryRunner(dataset_registry=dataset_registry)

    return QueryService(
        settings=settings,
        dataset_registry=dataset_registry,
        query_parser=query_parser,
        query_compiler=query_compiler,
        query_runner=query_runner,
    )


def build_llm_provider(settings: Settings):
    if settings.llm_provider == "ollama":
        return OllamaLLMProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=settings.llm_temperature,
        )

    return RemoteLLMProvider(model=settings.remote_llm_model)


def bind_app_state(
    app: FastAPI,
    settings: Settings,
    query_service: QueryService,
    copilot_service: CopilotService,
    llm_provider,
) -> None:
    app.state.settings = settings
    app.state.dataset_registry = query_service.dataset_registry
    app.state.query_parser = query_service.query_parser
    app.state.physical_planner = query_service.query_compiler.physical_planner
    app.state.query_compiler = query_service.query_compiler
    app.state.query_runner = query_service.query_runner
    app.state.query_service = query_service
    app.state.llm_provider = llm_provider
    app.state.copilot_service = copilot_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(json_logs=settings.log_json, log_level=settings.log_level)

    query_service = build_query_service(settings=settings)
    llm_provider = build_llm_provider(settings=settings)
    copilot_service = CopilotService(
        dataset_registry=query_service.dataset_registry,
        query_service=query_service,
        llm_provider=llm_provider,
    )

    bind_app_state(
        app,
        settings=settings,
        query_service=query_service,
        copilot_service=copilot_service,
        llm_provider=llm_provider,
    )

    logger.info(
        "Starting %s env=%s",
        settings.app_name,
        settings.environment,
        extra={
            "stage": "startup",
            "environment": settings.environment,
            "llm_provider": settings.llm_provider,
            "llm_model": getattr(llm_provider, "model_name", "unknown"),
        },
    )

    yield

    logger.info(
        "Shutting down %s env=%s",
        settings.app_name,
        settings.environment,
        extra={
            "stage": "shutdown",
            "environment": settings.environment,
            "llm_provider": settings.llm_provider,
            "llm_model": getattr(llm_provider, "model_name", "unknown"),
        },
    )