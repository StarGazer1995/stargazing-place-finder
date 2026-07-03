"""Unit tests for server.tile_renderer — covers the full tile rendering pipeline."""

import time
from unittest.mock import MagicMock, patch

import numpy as np

from server.tile_renderer import (
    _MAX_TILE_CACHE,
    TILE_SIZE,
    build_tile_cmap_lut,
    clamp_tile_bounds,
    clear_tile_cache,
    empty_tile_png,
    get_cached_tile,
    read_tile_window,
    render_tile,
    render_tile_png,
    set_tile_cache,
    tile_bounds,
    tile_to_lat,
    tile_to_lng,
)


class TestTileCoordinates:
    """Test Web Mercator tile coordinate helpers."""

    def test_tile_to_lat_equator(self):
        """tile_to_lat at zoom 1, y=0 returns ~85° (near north pole)."""
        lat = tile_to_lat(0, 1)
        assert lat > 80

    def test_tile_to_lng_origin(self):
        """tile_to_lng at zoom 1, x=0 returns -180."""
        assert tile_to_lng(0, 1) == -180.0

    def test_tile_bounds_shape(self):
        """tile_bounds returns (north, south, east, west)."""
        n, s, e, w = tile_bounds(0, 0, 1)
        assert n > s
        assert e > w


class TestCmapLut:
    """Test colourmap LUT building."""

    def test_build_lut_returns_256x4(self):
        lut = build_tile_cmap_lut()
        assert lut.shape == (256, 4)
        assert lut.dtype == np.uint8

    def test_build_lut_idempotent(self):
        """build_lut called twice returns same cached LUT."""
        lut1 = build_tile_cmap_lut()
        lut2 = build_tile_cmap_lut()
        assert lut1 is lut2

    def test_lut_darkest_is_blue(self):
        lut = build_tile_cmap_lut()
        r, g, b, a = lut[0]
        assert b > r
        assert a == 255


class TestTileCache:
    """Test the thread-safe tile cache."""

    def setup_method(self):
        clear_tile_cache()

    def teardown_method(self):
        clear_tile_cache()

    def test_empty_tile_png_returns_bytes(self):
        png = empty_tile_png()
        assert isinstance(png, bytes)
        assert png[:4] == b"\x89PNG"
        assert len(png) > 0

    def test_empty_tile_png_cached(self):
        """Second call returns the cached empty tile."""
        png1 = empty_tile_png()
        png2 = empty_tile_png()
        assert png1 == png2  # same cached bytes

    def test_empty_tile_png_expired_regenerates(self):
        """Expired empty tile is regenerated."""
        import server.tile_renderer as tr

        # Insert an expired entry
        with tr._tile_lock:
            tr._tile_cache["__empty__"] = (b"stale", 0.0)
        png = empty_tile_png()
        assert png != b"stale"  # regenerated, not stale

    def test_get_cached_tile_miss_returns_none(self):
        assert get_cached_tile("nonexistent/0/0") is None

    def test_get_cached_tile_hit_returns_data(self):
        from collections import OrderedDict

        import server.tile_renderer as tr

        with tr._tile_lock:
            tr._tile_cache = OrderedDict()
            tr._tile_cache["test/0/0"] = (b"hello", time.time())
        result = get_cached_tile("test/0/0")
        assert result == b"hello"

    def test_get_cached_tile_expired_returns_none(self):
        from collections import OrderedDict

        import server.tile_renderer as tr

        with tr._tile_lock:
            tr._tile_cache = OrderedDict()
            tr._tile_cache["old/0/0"] = (b"stale", 0.0)  # epoch → expired
        assert get_cached_tile("old/0/0") is None

    def test_set_tile_cache_adds_key(self):
        set_tile_cache("k/1/2", b"data")
        assert get_cached_tile("k/1/2") == b"data"

    def test_set_tile_cache_updates_existing(self):
        set_tile_cache("k/1/2", b"first")
        set_tile_cache("k/1/2", b"second")
        assert get_cached_tile("k/1/2") == b"second"

    def test_set_tile_cache_evicts_oldest(self):
        # Fill beyond max
        for i in range(_MAX_TILE_CACHE + 10):
            set_tile_cache(f"k/{i}/0", bytes([i % 256]))
        # Oldest entries should be evicted
        assert get_cached_tile("k/0/0") is None

    def test_clear_tile_cache(self):
        set_tile_cache("test/0/0", b"x")
        clear_tile_cache()
        assert get_cached_tile("test/0/0") is None


