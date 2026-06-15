# -*- coding: utf-8 -*-
"""
Unit tests for parallel batch_check_accessibility and PostGIS fast path.

All PostGIS and external API calls are mocked.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from models import GeoCoordinate


class TestBatchCheckAccessibilityParallel(unittest.TestCase):
    """Test the parallel batch_check_accessibility with mocked PostGIS."""

    def setUp(self):
        # FAST_TESTS shortcuts the logic — disable it for these unit tests
        self._old_fast = os.environ.pop("FAST_TESTS", None)
        # Mock is_road_accessible directly — it's what batch_check_accessibility calls.
        # This avoids complexity from cache, FAST_TESTS, and OSMnx fallback.
        self.patcher = patch("road_connectivity.road_connectivity_checker.RoadConnectivityChecker.is_road_accessible")
        self.mock_road = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def tearDown(self):
        if self._old_fast is not None:
            os.environ["FAST_TESTS"] = self._old_fast

    def _make_checker(self):
        from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

        return RoadConnectivityChecker(search_radius_km=10.0)

    def _make_coord_mock(self, result_map):
        """Create a deterministic mock based on coordinate -> result mapping."""

        def side_effect(point, *args):
            lat, lon = point.latitude, point.longitude
            return result_map.get((lat, lon), False)

        self.mock_road.side_effect = side_effect

    def test_batch_check_parallel_all_accessible(self):
        """All points accessible."""
        self._make_coord_mock({(39.9, 116.4): True, (40.0, 116.5): True, (40.1, 116.6): True})
        checker = self._make_checker()
        coords = [
            GeoCoordinate(latitude=39.9, longitude=116.4),
            GeoCoordinate(latitude=40.0, longitude=116.5),
            GeoCoordinate(latitude=40.1, longitude=116.6),
        ]
        results = checker.batch_check_accessibility(coords)
        self.assertEqual(results, [True, True, True])

    def test_batch_check_parallel_mixed(self):
        """Mixed accessible/inaccessible results."""
        self._make_coord_mock({(39.9, 116.4): True, (0.0, 160.0): False, (40.0, 116.5): True, (0.0, 180.0): False})
        checker = self._make_checker()
        coords = [
            GeoCoordinate(latitude=39.9, longitude=116.4),
            GeoCoordinate(latitude=0.0, longitude=160.0),
            GeoCoordinate(latitude=40.0, longitude=116.5),
            GeoCoordinate(latitude=0.0, longitude=180.0),
        ]
        results = checker.batch_check_accessibility(coords)
        self.assertEqual(results, [True, False, True, False])

    def test_batch_check_parallel_all_inaccessible(self):
        """All points inaccessible."""
        self._make_coord_mock({(0.0, 160.0): False, (0.0, 180.0): False})
        checker = self._make_checker()
        coords = [
            GeoCoordinate(latitude=0.0, longitude=160.0),
            GeoCoordinate(latitude=0.0, longitude=180.0),
        ]
        results = checker.batch_check_accessibility(coords)
        self.assertEqual(results, [False, False])

    def test_batch_check_parallel_empty(self):
        """Empty coordinate list returns empty results."""
        checker = self._make_checker()
        results = checker.batch_check_accessibility([])
        self.assertEqual(results, [])

    def test_batch_check_parallel_preserves_order(self):
        """Results respect the input order."""
        self._make_coord_mock({(0.0, 0.0): False, (39.9, 116.4): True, (0.0, 180.0): False})
        checker = self._make_checker()
        coords = [
            GeoCoordinate(latitude=0.0, longitude=0.0),
            GeoCoordinate(latitude=39.9, longitude=116.4),
            GeoCoordinate(latitude=0.0, longitude=180.0),
        ]
        results = checker.batch_check_accessibility(coords)
        self.assertEqual(results, [False, True, False])

    def test_batch_check_parallel_exception(self):
        """Mock returns result that is falsy → False."""
        self.mock_road.return_value = False
        checker = self._make_checker()
        results = checker.batch_check_accessibility([GeoCoordinate(latitude=39.9, longitude=116.4)])
        self.assertEqual(results, [False])

    def test_batch_check_without_gis_service(self):
        """Basic batch check works without GIS service (is_road_accessible is mocked)."""
        self.mock_road.return_value = True
        checker = self._make_checker()
        coords = [GeoCoordinate(latitude=39.9, longitude=116.4)]
        results = checker.batch_check_accessibility(coords)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], bool)


class TestCheckViaPostgis(unittest.TestCase):
    """Test the _check_via_postgis fast path directly."""

    def test_check_via_postgis_accessible(self):
        """PostGIS returns accessible → returns True."""
        from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

        gis = MagicMock()
        gis.postgis_enabled = True
        gis.query_road_connectivity.return_value = {
            "accessible": True,
            "distance_meters": 50.0,
            "road_type": "residential",
        }
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=gis)
        result = checker._check_via_postgis(GeoCoordinate(latitude=39.9, longitude=116.4))
        self.assertTrue(result)

    def test_check_via_postgis_inaccessible(self):
        """Far from road → returns False."""
        from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

        gis = MagicMock()
        gis.postgis_enabled = True
        gis.query_road_connectivity.return_value = {
            "accessible": False,
            "distance_meters": 100000.0,
            "road_type": None,
        }
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=gis)
        result = checker._check_via_postgis(GeoCoordinate(latitude=0.0, longitude=160.0))
        self.assertFalse(result)

    def test_check_via_postgis_no_gis_service(self):
        """No gis_service → returns None."""
        from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

        checker = RoadConnectivityChecker(search_radius_km=10.0)
        result = checker._check_via_postgis(GeoCoordinate(latitude=39.9, longitude=116.4))
        self.assertIsNone(result)

    def test_check_via_postgis_postgis_disabled(self):
        """gis_service exists but postgis_enabled=False → fallback."""
        from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

        gis = MagicMock()
        gis.postgis_enabled = False
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=gis)
        result = checker._check_via_postgis(GeoCoordinate(latitude=39.9, longitude=116.4))
        self.assertIsNone(result)

    def test_check_via_postgis_fallback_needed(self):
        """PostGIS returns fallback_needed → returns None."""
        from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

        gis = MagicMock()
        gis.postgis_enabled = True
        gis.query_road_connectivity.return_value = {"fallback_needed": True}
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=gis)
        result = checker._check_via_postgis(GeoCoordinate(latitude=39.9, longitude=116.4))
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
