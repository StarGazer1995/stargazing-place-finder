"""Lazy public exports for the ``stargazingplacefinder`` package."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "analyze_area": ("stargazing_analyzer.public_api", "analyze_area"),
    "analyze_area_simple": ("stargazing_analyzer.public_api", "analyze_area_simple"),
    "init_stargazing_analyzer": ("stargazing_analyzer.public_api", "init_stargazing_analyzer"),
    "init_light_pollution_analyzer": (
        "light_pollution.public_api",
        "init_light_pollution_analyzer",
    ),
    "get_light_pollution_grid": ("light_pollution.public_api", "get_light_pollution_grid"),
    "analyze_coordinate": ("light_pollution.public_api", "analyze_coordinate"),
    "StargazingError": ("stargazingplacefinder.models", "StargazingError"),
    "DataError": ("stargazingplacefinder.models", "DataError"),
    "NoDataError": ("stargazingplacefinder.models", "NoDataError"),
    "ValidationError": ("stargazingplacefinder.models", "ValidationError"),
    "NetworkError": ("stargazingplacefinder.models", "NetworkError"),
    "CacheError": ("stargazingplacefinder.models", "CacheError"),
    "ConfigError": ("stargazingplacefinder.models", "ConfigError"),
    "GeoError": ("stargazingplacefinder.models", "GeoError"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve public exports lazily so submodule imports avoid circular imports."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable package attributes for introspection and tab completion."""
    return sorted(list(globals().keys()) + __all__)
