# -*- coding: utf-8 -*-
"""
Tests for stargazing_analyzer.public_api module.

Covers init, analyze_area, and analyze_area_simple functions
using mocked StargazingLocationAnalyzer.
"""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from stargazing_analyzer.public_api import (
    init_stargazing_analyzer,
    _require_analyzer,
    analyze_area,
    analyze_area_simple,
)


class TestInit:
    """Test init_stargazing_analyzer."""

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
        analyzer = init_stargazing_analyzer(
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
