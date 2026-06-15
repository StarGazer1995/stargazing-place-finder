"""Location model — unified intermediate representation from finder layer."""

from typing import Literal, Optional

from pydantic import Field

from .geo import GeoCoordinate

LocationType = Literal["mountain_peak", "observatory", "viewpoint"]


class Location(GeoCoordinate):
    """Unified location — the intermediate data object passed from finders to analyzer.

    Created by StarGazingPlaceFinder methods (find_peaks_in_area, etc.)
    and consumed by StargazingLocationAnalyzer.analyze_area().
    """

    # Required core fields
    name: str
    elevation: float = Field(ge=0)
    distance_to_nearest_town: float = Field(ge=0)
    nearest_town_name: str
    location_type: LocationType

    # Optional type-specific fields
    description: Optional[str] = None
    prominence: Optional[float] = Field(default=None, ge=0)
    height_difference: Optional[float] = Field(default=None, ge=0)
    observatory_type: Optional[str] = None
    viewpoint_type: Optional[str] = None
    light_pollution_level: Optional[str] = None
    scenic_value: Optional[str] = None

    # Convenience aliases for type checking
    def is_mountain_peak(self) -> bool:
        return self.location_type == "mountain_peak"

    def is_observatory(self) -> bool:
        return self.location_type == "observatory"

    def is_viewpoint(self) -> bool:
        return self.location_type == "viewpoint"


# Backward-compatible aliases used by stargazing_place_finder
Peak = Location
Observatory = Location
Viewpoint = Location
