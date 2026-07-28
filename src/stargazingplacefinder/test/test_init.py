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
            "init_stargazing_analyzer",
            "init_light_pollution_analyzer",
            "get_light_pollution_grid",
            "analyze_coordinate",
            # Exception types (exposed for isinstance checks in bridge layers)
            "StargazingError",
            "DataError",
            "NoDataError",
            "ValidationError",
            "NetworkError",
            "CacheError",
            "ConfigError",
            "GeoError",
        ]
        assert sorted(__all__) == sorted(expected)

    def test_namespaced_config_wrapper_exports_expected_symbols(self):
        """Verify package-scoped config imports remain available to bridge callers."""
        from stargazingplacefinder.config import StargazingConfig, load_stargazing_config

        assert StargazingConfig is not None
        assert callable(load_stargazing_config)

    def test_namespaced_models_wrapper_exports_expected_symbols(self):
        """Verify package-scoped model imports expose bridge-facing exception types."""
        from stargazingplacefinder.models import DataError, GeoPoint, StargazingLocation

        assert DataError is not None
        assert GeoPoint is not None
        assert StargazingLocation is not None

    def test_dir_exposes_lazy_public_symbols(self):
        """Verify package introspection still lists the lazy exports."""
        import stargazingplacefinder

        exported = dir(stargazingplacefinder)

        assert "analyze_area" in exported
        assert "GeoError" in exported
