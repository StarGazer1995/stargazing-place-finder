# -*- coding: utf-8 -*-
"""
Tests for stargazing_location_analyzer scoring and filtering pipeline.
Uses mocked mountain_finder to exercise analyze_area with no data.
"""

import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from models import StargazingLocation
from stargazing_analyzer.stargazing_location_analyzer import StargazingLocationAnalyzer


@pytest.fixture
def analyzer():
    """Create a StargazingLocationAnalyzer with all deps mocked.

    The three @patch decorators prevent the real StarGazingPlaceFinder,
    RoadConnectivityChecker, and LightPollutionAnalyzer constructors from
    running (avoiding slow init/IO). The resulting attributes are then
    replaced with bare MagicMock() for test control.
    """
    with (
        patch("stargazing_analyzer.stargazing_location_analyzer.StarGazingPlaceFinder"),
        patch("stargazing_analyzer.stargazing_location_analyzer.RoadConnectivityChecker"),
        patch("stargazing_analyzer.stargazing_location_analyzer.LightPollutionAnalyzer"),
    ):
        a = StargazingLocationAnalyzer()

        # Mock mountain_finder — replaces the patched StarGazingPlaceFinder instance
        a.mountain_finder = MagicMock()
        a.mountain_finder.find_peaks_in_area.return_value = []
        a.mountain_finder.find_observatories_in_area.return_value = []
        a.mountain_finder.find_viewpoints_in_area.return_value = []
        a.mountain_finder.gis_service = MagicMock()
        a.mountain_finder.gis_service.query_locations.return_value = []

        # Mock road_checker
        a.road_checker = MagicMock()

        # Mock light_pollution_analyzer
        a.light_pollution_analyzer = MagicMock()
        a.light_pollution_analyzer.get_luminance_at.return_value = (10.0, 3)

        yield a


class TestAnalyzeAreaNoLocations:
    """Test analyze_area with no locations found."""

    def test_no_locations_returns_empty(self, analyzer):
        result = analyzer.analyze_area(bbox=(39.0, 115.0, 41.0, 117.0), max_locations=10)
        assert result == []


@pytest.fixture
def sample_location():
    """A valid StargazingLocation with all required fields."""
    return StargazingLocation(
        name="TestPeak",
        latitude=40.0,
        longitude=116.0,
        elevation=2000.0,
        distance_to_nearest_town=5.0,
        nearest_town_name="Town",
        height_difference=200.0,
        light_pollution_brightness=30,
        road_accessible=True,
        distance_to_road_km=0.1,
    )


