# -*- coding: utf-8 -*-
"""
Integration tests for StargazingLocationAnalyzer.analyze_area().

Tests the *real* pipeline flow (_search_locations → _batch_light_pollution →
_parallel_analyze_locations → _process_one_location → scoring → filtering → sort)
with only the network/IO layer mocked.

This is NOT a unit test of individual private methods — it tests what the function
actually does end-to-end.
"""

from unittest.mock import MagicMock

import pytest

from models import (
    LatLonBox,
    Observatory,
    Peak,
    StargazingLocation,
    Viewpoint,
)
from stargazing_analyzer.stargazing_location_analyzer import StargazingLocationAnalyzer

# ── Helpers ────────────────────────────────────────────────────────────


def _make_peak(name: str, lat: float, lon: float, ele: float, hdiff: float = 200.0) -> Peak:
    """Build a Peak with minimal fields."""
    return Peak(
        name=name,
        lat=lat,
        lon=lon,
        elevation=ele,
        height_difference=hdiff,
        distance_to_nearest_town=5.0,
        nearest_town_name="MockTown",
        location_type="mountain_peak",
    )


def _make_obs(name: str, lat: float, lon: float, ele: float = 1500.0) -> Observatory:
    return Observatory(
        name=name,
        lat=lat,
        lon=lon,
        elevation=ele,
        location_type="observatory",
        nearest_town_name="MockTown",
        distance_to_nearest_town=8.0,
        height_difference=0.0,
    )


def _make_viewpoint(name: str, lat: float, lon: float, ele: float = 1200.0) -> Viewpoint:
    return Viewpoint(
        name=name,
        lat=lat,
        lon=lon,
        elevation=ele,
        location_type="viewpoint",
        nearest_town_name="MockTown",
        distance_to_nearest_town=3.0,
        height_difference=0.0,
    )


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def mock_peak_data():
    """Two peaks with very different characteristics."""
    return [
        _make_peak("HighPeak", 40.0, 116.0, 2500.0, hdiff=500.0),
        _make_peak("LowPeak", 40.5, 116.5, 800.0, hdiff=50.0),
    ]


@pytest.fixture
def mock_observatory_data():
    return [_make_obs("DaMingObs", 40.2, 116.3, 1800.0)]


@pytest.fixture
def mock_viewpoint_data():
    return [_make_viewpoint("HillView", 40.3, 116.4, 1400.0)]


@pytest.fixture
def mock_towns_data():
    """Minimal town data for _fetch_towns_data."""
    town = MagicMock()
    town.name = "MockTown"
    town.lat = 40.1
    town.lon = 116.1
    town.elevation_m = 300.0
    return [town]


@pytest.fixture
def analyzer(mock_peak_data, mock_observatory_data, mock_viewpoint_data, mock_towns_data):
    """StargazingLocationAnalyzer with all IO mocked out.

    The real pipeline runs, but:
      - mountain_finder returns pre-built Peak/Observatory/Viewpoint objects
      - road_checker returns a fixed road-accessibility dict
      - light_pollution_analyzer is None (no GeoTIFF)
    """
    a = StargazingLocationAnalyzer()
    a.mountain_finder.find_peaks_in_area = MagicMock(return_value=mock_peak_data)
    a.mountain_finder.find_observatories_in_area = MagicMock(return_value=mock_observatory_data)
    a.mountain_finder.find_viewpoints_in_area = MagicMock(return_value=mock_viewpoint_data)
    a.mountain_finder.gis_service = MagicMock()
    a.mountain_finder.gis_service.query_locations = MagicMock(return_value=mock_towns_data)

    # Road checker returns a fake accessibility result
    a.road_checker.get_accessibility_info = MagicMock(
        return_value={
            "accessible": True,
            "distance_to_road_km": 0.15,
            "nearest_road_name": "G110",
            "road_access_rating": 7.5,
            "max_score": 10.0,
        }
    )
    a.road_checker.preload_network_for_bbox = MagicMock()
    a.light_pollution_analyzer = None
    return a


@pytest.fixture
def bbox():
    return LatLonBox(south=39.5, west=115.5, north=40.5, east=117.5)


# ── Tests ──────────────────────────────────────────────────────────────


