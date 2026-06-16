from __future__ import annotations

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api import router as api_router
from app.core.error_handlers import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.middleware import register_middleware
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router)

    register_exception_handlers(app)
    register_middleware(app)

    FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()