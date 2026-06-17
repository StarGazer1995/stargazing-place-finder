# -*- coding: utf-8 -*-
"""
Tests for light_pollution.public_api module.

Covers conversion utilities, grid helpers, and public API functions
using mocked LightPollutionAnalyzer to avoid GeoTIFF dependency.
"""

from unittest.mock import MagicMock, patch

# Ensure src is on path
from light_pollution.public_api import (
    _calculate_grid_dims,
    _grid_resolution_from_zoom,
    analyze_coordinate,
    bortle_to_sqm,
    brightness_to_bortle,
    radiance_to_bortle,
    radiance_to_brightness,
    radiance_to_pollution_level,
)

# ── Conversion utilities ────────────────────────────────────────────


class TestBrightnessToBortle:
    """Test brightness_to_bortle mapping (backward compat)."""

    def test_class_1_dark_sky(self):
        assert brightness_to_bortle(10) == 1
        assert brightness_to_bortle(28) == 1

    def test_class_9_inner_city(self):
        assert brightness_to_bortle(240) == 9
        assert brightness_to_bortle(255) == 9

    def test_boundary_values(self):
        assert brightness_to_bortle(0) == 1
        assert brightness_to_bortle(29) == 2
        assert brightness_to_bortle(56) == 2
        assert brightness_to_bortle(57) == 3
        assert brightness_to_bortle(84) == 3
        assert brightness_to_bortle(85) == 4

    def test_mid_classes(self):
        """Test brightness 5-8 (lines 94, 96, 98, 100)."""
        assert brightness_to_bortle(112) == 4
        assert brightness_to_bortle(140) == 5
        assert brightness_to_bortle(168) == 6
        assert brightness_to_bortle(196) == 7
        assert brightness_to_bortle(224) == 8


class TestBortleToSqm:
    """Test Bortle → SQM conversion."""

    def test_known_values(self):
        assert bortle_to_sqm(1) == 21.9
        assert bortle_to_sqm(5) == 19.5
        assert bortle_to_sqm(9) == 15.5

    def test_unknown_bortle_defaults(self):
        assert bortle_to_sqm(0) == 20.0
        assert bortle_to_sqm(99) == 20.0


class TestRadianceConversions:
    """Test radiance conversion functions (pure math, no GeoTIFF)."""

    def test_radiance_to_bortle_zero(self):
        assert radiance_to_bortle(0.0) == 1

    def test_radiance_to_bortle_boundaries(self):
        assert radiance_to_bortle(-1.0) == 1
        assert radiance_to_bortle(0.5) == 2
        assert radiance_to_bortle(1.5) == 3
        assert radiance_to_bortle(4.0) == 4
        assert radiance_to_bortle(10.0) == 5
        assert radiance_to_bortle(25.0) == 6
        assert radiance_to_bortle(60.0) == 7
        assert radiance_to_bortle(150.0) == 8
        assert radiance_to_bortle(500.0) == 9

    def test_radiance_to_brightness(self):
        assert radiance_to_brightness(0) == 0
        assert 0 < radiance_to_brightness(1.0) < 255
        # Asymptotically approaches 255 but never quite reaches it
        assert radiance_to_brightness(1000) == 252
        assert radiance_to_brightness(10000) == 254

    def test_radiance_to_pollution_level(self):
        level = radiance_to_pollution_level(0.0)
        assert "Class 1" in level
        level_high = radiance_to_pollution_level(500.0)
        assert "Class 9" in level_high


# ── Grid helper functions ───────────────────────────────────────────


class TestGridHelpers:
    """Test grid resolution and dimension helpers."""

    def test_grid_resolution_from_zoom_low(self):
        assert _grid_resolution_from_zoom(8) == 0.1

    def test_grid_resolution_from_zoom_medium(self):
        assert _grid_resolution_from_zoom(10) == 0.05
        assert _grid_resolution_from_zoom(12) == 0.05

    def test_grid_resolution_from_zoom_high(self):
        assert _grid_resolution_from_zoom(14) == 0.02
        assert _grid_resolution_from_zoom(16) == 0.02

    def test_grid_resolution_from_zoom_max(self):
        assert _grid_resolution_from_zoom(18) == 0.01

    def test_calculate_grid_dims_small(self):
        """Small area should produce at least 1 row and col."""
        rows, cols = _calculate_grid_dims(0.01, 0.01, 0.1)
        assert rows >= 1
        assert cols >= 1

    def test_calculate_grid_dims_large_capped(self):
        """Large area should be capped at max_points=2000."""
        rows, cols = _calculate_grid_dims(20.0, 20.0, 0.01)
        total = rows * cols
        # Should be capped near 2000
        assert total <= 2100
        assert total >= 1500


