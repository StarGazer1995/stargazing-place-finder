# -*- coding: utf-8 -*-
"""
Performance baseline benchmarks for the stargazing pipeline.

These benchmarks establish baselines for the most performance-critical
code paths. Run with::

    uv run pytest src/stargazing_analyzer/test/test_benchmarks.py --benchmark-only
    uv run pytest src/stargazing_analyzer/test/test_benchmarks.py --benchmark-histogram

Dependencies IO-bound (road network downloads, GeoTIFF reads) are mocked so
benchmarks measure CPU-bound logic, not network latency.
"""

from unittest.mock import MagicMock

import pytest

from models import StargazingLocation

# ═══════════════════════════════════════════════════════════════════
# Fixtures — sample location objects (no conftest dependency for isolation)
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def peak_location() -> StargazingLocation:
    """A typical mountain-peak location."""
    return StargazingLocation(
        name="Benchmark Peak",
        latitude=40.0,
        longitude=116.0,
        elevation=1500.0,
        prominence=600.0,
        distance_to_nearest_town=35.0,
        nearest_town_name="Sample Town",
        height_difference=400.0,
        light_pollution_brightness=45,  # Bortle ~2
        light_pollution_bortle=2,
        road_accessible=True,
        distance_to_road_km=0.12,
        stargazing_score=0.0,
    )


@pytest.fixture
def dim_location() -> StargazingLocation:
    """A high-light-pollution location (worst case for scoring)."""
    return StargazingLocation(
        name="City Adjacent",
        latitude=39.9,
        longitude=116.4,
        elevation=50.0,
        prominence=0.0,
        distance_to_nearest_town=2.0,
        nearest_town_name="Big City",
        height_difference=10.0,
        light_pollution_brightness=255,  # Bortle 9
        road_accessible=False,
        distance_to_road_km=0.01,
        nearby_town_count=15,
        stargazing_score=0.0,
    )


# ═══════════════════════════════════════════════════════════════════
# Benchmark 1 — Scoring pipeline (pure CPU, no IO)
# ═══════════════════════════════════════════════════════════════════


class TestScoringBenchmarks:
    """Baseline for ``_calculate_stargazing_score`` and all sub-scores."""

    @pytest.fixture
    def analyzer(self):
        """A bare ``StargazingLocationAnalyzer`` with no real dependencies."""
        from stargazing_analyzer.stargazing_location_analyzer import (
            StargazingLocationAnalyzer,
        )

        return StargazingLocationAnalyzer()

    def test_score_peak_location(self, analyzer, peak_location, benchmark):
        """Score an ideal mountain-peak location (all data present)."""
        result = benchmark(analyzer._calculate_stargazing_score, peak_location)
        assert 0 <= result <= 100

    def test_score_dim_location(self, analyzer, dim_location, benchmark):
        """Score a city-adjacent location (worst data)."""
        result = benchmark(analyzer._calculate_stargazing_score, dim_location)
        assert 0 <= result <= 100

    def test_score_light_pollution(self, analyzer, peak_location, benchmark):
        """Light-pollution sub-score (Bortle lookup path)."""
        result = benchmark(analyzer._score_light_pollution, peak_location)
        assert 0 <= result <= 35

    def test_score_town_isolation(self, analyzer, peak_location, benchmark):
        """Town-isolation sub-score (distance + density)."""
        result = benchmark(analyzer._score_town_isolation, peak_location)
        assert 0 <= result <= 20

    def test_score_road_access(self, analyzer, peak_location, benchmark):
        """Road-accessibility sub-score."""
        result = benchmark(analyzer._score_road_accessibility, peak_location)
        assert 0 <= result <= 20

    def test_score_elevation_terrain(self, analyzer, peak_location, benchmark):
        """Elevation + terrain sub-score."""
        result = benchmark(analyzer._score_elevation_terrain, peak_location)
        assert 0 <= result <= 15

    def test_score_location_type(self, analyzer, peak_location, benchmark):
        """Location-type sub-score (mountain prominence path)."""
        result = benchmark(analyzer._score_location_type, peak_location)
        assert 0 <= result <= 10


# ═══════════════════════════════════════════════════════════════════
# Benchmark 2 — Light pollution GeoTIFF lookup (mocked GeoTIFF)
# ═══════════════════════════════════════════════════════════════════


