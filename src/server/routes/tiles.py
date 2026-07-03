"""Dynamic tile server endpoint — XYZ slippy-map tiles from VIIRS GeoTIFF."""

import asyncio

from fastapi import APIRouter, Response

from light_pollution.public_api import _require_analyzer
from server.tile_renderer import (
    empty_tile_png,
    get_cached_tile,
    render_tile,
)

router = APIRouter(tags=["tiles"])


@router.get("/api/light_pollution/tiles/{z}/{x}/{y}.png")
async def serve_light_pollution_tile(z: int, x: int, y: int) -> Response:
    """Serve a single light-pollution raster tile (XYZ / slippy map).

    Cached tiles are returned synchronously from the event loop; cache misses
    run the full GeoTIFF read + colourmap + PNG encode pipeline inside
    ``asyncio.to_thread`` to avoid blocking the server.
    """
    cache_key = f"{z}/{x}/{y}"

    # Fast path: cache hit (no I/O needed)
    cached = get_cached_tile(cache_key)
    if cached is not None:
        return Response(content=cached, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})

    # Slow path: GeoTIFF read + render in thread pool
    analyzer = await asyncio.to_thread(_require_analyzer)
    png_bytes = await asyncio.to_thread(render_tile, z, x, y, analyzer)

    if png_bytes is None:
        png_bytes = empty_tile_png()

    return Response(content=png_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})