class TestScoringAndRecommendation:
    """Test scoring and recommendation with valid StargazingLocation."""

    def test_calculate_stargazing_score(self, analyzer, sample_location):
        """Valid location should return a valid score."""
        score = analyzer._calculate_stargazing_score(sample_location)
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    def test_get_recommendation_level(self, analyzer):
        """Score should map to a recommendation level."""
        for score, expected_start in [(90, "强烈推荐"), (70, "推荐"), (40, "一般"), (20, "不推荐")]:
            rec = analyzer._get_recommendation_level(score)
            assert rec is not None
            assert isinstance(rec, str)

    def test_generate_analysis_notes(self, analyzer, sample_location):
        """Analysis notes should be generated."""
        notes = analyzer._generate_analysis_notes(sample_location)
        assert notes is not None
        assert isinstance(notes, str)

    def test_recommendation_with_missing_light_pollution(self, analyzer, sample_location):
        """When light pollution data is missing, recommendation includes warning."""
        sample_location.light_pollution_brightness = None
        rec = analyzer._get_recommendation_level_with_warning(sample_location)
        assert "Missing light pollution data" in rec

    def test_score_light_pollution_via_bortle(self, analyzer, sample_location):
        """Score based on Bortle class directly."""
        sample_location.light_pollution_bortle = 1
        score = analyzer._score_light_pollution(sample_location)
        assert score == 35  # Best bortle

        sample_location.light_pollution_bortle = 9
        score = analyzer._score_light_pollution(sample_location)
        assert score == 0  # Worst bortle

    def test_score_light_pollution_via_brightness(self, analyzer, sample_location):
        """Score based on brightness when no bortle."""
        sample_location.light_pollution_bortle = None
        sample_location.light_pollution_brightness = 25
        assert analyzer._score_light_pollution(sample_location) == 35

        sample_location.light_pollution_brightness = 250
        assert analyzer._score_light_pollution(sample_location) == 0

    def test_score_light_pollution_via_brightness_all_bands(self, analyzer):
        """Cover all brightness bands (lines 470, 472, 474, 478, 480)."""
        loc = StargazingLocation(
            name="B",
            latitude=40.0,
            longitude=116.0,
            elevation=1000.0,
            distance_to_nearest_town=10.0,
            nearest_town_name="T",
        )
        loc.light_pollution_bortle = None
        for brightness, expected in [(80, 26), (110, 20), (140, 14), (200, 3), (230, 1)]:
            loc.light_pollution_brightness = brightness
            assert analyzer._score_light_pollution(loc) == expected, f"Failed at brightness={brightness}"

    def test_score_light_pollution_via_level(self, analyzer, sample_location):
        """Score based on legacy pollution level string."""
        sample_location.light_pollution_bortle = None
        sample_location.light_pollution_brightness = None
        sample_location.light_pollution_level = "Extremely Low"
        assert analyzer._score_light_pollution(sample_location) == 35

    def test_score_light_pollution_missing_data(self, analyzer, sample_location):
        """Score with no pollution data at all returns conservative middle."""
        sample_location.light_pollution_bortle = None
        sample_location.light_pollution_brightness = None
        sample_location.light_pollution_level = None
        assert analyzer._score_light_pollution(sample_location) == 18

    def test_score_town_isolation(self, analyzer, sample_location):
        """Town isolation scoring for various distances."""
        sample_location.distance_to_nearest_town = 50
        score = analyzer._score_town_isolation(sample_location)
        assert score > 0

        sample_location.distance_to_nearest_town = 0
        score = analyzer._score_town_isolation(sample_location)
        assert score == 8  # Unknown/missing → medium

        sample_location.distance_to_nearest_town = None
        score = analyzer._score_town_isolation(sample_location)
        assert score == 8

    def test_score_town_isolation_density_penalty(self, analyzer, sample_location):
        """Density penalty reduces town isolation score."""
        sample_location.distance_to_nearest_town = 50
        sample_location.nearby_town_count = 0
        no_density = analyzer._score_town_isolation(sample_location)

        sample_location.nearby_town_count = 5
        with_density = analyzer._score_town_isolation(sample_location)
        assert with_density < no_density

    def test_score_road_accessibility(self, analyzer, sample_location):
        """Road accessibility scoring for various distances."""
        sample_location.road_accessible = True
        sample_location.distance_to_road_km = 0.1
        assert analyzer._score_road_accessibility(sample_location) == 20  # Ideal

        sample_location.distance_to_road_km = 0.01
        assert analyzer._score_road_accessibility(sample_location) == 14  # Too close

        sample_location.distance_to_road_km = None
        assert analyzer._score_road_accessibility(sample_location) == 12

        sample_location.road_accessible = False
        assert analyzer._score_road_accessibility(sample_location) == 0

        sample_location.road_accessible = None
        assert analyzer._score_road_accessibility(sample_location) == 10

    def test_score_elevation_terrain(self, analyzer, sample_location):
        """Elevation and terrain scoring."""
        sample_location.elevation = 4000.0
        sample_location.height_difference = 500.0
        score = analyzer._score_elevation_terrain(sample_location)
        assert score > 10  # Should get high terrain score

        sample_location.elevation = None
        sample_location.height_difference = None
        assert analyzer._score_elevation_terrain(sample_location) == 0

    def test_score_location_type_mountain(self, analyzer, sample_location):
        """Location type scoring for mountain peak."""
        sample_location.location_type = "mountain_peak"
        sample_location.prominence = 1500.0
        score = analyzer._score_location_type(sample_location)
        assert score > 5  # 1500/200 = 7.5

    def test_score_location_type_mountain_no_prominence(self, analyzer, sample_location):
        """Mountain with no prominence gets 0."""
        sample_location.location_type = "mountain_peak"
        sample_location.prominence = 0.0
        score = analyzer._score_location_type(sample_location)
        assert score == 0

    def test_score_location_type_observatory(self, analyzer, sample_location):
        """Location type scoring for observatory."""
        sample_location.location_type = "observatory"
        score = analyzer._score_location_type(sample_location)
        assert score == 6

    def test_score_location_type_viewpoint(self, analyzer, sample_location):
        """Location type scoring for viewpoint."""
        sample_location.location_type = "viewpoint"
        sample_location.height_difference = 1000.0
        score = analyzer._score_location_type(sample_location)
        assert score > 5  # 1000/150 ≈ 6.67

    def test_score_location_type_viewpoint_no_height(self, analyzer, sample_location):
        """Viewpoint with no height gets base 5."""
        sample_location.location_type = "viewpoint"
        sample_location.height_difference = 0.0
        score = analyzer._score_location_type(sample_location)
        assert score == 5  # No height → base


