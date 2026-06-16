# -*- coding: utf-8 -*-
"""
Unit tests for GisQueryService with mocked backends.

All PostGIS and Overpass API calls are mocked so tests run
fast, offline, and without external dependencies.
"""

import sys
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from models import LatLonBox, NetworkError


class TestGisQueryService(unittest.TestCase):
    """Test GisQueryService with mocked PostGIS backend."""

    def setUp(self):
        # Patch PostgisBackend in query_service's namespace (where it's imported)
        self.postgis_patcher = patch("gis_service.query_service.PostgisBackend")
        self.overpass_patcher = patch("gis_service.query_service.OverpassBackend")
        self.mock_postgis_cls = self.postgis_patcher.start()
        self.mock_overpass_cls = self.overpass_patcher.start()
        self.mock_postgis = self.mock_postgis_cls.return_value
        self.mock_overpass = self.mock_overpass_cls.return_value

    def tearDown(self):
        self.postgis_patcher.stop()
        self.overpass_patcher.stop()

    def _make_service(self, db_config: Any = None):
        """Create a GisQueryService with optional db config."""
        from gis_service.query_service import GisQueryService

        return GisQueryService(db_config=db_config, enable_cache=False)

    # ── query_road_connectivity ──────────────────────────────

    def test_road_connectivity_postgis_accessible(self):
        """PostGIS returns accessible road → result reflects that."""
        self.mock_postgis.query_road_connectivity.return_value = {
            "accessible": True,
            "distance_meters": 24.5,
            "road_type": "residential",
            "road_name": None,
            "nearest_lat": 39.9044,
            "nearest_lon": 116.4074,
        }
        service = self._make_service(db_config={"host": "localhost"})
        result = service.query_road_connectivity(39.9042, 116.4074)

        self.assertTrue(result["accessible"])
        self.assertEqual(result["distance_meters"], 24.5)
        self.assertEqual(result["road_type"], "residential")
        self.mock_postgis.query_road_connectivity.assert_called_once_with(39.9042, 116.4074, 10.0, "drive")

    def test_road_connectivity_postgis_inaccessible(self):
        """Far from any road → accessible=False."""
        self.mock_postgis.query_road_connectivity.return_value = {
            "accessible": False,
            "distance_meters": 50000.0,
            "road_type": "residential",
            "road_name": None,
            "nearest_lat": None,
            "nearest_lon": None,
        }
        service = self._make_service(db_config={"host": "localhost"})
        result = service.query_road_connectivity(0.0, 160.0)

        self.assertFalse(result["accessible"])
        self.assertEqual(result["distance_meters"], 50000.0)

    def test_road_connectivity_fallback_no_postgis(self):
        """No PostGIS config → returns fallback_needed signal."""
        service = self._make_service(db_config=None)
        result = service.query_road_connectivity(39.9, 116.4)

        self.assertTrue(result.get("fallback_needed"))
        self.assertFalse(result["accessible"])
        self.mock_postgis.query_road_connectivity.assert_not_called()

    def test_road_connectivity_custom_radius_and_network(self):
        """Custom radius_km and network_type are passed through."""
        self.mock_postgis.query_road_connectivity.return_value = {
            "accessible": True,
            "distance_meters": 10.0,
            "road_type": "footway",
        }
        service = self._make_service(db_config={"host": "localhost"})
        service.query_road_connectivity(39.9, 116.4, radius_km=5.0, network_type="walk")

        self.mock_postgis.query_road_connectivity.assert_called_once_with(39.9, 116.4, 5.0, "walk")

    def test_road_connectivity_propagates_postgis_error(self):
        """PostGIS exception propagates (PostgisBackend handles its own errors)."""
        self.mock_postgis.query_road_connectivity.side_effect = Exception("DB down")
        service = self._make_service(db_config={"host": "localhost"})
        with self.assertRaises(Exception):
            service.query_road_connectivity(39.9, 116.4)

    # ── query_locations ────────────────────────────────────

    def _make_mock_element(self, osm_id: int, lat: float, lon: float, tags: Dict[str, str]) -> Dict[str, Any]:
        return {"type": "node", "id": osm_id, "lat": lat, "lon": lon, "tags": tags}

    def test_query_locations_postgis(self):
        """PostGIS path returns formatted results."""
        mock_elements = [
            self._make_mock_element(1, 39.9, 116.3, {"name": "Peak A", "natural": "peak"}),
            self._make_mock_element(2, 40.0, 116.4, {"name": "Peak B", "natural": "peak"}),
        ]
        self.mock_postgis.query_locations_in_bbox.return_value = mock_elements

        service = self._make_service(db_config={"host": "localhost"})
        bbox = LatLonBox(south=39.5, west=115.5, north=40.5, east=117.5)
        results = service.query_locations(bbox, "peak")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["tags"]["name"], "Peak A")
        # Verify PostGIS was called with correct bbox (lon_min, lat_min, ...)
        self.mock_postgis.query_locations_in_bbox.assert_called_once()

    def test_query_locations_overpass_fallback(self):
        """Without PostGIS → uses Overpass backend."""
        mock_elements = [
            self._make_mock_element(3, 39.8, 116.2, {"name": "Town A", "place": "town"}),
        ]
        self.mock_overpass.query_locations_in_bbox.return_value = mock_elements

        service = self._make_service(db_config=None)
        bbox = LatLonBox(south=39.5, west=115.5, north=40.5, east=117.5)
        results = service.query_locations(bbox, "town")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tags"]["name"], "Town A")
        self.mock_postgis.query_locations_in_bbox.assert_not_called()
        self.mock_overpass.query_locations_in_bbox.assert_called_once()

    def test_query_locations_overpass_fallback_when_postgis_fails(self):
        """PostGIS enabled but backend raises → currently no auto-fallback."""
        self.mock_postgis.query_locations_in_bbox.side_effect = Exception("DB error")

        service = self._make_service(db_config={"host": "localhost"})
        with self.assertRaises(Exception):
            service.query_locations(LatLonBox(south=39.5, west=115.5, north=40.5, east=117.5))

    # ── helper query methods ────────────────────────────────

    def test_query_towns_delegates(self):
        self.mock_postgis.query_locations_in_bbox.return_value = []
        service = self._make_service(db_config={"host": "localhost"})
        service.query_towns(LatLonBox(south=39, west=115, north=41, east=117))
        # Should have called with 'town' type
        call_kwargs = self.mock_postgis.query_locations_in_bbox.call_args
        self.assertIsNotNone(call_kwargs)

    def test_query_peaks_delegates(self):
        self.mock_postgis.query_locations_in_bbox.return_value = []
        service = self._make_service(db_config={"host": "localhost"})
        service.query_peaks(LatLonBox(south=39, west=115, north=41, east=117))
        self.assertTrue(self.mock_postgis.query_locations_in_bbox.called)

    def test_query_observatories_delegates(self):
        self.mock_postgis.query_locations_in_bbox.return_value = []
        service = self._make_service(db_config={"host": "localhost"})
        service.query_observatories(LatLonBox(south=39, west=115, north=41, east=117))
        self.assertTrue(self.mock_postgis.query_locations_in_bbox.called)

    def test_query_viewpoints_delegates(self):
        self.mock_postgis.query_locations_in_bbox.return_value = []
        service = self._make_service(db_config={"host": "localhost"})
        service.query_viewpoints(LatLonBox(south=39, west=115, north=41, east=117))
        self.assertTrue(self.mock_postgis.query_locations_in_bbox.called)

    # ── elevation ──────────────────────────────────────────

    def test_find_elevation_delegates(self):
        with patch.object(self.mock_postgis, "find_elevation_at_point", return_value=500.0):
            service = self._make_service(db_config={"host": "localhost"})
            elev = service.find_elevation(39.9, 116.4)
            self.assertIsNotNone(elev)

    def test_find_elevation_no_postgis_returns_default(self):
        """Without PostGIS, elevation falls through to ElevationBackend chain."""
        with patch("gis_service.backends.elevation_backend.requests.get") as mock_get:
            # Simulate API failure → fallback to 0.0
            mock_get.side_effect = Exception("API unavailable")
            service = self._make_service(db_config=None)
            elev = service.find_elevation(39.9, 116.4)
            self.assertEqual(elev, 0.0)

    def test_find_elevation_invalid_osm_tags(self):
        """Invalid ele tag logs warning and falls through."""
        with patch("gis_service.backends.elevation_backend.requests.get") as mock_get:
            mock_get.side_effect = Exception("API unavailable")
            service = self._make_service(db_config=None)
            elev = service.find_elevation(39.9, 116.4, osm_tags={"ele": "not_a_number"})
            self.assertEqual(elev, 0.0)

    def test_batch_find_elevations_invalid_osm_tags(self):
        """Invalid ele tag in batch logs warning and falls through."""
        with patch("gis_service.backends.elevation_backend.requests.get") as mock_get:
            mock_get.side_effect = NetworkError("API unavailable")
            service = self._make_service(db_config=None)
            results = service.batch_find_elevations(
                [(39.9, 116.4), (40.0, 116.5)],
                osm_tags_list=[{"ele": "bad"}, {"ele": "invalid"}],
            )
            self.assertEqual(results, [0.0, 0.0])

    def test_batch_find_elevations_api_failure(self):
        """Open-Elevation API failure in batch logs debug and returns default."""
        with patch("gis_service.backends.elevation_backend.requests.get") as mock_get:
            mock_get.side_effect = NetworkError("API unavailable")
            service = self._make_service(db_config=None)
            results = service.batch_find_elevations(
                [(39.9, 116.4), (40.0, 116.5)],
            )
            self.assertEqual(results, [0.0, 0.0])


