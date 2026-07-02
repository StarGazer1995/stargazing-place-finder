# -*- coding: utf-8 -*-
"""
Unit tests for parallel batch_check_accessibility and PostGIS fast path.

All PostGIS and external API calls are mocked.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

import road_connectivity.road_connectivity_checker
from models import GeoCoordinate, LatLonBox, NetworkError
from road_connectivity.road_connectivity_checker import RoadAccessInfoCache, RoadConnectivityChecker


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
        """PostGIS returns accessible → returns dict with accessible=True and details."""

        gis = MagicMock()
        gis.postgis_enabled = True
        gis.query_road_connectivity.return_value = {
            "accessible": True,
            "distance_meters": 50.0,
            "road_type": "residential",
        }
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=gis)
        result = checker._check_via_postgis(GeoCoordinate(latitude=39.9, longitude=116.4))
        self.assertTrue(result["accessible"])
        self.assertEqual(result["distance_meters"], 50.0)
        self.assertEqual(result["road_type"], "residential")

    def test_check_via_postgis_inaccessible(self):
        """Far from road → returns dict with accessible=False."""

        gis = MagicMock()
        gis.postgis_enabled = True
        gis.query_road_connectivity.return_value = {
            "accessible": False,
            "distance_meters": 100000.0,
            "road_type": None,
        }
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=gis)
        result = checker._check_via_postgis(GeoCoordinate(latitude=0.0, longitude=160.0))
        self.assertFalse(result["accessible"])
        self.assertEqual(result["distance_meters"], 100000.0)
        self.assertIsNone(result["road_type"])

    def test_check_via_postgis_no_gis_service(self):
        """No gis_service → returns None."""

        checker = RoadConnectivityChecker(search_radius_km=10.0)
        result = checker._check_via_postgis(GeoCoordinate(latitude=39.9, longitude=116.4))
        self.assertIsNone(result)

    def test_check_via_postgis_postgis_disabled(self):
        """gis_service exists but postgis_enabled=False → fallback."""

        gis = MagicMock()
        gis.postgis_enabled = False
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=gis)
        result = checker._check_via_postgis(GeoCoordinate(latitude=39.9, longitude=116.4))
        self.assertIsNone(result)

    def test_check_via_postgis_fallback_needed(self):
        """PostGIS returns fallback_needed → returns None."""

        gis = MagicMock()
        gis.postgis_enabled = True
        gis.query_road_connectivity.return_value = {"fallback_needed": True}
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=gis)
        result = checker._check_via_postgis(GeoCoordinate(latitude=39.9, longitude=116.4))
        self.assertIsNone(result)


class TestPreloadNetwork(unittest.TestCase):
    """Test preload_network_for_bbox and shared graph in _get_road_network."""

    def setUp(self):
        self.ox_patcher = patch("road_connectivity.road_connectivity_checker.ox.graph_from_bbox")
        self.mock_ox = self.ox_patcher.start()
        self.addCleanup(self.ox_patcher.stop)

    def _make_checker(self):

        return RoadConnectivityChecker(search_radius_km=10.0)

    # Use a bbox small enough to stay under the 500 km² single-tile threshold
    # (~0.1° × 0.1° ≈ 95 km² at 40°N).
    _SMALL_BBOX = (39.90, 116.30, 40.00, 116.40)

    def test_preload_with_tuple_bbox(self):
        """Tuple bbox (south, west, north, east) → single-tile success."""
        mock_graph = MagicMock()
        mock_graph.nodes.return_value = [1, 2, 3]
        self.mock_ox.return_value = mock_graph

        checker = self._make_checker()
        checker.preload_network_for_bbox(self._SMALL_BBOX)

        self.mock_ox.assert_called_once()
        _, kwargs = self.mock_ox.call_args
        self.assertEqual(kwargs["bbox"], (116.30, 39.90, 116.40, 40.00))
        self.assertEqual(kwargs["network_type"], "drive")
        self.assertIs(checker._shared_graph, mock_graph)

    def test_preload_with_latlonbox(self):
        """LatLonBox object → unpacks .south/.west/.north/.east."""
        mock_graph = MagicMock()
        mock_graph.nodes.return_value = [1, 2]
        self.mock_ox.return_value = mock_graph

        checker = self._make_checker()
        checker.preload_network_for_bbox(
            LatLonBox(
                south=self._SMALL_BBOX[0],
                west=self._SMALL_BBOX[1],
                north=self._SMALL_BBOX[2],
                east=self._SMALL_BBOX[3],
            )
        )

        self.mock_ox.assert_called_once()
        _, kwargs = self.mock_ox.call_args
        self.assertEqual(kwargs["bbox"], (116.30, 39.90, 116.40, 40.00))
        self.assertIs(checker._shared_graph, mock_graph)

    def test_preload_with_network_error(self):
        """ox.graph_from_bbox raises → _shared_graph set to None."""
        self.mock_ox.side_effect = NetworkError("OSM timeout")

        checker = self._make_checker()
        checker.preload_network_for_bbox(self._SMALL_BBOX)

        self.mock_ox.assert_called_once()
        self.assertIsNone(checker._shared_graph)

    def test_preload_with_request_exception(self):
        """ox.graph_from_bbox raises ConnectionError → _shared_graph set to None."""
        import requests

        self.mock_ox.side_effect = requests.exceptions.ConnectionError("Connection refused")

        checker = self._make_checker()
        checker.preload_network_for_bbox(self._SMALL_BBOX)

        self.mock_ox.assert_called_once()
        self.assertIsNone(checker._shared_graph)

    def test_preload_large_bbox_splits_into_tiles(self):
        """Large bbox (> 500 km²) is split and merged via compose_all."""
        import networkx as nx

        checker = self._make_checker()
        # 2° × 2° ≈ 19,000 km² → should split into many tiles
        large_bbox = (39.0, 115.0, 41.0, 117.0)

        # Return real MultiDiGraphs so compose_all doesn't choke
        def _fake_graph(*args, **kwargs):
            return nx.MultiDiGraph()

        self.mock_ox.side_effect = _fake_graph

        checker.preload_network_for_bbox(large_bbox)
        self.assertIsNotNone(checker._shared_graph)
        self.assertGreater(self.mock_ox.call_count, 1)  # multiple tiles

    def test_config_respects_tile_max_area(self):
        """RoadConnectivityChecker reads road_network_tile_max_area_km2 from config."""
        from config import StargazingConfig

        checker = RoadConnectivityChecker(
            search_radius_km=10.0,
            config=StargazingConfig(road_network_tile_max_area_km2=300.0),
        )
        self.assertEqual(checker._tile_max_area_km2, 300.0)

    def test_get_road_network_request_exception(self):
        """ox.graph_from_point raises ConnectionError → _get_road_network returns None."""
        import requests

        with patch.object(road_connectivity.road_connectivity_checker.ox, "graph_from_point") as mock_gfp:
            mock_gfp.side_effect = requests.exceptions.ConnectionError("Connection refused")

            checker = self._make_checker()
            checker._shared_graph = None
            result = checker._get_road_network(
                GeoCoordinate(latitude=39.9, longitude=116.4),
                network_type="drive",
            )

            self.assertIsNone(result)

    def test_get_road_accessibility_request_exception(self):
        """RequestException in is_road_accessible → returns False (line 248)."""
        import requests

        mock_graph = MagicMock()
        mock_graph.nodes.return_value = [1]

        with (
            patch.object(road_connectivity.road_connectivity_checker.ox, "distance") as mock_dist,
            patch.object(RoadConnectivityChecker, "_check_via_postgis", return_value=None),
        ):
            # _get_road_network returns the shared mock graph successfully,
            # but ox.distance.nearest_nodes raises RequestException
            checker = self._make_checker()
            checker._shared_graph = mock_graph
            mock_dist.nearest_nodes.side_effect = requests.exceptions.RequestException(
                "Connection error during nearest node lookup"
            )
            # Bypass disk cache
            with patch.object(checker.location_cache, "get_cached_result", return_value=None):
                result = checker.is_road_accessible(
                    GeoCoordinate(latitude=39.9, longitude=116.4),
                    network_type="drive",
                )

            self.assertFalse(result)
            mock_dist.nearest_nodes.assert_called_once()

    def test_get_road_network_uses_shared_graph(self):
        """_get_road_network returns _shared_graph when it is set."""
        mock_graph = MagicMock()
        checker = self._make_checker()
        checker._shared_graph = mock_graph

        result = checker._get_road_network(
            GeoCoordinate(latitude=39.9, longitude=116.4),
            network_type="drive",
        )
        self.assertIs(result, mock_graph)
        # ox.graph_from_bbox should NOT be called when shared graph is used
        self.mock_ox.assert_not_called()


class TestTryPostgisInfo(unittest.TestCase):
    """Test _try_postgis_info method (lines 573-584)."""

    def setUp(self):
        self.mock_gis = MagicMock()
        self.mock_gis.postgis_enabled = True
        self.mock_gis.query_road_connectivity.return_value = {
            "accessible": True,
            "distance_meters": 50.0,
            "road_type": "residential",
        }

    def test_try_postgis_info_sets_all_fields(self):
        """PostGIS success → result dict is populated with accessible/distance/road_type."""

        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=self.mock_gis)
        result = {"accessible": False, "distance_to_road_km": None, "nearest_road_type": None, "error": None}
        point = GeoCoordinate(latitude=39.9, longitude=116.4)

        success = checker._try_postgis_info(result, point, "drive")
        self.assertTrue(success)
        self.assertTrue(result["accessible"])
        self.assertEqual(result["distance_to_road_km"], 0.05)
        self.assertEqual(result["nearest_road_type"], "residential")
        self.assertIsNone(result["error"])

    def test_try_postgis_info_returns_false_when_postgis_unavailable(self):
        """No PostGIS → _try_postgis_info returns False, result unchanged."""

        checker = RoadConnectivityChecker(search_radius_km=10.0)  # No gis_service
        result = {"accessible": False}
        point = GeoCoordinate(latitude=39.9, longitude=116.4)

        success = checker._try_postgis_info(result, point, "drive")
        self.assertFalse(success)

    def test_try_postgis_info_handles_none_distance(self):
        """PostGIS returns None distance_meters → distance_to_road_km stays None."""

        self.mock_gis.query_road_connectivity.return_value = {
            "accessible": False,
            "distance_meters": None,
            "road_type": None,
        }
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=self.mock_gis)
        result = {"accessible": True, "distance_to_road_km": None, "nearest_road_type": None, "error": None}
        point = GeoCoordinate(latitude=39.9, longitude=116.4)

        success = checker._try_postgis_info(result, point, "drive")
        self.assertTrue(success)
        self.assertFalse(result["accessible"])
        self.assertIsNone(result["distance_to_road_km"])
        self.assertIsNone(result["nearest_road_type"])


class TestIsRoadAccessiblePostgisPath(unittest.TestCase):
    """Test is_road_accessible when PostGIS fast path is used (line 238)."""

    def test_postgis_fast_path_returns_accessible(self):
        """is_road_accessible returns True when PostGIS says accessible."""

        gis = MagicMock()
        gis.postgis_enabled = True
        gis.query_road_connectivity.return_value = {
            "accessible": True,
            "distance_meters": 25.0,
            "road_type": "residential",
        }
        checker = RoadConnectivityChecker(search_radius_km=10.0, gis_service=gis)
        # Bypass cache
        with patch.object(checker.location_cache, "get_cached_result", return_value=None):
            result = checker.is_road_accessible(GeoCoordinate(latitude=39.9, longitude=116.4))
        self.assertTrue(result)


class TestRoadAccessInfoCacheCleanup(unittest.TestCase):
    """Test save_road_access_info_to_cache temp file cleanup (lines 89-94)."""

    def test_atomic_write_cleans_up_on_pickle_failure(self):
        """When pickle.dump fails, temp file is cleaned up."""
        from models import RoadAccessInfo

        cache = RoadAccessInfoCache(cache_expiry_hours=24)
        data = [RoadAccessInfo(latitude=39.9, longitude=116.4, is_road_accessible=True)]

        # Ensure we get past mkdir and into the write block
        cache._generate_cache_key = MagicMock(return_value="test_cleanup_key")
        cache._get_cache_file_path = MagicMock(return_value=MagicMock())

        with (
            patch("road_connectivity.road_connectivity_checker.pickle.dump", side_effect=RuntimeError("pickle fail")),
            patch("road_connectivity.road_connectivity_checker.os.unlink") as mock_unlink,
            patch.object(cache, "get_cached_result", return_value=None),
        ):
            try:
                cache.save_road_access_info_to_cache("test_type", data)
            except RuntimeError:
                pass
            mock_unlink.assert_called()

    def test_atomic_write_cleanup_oserror_is_silent(self):
        """When os.unlink fails during cleanup, OSError is silently ignored (lines 92-93)."""
        from models import RoadAccessInfo

        cache = RoadAccessInfoCache(cache_expiry_hours=24)
        data = [RoadAccessInfo(latitude=39.9, longitude=116.4, is_road_accessible=True)]

        cache._generate_cache_key = MagicMock(return_value="test_cleanup_oserror")
        cache._get_cache_file_path = MagicMock(return_value=MagicMock())

        with (
            patch("road_connectivity.road_connectivity_checker.pickle.dump", side_effect=RuntimeError("pickle fail")),
            patch("road_connectivity.road_connectivity_checker.os.unlink", side_effect=OSError("permission denied")),
            patch.object(cache, "get_cached_result", return_value=None),
        ):
            with self.assertRaises(RuntimeError):
                cache.save_road_access_info_to_cache("test_type", data)
