"""Data models for the stargazing-place-finder project.

All inter-module data transfer objects live here, backed by Pydantic v2
for automatic validation and serialization.
"""

from .geo import LatLonBox, Icon, GroundOverlay, GeoCoordinate
from .location import Location, LocationType, Peak, Observatory, Viewpoint
from .light_pollution import LightPollutionInfo
from .road import RoadAccessInfo
from .elevation import ElevationResult
from .stargazing import StargazingLocation

__all__ = [
    # Geo / KML
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
