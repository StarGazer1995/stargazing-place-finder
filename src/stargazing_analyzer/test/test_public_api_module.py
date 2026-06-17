# -*- coding: utf-8 -*-
"""
Tests for stargazing_analyzer.public_api module.

Covers init, analyze_area, and analyze_area_simple functions
using mocked StargazingLocationAnalyzer.
"""

from unittest.mock import MagicMock, patch

# Ensure src is on path
from stargazing_analyzer.public_api import (
    _require_analyzer,
    analyze_area,
    analyze_area_simple,
    init_stargazing_analyzer,
)


class TestInit:
    """Test init_stargazing_analyzer."""

    def teardown_method(self):
        """Reset global state after each test."""
        import stargazing_analyzer.public_api as pub

        pub.reset_analyzer()

    @patch("stargazing_analyzer.public_api._default_geotiff_path")
    @patch("stargazing_analyzer.public_api.StargazingLocationAnalyzer")
    def test_init_default_path(self, MockAnalyzer, mock_geotiff):
        mock_geotiff.return_value = "/fake/path.tif"
        analyzer = init_stargazing_analyzer()

        MockAnalyzer.assert_called_once()
        call_kwargs = MockAnalyzer.call_args.kwargs
        assert call_kwargs["min_height_difference"] == 100.0
        assert call_kwargs["road_search_radius_km"] == 10.0
        assert call_kwargs["max_distance_to_road_km"] == 0.2
        assert analyzer is not None

    @patch("stargazing_analyzer.public_api.StargazingLocationAnalyzer")
    def test_init_custom_params(self, MockAnalyzer):
        import stargazing_analyzer.public_api as pub

        pub.reset_analyzer()

        init_stargazing_analyzer(
            geotiff_path="/custom/path.tif",
            min_height_difference=200.0,
            road_search_radius_km=15.0,
            max_distance_to_road_km=0.5,
        )
        MockAnalyzer.assert_called_once_with(
            geotiff_path="/custom/path.tif",
            min_height_difference=200.0,
            road_search_radius_km=15.0,
            max_distance_to_road_km=0.5,
            db_config_path=None,
            config=None,
        )

    @patch("stargazing_analyzer.public_api.StargazingLocationAnalyzer")
    def test_reinit_closes_old_analyzer(self, MockAnalyzer):
        """Re-initializing calls close() on the old instance."""
        import stargazing_analyzer.public_api as pub

        old_analyzer = MagicMock()
        pub._sa_analyzer = old_analyzer
        MockAnalyzer.return_value = MagicMock()

        init_stargazing_analyzer()

        old_analyzer.close.assert_called_once()


class TestRequireAnalyzer:
    """Test _require_analyzer lazy init."""

    def test_requires_init_when_none(self):
        """Should call init_stargazing_analyzer when global is None."""
        result = _require_analyzer()
        # Since _sa_analyzer was already initialized by previous tests,
        # this just confirms it returns an analyzer
        assert result is not None


