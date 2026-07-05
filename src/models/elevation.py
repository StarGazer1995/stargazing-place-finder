"""Elevation query result model."""

from typing import Optional

from pydantic import Field
from stargazing_core import GeoPoint


class ElevationResult(GeoPoint):
    """Result of a single elevation query."""

    elevation: Optional[float] = None
    source_name: Optional[str] = None
    distance_meters: Optional[float] = Field(default=None, ge=0)
    feature_type: Optional[str] = None
    error: Optional[str] = None
