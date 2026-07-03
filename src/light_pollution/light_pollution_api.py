#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backward-compatibility shim for the old Flask-based API server.

The Flask web layer has been replaced by FastAPI in ``server.main``.
This module remains importable so that existing code (especially tests)
that references module-level state and helper functions does not break.

.. deprecated::
    Import from ``server.tile_renderer`` and ``server.main`` directly
    in new code.
"""

import logging
import warnings

from light_pollution.public_api import _require_analyzer, init_light_pollution_analyzer  # noqa: E402
from server.tile_renderer import (
    _MAX_TILE_CACHE,
    _TILE_CACHE_TTL,
    build_tile_cmap_lut,
    clamp_tile_bounds,
    read_tile_window,
    render_tile_png,
    tile_bounds,
    tile_to_lat,
    tile_to_lng,
)
from server.tile_renderer import (
    TILE_SIZE as _TILE_SIZE,
)
from server.tile_renderer import (
    _tile_cache as tile_cache_obj,
)

warnings.warn(
    "light_pollution.light_pollution_api is deprecated. Use server.main instead.",
    DeprecationWarning,
    stacklevel=2,
)

logger = logging.getLogger(__name__)

# Convenience alias for the old name
init_analyzer = init_light_pollution_analyzer

# ---------------------------------------------------------------------------
# Compatibility Response wrapper
# ---------------------------------------------------------------------------


class _CompatResponse:
    """Minimal response-like object with ``.data`` and ``.mimetype``."""

    __slots__ = ("data", "mimetype")

    def __init__(self, data: bytes, mimetype: str = "image/png") -> None:
        self.data = data
        self.mimetype = mimetype


# Module-level state aliases (matching old names)
_tile_cache = tile_cache_obj  # shared OrderedDict

# Lazy access to the analyzer (via the public_api singleton)
# The old code did ``api.analyzer`` to check if it was None.
try:
    _analyzer = _require_analyzer()
except Exception:  # pragma: no cover — environment-dependent
    _analyzer = None
analyzer = _analyzer  # module-level for backward compat


# ---------------------------------------------------------------------------
# Compatibility wrappers — self-contained implementations that operate on
# the shim module's own ``_tile_cache`` (so that tests can replace it).
# ---------------------------------------------------------------------------


def _empty_tile() -> _CompatResponse:
    """Return a 256×256 fully transparent PNG tile (self-contained compat)."""
    import time
    from io import BytesIO

    import numpy as np
    from PIL import Image

    key = "__empty__"
    now = time.time()
    if key in _tile_cache:
        data, created_at = _tile_cache[key]
        if now - created_at < _TILE_CACHE_TTL:
            # Move to end (LRU) — OrderedDict compatible
            _tile_cache.move_to_end(key)
            return _CompatResponse(data)
        del _tile_cache[key]

    rgba = np.zeros((_TILE_SIZE, _TILE_SIZE, 4), dtype=np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    png_data = buf.getvalue()
    _set_tile_cache(key, png_data)
    return _CompatResponse(png_data)


def _validate_tile_request(z: int, x: int, y: int):
    """Check analyzer and tile cache; return cached response or None (compat).

    References the mutable ``analyzer`` module-level variable so that tests
    can patch it via ``api.analyzer = ...``.
    """
    import time as _time

    if analyzer is None:
        return _empty_tile()
    try:
        src = getattr(analyzer, "_src", None)
    except Exception:  # pragma: no cover — unexpected getattr failure
        src = None
    if src is None:
        return _empty_tile()

    cache_key = f"{z}/{x}/{y}"
    entry = _tile_cache.get(cache_key)
    if entry is not None:
        data, created_at = entry
        if _time.time() - created_at < _TILE_CACHE_TTL:
            _tile_cache.move_to_end(cache_key)
            return _CompatResponse(data)
        del _tile_cache[cache_key]
    return None


def _render_tile_png(data, src, cache_key: str) -> _CompatResponse:
    """Render tile, store in cache, return compat response (self-contained)."""
    png_data = render_tile_png(data, src, cache_key)
    # Ensure the compat cache is also synced (render_tile_png writes to
    # tile_renderer's cache, but we mirror it here for backward compat).
    _tile_cache[cache_key] = _tile_cache.get(cache_key, (png_data, __import__("time").time()))
    return _CompatResponse(png_data)


# Standalone cache helper (operates on shim's _tile_cache)
def _set_tile_cache(key: str, png_data: bytes) -> None:
    """Store *png_data* in the shim LRU cache (evicts oldest if full)."""
    import time as _time

    if key in _tile_cache:
        _tile_cache.move_to_end(key)
    else:
        while len(_tile_cache) >= _MAX_TILE_CACHE:
            _tile_cache.popitem(last=False)
    _tile_cache[key] = (png_data, _time.time())


# Alias that delegates to tile_renderer.tile_to_lat
def _tile_to_lat(y: int, z: int) -> float:
    return tile_to_lat(y, z)


def _tile_to_lng(x: int, z: int) -> float:
    return tile_to_lng(x, z)


def _tile_bounds(x: int, y: int, z: int):
    return tile_bounds(x, y, z)


def _clamp_tile_bounds(north, south, east, west, src):
    return clamp_tile_bounds(north, south, east, west, src)


def _read_tile_window(src, west, east, south, north):
    # Note: the old function signature was (src, west, east, south, north)
    return read_tile_window(src, west, east, south, north, _analyzer)


def _build_tile_cmap_lut():
    return build_tile_cmap_lut()
