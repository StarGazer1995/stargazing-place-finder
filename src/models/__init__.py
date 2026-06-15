"""Data models for the stargazing-place-finder project.

All inter-module data transfer objects live here, backed by Pydantic v2
for automatic validation and serialization.
"""

from .elevation import ElevationResult
from .geo import GeoCoordinate, GroundOverlay, Icon, LatLonBox
from .light_pollution import LightPollutionInfo
from .location import Location, LocationType, Observatory, Peak, Viewpoint
from .road import RoadAccessInfo
from .stargazing import StargazingLocation

__all__ = [
    # Geo / KML
    "GeoCoordinate",
    "LatLonBox",
    "Icon",
    "GroundOverlay",
    # Location
    "Location",
    "LocationType",
    "Peak",
    "Observatory",
    "Viewpoint",
    # Light pollution
    "LightPollutionInfo",
    # Road
    "RoadAccessInfo",
    # Elevation
    "ElevationResult",
    # Stargazing
    "StargazingLocation",
]
