# -*- coding: utf-8 -*-
"""Tests for config loader and StargazingConfig model."""

from unittest.mock import patch

import pytest

from config import load_stargazing_config
from config.stargazing_config import StargazingConfig as SC


class TestStargazingConfig:
    def test_defaults(self):
        cfg = SC()
        assert cfg.road_network_tile_max_area_km2 == 500.0
        assert cfg.max_locations == 50
        assert cfg.road_search_radius_km == 10.0

    def test_override(self):
        cfg = SC(road_network_tile_max_area_km2=200.0)
        assert cfg.road_network_tile_max_area_km2 == 200.0

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValueError):
            SC(unknown_field=123)  # type: ignore[call-arg]


class TestLoadStargazingConfig:
    def test_no_path_and_no_default_file_returns_defaults(self, monkeypatch):
        """When no path is given and no env/file found, use programmatic defaults."""
        monkeypatch.delenv("STARGAZING_CONFIG", raising=False)
        with patch("config._resolve_config_path", return_value=None):
            cfg = load_stargazing_config()
        assert cfg.road_network_tile_max_area_km2 == 500.0

    def test_explicit_path_not_found_returns_defaults(self):
        cfg = load_stargazing_config("/nonexistent/config.toml")
        assert cfg.max_locations == 50

    def test_loads_valid_toml(self, tmp_path):
        toml_file = tmp_path / "cfg.toml"
        toml_file.write_text("road_network_tile_max_area_km2 = 300.0\nmax_locations = 20\n")
        cfg = load_stargazing_config(str(toml_file))
        assert cfg.road_network_tile_max_area_km2 == 300.0
        assert cfg.max_locations == 20

    def test_parse_error_returns_defaults(self, tmp_path):
        bad_file = tmp_path / "bad.toml"
        bad_file.write_text("this is not valid toml [[[")
        cfg = load_stargazing_config(str(bad_file))
        assert cfg.road_network_tile_max_area_km2 == 500.0  # fallback

    def test_env_var_takes_precedence(self, tmp_path, monkeypatch):
        toml_file = tmp_path / "env_cfg.toml"
        toml_file.write_text("max_locations = 77\n")
        monkeypatch.setenv("STARGAZING_CONFIG", str(toml_file))
        cfg = load_stargazing_config()
        assert cfg.max_locations == 77

    def test_env_var_nonexistent_file_returns_defaults(self, monkeypatch):
        monkeypatch.setenv("STARGAZING_CONFIG", "/no/such/file.toml")
        cfg = load_stargazing_config()
        assert cfg.max_locations == 50

    def test_falls_back_to_tomli_when_tomllib_unavailable(self, tmp_path, monkeypatch):
        """When tomllib is missing, tomli is used as fallback (Py 3.9/3.10)."""
        import sys
        import types

        import tomllib as _real_tomllib

        toml_file = tmp_path / "cfg.toml"
        toml_file.write_text("max_locations = 42\n")
        monkeypatch.setenv("STARGAZING_CONFIG", str(toml_file))

        fake_tomli = types.ModuleType("tomli")
        fake_tomli.load = _real_tomllib.load

        with patch.dict(sys.modules, {"tomllib": None, "tomli": fake_tomli}, clear=False):
            cfg = load_stargazing_config()
        assert cfg.max_locations == 42

    def test_no_toml_library_returns_defaults(self, tmp_path, monkeypatch):
        """When neither tomllib nor tomli is available, return programmatic defaults."""
        import sys

        toml_file = tmp_path / "cfg.toml"
        toml_file.write_text("max_locations = 99\n")
        monkeypatch.setenv("STARGAZING_CONFIG", str(toml_file))

        # Simulate environment where no TOML library exists
        with patch.dict(sys.modules, {"tomllib": None, "tomli": None}, clear=False):
            cfg = load_stargazing_config()
        assert cfg.max_locations == 50  # programmatic default


class TestResolveConfigPath:
    def _call(self, explicit=None):
        from config import _resolve_config_path

        return _resolve_config_path(explicit)

    def test_explicit_exists(self, tmp_path):
        f = tmp_path / "cfg.toml"
        f.write_text("max_locations = 1\n")
        result = self._call(str(f))
        assert result == f

    def test_explicit_missing_returns_none(self):
        assert self._call("/no/such.toml") is None

    def test_env_var_exists(self, tmp_path, monkeypatch):
        f = tmp_path / "env.toml"
        f.write_text("max_locations = 2\n")
        monkeypatch.setenv("STARGAZING_CONFIG", str(f))
        result = self._call()
        assert result == f

    def test_env_var_missing_returns_none(self, monkeypatch):
        monkeypatch.setenv("STARGAZING_CONFIG", "/no/such.toml")
        assert self._call() is None

    def test_default_path_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("STARGAZING_CONFIG", raising=False)
        result = self._call()
        # Should find the default config file in the repo
        assert result is not None
        assert result.name == "stargazing_config.toml"
