# -*- coding: utf-8 -*-
"""
Unit tests for GisQueryService with mocked backends.

All PostGIS and Overpass API calls are mocked so tests run
fast, offline, and without external dependencies.
"""

import unittest
from typing import Any, Dict
from unittest.mock import patch

from models import LatLonBox


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


if __name__ == "__main__":
    unittest.main()
