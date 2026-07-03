# -*- coding: utf-8 -*-
"""
Tests for light_pollution_analyzer: false-colour rendering and init/close edge cases.

Conversion tests (radiance_to_bortle/brightness/pollution_level) live in
``test_public_api.py`` to avoid duplication.
"""

from light_pollution.light_pollution_analyzer import (
    LightPollutionAnalyzer,
    radiance_to_false_color,
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
        assert r < 100
        assert b > r  # blue channel should be brighter

    def test_medium_radiance(self):
        """Medium radiance should be in green-yellow range."""
        r, g, b = radiance_to_false_color(10)
        assert g > 80

    def test_high_radiance(self):
        """High radiance should return bright warm colors."""
        r, g, b = radiance_to_false_color(500)
        assert r >= 200
        assert b <= 100

    def test_negative_radiance(self):
        """Negative radiance is clamped to dark value."""
        r, g, b = radiance_to_false_color(-1)
        assert r < 100


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
        analyzer.close()
