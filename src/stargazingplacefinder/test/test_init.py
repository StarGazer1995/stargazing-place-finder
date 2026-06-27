# -*- coding: utf-8 -*-
"""
Tests for stargazingplacefinder top-level package re-exports.
"""


# Ensure src is on path


class TestPackageExports:
    """Test that the top-level package exports work."""

    def test_import_all_symbols(self):
        """Verify all public symbols are importable and callable."""
        from stargazingplacefinder import (
            analyze_area,
            analyze_area_simple,
            analyze_coordinate,
            get_light_pollution_grid,
            init_light_pollution_analyzer,
        )

        assert callable(analyze_area)
        assert callable(analyze_area_simple)
        assert callable(init_light_pollution_analyzer)
        assert callable(get_light_pollution_grid)
        assert callable(analyze_coordinate)

    def test_all_exports(self):
        """Verify __all__ matches expected exports."""
        from stargazingplacefinder import __all__

        expected = [
            "analyze_area",
            "analyze_area_simple",
            "init_light_pollution_analyzer",
            "get_light_pollution_grid",
            "analyze_coordinate",
        ]
        assert sorted(__all__) == sorted(expected)