# ── analyze_coordinate with mocked analyzer ─────────────────────────


class TestAnalyzeCoordinate:
    """Test analyze_coordinate with a mocked LightPollutionAnalyzer."""

    @patch("light_pollution.public_api._require_analyzer")
    def test_successful_analysis(self, mock_require):
        """When analyzer returns valid pollution info."""
        mock_analyzer = MagicMock()
        mock_analyzer.get_light_pollution_color.return_value = MagicMock(
            bortle=3,
            brightness=64,
            rgb=(50, 120, 50),
            hex="#327832",
            overlay_name="VIIRS 2025",
            radiance=1.2,
        )
        mock_require.return_value = mock_analyzer

        result = analyze_coordinate(40.0, 116.0)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["light_pollution"]["bortle_class"] == 3
        assert result["data"]["coordinates"]["lat"] == 40.0
        assert result["data"]["coordinates"]["lng"] == 116.0
        assert "radiance" in result["data"]["light_pollution"]
        assert "rgb" in result["data"]["color_info"]
        mock_analyzer.get_light_pollution_color.assert_called_once_with(40.0, 116.0)

    @patch("light_pollution.public_api._require_analyzer")
    def test_no_data_returns_default(self, mock_require):
        """When analyzer returns None, should return default values with warning."""
        mock_analyzer = MagicMock()
        mock_analyzer.get_light_pollution_color.return_value = None
        mock_require.return_value = mock_analyzer

        result = analyze_coordinate(50.0, 120.0)

        assert result["success"] is True
        assert "warning" in result
        assert result["data"]["light_pollution"]["bortle_class"] == 5
        assert result["data"]["light_pollution"]["brightness"] == 128


class TestInitAndRequire:
    """Test init_light_pollution_analyzer and _require_analyzer."""

    def teardown_method(self):
        """Reset global state after each test."""
        import light_pollution.public_api as pub

        pub._lp_analyzer = None

    @patch("light_pollution.public_api.LightPollutionAnalyzer")
    @patch("light_pollution.public_api._default_geotiff_path")
    def test_init_with_default_path(self, mock_default_path, mock_lp_cls):
        """init with no path uses _default_geotiff_path."""
        import light_pollution.public_api as pub

        pub._lp_analyzer = None
        mock_default_path.return_value = "/fake/path.tif"
        mock_lp_cls.return_value = MagicMock()

        result = pub.init_light_pollution_analyzer()

        assert result is not None
        mock_lp_cls.assert_called_once_with(
            geotiff_path="/fake/path.tif",
            skyglow_sigma_km=15.0,
            skyglow_weight=0.4,
        )

    @patch("light_pollution.public_api.LightPollutionAnalyzer")
    @patch("light_pollution.public_api._default_geotiff_path")
    def test_require_initialises_when_none(self, mock_default_path, mock_lp_cls):
        """_require_analyzer calls init when _lp_analyzer is None."""
        import light_pollution.public_api as pub

        pub._lp_analyzer = None
        mock_lp_cls.return_value = MagicMock()

        result = pub._require_analyzer()

        assert result is not None
        mock_lp_cls.assert_called_once()

    @patch("light_pollution.public_api.LightPollutionAnalyzer")
    @patch("light_pollution.public_api._default_geotiff_path")
    def test_reinit_closes_old_analyzer(self, mock_default_path, mock_lp_cls):
        """Re-initializing calls close() on the old instance."""
        import light_pollution.public_api as pub

        old_analyzer = MagicMock()
        pub._lp_analyzer = old_analyzer
        mock_lp_cls.return_value = MagicMock()

        pub.init_light_pollution_analyzer()

        old_analyzer.close.assert_called_once()

    @patch("light_pollution.public_api.LightPollutionAnalyzer")
    @patch("light_pollution.public_api._default_geotiff_path")
    @patch("light_pollution.public_api._require_analyzer")
    def test_get_light_pollution_grid(self, mock_require, mock_default_path, mock_lp_cls):
        """get_light_pollution_grid with mocked analyzer."""
        import light_pollution.public_api as pub

        # Reset global state
        pub._lp_analyzer = None

        mock_analyzer = MagicMock()
        mock_info = MagicMock(
            bortle=3,
            brightness=64,
            rgb=(50, 120, 50),
            hex="#327832",
            overlay_name="VIIRS",
            radiance=1.2,
        )

        # Mix of real and None (default) results
        call_count = [0]

        def mock_get_color(lat, lng):
            call_count[0] += 1
            # Return None for the first point (forces default), real data for rest
            if call_count[0] == 1:
                return None
            return mock_info

        mock_analyzer.get_light_pollution_color.side_effect = mock_get_color
        mock_require.return_value = mock_analyzer

        # Small bbox -> grid will poll at least 1 point
        result = pub.get_light_pollution_grid(north=40.0, south=39.0, east=117.0, west=115.0, zoom=10)

        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) > 0
        assert "metadata" in result
        assert result["metadata"]["zoom"] == 10
        # At least first point should have default data
        assert result["data"][0]["bortle"] == 5

    @patch("light_pollution.public_api._require_analyzer")
    def test_query_grid_point_returns_none_on_data_error(self, mock_require):
        """_query_grid_point returns None when analyzer raises DataError."""
        import light_pollution.public_api as pub
        from models import DataError

        mock_analyzer = MagicMock()
        mock_analyzer.get_light_pollution_color.side_effect = DataError("test error")
        mock_require.return_value = mock_analyzer

        result = pub._query_grid_point(mock_analyzer, 40.0, 116.0, 0)
        assert result is None

    @patch("light_pollution.public_api._require_analyzer")
    def test_grid_default_point(self, mock_require):
        """_grid_default_point returns fallback structure."""
        import light_pollution.public_api as pub

        result = pub._grid_default_point(40.0, 116.0, 0)
        assert result["lat"] == 40.0
        assert result["lng"] == 116.0
        assert result["bortle"] == 5
        assert result["name"] == "数据点 1"

    def test_default_geotiff_path_returns_path(self):
        """_default_geotiff_path returns a Path object."""
        from light_pollution.public_api import _default_geotiff_path

        path = _default_geotiff_path()
        assert str(path).endswith("viirs_china_2025.tif")