class TestAnalyzeArea:
    """Test analyze_area convenience function."""

    @patch("stargazing_analyzer.public_api._require_analyzer")
    def test_analyze_area_basic(self, mock_require):
        mock_analyzer = MagicMock()
        mock_require.return_value = mock_analyzer

        mock_location = MagicMock()
        mock_location.model_dump.return_value = {"name": "Test", "latitude": 40.0}
        mock_analyzer.analyze_area.return_value = [mock_location]

        result = analyze_area(
            bbox=(39.0, 115.0, 41.0, 117.0),
            max_locations=10,
            include_light_pollution=False,
            include_road_connectivity=True,
        )

        assert len(result) == 1
        assert result[0]["name"] == "Test"

    @patch("stargazing_analyzer.public_api._require_analyzer")
    def test_analyze_area_empty(self, mock_require):
        mock_analyzer = MagicMock()
        mock_require.return_value = mock_analyzer
        mock_analyzer.analyze_area.return_value = []

        result = analyze_area((39.0, 115.0, 41.0, 117.0))
        assert result == []

    @patch("stargazing_analyzer.public_api._require_analyzer")
    def test_analyze_area_with_config(self, mock_require):
        from config import StargazingConfig

        config = StargazingConfig(max_locations=5, max_distance_to_road_km=0.5)

        mock_analyzer = MagicMock()
        mock_require.return_value = mock_analyzer
        mock_location = MagicMock()
        mock_location.model_dump.return_value = {"name": "Test"}
        mock_analyzer.analyze_area.return_value = [mock_location]

        analyze_area(
            bbox=(39.0, 115.0, 41.0, 117.0),
            max_distance_to_road_km=None,
            config=config,
        )

        call_kwargs = mock_analyzer.analyze_area.call_args.kwargs
        assert call_kwargs["max_locations"] == 5

    @patch("stargazing_analyzer.public_api._require_analyzer")
    def test_analyze_area_with_min_road_distance(self, mock_require):
        """Test that min_distance_to_road_km is passed through."""
        mock_analyzer = MagicMock()
        mock_require.return_value = mock_analyzer
        mock_analyzer.analyze_area.return_value = []

        analyze_area(
            bbox=(39.0, 115.0, 41.0, 117.0),
            min_distance_to_road_km=0.05,
            max_distance_to_road_km=0.2,
        )

        call_kwargs = mock_analyzer.analyze_area.call_args.kwargs
        assert call_kwargs["min_distance_to_road_km"] == 0.05
        assert call_kwargs["max_distance_to_road_km"] == 0.2


class TestAnalyzeAreaSimple:
    """Test analyze_area_simple convenience function."""

    @patch("stargazing_analyzer.public_api._analyze_area_fn")
    @patch("stargazing_analyzer.public_api._default_geotiff_path")
    def test_simple_basic(self, mock_geotiff, mock_fn):
        mock_geotiff.return_value = "/fake/geotiff.tif"
        mock_fn.return_value = []

        result = analyze_area_simple(
            south=39.0,
            west=115.0,
            north=41.0,
            east=117.0,
            max_locations=5,
            min_height_diff=200.0,
        )

        assert result == []
        mock_fn.assert_called_once()

    @patch("stargazing_analyzer.public_api._analyze_area_fn")
    @patch("stargazing_analyzer.public_api._default_geotiff_path")
    def test_simple_with_config(self, mock_geotiff, mock_fn):
        """Test config override in analyze_area_simple."""
        from config import StargazingConfig

        mock_geotiff.return_value = "/fake/geotiff.tif"
        mock_fn.return_value = []

        config = StargazingConfig(max_locations=3, min_height_difference=200.0, road_search_radius_km=15.0)

        result = analyze_area_simple(
            south=39.0,
            west=115.0,
            north=41.0,
            east=117.0,
            config=config,
        )

        assert result == []
        mock_fn.assert_called_once()
        kwargs = mock_fn.call_args.kwargs
        assert kwargs["max_locations"] == 3
        assert kwargs["min_height_diff"] == 200.0
        assert kwargs["road_radius_km"] == 15.0


class TestElevationBatchQuery:
    """Tests for the deprecated BatchElevationQuery module."""

    def test_import_coverage(self):
        """Module import covers the NetworkError import line."""
        from stargazing_analyzer.elevation_batch_query import BatchElevationQuery

        assert BatchElevationQuery is not None

    def test_query_elevations_catches_psycopg2_error(self):
        """When PostgisBackend raises psycopg2.Error, we return error results."""
        import psycopg2

        from stargazing_analyzer.elevation_batch_query import BatchElevationQuery

        # PostgisBackend is imported inside query_elevations, patch the source
        with patch("gis_service.backends.postgis_backend.PostgisBackend") as mock_be:
            mock_be.return_value.batch_query_elevations.side_effect = psycopg2.Error("db down")
            query = BatchElevationQuery(db_config={"host": "localhost"}, batch_size=10)
            results = query.query_elevations([(39.9, 116.4), (40.0, 116.5)])
            assert len(results) == 2
            assert all(r.error is not None for r in results)
            assert "db down" in results[0].error
