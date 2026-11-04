"""Dynamic tile server endpoint — XYZ slippy-map tiles from VIIRS GeoTIFF."""

import asyncio

from fastapi import APIRouter, Response

from light_pollution.public_api import _require_analyzer
from server.tile_renderer import (
    empty_tile_png,
    render_tile,
)

router = APIRouter(tags=["tiles"])


@router.get("/api/light_pollution/tiles/{z}/{x}/{y}.png")
async def serve_light_pollution_tile(z: int, x: int, y: int) -> Response:
    """Serve a single light-pollution raster tile (XYZ / slippy map).

    Resolve the current analyzer before its handle-scoped cache lookup. The
    lookup and GeoTIFF read + colourmap + PNG pipeline run in a worker thread.
    Reinitializing the analyzer cannot reuse a previous handle's cached tile.
    """
    analyzer = await asyncio.to_thread(_require_analyzer)
    png_bytes = await asyncio.to_thread(render_tile, z, x, y, analyzer)

    if png_bytes is None:
        png_bytes = empty_tile_png()

    return Response(content=png_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})