class TestLightPollutionApiIntegration:
    """Test that light_pollution_api uses the same path logic as public_api."""

    def test_api_uses_default_geotiff_path(self):
        """light_pollution_api.init_analyzer uses _default_geotiff_path()."""
        from light_pollution.public_api import _default_geotiff_path

        # The path used by the API must match the canonical one from public_api.
        # We can't easily mock the analyzer init without the actual GeoTIFF,
        # but we verify the path would be derived from the same source.
        expected = str(_default_geotiff_path())
        assert expected.endswith("viirs_china_2025.tif")

    @patch("light_pollution.light_pollution_api.LightPollutionAnalyzer")
    @patch("light_pollution.light_pollution_api._default_geotiff_path")
    def test_init_analyzer_calls_default_geotiff_path(self, mock_geotiff, mock_lp):
        """init_analyzer() calls _default_geotiff_path() (line 41)."""
        from light_pollution.light_pollution_api import init_analyzer as ia

        mock_geotiff.return_value = "/fake/path.tif"
        mock_lp.return_value = MagicMock()

        ia()

        mock_geotiff.assert_called_once()
        mock_lp.assert_called_once_with(geotiff_path="/fake/path.tif", skyglow_sigma_km=15.0, skyglow_weight=0.4)

    @patch("light_pollution.light_pollution_api.analyze_stargazing_area")
    @patch("light_pollution.light_pollution_api._default_geotiff_path")
    def test_analyze_stargazing_area_endpoint(self, mock_geotiff_path, mock_analyze):
        """post_analyze_area uses _default_geotiff_path() (line 766)."""
        from light_pollution.light_pollution_api import app

        mock_geotiff_path.return_value = "/fake/path.tif"
        mock_analyze.return_value = []

        with app.test_client() as client:
            resp = client.post(
                "/api/analyze_stargazing_area",
                json={
                    "north": 41.0,
                    "south": 39.0,
                    "east": 117.0,
                    "west": 115.0,
                    "max_locations": 5,
                    "min_height_diff": 100,
                    "road_radius_km": 10,
                    "network_type": "drive",
                },
            )
            assert resp.status_code == 200

        mock_geotiff_path.assert_called()