class TestClampTileBounds:
    """Test geographic bounds clamping."""

    def _fake_src(self, left=-180, right=180, bottom=-90, top=90):
        src = MagicMock()
        src.bounds.left = left
        src.bounds.right = right
        src.bounds.bottom = bottom
        src.bounds.top = top
        return src

    def test_no_overlap_returns_none(self):
        src = self._fake_src(left=100, right=120)
        assert clamp_tile_bounds(50, 40, 30, 20, src) is None

    def test_clamp_inside_bounds(self):
        src = self._fake_src()
        result = clamp_tile_bounds(50, 40, 120, 110, src)
        assert result == (50, 40, 120, 110)  # unchanged

    def test_clamp_lat_capped(self):
        src = self._fake_src()
        result = clamp_tile_bounds(100, 40, 120, 110, src)
        assert result[0] == 90.0  # north capped


class TestReadTileWindow:
    """Test GeoTIFF window reading."""

    def _fake_src(self, width=500, height=500, data_val=10.0):
        src = MagicMock()
        src.width = width
        src.height = height
        src.bounds.left = -180
        src.bounds.right = 180
        src.bounds.bottom = -90
        src.bounds.top = 90

        def _index(lon, lat):
            col = int((lon + 180) / 360 * width)
            row = int((90 - lat) / 180 * height)
            return row, col

        src.index.side_effect = _index

        data = np.full((TILE_SIZE, TILE_SIZE), data_val, dtype=np.float32)
        src.read.return_value = data
        return src

    def test_read_valid_window(self):
        src = self._fake_src()
        analyzer = MagicMock()
        analyzer._skyglow_grid = None
        result = read_tile_window(src, -10, 10, 30, 50, analyzer)
        assert result is not None
        assert result.shape == (TILE_SIZE, TILE_SIZE)

    def test_read_with_skyglow(self):
        src = self._fake_src()
        analyzer = MagicMock()
        analyzer._skyglow_grid = object()  # not None → triggers skyglow path
        analyzer._skyglow_weight = 0.4
        analyzer.get_skyglow_for_window.return_value = np.zeros((TILE_SIZE, TILE_SIZE), dtype=np.float32)
        result = read_tile_window(src, -10, 10, 30, 50, analyzer)
        assert result is not None
        analyzer.get_skyglow_for_window.assert_called_once()

    def test_read_invalid_window(self):
        src = self._fake_src(width=0, height=0)
        analyzer = MagicMock()
        analyzer._skyglow_grid = None
        result = read_tile_window(src, -10, 10, -50, -30, analyzer)
        assert result is None


class TestRenderTilePng:
    """Test PNG rendering from GeoTIFF data."""

    def _fake_src(self, nodata=None):
        src = MagicMock()
        src.nodata = nodata
        return src

    def test_render_png_returns_bytes(self):
        data = np.full((TILE_SIZE, TILE_SIZE), 5.0, dtype=np.float32)
        src = self._fake_src()
        png = render_tile_png(data, src, "test/0/0")
        assert isinstance(png, bytes)
        assert png[:4] == b"\x89PNG"

    def test_render_png_with_nodata(self):
        data = np.full((TILE_SIZE, TILE_SIZE), 5.0, dtype=np.float32)
        data[0, 0] = -9999.0
        src = self._fake_src(nodata=-9999.0)
        png = render_tile_png(data, src, "test/0/0")
        assert len(png) > 0

    def test_render_png_int_data(self):
        """render_tile_png with integer (non-float) data."""
        data = np.full((TILE_SIZE, TILE_SIZE), 50, dtype=np.int16)
        src = self._fake_src()
        png = render_tile_png(data, src, "int_test/0/0")
        assert len(png) > 0

    def test_render_png_caches_result(self):
        data = np.full((TILE_SIZE, TILE_SIZE), 1.0, dtype=np.float32)
        src = self._fake_src()
        render_tile_png(data, src, "cached_key/0/0")
        assert get_cached_tile("cached_key/0/0") is not None


