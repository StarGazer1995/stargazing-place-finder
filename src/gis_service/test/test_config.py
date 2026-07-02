# -*- coding: utf-8 -*-
"""
Tests for gis_service.config database config loading helpers.
"""

import types
from unittest.mock import patch

# Ensure src is on path
from gis_service.config import load_db_config


class TestLoadDbConfig:
    """Test load_db_config with explicit paths and environment fallbacks."""

    def test_load_db_config_reads_toml_file(self, tmp_path):
        """TOML config loads correctly through the public gis_service helper."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('host = "localhost"\nport = 5432\n')

        result = load_db_config(str(cfg_file))

        assert result == {"host": "localhost", "port": 5432}

    def test_load_db_config_falls_back_to_tomli(self, tmp_path):
        """When tomllib is unavailable, load_db_config falls back to tomli."""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text('host = "localhost"\nport = 5432\n')
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
            result = load_db_config(str(cfg_file))

        assert result == {"host": "localhost", "port": 5432, "loaded_by": "tomli"}

    def test_load_db_config_prefers_new_environment_variable(self, tmp_path, monkeypatch):
        """STARGAZING_DB_CONFIG takes precedence over the deprecated variable."""
        new_cfg_file = tmp_path / "new.json"
        old_cfg_file = tmp_path / "old.json"
        new_cfg_file.write_text('{"host": "new-host"}')
        old_cfg_file.write_text('{"host": "old-host"}')

        monkeypatch.setenv("STARGAZING_DB_CONFIG", str(new_cfg_file))
        monkeypatch.setenv("DB_CONFIG_PATH", str(old_cfg_file))

        result = load_db_config()

        assert result == {"host": "new-host"}

    def test_load_db_config_uses_deprecated_environment_variable(self, tmp_path, monkeypatch, caplog):
        """DB_CONFIG_PATH still works for backward compatibility with a warning."""
        cfg_file = tmp_path / "old.json"
        cfg_file.write_text('{"host": "legacy-host"}')
        monkeypatch.delenv("STARGAZING_DB_CONFIG", raising=False)
        monkeypatch.setenv("DB_CONFIG_PATH", str(cfg_file))

        with caplog.at_level("WARNING"):
            result = load_db_config()

        assert result == {"host": "legacy-host"}
        assert "DB_CONFIG_PATH is deprecated" in caplog.text

    def test_load_db_config_invalid_toml_raises_runtime_error(self, tmp_path):
        """Invalid TOML content raises RuntimeError (lines 74-75)."""
        import pytest

        cfg_file = tmp_path / "broken.toml"
        cfg_file.write_text("key = [unclosed\n")  # Malformed TOML
        with pytest.raises(RuntimeError, match="Failed to parse TOML config"):
            load_db_config(str(cfg_file))
