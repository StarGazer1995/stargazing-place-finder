"""Weather tile server — XYZ slippy-map tiles from Open-Meteo OM files.

Each tile is fetched via the local :class:`OmWeatherReader` (which downloads
and caches the OM file on first use), rendered to a 256×256 RGBA PNG, and
cached in-memory for the tile TTL.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Query, Response
from stargazing_core import (
    OmWeatherReader,
    WeatherModel,
    WeatherVariable,
    render_weather_tile,
    weather_tile_bounds,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["weather-tiles"])

# ── Configuration ──────────────────────────────────────────────────────────

_CACHE_DIR = Path(os.environ.get("OM_CACHE_DIR", str(Path(tempfile.gettempdir()) / "om_cache")))
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_CACHE_TTL = 900.0  # seconds (15 min — weather data updates ~hourly)

# ── Reader singleton (lazy-init, cached per model) ─────────────────────────

_reader_cache: dict[str, OmWeatherReader] = {}
_tile_cache: dict[str, tuple[bytes, float]] = {}


def _get_reader(model: str) -> OmWeatherReader:
    """Return a cached OmWeatherReader for *model*.

    On first call, downloads the OM file to local disk cache (~148 MB).
    Subsequent calls reuse the cached file.
    """
    if model not in _reader_cache:
        _reader_cache[model] = OmWeatherReader(
            WeatherModel(model),
            cache_dir=str(_CACHE_DIR),
        )
    return _reader_cache[model]


# ── Route ──────────────────────────────────────────────────────────────────


@router.get("/api/weather/tiles/{z}/{x}/{y}.png")
async def serve_weather_tile(
    z: int,
    x: int,
    y: int,
    variable: str = Query("cloud_cover", description="Weather variable"),
    model: str = Query("dwd_icon", description="Weather model"),
    time_index: int = Query(0, ge=0, description="Forecast time step index"),
) -> Response:
    """Serve a weather-overlay raster tile (XYZ / slippy map).

    Fetches OM spatial data for the tile bounds, renders to 256×256 RGBA PNG
    with a variable-specific colormap, and caches the result.
    """
    cache_key = f"{model}/{variable}/{time_index}/{z}/{x}/{y}"

    # ---- Fast path: memory cache hit ----
    import time as _time

    entry = _tile_cache.get(cache_key)
    if entry is not None:
        data, created_at = entry
        if _time.time() - created_at < _CACHE_TTL:
            return Response(
                content=data,
                media_type="image/png",
                headers={"Cache-Control": f"public, max-age={int(_CACHE_TTL)}"},
            )
        del _tile_cache[cache_key]

    # ---- Slow path: OM data → render ----
    try:
        var = WeatherVariable(variable)
        reader = _get_reader(model)

        # Map XYZ → lat/lon bounds
        north, south, east, west = weather_tile_bounds(z, x, y)

        # Read window + render in thread pool (blocking I/O + NumPy)
        def _render():
            data = reader.read_window(
                var,
                north=north,
                south=south,
                east=east,
                west=west,
                shape=(256, 256),
                valid_time_index=time_index,
            )
            return render_weather_tile(data, var)

        png_bytes = await asyncio.to_thread(_render)

        # Cache
        _tile_cache[cache_key] = (png_bytes, _time.time())

        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Cache-Control": f"public, max-age={int(_CACHE_TTL)}"},
        )

    except ValueError as exc:
        logger.warning("Weather tile error: %s", exc)
        return Response(status_code=400, content=str(exc))
    except OSError as exc:  # pragma: no cover — requires live network failure
        logger.error("Weather tile fetch error: %s", exc)
        # Return transparent/empty tile on network errors
        from io import BytesIO

        from PIL import Image

        empty = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        buf = BytesIO()
        empty.save(buf, format="PNG")
        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "no-cache"},
        )


@router.get("/api/weather/meta")
async def weather_meta(
    model: str = Query("dwd_icon"),
) -> dict:
    """Return metadata about the current weather model run."""
    try:
        reader = _get_reader(model)
        return {
            "model": reader.model.value,
            "reference_time": reader.reference_time,
            "valid_times": reader.valid_times,  # all time steps
            "total_steps": len(reader.valid_times),
            "variables": reader.available_variables,
        }
    except Exception as exc:
        return {"error": str(exc)}