class TestLightPollutionBenchmarks:
    """Baseline for ``get_luminance_at`` and ``batch_analyze_coordinates``."""

    @pytest.fixture
    def mock_analyzer(self):
        """``LightPollutionAnalyzer`` with a tiny in-memory GeoTIFF mock."""
        from light_pollution.light_pollution_analyzer import (
            LightPollutionAnalyzer,
        )

        a = LightPollutionAnalyzer(geotiff_path=None)
        a._geotiff_path = "/fake/path.tif"
        a._src = MagicMock()
        # Stub get_radiance so get_light_pollution_color exercises the full
        # transformation pipeline (Bortle, brightness, false-color) without IO.
        a.get_radiance = MagicMock(return_value=50.0)
        return a

    def test_get_light_pollution_color(self, mock_analyzer, benchmark):
        """Single-coordinate light pollution lookup (fast path)."""
        result = benchmark(mock_analyzer.get_light_pollution_color, 40.0, 116.0)
        assert result is not None

    def test_batch_analyze_coordinates(self, mock_analyzer, benchmark):
        """Batch of 10 coordinates."""
        coords = [(40.0 + i * 0.01, 116.0 + i * 0.01) for i in range(10)]
        result = benchmark(mock_analyzer.batch_analyze_coordinates, coords)
        assert len(result) == 10


# ═══════════════════════════════════════════════════════════════════
# Benchmark 3 — Road connectivity check (GeoFence fast path)
# ═══════════════════════════════════════════════════════════════════


class TestRoadConnectivityBenchmarks:
    """Baseline for ``get_accessibility_info`` via GeoFence (no OSMnx)."""

    @pytest.fixture
    def geo_fence_checker(self):
        """``RoadConnectivityChecker`` with GeoFence enabled."""
        from road_connectivity.geo_fence import GeoFence
        from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

        return RoadConnectivityChecker(search_radius_km=5.0, geo_fence=GeoFence(enabled=True))

    def test_get_accessibility_info(self, geo_fence_checker, benchmark):
        """Accessibility info for a single coordinate (GeoFence fast path)."""
        from models import GeoCoordinate

        point = GeoCoordinate(latitude=40.3242, longitude=116.6312)
        info = benchmark(geo_fence_checker.get_accessibility_info, point)
        assert "accessible" in info


# ═══════════════════════════════════════════════════════════════════
# Benchmark 4 — Full analyze_area (IO mocked, pipeline intact)
# ═══════════════════════════════════════════════════════════════════


class TestFullPipelineBenchmarks:
    """Baseline for the end-to-end ``analyze_area`` with mocked IO."""

    @pytest.fixture
    def mock_pipeline(self):
        """``StargazingLocationAnalyzer`` with all IO-bound deps mocked."""
        from road_connectivity.road_connectivity_checker import RoadConnectivityChecker
        from stargazing_analyzer.stargazing_location_analyzer import (
            StargazingLocationAnalyzer,
        )

        a = StargazingLocationAnalyzer(min_height_difference=50.0)
        # Mock mountain-finder to return pre-built Location objects
        a.mountain_finder.find_peaks_in_area = MagicMock(
            return_value=[
                StargazingLocation(
                    name="Mocked Peak",
                    latitude=40.0,
                    longitude=116.0,
                    elevation=1000.0,
                    prominence=300.0,
                    distance_to_nearest_town=25.0,
                    nearest_town_name="Sample Town",
                    height_difference=200.0,
                )
            ]
        )
        a.mountain_finder.find_observatories_in_area = MagicMock(return_value=[])
        a.mountain_finder.find_viewpoints_in_area = MagicMock(return_value=[])
        a.mountain_finder.gis_service = MagicMock()
        a.mountain_finder.gis_service.query_locations = MagicMock(return_value=[])
        # Mock road checker
        a.road_checker = MagicMock(spec=RoadConnectivityChecker)
        a.road_checker.get_accessibility_info.return_value = {
            "accessible": True,
            "distance_to_road_km": 0.15,
            "nearest_road_type": "secondary",
        }
        a.road_checker.is_road_accessible.return_value = True
        # Disable light pollution (no GeoTIFF in CI)
        a.light_pollution_analyzer = None
        return a

    def test_analyze_area_small(self, mock_pipeline, benchmark):
        """``analyze_area`` with 1 mocked location."""
        from models import LatLonBox

        bbox = LatLonBox(south=39.9, west=115.9, north=40.1, east=116.1)
        results = benchmark(
            mock_pipeline.analyze_area,
            bbox,
            max_locations=5,
            include_light_pollution=False,
            include_road_connectivity=True,
        )
        assert len(results) >= 0
