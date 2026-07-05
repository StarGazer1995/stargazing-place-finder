"""StargazingLocation — the final enriched output model."""

from typing import Optional, Tuple

from pydantic import Field
from stargazing_core import GeoPoint

from .location import LocationType


class StargazingLocation(GeoPoint):
    """Fully analyzed stargazing location with light pollution, road, and scoring data.

    This is THE output model — returned by StargazingLocationAnalyzer.analyze_area()
    and serialized by the public API.
    """

    # Basic location information
    name: str
    elevation: float = Field(ge=0)
    distance_to_nearest_town: float = Field(ge=0)
    nearest_town_name: str
    location_type: LocationType = "mountain_peak"
    description: Optional[str] = None

    # Peak-specific
    prominence: Optional[float] = Field(default=None, ge=0)
    height_difference: Optional[float] = Field(default=None, ge=0)

    # Light pollution
    light_pollution_rgb: Optional[Tuple[int, int, int]] = None
    light_pollution_hex: Optional[str] = None
    light_pollution_brightness: Optional[int] = Field(default=None, ge=0, le=255)
    light_pollution_level: Optional[str] = None
    light_pollution_bortle: Optional[int] = Field(default=None, ge=1, le=9)
    light_pollution_overlay: Optional[str] = None

    # Town isolation
    nearby_town_count: int = Field(default=0, ge=0)

    # Road connectivity
    road_accessible: Optional[bool] = None
    distance_to_road_km: Optional[float] = Field(default=None, ge=0)
    road_network_type: Optional[str] = None
    road_check_error: Optional[str] = None

    # Comprehensive scoring
    stargazing_score: Optional[float] = Field(default=None, ge=0, le=100)
    recommendation_level: Optional[str] = None
    analysis_notes: Optional[str] = None

    # Convenience type checks
    def is_mountain_peak(self) -> bool:
        return self.location_type == "mountain_peak"

    def is_observatory(self) -> bool:
        return self.location_type == "observatory"

    def is_viewpoint(self) -> bool:
        return self.location_type == "viewpoint"