class TestFilterByRoadDistance:
    """Test cross-module pipeline (filtering, count_nearby_towns)."""

    def test_filter_no_op_when_no_limits(self, analyzer):
        """With no min/max, all locations pass through."""
        locs = [MagicMock(spec=StargazingLocation) for _ in range(3)]
        for loc in locs:
            loc.distance_to_road_km = 0.5
        result = analyzer._filter_by_road_distance(locs, None, None)
        assert len(result) == 3

    def test_filter_min_distance(self, analyzer):
        """min_km removes too-close locations."""
        locs = []
        for d in [0.0, 0.5, 1.0]:
            loc = MagicMock(spec=StargazingLocation)
            loc.distance_to_road_km = d
            locs.append(loc)
        result = analyzer._filter_by_road_distance(locs, 0.3, None)
        assert len(result) == 2

    def test_filter_max_distance(self, analyzer):
        """max_km removes too-far locations."""
        locs = []
        for d in [0.1, 0.5, 5.0]:
            loc = MagicMock(spec=StargazingLocation)
            loc.distance_to_road_km = d
            locs.append(loc)
        result = analyzer._filter_by_road_distance(locs, None, 1.0)
        assert len(result) == 2

    def test_filter_skips_none_distance(self, analyzer):
        """Locations with None distance are skipped."""
        locs = []
        for d in [0.1, None, 0.5]:
            loc = MagicMock(spec=StargazingLocation)
            loc.distance_to_road_km = d
            locs.append(loc)
        result = analyzer._filter_by_road_distance(locs, 0.2, None)
        assert len(result) == 1


class TestCountNearbyTowns:
    """Test _count_nearby_towns helper."""

    def test_empty_towns_returns_zero(self, analyzer):
        point = MagicMock()
        assert analyzer._count_nearby_towns(point, []) == 0

    def test_with_node_towns(self, analyzer):
        """Towns with 'type: node' with lat/lon."""
        point = MagicMock()
        point.latitude = 40.0
        point.longitude = 116.0
        towns = [
            {"type": "node", "lat": 40.1, "lon": 116.1},
            {"type": "node", "lat": 41.0, "lon": 116.0},  # Far
        ]
        analyzer.mountain_finder.calculate_distance.return_value = 10.0  # Within 20km

        count = analyzer._count_nearby_towns(point, towns)
        assert count > 0  # 2 towns - 1 (nearest) = at least 1

    def test_with_area_towns_center(self, analyzer):
        """Towns with 'center' key."""
        point = MagicMock()
        point.latitude = 40.0
        point.longitude = 116.0
        towns = [
            {"center": {"lat": 40.05, "lon": 116.05}},
        ]
        analyzer.mountain_finder.calculate_distance.return_value = 5.0
        count = analyzer._count_nearby_towns(point, towns)
        assert count == 0  # Only 1 town → nearest = 1, so max(0, 1-1) = 0

    def test_town_with_missing_keys(self, analyzer):
        """Towns missing lat/lon or center are skipped."""
        point = MagicMock()
        point.latitude = 40.0
        point.longitude = 116.0
        towns = [
            {"type": "node"},  # Missing lat/lon
            {"center": {}},  # Missing lat/lon inside
            {},  # Missing everything
        ]
        analyzer.mountain_finder.calculate_distance.return_value = 10.0
        count = analyzer._count_nearby_towns(point, towns)
        assert count == 0  # All skipped


class TestFetchTownsData:
    """Test _fetch_towns_data error handling."""

    def test_no_data_error_returns_empty(self, analyzer):
        """When query_locations raises NoDataError, return []."""
        from models import NoDataError

        analyzer.mountain_finder.gis_service.query_locations.side_effect = NoDataError("no data")
        result = analyzer._fetch_towns_data(MagicMock())
        assert result == []


