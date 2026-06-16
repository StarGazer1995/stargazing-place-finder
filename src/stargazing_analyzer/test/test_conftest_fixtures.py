# -*- coding: utf-8 -*-
"""
Verify all shared ``conftest.py`` fixtures return expected types and shapes.

This file ensures the shared test infrastructure is exercised for code-coverage
purposes and provides a single location to validate fixture contracts.
"""

from unittest.mock import MagicMock, patch

from conftest import FIND_OBS, FIND_PEAKS, FIND_VP
from models import GeoCoordinate, LatLonBox, StargazingLocation

# ═══ Geo-coordinate fixtures ═══════════════════════════════════════


def test_bbox_beijing(bbox_beijing):
    """Verify the plain tuple bounding box fixture."""
    south, west, north, east = bbox_beijing
    assert south < north
    assert west < east
    assert isinstance(south, float)


def test_latlon_box_beijing(latlon_box_beijing):
    """Verify the ``LatLonBox`` fixture."""
    box = latlon_box_beijing
    assert isinstance(box, LatLonBox)
    assert box.south < box.north
    assert box.west < box.east


def test_coord_tiananmen(coord_tiananmen):
    """Verify the Tiananmen coordinate fixture."""
    coord = coord_tiananmen
    assert isinstance(coord, GeoCoordinate)
    assert 39.0 < coord.latitude < 41.0
    assert 115.0 < coord.longitude < 118.0


def test_coord_beijing(coord_beijing):
    """Verify the generic Beijing coordinate fixture."""
    coord = coord_beijing
    assert isinstance(coord, GeoCoordinate)
    assert coord.latitude == 40.0
    assert coord.longitude == 116.0


# ═══ Mock dependency fixtures ══════════════════════════════════════


def test_mock_gis_service(mock_gis_service):
    """Verify the mocked GIS service fixture."""
    mock = mock_gis_service
    assert isinstance(mock, MagicMock)
    assert mock.query_locations() == []
    assert mock.find_elevation((0.0, 0.0)) == 500.0
    assert mock.clear_cache() is None
    assert mock.get_elevation_statistics() == {"total_requests": 0}


def test_mock_light_analyzer(mock_light_analyzer):
    """Verify the mocked light pollution analyzer fixture."""
    mock = mock_light_analyzer
    assert mock.get_luminance_at(0.0, 0.0) == (10.0, 3)
    assert mock.close() is None


def test_mock_road_checker(mock_road_checker):
    """Verify the mocked road-checker fixture."""
    mock = mock_road_checker
    assert isinstance(mock, MagicMock)
    info = mock.get_accessibility_info(None)
    assert info["accessible"] is True
    assert info["distance_to_road_km"] == 0.5
    assert info["nearest_road_type"] == "secondary"


def test_mock_finder(mock_finder):
    """Verify the mocked place-finder fixture."""
    mock = mock_finder
    assert isinstance(mock, MagicMock)
    assert mock.find_peaks_in_area() == []
    assert mock.find_observatories_in_area() == []
    assert mock.find_viewpoints_in_area() == []
    assert mock.get_towns_from_overpass() == []


# ═══ Sample data fixtures ═════════════════════════════════════════


def test_sample_stargazing_location(sample_stargazing_location):
    """Verify the single-location fixture."""
    loc = sample_stargazing_location
    assert isinstance(loc, StargazingLocation)
    assert loc.name == "Test Peak"
    assert loc.latitude == 40.0
    assert loc.road_accessible is True


def test_sample_locations_list(sample_locations_list):
    """Verify the multi-location fixture and its sort order."""
    locs = sample_locations_list
    assert len(locs) == 3
    all(isinstance(loc, StargazingLocation) for loc in locs)
    scores = [loc.stargazing_score for loc in locs]
    assert scores == sorted(scores), "fixture should already be ascending"


# ═══ Mock-patching path constants ═════════════════════════════════


class TestPatchPathConstants:
    """Verify constant strings match real module paths (schema check)."""

    def test_find_peaks_constant(self):
        assert FIND_PEAKS.endswith("find_peaks_in_area")
        assert "StarGazingPlaceFinder" in FIND_PEAKS

    def test_find_obs_constant(self):
        assert FIND_OBS.endswith("find_observatories_in_area")
        assert "StarGazingPlaceFinder" in FIND_OBS

    def test_find_vp_constant(self):
        assert FIND_VP.endswith("find_viewpoints_in_area")
        assert "StarGazingPlaceFinder" in FIND_VP

    def test_patch_uses_constant(self):
        """Verify the constant is usable with ``unittest.mock.patch``."""
        with patch(FIND_PEAKS, return_value=[]):
            pass  # successful import + patching is the assertion
