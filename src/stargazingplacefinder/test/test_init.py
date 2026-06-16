# -*- coding: utf-8 -*-
"""
Tests for stargazingplacefinder top-level package re-exports.
"""

import sys
import os

import pytest

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))


class TestPackageExports:
    """Test that the top-level package exports work."""

    def test_import_all_symbols(self):
        """Verify all __all__ symbols are importable."""
        from stargazingplacefinder import (
            init_stargazing_analyzer,
            analyze_area,
            analyze_area_simple,
            init_light_pollution_analyzer,
            get_light_pollution_grid,
            analyze_coordinate,
        )

        assert callable(init_stargazing_analyzer)
        assert callable(analyze_area)
        assert callable(analyze_area_simple)
        assert callable(init_light_pollution_analyzer)
        assert callable(get_light_pollution_grid)
        assert callable(analyze_coordinate)

    def test_all_exports(self):
        """Verify __all__ matches expected exports."""
        from stargazingplacefinder import __all__

        expected = [
            "init_stargazing_analyzer",
            "analyze_area",
            "analyze_area_simple",
            "init_light_pollution_analyzer",
            "get_light_pollution_grid",
            "analyze_coordinate",
        ]
        assert sorted(__all__) == sorted(expected)
