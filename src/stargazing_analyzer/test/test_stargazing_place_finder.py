# -*- coding: utf-8 -*-
"""
Tests for stargazing_analyzer.stargazing_place_finder module.

Uses mocked GisQueryService and LightPollutionAnalyzer to avoid
network calls and GeoTIFF dependencies.
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock

import pytest

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from models import GeoCoordinate, LatLonBox, Observatory, Peak, Viewpoint
from stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder


@pytest.fixture
def mock_gis_service():
    """Create a mocked GisQueryService."""
    mock = MagicMock()
    mock.query_locations.return_value = []
    mock.find_elevation.return_value = 500.0
    mock.clear_cache.return_value = None
    mock.get_elevation_statistics.return_value = {"total_requests": 0}
    return mock


@pytest.fixture
def finder(mock_gis_service):
    """Create StarGazingPlaceFinder with mocked dependencies."""
    return StarGazingPlaceFinder(
        min_height_difference=100.0,
        light_pollution_analyzer=None,
        gis_service=mock_gis_service,
    )


@pytest.fixture
def mock_bbox():
    """Standard test bounding box."""
    return LatLonBox(south=39.5, west=115.5, north=40.5, east=117.5)


class TestInitialization:
    """Test constructor and config handling."""

    def test_default_gis_service(self):
        """When no gis_service provided, should create a default one."""
        finder = StarGazingPlaceFinder(min_height_difference=100.0)
        assert finder.gis_service is not None
        assert finder.min_height_difference == 100.0

    def test_custom_min_height(self):
        finder = StarGazingPlaceFinder(min_height_difference=200.0)
        assert finder.min_height_difference == 200.0

    def test_config_override(self, mock_gis_service):
        """StargazingConfig should override min_height_difference."""
        from config import StargazingConfig

        config = StargazingConfig(min_height_difference=300.0)
        finder = StarGazingPlaceFinder(
            min_height_difference=100.0,
            config=config,
            gis_service=mock_gis_service,
        )
        assert finder.min_height_difference == 300.0


class TestFindPeaksInArea:
    """Test find_peaks_in_area with mocked GIS service."""

    def test_empty_result(self, finder, mock_bbox):
        """When no data returned, should return empty list."""
        peaks = finder.find_peaks_in_area(mock_bbox, max_locations=5)
        assert peaks == []
        finder.gis_service.query_locations.assert_called()

    def test_with_mock_peak_data(self, mock_gis_service, mock_bbox):
        """When GIS returns peak data, should process into Peak objects."""
        mock_gis_service.query_locations.side_effect = [
            # First call: peak locations
            [
                {
                    "type": "node",
                    "lat": 40.0,
                    "lon": 116.0,
                    "id": 1,
                    "tags": {"name": "Test Peak", "ele": "1200"},
                }
            ],
            # Second call: towns
            [
                {
                    "type": "node",
                    "lat": 39.9,
                    "lon": 116.1,
                    "id": 100,
                    "tags": {"name": "Test Town"},
                }
            ],
        ]
        finder2 = StarGazingPlaceFinder(
            min_height_difference=100.0,
            light_pollution_analyzer=None,
            gis_service=mock_gis_service,
        )
        peaks = finder2.find_peaks_in_area(mock_bbox, max_locations=5)
        assert len(peaks) >= 1
        peak = peaks[0]
        assert isinstance(peak, Peak)
        assert peak.name == "Test Peak"
        assert peak.latitude == 40.0
        assert peak.longitude == 116.0


class TestFindObservatoriesInArea:
    """Test find_observatories_in_area with mocked GIS."""

    def test_empty_result(self, finder, mock_bbox):
        obs = finder.find_observatories_in_area(mock_bbox, max_observatories=3)
        assert obs == []

    def test_with_mock_observatory_data(self, mock_gis_service, mock_bbox):
        mock_gis_service.query_locations.side_effect = [
            [{"type": "node", "lat": 40.0, "lon": 116.0, "id": 1, "tags": {"name": "Obs", "man_made": "observatory"}}],
            [],
        ]
        finder2 = StarGazingPlaceFinder(
            min_height_difference=100.0,
            light_pollution_analyzer=None,
            gis_service=mock_gis_service,
        )
        obs = finder2.find_observatories_in_area(mock_bbox, max_observatories=3)
        assert len(obs) >= 1
        assert isinstance(obs[0], Observatory)
        assert obs[0].name == "Obs"


class TestFindViewpointsInArea:
    """Test find_viewpoints_in_area with mocked GIS."""

    def test_empty_result(self, finder, mock_bbox):
        vp = finder.find_viewpoints_in_area(mock_bbox, max_viewpoints=3)
        assert vp == []

    def test_with_mock_viewpoint_data(self, mock_gis_service, mock_bbox):
        mock_gis_service.query_locations.side_effect = [
            [{"type": "node", "lat": 41.0, "lon": 117.0, "id": 1, "tags": {"name": "VP", "tourism": "viewpoint"}}],
            [],
        ]
        finder2 = StarGazingPlaceFinder(
            min_height_difference=100.0,
            light_pollution_analyzer=None,
            gis_service=mock_gis_service,
        )
        vp = finder2.find_viewpoints_in_area(mock_bbox, max_viewpoints=3)
        assert len(vp) >= 1
        assert isinstance(vp[0], Viewpoint)
        assert vp[0].name == "VP"


class TestCacheAndUtils:
    """Test cache operations and utility methods."""

    def test_clear_cache(self, finder):
        finder.clear_cache()
        finder.gis_service.clear_cache.assert_called_once()

    def test_clear_cache_no_gis(self):
        """clear_cache should not crash when gis_service is None."""
        finder = StarGazingPlaceFinder(min_height_difference=100.0)
        finder.gis_service = None
        finder.clear_cache()  # Should just log a warning, not crash

    def test_get_cache_info(self, finder):
        info = finder.get_cache_info()
        assert info is not None
        assert "elevation_statistics" in info

    def test_get_cache_info_no_gis(self):
        """get_cache_info should return None when gis_service is None."""
        finder = StarGazingPlaceFinder(min_height_difference=100.0)
        finder.gis_service = None
        assert finder.get_cache_info() is None

    def test_calculate_distance(self, finder):
        p1 = GeoCoordinate(latitude=40.0, longitude=116.0)
        p2 = GeoCoordinate(latitude=41.0, longitude=117.0)
        dist = finder.calculate_distance(p1, p2)
        assert dist > 0
        # Rough distance Beijing-ish area: ~130 km
        assert 100 < dist < 200

    def test_save_results_to_json(self, finder):
        peaks = [
            Peak(
                name="P1",
                latitude=40.0,
                longitude=116.0,
                elevation=1000,
                distance_to_nearest_town=25.0,
                nearest_town_name="Test Town",
                location_type="mountain_peak",
                height_difference=200,
            ),
            Peak(
                name="P2",
                latitude=41.0,
                longitude=117.0,
                elevation=800,
                distance_to_nearest_town=15.0,
                nearest_town_name="Another Town",
                location_type="mountain_peak",
                height_difference=150,
            ),
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.close()
            finder.save_results_to_json(peaks, f.name)
            with open(f.name, "r", encoding="utf-8") as rf:
                data = json.load(rf)
            assert data["total_peaks_found"] == 2
            assert len(data["peaks"]) == 2
            assert data["peaks"][0]["name"] == "P1"
            os.unlink(f.name)

    def test_resolve_elevation_with_invalid_ele_tag(self, finder):
        """_resolve_elevation logs warning on invalid ele tag and falls through to gis_service."""
        point = GeoCoordinate(latitude=40.0, longitude=116.0)
        tags = {"ele": "not_a_number", "name": "Test"}
        result = finder._resolve_elevation(tags, point)
        assert result == 500.0  # Falls through to mocked gis_service.find_elevation
        finder.gis_service.find_elevation.assert_called_once_with(40.0, 116.0)