class TestOverpassBackendFallback(unittest.TestCase):
    """Tests for OverpassBackend._request with multi-URL fallback + retry."""

    def setUp(self):
        self.req_patcher = patch("gis_service.backends.overpass_backend.requests.post")
        self.time_patcher = patch("gis_service.backends.overpass_backend.time.sleep")
        self.mock_post = self.req_patcher.start()
        self.mock_sleep = self.time_patcher.start()
        from gis_service.backends.overpass_backend import OverpassBackend

        self.backend = OverpassBackend(
            url="https://primary.example.com/api",
            timeout=5,
            max_retries=2,
        )
        self.assertEqual(len(self.backend.urls), 2)
        self.assertEqual(self.backend.urls[0], "https://primary.example.com/api")

    def tearDown(self):
        self.req_patcher.stop()
        self.time_patcher.stop()

    def test_request_primary_success(self):
        """Primary URL succeeds on first try → returns elements immediately."""
        mock_resp = self.mock_post.return_value
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"elements": [{"id": 1, "tags": {"name": "Peak"}}]}

        result = self.backend._request("[out:json];node;out;", "peak")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 1)
        # POST body format: data={"data": query}
        _, kwargs = self.mock_post.call_args
        self.assertEqual(kwargs["data"], {"data": "[out:json];node;out;"})
        self.assertEqual(kwargs["timeout"], 5)

    def test_request_primary_fails_fallback_succeeds(self):
        """Primary URL fails (all retries) → fallback URL succeeds."""
        mock_resp = self.mock_post.return_value
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"elements": [{"id": 2}]}

        def side_effect(url, *args, **kwargs):
            if "primary" in url:
                from requests.exceptions import Timeout

                raise Timeout("timed out")
            return mock_resp

        self.mock_post.side_effect = side_effect

        result = self.backend._request("[out:json];node;out;", "town")
        self.assertEqual(len(result), 1)
        # 2 retries on primary (fail) + 1 call on fallback (success) = 3 total calls
        self.assertEqual(self.mock_post.call_count, 3)

    def test_request_all_urls_fail(self):
        """All URLs fail → returns empty list."""
        from requests.exceptions import HTTPError

        mock_resp = self.mock_post.return_value
        mock_resp.raise_for_status.side_effect = HTTPError("500 Server Error")

        result = self.backend._request("[out:json];node;out;", "town")
        self.assertEqual(result, [])
        # 2 URLs × 2 retries = 4 calls
        self.assertEqual(self.mock_post.call_count, 4)

    def test_request_timeout_retry_then_success(self):
        """First attempt times out, retry succeeds on primary URL."""
        mock_resp = self.mock_post.return_value
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"elements": [{"id": 3}]}

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                from requests.exceptions import Timeout

                raise Timeout("timed out")
            return mock_resp

        self.mock_post.side_effect = side_effect

        result = self.backend._request("[out:json];node;out;", "peak")
        self.assertEqual(len(result), 1)
        # First attempt timeout + retry success = 2 calls
        self.assertEqual(self.mock_post.call_count, 2)
        # Sleep should have been called once for retry delay
        self.mock_sleep.assert_called_once()

    def test_request_network_error_fallback(self):
        """NetworkError on primary → retries exhausted → fallback succeeds."""

        class FakeNetworkError(Exception):
            pass

        from models import NetworkError as NetExc

        mock_resp = self.mock_post.return_value
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"elements": [{"id": 4}]}

        def side_effect(url, *args, **kwargs):
            if "primary" in url:
                raise NetExc("DNS failure")
            return mock_resp

        self.mock_post.side_effect = side_effect

        result = self.backend._request("[out:json];node;out;", "viewpoint")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 4)
        # 2 retries on primary + 1 on fallback = 3 calls
        self.assertEqual(self.mock_post.call_count, 3)


