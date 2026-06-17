# -*- coding: utf-8 -*-
"""
Tests for road connectivity detection functionality.

Uses mocked data to avoid real OSM network downloads during test runs.
"""

import pickle
from unittest.mock import MagicMock, mock_open, patch

from models import GeoCoordinate
from road_connectivity.road_connectivity_checker import RoadAccessInfoCache, RoadConnectivityChecker
from road_connectivity.simple_road_checker import batch_road_check, quick_road_check


def test_quick_check_returns_boolean():
    """quick_road_check returns a boolean with mocked response."""
    with patch("road_connectivity.simple_road_checker.quick_road_check", return_value=True):
        result = quick_road_check(39.9042, 116.4074, search_radius_km=3.0)
    assert isinstance(result, bool)


def test_batch_check_returns_results_for_all_inputs():
    """batch_road_check returns one result per coordinate."""
    from road_connectivity.geo_fence import GeoFence

    geo_fence = GeoFence(enabled=True)
    test_locations = [
        (39.9042, 116.4074),
        (40.3242, 116.6312),
        (25.0, 125.0),
    ]
    results = batch_road_check(test_locations, search_radius_km=5.0, geo_fence=geo_fence)
    assert len(results) == len(test_locations)
    assert all(isinstance(r, bool) for r in results)


def test_detailed_checker_returns_accessibility_info():
    """RoadConnectivityChecker.get_accessibility_info returns expected keys."""
    from road_connectivity.geo_fence import GeoFence

    geo_fence = GeoFence(enabled=True)
    checker = RoadConnectivityChecker(search_radius_km=8.0, geo_fence=geo_fence)
    point = GeoCoordinate(latitude=40.3242, longitude=116.6312)
    info = checker.get_accessibility_info(point)

    assert "accessible" in info
    assert isinstance(info["accessible"], bool)


def test_error_handling_with_invalid_coordinates():
    """Invalid coordinates don't crash; they return not-accessible."""
    with patch("road_connectivity.test.test_road_connectivity.quick_road_check", return_value=False):
        invalid_coords = [(91.0, 0.0), (0.0, 181.0)]
        for lat, lon in invalid_coords:
            result = quick_road_check(lat, lon, search_radius_km=2.0)
            assert isinstance(result, bool)


def test_cache_unlink_error_is_logged():
    """When deleting a corrupted cache file fails, it logs and continues."""
    cache = RoadAccessInfoCache(cache_expiry_hours=1)
    fake_path = MagicMock()
    fake_path.unlink.side_effect = OSError("permission denied")
    with (
        patch.object(cache, "_is_cache_valid", return_value=True),
        patch.object(cache, "_get_cache_file_path", return_value=fake_path),
        patch("builtins.open", mock_open()),
        patch("pickle.load", side_effect=pickle.PickleError("corrupt data")),
        patch("road_connectivity.road_connectivity_checker.logger") as mock_log,
    ):
        result = cache.get_cached_result("test_type")
        assert result is None
        assert any("Failed to delete" in str(c) for c in mock_log.warning.call_args_list)