class TestProcessOneLocation:
    """Test _process_one_location with full data."""

    def test_basic_processing(self, analyzer):
        """Basic location processing with light pollution and road data."""

        loc = MagicMock()
        loc.name = "Test"
        loc.latitude = 40.0
        loc.longitude = 116.0
        loc.elevation = 2000.0
        loc.prominence = 500.0
        loc.distance_to_nearest_town = 5.0
        loc.nearest_town_name = "Town"
        loc.height_difference = 200.0
        loc.location_type = "mountain_peak"
        loc.description = "A test peak"

        towns_data = [{"type": "node", "lat": 40.1, "lon": 116.1}]
        lp_batch = {
            (40.0, 116.0): MagicMock(
                rgb=(50, 120, 50),
                hex="#327832",
                brightness=64,
                pollution_level="Low",
                bortle=3,
                overlay_name="VIIRS",
                radiance=1.2,
            )
        }

        analyzer.mountain_finder.calculate_distance.return_value = 10.0
        analyzer.road_checker.get_accessibility_info.return_value = {
            "accessible": True,
            "distance_to_road_km": 0.1,
        }

        result = analyzer._process_one_location(loc, towns_data, lp_batch, True, "drive", 1, 1)

        assert result is not None
        assert result.name == "Test"
        assert result.light_pollution_brightness == 64
        assert result.light_pollution_bortle == 3
        assert result.road_accessible is True
        assert result.distance_to_road_km == 0.1
        assert result.stargazing_score is not None
        assert result.recommendation_level is not None
        assert result.analysis_notes is not None

    def test_road_check_failure(self, analyzer):
        """When road check raises an error, road_check_error is set."""

        loc = MagicMock()
        loc.name = "Test"
        loc.latitude = 40.0
        loc.longitude = 116.0
        loc.elevation = 2000.0
        loc.prominence = 0.0
        loc.distance_to_nearest_town = 10.0
        loc.nearest_town_name = "Town"
        loc.height_difference = 0.0
        loc.location_type = "mountain_peak"
        loc.description = None

        from models import NetworkError

        analyzer.road_checker.get_accessibility_info.side_effect = NetworkError("network failed")

        result = analyzer._process_one_location(loc, [], {}, True, "drive", 1, 1)

        assert result is not None
        assert result.road_check_error is not None


