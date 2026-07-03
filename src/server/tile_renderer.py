#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamic tile renderer — samples VIIRS GeoTIFF and produces 256×256 PNG tiles.

This module is framework-agnostic (zero Flask/FastAPI dependency).  All functions
return raw bytes or plain Python types; HTTP concerns live in the route layer.

Thread-safety: the LRU tile cache and the colourmap LUT are guarded by locks
following the same ``threading.RLock`` / double-checked-locking pattern used in
``light_pollution.public_api``.
"""

import logging
import math
import threading
import time
from collections import OrderedDict
from io import BytesIO
from typing import Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TILE_SIZE: int = 256
_MAX_TILE_CACHE: int = 500
_TILE_CACHE_TTL: float = 3600.0  # seconds

# LRU tile cache:  dict[str, tuple[bytes, float]]
_tile_cache: OrderedDict[str, Tuple[bytes, float]] = OrderedDict()
_tile_lock = threading.RLock()

# Colormap stops matching the heatmap gradient (value → RGB)
TILE_CMAP_STOPS: list = [
    (0.00, (0, 0, 51)),
    (0.10, (0, 0, 102)),
    (0.20, (0, 51, 153)),
    (0.30, (0, 102, 204)),
    (0.40, (0, 153, 255)),
    (0.50, (0, 204, 102)),
    (0.60, (102, 255, 51)),
    (0.70, (255, 255, 0)),
    (0.80, (255, 153, 0)),
    (0.90, (255, 51, 0)),
    (1.00, (204, 0, 0)),
]

# Pre-built 256-entry RGBA lookup table (lazy-initialised)
_TILE_CMAP_LUT: Optional[np.ndarray] = None
_cmap_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Colourmap LUT
# ---------------------------------------------------------------------------


def build_tile_cmap_lut() -> np.ndarray:
    """Build a 256×4 RGBA lookup table from the colormap stops.

    Thread-safe lazy initialisation with double-checked locking.
    """
    global _TILE_CMAP_LUT
    if _TILE_CMAP_LUT is not None:
        return _TILE_CMAP_LUT

    with _cmap_lock:  # pragma: no cover — double-check for thread race only
        if _TILE_CMAP_LUT is not None:
            return _TILE_CMAP_LUT

        lut = np.zeros((256, 4), dtype=np.uint8)
        for i in range(256):
            v = i / 255.0
            if v <= 0:
                r, g, b = TILE_CMAP_STOPS[0][1]
            elif v >= 1.0:
                r, g, b = TILE_CMAP_STOPS[-1][1]
            else:
                for j in range(len(TILE_CMAP_STOPS) - 1):
                    t0, (r0, g0, b0) = TILE_CMAP_STOPS[j]
                    t1, (r1, g1, b1) = TILE_CMAP_STOPS[j + 1]
                    if t0 <= v <= t1:
                        f = (v - t0) / (t1 - t0)
                        r = int(r0 + (r1 - r0) * f)
                        g = int(g0 + (g1 - g0) * f)
                        b = int(b0 + (b1 - b0) * f)
                        break
            lut[i] = (r, g, b, 255)
        lut[0] = (0, 0, 51, 255)  # intensity=0 → dark sky

        _TILE_CMAP_LUT = lut
        return lut


# ---------------------------------------------------------------------------
# Web Mercator ↔ geographic coordinate helpers
# ---------------------------------------------------------------------------


def tile_to_lat(y: int, z: int) -> float:
    """Convert XYZ tile Y coordinate to latitude (Web Mercator inverse)."""
    n = math.pi - 2.0 * math.pi * y / (1 << z)
    return math.degrees(math.atan(math.sinh(n)))


def tile_to_lng(x: int, z: int) -> float:
    """Convert XYZ tile X coordinate to longitude."""
    return x / (1 << z) * 360.0 - 180.0


def tile_bounds(x: int, y: int, z: int) -> Tuple[float, float, float, float]:
    """Get (north, south, east, west) geographic bounds for an XYZ tile."""
    north = tile_to_lat(y, z)
    south = tile_to_lat(y + 1, z)
    west = tile_to_lng(x, z)
    east = tile_to_lng(x + 1, z)
    return north, south, east, west


# ---------------------------------------------------------------------------
# Tile cache (thread-safe)
# ---------------------------------------------------------------------------


def _empty_tile_png_bytes() -> bytes:
    """Generate a 256×256 fully transparent PNG tile (cached)."""
    key = "__empty__"
    now = time.time()
    with _tile_lock:
        if key in _tile_cache:
            data, created_at = _tile_cache[key]
            if now - created_at < _TILE_CACHE_TTL:
                _tile_cache.move_to_end(key)
                return data
            del _tile_cache[key]

    rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    png_data = buf.getvalue()
    _set_tile_cache(key, png_data)
    return png_data


empty_tile_png = _empty_tile_png_bytes  # public alias


def get_cached_tile(cache_key: str) -> Optional[bytes]:
    """Return cached PNG bytes for *cache_key*, or *None* on miss/expiry.

    Thread-safe.
    """
    with _tile_lock:
        entry = _tile_cache.get(cache_key)
        if entry is None:
            return None
        data, created_at = entry
        if time.time() - created_at < _TILE_CACHE_TTL:
            _tile_cache.move_to_end(cache_key)
            return data
        del _tile_cache[cache_key]
    return None


def set_tile_cache(cache_key: str, png_data: bytes) -> None:
    """Store *png_data* in the LRU tile cache.  Evicts oldest entries if full.

    Thread-safe.
    """
    with _tile_lock:
        if cache_key in _tile_cache:
            _tile_cache.move_to_end(cache_key)
        else:
            while len(_tile_cache) >= _MAX_TILE_CACHE:
                _tile_cache.popitem(last=False)
        _tile_cache[cache_key] = (png_data, time.time())


# Re-export the internal setter for backward-compat (used by the old name)
_set_tile_cache = set_tile_cache


def clear_tile_cache() -> None:
    """Clear the tile cache (for test teardown)."""
    with _tile_lock:
        _tile_cache.clear()


# ---------------------------------------------------------------------------
# GeoTIFF window reading
# ---------------------------------------------------------------------------


def clamp_tile_bounds(
    north: float,
    south: float,
    east: float,
    west: float,
    src,  # rasterio.DatasetReader
) -> Optional[Tuple[float, float, float, float]]:
    """Clamp tile bounds to valid latitude range and GeoTIFF extent.

    Returns ``(north, south, east, west)`` or *None* if there is no overlap
    between the tile and the dataset.
    """
    north = min(north, 90.0)
    south = max(south, -90.0)
    if west > src.bounds.right or east < src.bounds.left or south > src.bounds.top or north < src.bounds.bottom:
        return None
    west = max(west, float(src.bounds.left))
    east = min(east, float(src.bounds.right))
    south = max(south, float(src.bounds.bottom))
    north = min(north, float(src.bounds.top))
    return north, south, east, west


def read_tile_window(
    src,  # rasterio.DatasetReader
    west: float,
    east: float,
    south: float,
    north: float,
    analyzer,  # LightPollutionAnalyzer (or any object with get_skyglow_for_window / _skyglow_* attrs)
) -> Optional[np.ndarray]:
    """Read GeoTIFF data for the geographic window, decimated to TILE_SIZE.

    If the analyzer has a skyglow grid, the skyglow component is added to the
    raw radiance data.

    Returns a 2-D numpy array of shape ``(TILE_SIZE, TILE_SIZE)``, or *None*
    if the window is invalid.
    """
    row_nw, col_nw = src.index(west, north)
    row_se, col_se = src.index(east, south)
    row_start = max(0, min(row_nw, row_se))
    row_end = min(int(src.height), max(row_nw, row_se) + 1)
    col_start = max(0, min(col_nw, col_se))
    col_end = min(int(src.width), max(col_nw, col_se) + 1)
    if row_end <= row_start or col_end <= col_start:
        return None
    data = src.read(
        1,
        window=((row_start, row_end), (col_start, col_end)),
        out_shape=(TILE_SIZE, TILE_SIZE),
    )
    if hasattr(analyzer, "get_skyglow_for_window") and getattr(analyzer, "_skyglow_grid", None) is not None:
        sg = analyzer.get_skyglow_for_window(west, east, south, north, (TILE_SIZE, TILE_SIZE))
        data = data.astype(np.float32) + analyzer._skyglow_weight * sg
    return data


# ---------------------------------------------------------------------------
# PNG rendering
# ---------------------------------------------------------------------------


def render_tile_png(
    data: np.ndarray,
    src,  # rasterio.DatasetReader (for nodata)
    cache_key: str,
) -> bytes:
    """Apply colormap to *data*, encode as PNG, cache, and return bytes."""
    lut = build_tile_cmap_lut()

    if data.dtype.kind == "f":
        valid = ~np.isnan(data)
    else:
        valid = np.ones_like(data, dtype=bool)
    nodata = src.nodata
    if nodata is not None:
        valid = valid & (data != nodata)

    with np.errstate(divide="ignore", invalid="ignore"):
        intensity = np.where(valid, data, 0.0)
        intensity = np.minimum(1.0, 1.0 - 1.0 / (1.0 + intensity * 0.1))
    idx = np.clip((intensity * 255).astype(np.uint8), 0, 255)
    rgba = lut[idx].copy()
    rgba[~valid] = (0, 0, 0, 0)

    img = Image.fromarray(rgba, "RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    png_data = buf.getvalue()
    set_tile_cache(cache_key, png_data)
    return png_data


# ---------------------------------------------------------------------------
# Convenience: full render pipeline for an XY tile
# ---------------------------------------------------------------------------


def render_tile(
    z: int,
    x: int,
    y: int,
    analyzer,  # LightPollutionAnalyzer
) -> Optional[bytes]:
    """Run the full tile-rendering pipeline for tile (z, x, y).

    Returns PNG bytes, or *None* if the tile is outside the dataset.
    """
    cache_key = f"{z}/{x}/{y}"

    # 1. Cache hit?
    cached = get_cached_tile(cache_key)
    if cached is not None:
        return cached

    # 2. Check analyzer
    src = getattr(analyzer, "_src", None)
    if src is None:
        return empty_tile_png()

    # 3. Geographic bounds
    north, south, east, west = tile_bounds(x, y, z)
    bounds = clamp_tile_bounds(north, south, east, west, src)
    if bounds is None:
        return empty_tile_png()
    north, south, east, west = bounds

    # 4. Read window
    try:
        data = read_tile_window(src, west, east, south, north, analyzer)
    except Exception as exc:
        logger.warning("⚠️ Tile read error (%s/%s/%s): %s", z, x, y, exc)
        return empty_tile_png()

    if data is None:
        return empty_tile_png()

    # 5. Render PNG
    try:
        return render_tile_png(data, src, cache_key)
    except Exception as exc:
        logger.warning("⚠️ Tile render error (%s/%s/%s): %s", z, x, y, exc)
        return empty_tile_png()
