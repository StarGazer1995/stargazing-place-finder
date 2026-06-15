"""Geographic data models — KML internal structures and geo coordinate base."""

from pydantic import BaseModel, Field


class GeoCoordinate(BaseModel):
    """Shared base: latitude/longitude with standard validation.

    All location models (Location, StargazingLocation, LightPollutionInfo,
    ElevationResult, RoadAccessInfo) inherit from this to avoid duplicating
    the coordinate fields and their constraints.
    """

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class LatLonBox(BaseModel):
    """Bounding box from KML GroundOverlay."""

    north: float
    south: float
    east: float
    west: float
    rotation: float = 0.0


class Icon(BaseModel):
    """Icon reference from KML GroundOverlay."""

    href: str


class GroundOverlay(BaseModel):
    """KML GroundOverlay — maps a light-pollution tile to geographic coordinates."""

    name: str
    draw_order: int
    color: str
    description: str
    icon: Icon
    lat_lon_box: LatLonBox
