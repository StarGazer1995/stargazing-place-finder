"""Road connectivity model."""

from typing import Optional
from pydantic import Field
from .geo import GeoCoordinate


class RoadAccessInfo(GeoCoordinate):
    """Cached road accessibility check result."""

    is_road_accessible: bool = False
    network_nodes_count: int = Field(default=0, ge=0)
    nearest_road_type: Optional[str] = None
    distance_to_road_km: Optional[float] = Field(default=None, ge=0)
    error: Optional[str] = None
