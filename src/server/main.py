#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI application entry point for the Stargazing Place Finder web server.

Serves both the REST API and the static frontend (Leaflet SPA) from a single
uvicorn process — no separate static-file server or CORS needed for same-origin
deployments.

Start::

    uv run uvicorn server.main:app --host 0.0.0.0 --port 5001 --reload
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.routes.health import router as health_router
from server.routes.pollution import router as pollution_router
from server.routes.stargazing import router as stargazing_router
from server.routes.telescope import router as telescope_router
from server.routes.tiles import router as tiles_router
from server.routes.weather_tiles import router as weather_tiles_router

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_SERVER_DIR = Path(__file__).resolve().parent
_STATIC_DIR = (_SERVER_DIR.parent / "source").resolve()

if not _STATIC_DIR.is_dir():  # pragma: no cover — Docker fallback
    _STATIC_DIR = Path(os.getcwd()) / "src" / "source"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — eager init of the LightPollutionAnalyzer
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise the light-pollution analyzer in a thread pool."""
    import asyncio

    from light_pollution.public_api import init_light_pollution_analyzer

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, init_light_pollution_analyzer)
        logger.info("✅ Light pollution analyzer initialised")
    except Exception:
        logger.exception("❌ Light pollution analyzer failed to initialise — server will start degraded")

    yield
    # Shutdown (nothing to clean up right now)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Stargazing Place Finder API",
    description="光污染地图与观星区域分析 API",
    version="0.7.2",
    lifespan=lifespan,
)

# API routes — MUST be registered BEFORE the static mount, otherwise
# FastAPI will try to match /api/* paths against static files first.
app.include_router(health_router)
app.include_router(tiles_router)
app.include_router(pollution_router)
app.include_router(stargazing_router)
app.include_router(telescope_router)
app.include_router(weather_tiles_router)

# Static assets (JS / CSS)
_assets_dir = _STATIC_DIR / "assets"
if _assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

# CORS — needed only for cross-origin deployments (e.g. ?apiBaseUrl= override)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Root → serve the SPA entry point
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    """Serve the Leaflet-based SPA (template.html)."""
    template_path = _STATIC_DIR / "template.html"
    if not template_path.is_file():
        from fastapi.responses import HTMLResponse

        return HTMLResponse(
            "<h1>Frontend not found</h1><p>template.html is missing.</p>",
            status_code=404,
        )
    return FileResponse(template_path)
