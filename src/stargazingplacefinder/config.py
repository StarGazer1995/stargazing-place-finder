"""Namespaced configuration re-exports for the stargazingplacefinder package."""

from config import StargazingConfig, _import_tomllib, load_stargazing_config

__all__ = ["StargazingConfig", "load_stargazing_config", "_import_tomllib"]
