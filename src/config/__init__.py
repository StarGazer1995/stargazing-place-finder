# -*- coding: utf-8 -*-
"""
Configuration module for the stargazing-place-finder project.

Centralizes all default parameter values so magic numbers are defined
in one place rather than scattered across module constructors.

Usage::

    from config import load_stargazing_config

    cfg = load_stargazing_config()                 # env var or default
    cfg = load_stargazing_config("my_config.toml")  # explicit path
"""

import os
from pathlib import Path
from typing import Optional

from .stargazing_config import StargazingConfig


def load_stargazing_config(path: Optional[str] = None) -> StargazingConfig:
    """Load configuration from a TOML file, falling back to programmatic defaults.

    Resolution order:
    1. Explicit *path* argument.
    2. ``STARGAZING_CONFIG`` environment variable.
    3. ``config/stargazing_config.toml`` in the package source tree.
    4. Programmatic defaults (``StargazingConfig()``).

    Returns:
        StargazingConfig instance.
    """
    cfg_path = _resolve_config_path(path)
    if cfg_path is None:
        return StargazingConfig()

    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:  # pragma: no cover — only on Python < 3.11
            import tomli as tomllib  # Python 3.9/3.10
    except ImportError:  # pragma: no cover — no TOML library available
        return StargazingConfig()  # programmatic defaults

    try:
        with open(cfg_path, "rb") as f:
            data = tomllib.load(f)
        return StargazingConfig(**data)
    except (OSError, ValueError, RuntimeError) as e:
        import logging

        logging.getLogger(__name__).warning("Failed to load config from %s: %s — using defaults", cfg_path, e)
        return StargazingConfig()


def _resolve_config_path(explicit: Optional[str]) -> Optional[Path]:
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None

    env = os.environ.get("STARGAZING_CONFIG")
    if env:
        p = Path(env)
        return p if p.exists() else None

    # fallback: look for config/stargazing_config.toml relative to this file
    # (src/config/__init__.py → config/ at repo root)
    candidate = Path(__file__).resolve().parents[2] / "config" / "stargazing_config.toml"
    return candidate if candidate.exists() else None


__all__ = [
    "StargazingConfig",
    "load_stargazing_config",
]