class TestRenderTilePipeline:
    """Test the full render_tile() convenience function."""

    def _fake_analyzer(self, with_src=True):
        analyzer = MagicMock()
        if with_src:
            src = MagicMock()
            src.width = 1000
            src.height = 1000
            src.bounds.left = -180
            src.bounds.right = 180
            src.bounds.bottom = -90
            src.bounds.top = 90

            def _index(lon, lat):
                return int((90 - lat) / 180 * 1000), int((lon + 180) / 360 * 1000)

            src.index.side_effect = _index
            data = np.full((TILE_SIZE, TILE_SIZE), 1.0, dtype=np.float32)
            src.read.return_value = data
            src.nodata = None
            analyzer._src = src
        else:
            analyzer._src = None
        analyzer._skyglow_grid = None
        return analyzer

    def setup_method(self):
        clear_tile_cache()

    def test_render_tile_returns_png(self):
        analyzer = self._fake_analyzer()
        png = render_tile(5, 10, 10, analyzer)
        # Tile (10,10) at zoom 5: lng ~ -67.5 to -56.25, lat ~ 74.0 to 79.2
        # This should be within our fake bounds
        assert png is not None
        assert isinstance(png, bytes)

    def test_render_tile_no_src_returns_empty(self):
        analyzer = self._fake_analyzer(with_src=False)
        png = render_tile(5, 10, 10, analyzer)
        assert png is not None
        assert len(png) > 0

    def test_render_tile_cache_hit(self):
        # Pre-populate cache
        set_tile_cache("5/10/10", b"cached_result")
        analyzer = self._fake_analyzer(with_src=False)
        png = render_tile(5, 10, 10, analyzer)
        assert png == b"cached_result"

    def test_render_tile_out_of_bounds(self):
        """Tile with coords outside GeoTIFF returns empty tile."""
        analyzer = self._fake_analyzer()
        analyzer._src.bounds.left = 0
        analyzer._src.bounds.right = 1
        analyzer._src.bounds.bottom = 0
        analyzer._src.bounds.top = 1
        png = render_tile(5, 10, 10, analyzer)
        assert png is not None
        assert len(png) > 0

    def test_render_tile_read_error_fallback(self):
        """render_tile returns empty tile when GeoTIFF read raises."""
        analyzer = self._fake_analyzer()
        analyzer._src.read.side_effect = RuntimeError("read failed")
        png = render_tile(5, 10, 10, analyzer)
        assert png is not None
        assert len(png) > 0

    @patch("server.tile_renderer.render_tile_png", side_effect=RuntimeError("render fail"))
    def test_render_tile_render_error_fallback(self, mock_render):
        """render_tile returns empty tile when PNG render raises."""
        analyzer = self._fake_analyzer()
        png = render_tile(5, 10, 10, analyzer)
        assert png is not None
        assert len(png) > 0

    def test_get_cached_tile_move_to_end(self):
        """get_cached_tile moves entry to end on cache hit."""
        from collections import OrderedDict

        import server.tile_renderer as tr

        with tr._tile_lock:
            tr._tile_cache = OrderedDict()
            tr._tile_cache["a/0/0"] = (b"a", time.time())
            tr._tile_cache["b/0/0"] = (b"b", time.time())
        # Cache hit on "a" should move it to end
        result = get_cached_tile("a/0/0")
        assert result == b"a"
        with tr._tile_lock:
            assert list(tr._tile_cache.keys())[-1] == "a/0/0"

    def test_render_tile_data_none_fallback(self):
        """render_tile returns empty tile when read_tile_window returns None."""
        analyzer = self._fake_analyzer()
        # Make src too small to extract any data
        analyzer._src.width = 0
        analyzer._src.height = 0
        png = render_tile(5, 10, 10, analyzer)
        assert png is not None and len(png) > 0

    def test_read_tile_window_empty_row_col(self):
        """read_tile_window returns None when row/col range is empty."""
        src = MagicMock()
        src.width = 0
        src.height = 0
        src.bounds.left = -180
        src.bounds.right = 180
        src.bounds.bottom = -90
        src.bounds.top = 90
        src.index.return_value = (5, 5)
        analyzer = MagicMock()
        analyzer._skyglow_grid = None
        result = read_tile_window(src, -10, 10, 30, 50, analyzer)
        assert result is None
