from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from app.main import create_app

api = create_app()


@asynccontextmanager
async def lifespan(application):
    async with api.router.lifespan_context(api):
        yield


async def demo_catalog_read_only(request):
    return JSONResponse({"detail": "Dataset imports are disabled on this public demo."}, status_code=403)


dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
app = Starlette(routes=[
    Route("/api/catalog/ingest", demo_catalog_read_only, methods=["POST"]),
    Route("/api/catalog/upload", demo_catalog_read_only, methods=["POST"]),
    Mount("/api", app=api),
    Mount("/", app=StaticFiles(directory=dist, html=True)),
], lifespan=lifespan)