# -*- coding: utf-8 -*-
"""
Tests for LightPollutionAnalyzer class methods with mocked rasterio source.

These tests create a LightPollutionAnalyzer and replace _src with a
properly mocked rasterio dataset to exercise all the getter methods.
"""

import os
import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer


class FakeRasterioSrc:
    """A fake rasterio dataset source for testing."""

    def __init__(self):
        self.height = 200
        self.width = 100
        self.count = 1
        self.dtypes = ["float32"]
        self.bounds = MagicMock()
        self.bounds.top = 50.0
        self.bounds.bottom = 48.0
        self.bounds.left = 100.0
        self.bounds.right = 101.0
        # Transform: (west, res_x, 0, north, 0, res_y)
        self.transform = (100.0, 0.01, 0.0, 50.0, 0.0, -0.01)
        self.crs = "EPSG:4326"

        # Create a mock data grid (rows x cols)
        self._data = np.zeros((self.height, self.width), dtype=np.float32)
        # Set some values in the middle
        self._data[100, 50] = 15.0  # Center point
        self._data[100, 51] = 20.0
        self._data[101, 50] = 10.0

    def index(self, x, y):
        """Convert lon/lat to row,col using truncation (matches real rasterio behavior).

        Real rasterio uses int(float) truncation, NOT round().
        """
        west = self.transform[0]
        res_x = self.transform[1]
        _, _, _, north, _, res_y = self.transform  # noqa
        col = int((x - west) / res_x)
        row = int((north - y) / -self.transform[5])
        return (row, col)

    def read(self, index, window=None, masked=False, out_shape=None):
        """Read data values."""
        if window is not None:
            ((row_start, row_stop), (col_start, col_stop)) = window
            data = self._data[row_start:row_stop, col_start:col_stop]
            if out_shape:
                import scipy.ndimage as ndimage

                hr, wr = out_shape
                data = ndimage.zoom(data, (hr / data.shape[0], wr / data.shape[1]), order=0)
            return data
        return self._data

    def close(self):
        """No-op close."""
        pass


@pytest.fixture
def analyzer():
    """Create LightPollutionAnalyzer with mocked _src."""
    a = LightPollutionAnalyzer()
    a._src = FakeRasterioSrc()
    a._skyglow_grid = None  # No skyglow model
    a._skyglow_transform = None
    a._skyglow_weight = 0.4  # Default weight (normally set in the file-loading path)
    a._skyglow_sigma_km = 15.0
    a._skyglow_ds = 1
    return a


class TestGetRawRadiance:
    """Test get_raw_radiance with mocked source."""

    def test_valid_coordinate(self, analyzer):
        # Mock data has row 100, col 50 → lat ~49.0, lon ~100.5
        radiance = analyzer.get_raw_radiance(49.0, 100.5)
        assert radiance is not None
        assert radiance == 15.0

    def test_out_of_bounds(self, analyzer):
        radiance = analyzer.get_raw_radiance(0.0, 0.0)
        assert radiance is None

    def test_no_src(self):
        a = LightPollutionAnalyzer()
        radiance = a.get_raw_radiance(30.0, 100.0)
        assert radiance is None


class TestGetRadiance:
    """Test get_radiance with skyglow."""

    def test_with_skyglow_disabled(self, analyzer):
        radiance = analyzer.get_radiance(49.0, 100.5)
        assert radiance is not None
        # No skyglow grid → skyglow = 0.0
        assert radiance == 15.0

    def test_out_of_bounds(self, analyzer):
        assert analyzer.get_radiance(0.0, 0.0) is None


class TestGetLightPollutionColor:
    """Test get_light_pollution_color."""

    def test_valid_coordinate(self, analyzer):
        info = analyzer.get_light_pollution_color(49.0, 100.5)
        assert info is not None
        assert abs(info.radiance - 15.0) < 0.1
        assert info.brightness > 0
        assert 1 <= info.bortle <= 9

    def test_invalid_latitude(self, analyzer):
        with pytest.raises(ValueError):
            analyzer.get_light_pollution_color(100.0, 100.0)

    def test_invalid_longitude(self, analyzer):
        with pytest.raises(ValueError):
            analyzer.get_light_pollution_color(30.0, 200.0)

    def test_out_of_bounds(self, analyzer):
        info = analyzer.get_light_pollution_color(0.0, 0.0)
        assert info is None

    def test_no_src(self):
        a = LightPollutionAnalyzer()
        info = a.get_light_pollution_color(30.0, 100.0)
        assert info is None


class TestBatchAnalyzeCoordinates:
    """Test batch_analyze_coordinates."""

    def test_with_valid_points(self, analyzer):
        coords = [(49.0, 100.5), (49.0, 100.51)]
        results = analyzer.batch_analyze_coordinates(coords)
        assert len(results) == 2
        # At least the center one should succeed
        successes = [r for r in results if r["success"]]
        assert len(successes) >= 1

    def test_all_out_of_bounds(self, analyzer):
        coords = [(0.0, 0.0), (1.0, 1.0)]
        results = analyzer.batch_analyze_coordinates(coords)
        assert all(not r["success"] for r in results)

    def test_no_src(self):
        a = LightPollutionAnalyzer()
        results = a.batch_analyze_coordinates([(30.0, 100.0)])
        assert len(results) == 1
        assert not results[0]["success"]


class TestGetStatistics:
    """Test get_statistics."""

    def test_with_src(self, analyzer):
        stats = analyzer.get_statistics()
        assert stats["backend"] == "geotiff"
        assert stats["width"] == 100
        assert stats["height"] == 200

    def test_no_src(self):
        a = LightPollutionAnalyzer()
        stats = a.get_statistics()
        assert "error" in stats