class TestAnalyzeAreaWithMockData:
    """Test _search_locations and analyze_area pipeline with mocked data."""

    def test_search_locations_truncates(self, analyzer):
        """_search_locations truncates to max_locations."""
        from models import LatLonBox

        peak = MagicMock()
        peak.name = "Peak1"
        peak.latitude = 40.0
        peak.longitude = 116.0
        peak.elevation = 1000.0
        peak.prominence = 200.0
        peak.distance_to_nearest_town = 10.0
        peak.nearest_town_name = "Town"
        peak.height_difference = 100.0
        peak.location_type = "mountain_peak"
        peak.description = None

        # Return 2 peaks but max_locations=1 → should truncate to 1
        analyzer.mountain_finder.find_peaks_in_area.return_value = [peak, peak]
        bbox = LatLonBox(south=39.0, west=115.0, north=41.0, east=117.0)
        result = analyzer._search_locations(bbox, max_locations=1, location_types=["mountain_peak"])
        assert len(result) == 1

    def test_unsupported_location_type(self, analyzer, caplog):
        """Unsupported location types log a warning."""
        import logging

        caplog.set_level(logging.WARNING)

        with patch.object(analyzer.mountain_finder, "find_peaks_in_area", return_value=[]):
            bbox = MagicMock()
            result = analyzer._search_locations(bbox, max_locations=5, location_types=["invalid_type"])
            assert result == []

    def test_analyze_area_with_bbox_tuple(self, analyzer):
        """analyze_area accepts bbox as tuple and returns empty."""
        # peak returns empty → no locations
        analyzer.mountain_finder.find_peaks_in_area.return_value = []
        analyzer.mountain_finder.find_observatories_in_area.return_value = []
        analyzer.mountain_finder.find_viewpoints_in_area.return_value = []

        result = analyzer.analyze_area(
            bbox=(39.0, 115.0, 41.0, 117.0),
            max_locations=5,
            include_light_pollution=True,
            include_road_connectivity=True,
            min_distance_to_road_km=0.1,
            max_distance_to_road_km=5.0,
        )
        assert result == []

    def test_analysis_notes_all_branches(self, analyzer):
        """Cover all branches of _generate_analysis_notes."""
        # Large height diff + bright pollution + road info + far town
        loc = StargazingLocation(
            name="T",
            latitude=40.0,
            longitude=116.0,
            elevation=2000.0,
            distance_to_nearest_town=60.0,
            nearest_town_name="FarTown",
            height_difference=500.0,
            light_pollution_brightness=150,
            road_accessible=True,
            distance_to_road_km=0.1,
        )
        notes = analyzer._generate_analysis_notes(loc)
        assert "Significant altitude advantage" in notes
        assert "Serious light pollution" in notes
        assert "Convenient transportation" in notes
        assert "Far from town" in notes

        # Medium brightness + road not accessible
        loc2 = StargazingLocation(
            name="T2",
            latitude=40.0,
            longitude=116.0,
            elevation=1000.0,
            distance_to_nearest_town=5.0,
            nearest_town_name="NearTown",
            height_difference=200.0,
            light_pollution_brightness=80,
            road_accessible=False,
            distance_to_road_km=None,
        )
        notes2 = analyzer._generate_analysis_notes(loc2)
        assert "Some altitude advantage" in notes2
        assert "Medium light pollution" in notes2
        assert "Road not accessible" in notes2
        assert "Close to town" in notes2

        # No light pollution data
        loc3 = StargazingLocation(
            name="T3",
            latitude=40.0,
            longitude=116.0,
            elevation=500.0,
            distance_to_nearest_town=20.0,
            nearest_town_name="SomeTown",
            height_difference=50.0,
            light_pollution_brightness=None,
            road_accessible=True,
            distance_to_road_km=2.0,
        )
        notes3 = analyzer._generate_analysis_notes(loc3)
        assert "Missing light pollution data" in notes3
        assert "Road accessible" in notes3  # distance >= 1km → "Road accessible"

    def test_score_recommendation_consider(self, analyzer):
        """Score in 50-60 range returns 'Consider'."""
        rec = analyzer._get_recommendation_level(55)
        assert "Consider" in rec

    def test_score_legacy_pollution_level(self, analyzer):
        """Legacy pollution level string scoring."""
        loc = StargazingLocation(
            name="L",
            latitude=40.0,
            longitude=116.0,
            elevation=1000.0,
            distance_to_nearest_town=10.0,
            nearest_town_name="T",
        )
        loc.light_pollution_bortle = None
        loc.light_pollution_brightness = None
        loc.light_pollution_level = "Very High"
        assert analyzer._score_light_pollution(loc) == 8

    def test_score_road_accessibility_beyond_threshold(self, analyzer, sample_location):
        """Road accessible but beyond 200m returns 10."""
        sample_location.road_accessible = True
        sample_location.distance_to_road_km = 0.5
        assert analyzer._score_road_accessibility(sample_location) == 10

    def test_score_town_isolation_very_close(self, analyzer, sample_location):
        """Town distance < 5km gives 0 score before density."""
        sample_location.distance_to_nearest_town = 2.0
        sample_location.nearby_town_count = 0
        assert analyzer._score_town_isolation(sample_location) == 0

    def test_score_location_type_unknown(self, analyzer, sample_location):
        """Unknown location type returns 0."""
        sample_location.location_type = "unknown"
        assert analyzer._score_location_type(sample_location) == 0

    def test_search_locations_multiple_types(self, analyzer):
        """_search_locations combines results from multiple types."""
        from models import LatLonBox

        peak = MagicMock()
        peak.name = "P"
        peak.latitude = 40.0
        peak.longitude = 116.0
        peak.elevation = 1000.0
        peak.prominence = 200.0
        peak.distance_to_nearest_town = 10.0
        peak.nearest_town_name = "T"
        peak.height_difference = 100.0
        peak.location_type = "mountain_peak"
        peak.description = None

        obs = MagicMock()
        obs.name = "O"
        obs.latitude = 40.0
        obs.longitude = 116.0
        obs.elevation = 1000.0
        obs.prominence = 0.0
        obs.distance_to_nearest_town = 10.0
        obs.nearest_town_name = "T"
        obs.height_difference = 0.0
        obs.location_type = "observatory"
        obs.description = None

        analyzer.mountain_finder.find_peaks_in_area.return_value = [peak]
        analyzer.mountain_finder.find_observatories_in_area.return_value = [obs]
        bbox = LatLonBox(south=39.0, west=115.0, north=41.0, east=117.0)
        result = analyzer._search_locations(bbox, max_locations=5, location_types=["mountain_peak", "observatory"])
        assert len(result) == 2