class TestPostgisBackendElevation(unittest.TestCase):
    """Tests for PostgisBackend batch elevation query + find_elevation_at_point."""

    def setUp(self):
        # psycopg2 is imported inside method bodies, so we inject a mock into sys.modules
        self.psycopg2_patcher = patch.dict("sys.modules", {"psycopg2": MagicMock()})
        self.psycopg2_patcher.start()
        self.mock_psycopg2 = sys.modules["psycopg2"]
        self.mock_conn = self.mock_psycopg2.connect.return_value
        self.mock_cursor = self.mock_conn.cursor.return_value

    def tearDown(self):
        self.psycopg2_patcher.stop()

    def test_batch_query_empty_coords(self):
        """Empty coordinates → returns [] without calling psycopg2."""
        from gis_service.backends.postgis_backend import PostgisBackend

        backend = PostgisBackend(config={"host": "localhost"})
        result = backend._query_single_batch([], [])
        self.assertEqual(result, [])
        self.mock_psycopg2.connect.assert_not_called()

    def test_batch_query_single_point(self):
        """Single coordinate → VALUES query built and results parsed."""
        from gis_service.backends.postgis_backend import ElevationResult, PostgisBackend

        self.mock_cursor.fetchall.return_value = [
            (1, 39.9, 116.4, "TestPt", 1200.0, "Mt Foo", 150.0, "natural=peak"),
        ]

        backend = PostgisBackend(config={"host": "localhost"})
        results = backend._query_single_batch([(39.9, 116.4)], ["TestPt"])
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], ElevationResult)
        self.assertEqual(results[0].latitude, 39.9)
        self.assertEqual(results[0].longitude, 116.4)
        self.assertEqual(results[0].elevation, 1200.0)
        self.assertEqual(results[0].source_name, "Mt Foo")
        self.assertEqual(results[0].feature_type, "natural=peak")

        # Verify the VALUES query was used
        call_sql = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("VALUES", call_sql)
        self.assertIn("CROSS JOIN LATERAL", call_sql)

    def test_batch_query_multiple_points(self):
        """Multiple coordinates → all results returned in order."""
        from gis_service.backends.postgis_backend import PostgisBackend

        self.mock_cursor.fetchall.return_value = [
            (1, 39.9, 116.4, "A", 500.0, "S1", 100.0, "natural=peak"),
            (2, 40.0, 117.0, "B", None, "S2", 200.0, "unknown"),
        ]

        backend = PostgisBackend(config={"host": "localhost"})
        results = backend._query_single_batch([(39.9, 116.4), (40.0, 117.0)], ["A", "B"])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].elevation, 500.0)
        self.assertIsNone(results[1].elevation)
        self.assertEqual(results[1].feature_type, "unknown")

    def test_batch_query_psycopg2_parameters(self):
        """Verify SQL params match VALUES placeholders."""
        from gis_service.backends.postgis_backend import PostgisBackend

        self.mock_cursor.fetchall.return_value = []

        backend = PostgisBackend(config={"host": "localhost"})
        backend._query_single_batch([(39.9, 116.4), (40.0, 117.0)], ["P1", "P2"])

        call_args = self.mock_cursor.execute.call_args
        sql, params = call_args[0]
        self.assertIn("%s::float", sql)
        self.assertIn("%s::text", sql)
        self.assertEqual(params, [39.9, 116.4, "P1", 40.0, 117.0, "P2"])

    def test_batch_query_propagates_exception(self):
        """DB error in _query_single_batch raises DataError."""
        from gis_service.backends.postgis_backend import PostgisBackend
        from models import DataError

        self.mock_cursor.execute.side_effect = Exception("connection lost")

        backend = PostgisBackend(config={"host": "localhost"})
        with self.assertRaises(DataError):
            backend._query_single_batch([(39.9, 116.4)], ["P1"])

        # cursor and conn should still be closed
        self.mock_cursor.close.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_find_elevation_at_point_returns_value(self):
        """find_elevation_at_point returns elevation from first matching row."""
        from gis_service.backends.postgis_backend import PostgisBackend

        self.mock_cursor.fetchone.return_value = (1200.0,)

        backend = PostgisBackend(config={"host": "localhost"})
        result = backend.find_elevation_at_point(39.9, 116.4)
        self.assertEqual(result, 1200.0)

        # Verify the optimized ORDER BY (way <-> ... not ST_Transform(way, 4326) <-> ...)
        call_sql = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("ORDER BY way <->", call_sql)
        self.assertNotIn("ST_Transform(way, 4326) <->", call_sql)

    def test_find_elevation_at_point_returns_none(self):
        """When no row found, returns None."""
        from gis_service.backends.postgis_backend import PostgisBackend

        self.mock_cursor.fetchone.return_value = None

        backend = PostgisBackend(config={"host": "localhost"})
        result = backend.find_elevation_at_point(39.9, 116.4)
        self.assertIsNone(result)


