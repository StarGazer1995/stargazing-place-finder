# -*- coding: utf-8 -*-
"""
Custom exception hierarchy for stargazing-place-finder.

Provides fine-grained exception types so callers can distinguish
between expected failures (e.g. network timeouts, missing data) and
unexpected programming errors.
"""


class StargazingError(Exception):
    """Base exception for all project-specific errors."""


class DataError(StargazingError):
    """Raised when requested data cannot be retrieved or parsed."""


class NoDataError(DataError):
    """Raised when the queried area has no data (e.g. no roads, no peaks)."""


class ValidationError(StargazingError):
    """Raised when input parameters are invalid (e.g. out-of-range coords)."""


class NetworkError(StargazingError):
    """Raised when an external API call fails (Overpass, elevation, etc.)."""


class CacheError(StargazingError):
    """Raised when cache read/write fails."""


class ConfigError(StargazingError):
    """Raised when configuration is missing or invalid."""


class GeoError(StargazingError):
    """Raised when geospatial processing fails (rasterio, GDAL, etc.)."""
