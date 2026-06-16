# -*- coding: utf-8 -*-
"""
Tests for light_pollution_analyzer standalone functions.

Tests conversion functions and edge cases in LightPollutionAnalyzer
without requiring the actual GeoTIFF file.
"""

import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import numpy as np

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from light_pollution.light_pollution_analyzer import (
    radiance_to_brightness,
    radiance_to_bortle,
    radiance_to_false_color,
    radiance_to_pollution_level,
    LightPollutionAnalyzer,
)


class TestRadianceConversion:
    """Test radiance→brightness conversion."""

    @pytest.mark.parametrize(
        "radiance, expected",
        [
            (0, 0),
            (1, 23),
            (10, 127),
            (50, 212),
            (100, 231),
            (500, 250),
            (1000, 252),
            (0.5, 12),
            (-1, 0),  # negative clamped to 0
        ],
    )
    def test_radiance_to_brightness(self, radiance, expected):
        result = radiance_to_brightness(radiance)
        assert result == expected, f"radiance={radiance}: expected {expected}, got {result}"


class TestBortleConversions:
    """Test Bortle scale conversions."""

    @pytest.mark.parametrize(
        "radiance, expected_bortle",
        [
            (0, 1),
            (0.1, 2),
            (0.5, 2),
            (1.0, 3),
            (3.0, 4),
            (4.0, 4),
            (7.0, 5),
            (10.0, 5),
            (20.0, 6),
            (25.0, 6),
            (40.0, 7),
            (60.0, 7),
            (100.0, 8),
            (150.0, 8),
            (200.0, 9),
        ],
    )
    def test_radiance_to_bortle(self, radiance, expected_bortle):
        assert radiance_to_bortle(radiance) == expected_bortle, (
            f"radiance={radiance}: expected {expected_bortle}, got {radiance_to_bortle(radiance)}"
        )


class TestRadianceFalseColor:
    """Test radiance_to_false_color."""

    def test_zero_radiance(self):
        """Zero radiance should return dark blue-black."""
        r, g, b = radiance_to_false_color(0)
        assert r == 10
        assert g == 10
        assert b == 40

    def test_low_radiance(self):
        """Low radiance should return blue-ish colors."""
        r, g, b = radiance_to_false_color(0.1)
        # Values are logarithmic, for 0.1 the V = log10(0.1+1)/log10(1001) ~ 0.1
        # Should be in the first band (v < 0.33) → blue dominant
        assert r < 100
        assert b > r  # blue channel should be brighter

    def test_medium_radiance(self):
        """Medium radiance should be in green-yellow range."""
        r, g, b = radiance_to_false_color(10)
        # V = log10(11)/log10(1001) ≈ 1.0414/3.0 ≈ 0.347 → second band (0.33-0.66)
        # Should have noticeable green
        assert g > 80

    def test_high_radiance(self):
        """High radiance should return bright warm colors."""
        r, g, b = radiance_to_false_color(500)
        # V = log10(501)/log10(1001) ≈ 2.7/3.0 ≈ 0.9 → third band (v > 0.66)
        # Should be red-white
        assert r >= 200
        assert b <= 100

    def test_negative_radiance(self):
        """Negative radiance was historically clamped to dark value."""
        r, g, b = radiance_to_false_color(-1)
        # The code uses max(radiance, 0.01) so -1 becomes 0.01
        assert r < 100


class TestRadiancePollutionLevel:
    """Test radiance_to_pollution_level labels."""

    @pytest.mark.parametrize(
        "radiance, expected_substring",
        [
            (0, "Class 1"),
            (0.5, "Class 2"),
            (1.0, "Class 3"),
            (4.0, "Class 4"),
            (10.0, "Class 5"),
            (25.0, "Class 6"),
            (60.0, "Class 7"),
            (150.0, "Class 8"),
            (200.0, "Class 9"),
        ],
    )
    def test_pollution_levels(self, radiance, expected_substring):
        label = radiance_to_pollution_level(radiance)
        assert expected_substring in label, f"radiance={radiance}: label='{label}' missing '{expected_substring}'"


class TestLightPollutionAnalyzerWithMock:
    """Test LightPollutionAnalyzer basic initialization (no file needed)."""

    def test_init_no_path(self):
        """Initialization with no geotiff path should succeed."""
        analyzer = LightPollutionAnalyzer()
        assert analyzer is not None
        assert analyzer._geotiff_path is None
        assert analyzer._src is None
        analyzer.close()

    def test_close_no_src(self):
        """close() with no _src set should not raise."""
        analyzer = LightPollutionAnalyzer()
        # _src is None, close should be safe
        analyzer.close()