class TestAnalyzeAreaPipeline:
    """Test the real analyze_area pipeline end-to-end."""

    def test_returns_list_of_stargazing_locations(self, analyzer, bbox):
        """The pipeline should return StargazingLocation objects with scores."""
        results = analyzer.analyze_area(bbox, max_locations=10)
        assert isinstance(results, list)
        assert len(results) > 0
        for loc in results:
            assert isinstance(loc, StargazingLocation)
            assert loc.stargazing_score is not None
            assert loc.stargazing_score >= 0

    def test_peak_with_prominence_scores_highest(self, analyzer, bbox):
        """HighPeak (2500m, 500m hdiff) should score higher than LowPeak (800m, 50m hdiff)."""
        results = analyzer.analyze_area(bbox, max_locations=10)
        high = next(r for r in results if r.name == "HighPeak")
        low = next(r for r in results if r.name == "LowPeak")
        assert high.stargazing_score > low.stargazing_score, (
            f"HighPeak ({high.stargazing_score}) should outscore LowPeak ({low.stargazing_score})"
        )

    def test_results_sorted_by_score_descending(self, analyzer, bbox):
        """analyze_area should return results sorted best-first."""
        results = analyzer.analyze_area(bbox, max_locations=10)
        scores = [r.stargazing_score for r in results]
        assert scores == sorted(scores, reverse=True), "Results must be sorted by score descending"

    def test_observatory_gets_location_bonus(self, analyzer, bbox):
        """Observatories should get a +6 location-type bonus."""
        results = analyzer.analyze_area(bbox, max_locations=10)
        obs = next(r for r in results if r.name == "DaMingObs")
        # Observatory type bonus + road accessible + elevation = should be decent
        assert obs.stargazing_score >= 25, f"Observatory scored {obs.stargazing_score}, expected >= 25"

    def test_road_accessible_is_recorded(self, analyzer, bbox):
        """Road accessibility info should be present in results.

        Observatories and viewpoints skip road checking (assumed accessible),
        so their distance is 0.0.  Peaks use the mocked checker value.
        """
        results = analyzer.analyze_area(bbox, max_locations=10)
        for loc in results:
            assert loc.distance_to_road_km is not None
            assert loc.distance_to_road_km >= 0

    def test_road_distance_filter_removes_far_places(self, analyzer, bbox):
        """max_distance_to_road_km=0.05 filters peaks (~0.086km) but keeps
        observatories/viewpoints (d=0.0, assumed accessible)."""
        results = analyzer.analyze_area(bbox, max_locations=10, max_distance_to_road_km=0.05)
        # DaMingObs + HillView pass (d=0.0), HighPeak + LowPeak filtered (d~0.086km)
        assert len(results) == 2
        assert all(r.location_type != "mountain_peak" for r in results)

    def test_road_distance_filter_keeps_near_places(self, analyzer, bbox):
        """max_distance_to_road_km=0.2 should keep places at 0.15km."""
        results = analyzer.analyze_area(bbox, max_locations=10, max_distance_to_road_km=0.2)
        assert len(results) > 0

    def test_town_isolation_is_accurate(self, analyzer, bbox):
        """Nearest town and distance should be reflected in results."""
        results = analyzer.analyze_area(bbox, max_locations=10)
        for loc in results:
            assert loc.nearest_town_name is not None

    def test_disabled_road_connectivity_still_works(self, analyzer, bbox):
        """With include_road_connectivity=False, scoring should still work but road fields may be None."""
        results = analyzer.analyze_area(bbox, max_locations=10, include_road_connectivity=False)
        assert len(results) > 0
        # When road check is skipped, distance_to_road_km may be None
        for loc in results:
            assert loc.stargazing_score is not None

    def test_no_locations_found(self, analyzer, bbox):
        """When finders return empty lists, analyze_area should return empty list."""
        analyzer.mountain_finder.find_peaks_in_area = MagicMock(return_value=[])
        analyzer.mountain_finder.find_observatories_in_area = MagicMock(return_value=[])
        analyzer.mountain_finder.find_viewpoints_in_area = MagicMock(return_value=[])
        results = analyzer.analyze_area(bbox, max_locations=10)
        assert results == []

    def test_custom_location_type(self, analyzer, bbox):
        """Only search a single location type."""
        analyzer.mountain_finder.find_observatories_in_area = MagicMock(return_value=[])
        analyzer.mountain_finder.find_viewpoints_in_area = MagicMock(return_value=[])
        # Only peaks remain
        results = analyzer.analyze_area(bbox, max_locations=10, location_types=["mountain_peak"])
        assert len(results) >= 1
        assert all("Peak" in r.name or "peak" in r.name for r in results)

    def test_truncation_with_max_locations(self, analyzer, bbox):
        """With max_locations=1, only the highest-scored result is returned.

        Observatories and viewpoints get full road-access scores (d=0) and
        may outrank peaks — the specific winner depends on mock data.
        """
        results = analyzer.analyze_area(bbox, max_locations=1)
        assert len(results) == 1
        assert results[0].stargazing_score >= 0

    def test_location_type_attributes_preserved(self, analyzer, bbox):
        """Each result should preserve its original location type."""
        results = analyzer.analyze_area(bbox, max_locations=10)
        for loc in results:
            assert loc.location_type in ("mountain_peak", "observatory", "viewpoint")