class TestPostgisBackendFormatRow(unittest.TestCase):
    """Direct tests for PostgisBackend._format_location_row."""

    def test_format_location_row_returns_correct_dict(self):
        """_format_location_row formats a SQL row into an OSM-compatible dict."""
        from gis_service.backends.postgis_backend import PostgisBackend

        backend = PostgisBackend(config={})
        row = (
            12345,  # osm_id
            "Test Peak",  # name
            116.4,  # longitude
            39.9,  # latitude
            None,  # amenity
            None,  # tourism
            None,  # shop
            None,  # highway
            None,  # place
            None,  # man_made
            None,  # tower:type
            None,  # leisure
            "peak",  # natural
            None,  # ele
        )
        result = backend._format_location_row(row)
        self.assertEqual(result["type"], "node")
        self.assertEqual(result["id"], 12345)
        self.assertEqual(result["lat"], 39.9)
        self.assertEqual(result["lon"], 116.4)
        self.assertEqual(result["tags"]["name"], "Test Peak")
        self.assertEqual(result["tags"]["natural"], "peak")

    def test_format_location_row_with_ele_tag(self):
        """_format_location_row captures ele from column index 13."""
        from gis_service.backends.postgis_backend import PostgisBackend

        backend = PostgisBackend(config={})
        row = (
            67890,  # osm_id
            "High Peak",  # name
            117.0,  # longitude
            40.0,  # latitude
            None,  # amenity
            None,  # tourism
            None,  # shop
            None,  # highway
            None,  # place
            None,  # man_made
            None,  # tower:type
            None,  # leisure
            "peak",  # natural
            "2500",  # ele
        )
        result = backend._format_location_row(row)
        self.assertEqual(result["tags"]["ele"], "2500")
        self.assertEqual(result["tags"]["natural"], "peak")
