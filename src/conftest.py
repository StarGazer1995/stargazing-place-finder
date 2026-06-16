# -*- coding: utf-8 -*-
"""
Shared test fixtures and configuration for the stargazing-place-finder test suite.

Auto-discovered by pytest via ``conftest.py`` — all fixtures defined here are
available to every ``test_*.py`` file under ``src/`` without explicit import.
"""

from unittest.mock import MagicMock, Mock

import pytest

from models import GeoCoordinate, LatLonBox, StargazingLocation

# ═══════════════════════════════════════════════════════════════════
# Standard geographic coordinates (used across multiple test modules)
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def bbox_beijing():
    """Beijing Xiangshan area bounding box ``(south, west, north, east)``."""
    return 39.98, 116.18, 40.02, 116.22


@pytest.fixture
def latlon_box_beijing() -> LatLonBox:
    """Standard ``LatLonBox`` for Beijing-region integration tests."""
    return LatLonBox(south=39.5, west=115.5, north=40.5, east=117.5)


@pytest.fixture
def coord_tiananmen() -> GeoCoordinate:
    """Tiananmen Square coordinate for road connectivity tests."""
    return GeoCoordinate(latitude=39.9042, longitude=116.4074)


@pytest.fixture
def coord_beijing() -> GeoCoordinate:
    """Generic Beijing coordinate for general-purpose tests."""
    return GeoCoordinate(latitude=40.0, longitude=116.0)


# ═══════════════════════════════════════════════════════════════════
# Mocked dependency objects
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_gis_service():
    """``MagicMock`` simulating a ``GisQueryService`` with no-op defaults."""
    mock = MagicMock()
    mock.query_locations.return_value = []
    mock.find_elevation.return_value = 500.0
    mock.clear_cache.return_value = None
    mock.get_elevation_statistics.return_value = {"total_requests": 0}
    return mock


@pytest.fixture
def mock_light_analyzer():
    """``MagicMock`` simulating a ``LightPollutionAnalyzer`` with no-op defaults."""
    mock = Mock()
    mock.batch_analyze_coordinates.return_value = {}
    mock.get_luminance_at.return_value = (10.0, 3)
    mock.close.return_value = None
    return mock


@pytest.fixture
def mock_road_checker():
    """``MagicMock`` simulating a ``RoadConnectivityChecker``."""
    mock = MagicMock()
    mock.get_accessibility_info.return_value = {
        "accessible": True,
        "distance_to_road_km": 0.5,
        "nearest_road_type": "secondary",
    }
    return mock


@pytest.fixture
def mock_finder():
    """``MagicMock`` simulating a ``StarGazingPlaceFinder`` with empty returns."""
    mock = MagicMock()
    mock.find_peaks_in_area.return_value = []
    mock.find_observatories_in_area.return_value = []
    mock.find_viewpoints_in_area.return_value = []
    mock.get_towns_from_overpass.return_value = []
    return mock


# ═══════════════════════════════════════════════════════════════════
# Sample test data
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_stargazing_location() -> StargazingLocation:
    """A single ``StargazingLocation`` with moderate attributes."""
    return StargazingLocation(
        name="Test Peak",
        latitude=40.0,
        longitude=116.0,
        elevation=1000.0,
        prominence=500.0,
        distance_to_nearest_town=30.0,
        nearest_town_name="Test Town",
        height_difference=300.0,
        light_pollution_brightness=50,
        road_accessible=True,
    )


@pytest.fixture
def sample_locations_list() -> list[StargazingLocation]:
    """Three locations with ascending ``stargazing_score`` for sorting tests."""
    return [
        StargazingLocation(
            name="Low Score", latitude=40.0, longitude=116.0,
            elevation=500.0, prominence=200.0, distance_to_nearest_town=5.0,
            nearest_town_name="Town", height_difference=50.0, stargazing_score=30.0,
        ),
        StargazingLocation(
            name="Mid Score", latitude=40.2, longitude=116.2,
            elevation=1000.0, prominence=500.0, distance_to_nearest_town=25.0,
            nearest_town_name="Town", height_difference=200.0, stargazing_score=65.0,
        ),
        StargazingLocation(
            name="High Score", latitude=40.1, longitude=116.1,
            elevation=1500.0, prominence=800.0, distance_to_nearest_town=50.0,
            nearest_town_name="Town", height_difference=400.0, stargazing_score=85.0,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════
# Mock-patching path constants (for use with ``@patch`` / ``@pytest.mark.parametrize``)
# ═══════════════════════════════════════════════════════════════════

FIND_PEAKS = "stargazing_analyzer.stargazing_place_finder.StarGazingPlaceFinder.find_peaks_in_area"
FIND_OBS = "stargazing_analyzer.stargazing_place_finder.StarGazingPlaceFinder.find_observatories_in_area"
FIND_VP = "stargazing_analyzer.stargazing_place_finder.StarGazingPlaceFinder.find_viewpoints_in_area"
