"""Geographic data models — KML internal structures.

``GeoPoint`` from ``stargazing_core`` replaces the legacy ``GeoCoordinate``.
New code should use :class:`stargazing_core.GeoPoint` (``lat`` / ``lon`` naming)
which carries the same coordinate constraints and adds optional elevation support.
"""

from pydantic import BaseModel
from stargazing_core import GeoPoint  # noqa: F401 — re-export for convenience


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
