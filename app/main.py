from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as routes_router
from app.core.api_reference import render_api_reference_html
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.db.init_db import init_db

configure_logging()

APP_VERSION = "1.16.0"
STATIC_DIR = Path("app/static")
OPENAPI_TAGS = [
    {"name": "Files", "description": "Excel upload and route-block extraction."},
    {"name": "Routes", "description": "Route listing, route details, and route geometry."},
    {"name": "Optimization Runs", "description": "Background optimization jobs with REST polling."},
    {"name": "System", "description": "Health and aggregate system statistics."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Waste Route Optimizer API",
    version=APP_VERSION,
    description=(
        "Backend service for waste collection route optimization. It imports Excel route data, "
        "extracts individual route blocks, geocodes collection points via OpenStreetMap/Nominatim, "
        "calculates road-based route metrics via OSRM, optimizes point order, and exposes results "
        "through REST endpoints and a React + OpenStreetMap web UI."
    ),
    contact={"name": "Valentin", "email": "work@valentin.in.ua"},
    openapi_tags=OPENAPI_TAGS,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(routes_router, prefix="/api")

assets_dir = STATIC_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse(
            "<h1>React frontend is not built</h1><p>Run <code>npm run build</code> in ./frontend or build the Docker image.</p>",
            status_code=503,
        )
    return FileResponse(index_file)


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} · Swagger UI",
        swagger_ui_parameters={"defaultModelsExpandDepth": 1, "displayRequestDuration": True},
    )





@app.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
def api_reference():
    return HTMLResponse(render_api_reference_html(app.openapi()))

@app.get("/health", tags=["System"], summary="Health check")
def health():
    return {"status": "ok"}