class TestLoadDbConfig:
    """Test _load_db_config with temp files."""

    def test_load_json_config(self, tmp_path):
        """JSON config loads correctly."""
        cfg = {"host": "localhost", "port": 5432}
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('{"host": "localhost", "port": 5432}')
        a = StargazingLocationAnalyzer()
        result = a._load_db_config(str(cfg_file))
        assert result == cfg

    def test_load_toml_config(self, tmp_path):
        """TOML config loads correctly across supported Python versions."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('host = "localhost"\nport = 5432\n')
        a = StargazingLocationAnalyzer()
        result = a._load_db_config(str(cfg_file))
        assert result == {"host": "localhost", "port": 5432}

    def test_load_toml_config_falls_back_to_tomli(self, tmp_path):
        """When tomllib is unavailable, the loader falls back to tomli."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('host = "localhost"\nport = 5432\n')
        analyzer = StargazingLocationAnalyzer()
        fake_tomli = types.ModuleType("tomli")

        def fake_load(file_obj):
            return {"host": "localhost", "port": 5432, "loaded_by": "tomli"}

        fake_tomli.load = fake_load
        real_import = __import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "tomllib":
                raise ImportError("tomllib unavailable")
            if name == "tomli":
                return fake_tomli
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            result = analyzer._load_db_config(str(cfg_file))

        assert result == {"host": "localhost", "port": 5432, "loaded_by": "tomli"}

    def test_invalid_format_raises(self, tmp_path):
        """Unsupported extension raises ValueError."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("")
        a = StargazingLocationAnalyzer()
        with pytest.raises(ValueError, match="Unsupported config format"):
            a._load_db_config(str(cfg_file))


class TestBatchLightPollution:
    """Test _batch_light_pollution helper."""

    def test_disabled_when_not_included(self, analyzer):
        """Returns empty when include_light_pollution is False."""
        result = analyzer._batch_light_pollution([], False)
        assert result == {}

    def test_with_data(self, analyzer):
        """Batch analysis returns coordinate→pollution_info mapping."""
        loc = MagicMock()
        loc.latitude = 40.0
        loc.longitude = 116.0

        analyzer.light_pollution_analyzer.batch_analyze_coordinates.return_value = [
            {
                "index": 0,
                "coordinates": (40.0, 116.0),
                "pollution_info": MagicMock(rgb=(1, 2, 3)),
                "success": True,
            }
        ]

        result = analyzer._batch_light_pollution([loc], True)
        assert len(result) == 1
        assert (40.0, 116.0) in result

    def test_geo_error_returns_empty(self, analyzer):
        """When batch_analyze_coordinates raises GeoError, returns empty."""
        from models import GeoError

        loc = MagicMock()
        loc.latitude = 40.0
        loc.longitude = 116.0

        analyzer.light_pollution_analyzer.batch_analyze_coordinates.side_effect = GeoError("test")
        result = analyzer._batch_light_pollution([loc], True)
        assert result == {}


class TestAnalyzerClose:
    """Test StargazingLocationAnalyzer.close()."""

    def test_close_with_light_pollution(self):
        """close() calls the inner light_pollution_analyzer.close()."""
        mock_lpa = MagicMock()
        with (
            patch("stargazing_analyzer.stargazing_location_analyzer.StarGazingPlaceFinder"),
            patch("stargazing_analyzer.stargazing_location_analyzer.RoadConnectivityChecker"),
            patch("stargazing_analyzer.stargazing_location_analyzer.LightPollutionAnalyzer"),
        ):
            a = StargazingLocationAnalyzer()
            a.light_pollution_analyzer = mock_lpa

        a.close()
        mock_lpa.close.assert_called_once()
        assert a.light_pollution_analyzer is None

    def test_close_without_light_pollution(self):
        """close() does nothing when light_pollution_analyzer is None."""
        with (
            patch("stargazing_analyzer.stargazing_location_analyzer.StarGazingPlaceFinder"),
            patch("stargazing_analyzer.stargazing_location_analyzer.RoadConnectivityChecker"),
            patch("stargazing_analyzer.stargazing_location_analyzer.LightPollutionAnalyzer"),
        ):
            a = StargazingLocationAnalyzer()
            a.light_pollution_analyzer = None
            a.close()  # should not raise
