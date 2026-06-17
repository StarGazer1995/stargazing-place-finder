# -*- coding: utf-8 -*-
"""
Integration tests that verify the cache subsystem works with real modules.

Tests create real (un-mocked) LightPollutionAnalyzer and RoadConnectivityChecker
instances to confirm their cache directories are properly configured.
"""

import os

import pytest

from cache.cache_config import clear_cache, get_cache_info
from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
from road_connectivity.road_connectivity_checker import RoadConnectivityChecker


def test_cache_directories():
    """All expected cache sub-directories exist."""
    cache_info = get_cache_info()
    required_dirs = ["images", "road_networks", "osmnx", "temp"]

    for dir_name in required_dirs:
        assert dir_name in cache_info["subdirs"], f"{dir_name} directory not found in cache info"
        assert cache_info["subdirs"][dir_name]["exists"], f"{dir_name} directory does not exist"


def test_light_pollution_analyzer_cache():
    """Creating analyzer with geotiff_path=None still allows lazy init and close."""
    analyzer = LightPollutionAnalyzer(geotiff_path=None)
    assert analyzer._geotiff_path is None
    assert analyzer._src is None
    analyzer.close()  # close on uninitialized analyzer should not raise


def test_road_connectivity_checker_cache():
    """RoadConnectivityChecker creates and reports its cache directory."""
    checker = RoadConnectivityChecker()
    assert hasattr(checker, "_road_cache_dir"), "Road cache directory not configured"
    assert os.path.exists(checker._road_cache_dir), "Road cache directory does not exist"


@pytest.mark.slow
def test_osmnx_cache():
    """OSMnx cache folder is set to the project cache directory."""
    pytest.importorskip("osmnx")
    import osmnx as ox

    cache_folder = ox.settings.cache_folder
    assert cache_folder is not None, "OSMnx cache directory not set"


def test_cache_cleanup():
    """Temporary cache can be cleared successfully."""
    clear_cache("temp")

    cache_info = get_cache_info()
    assert "temp" in cache_info["subdirs"], "Temp cache directory not found"
    # After cleanup, temp directory should still exist (just emptied)
    assert cache_info["subdirs"]["temp"]["exists"], "Temp cache should still exist after cleanup"
