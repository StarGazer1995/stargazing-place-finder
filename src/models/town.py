"""Town metadata model — result of nearest town lookup."""

from typing import Optional

from pydantic import BaseModel, Field


class TownInfo(BaseModel):
    """Result of a nearest-town lookup.

    Attributes:
        name: Town name, or None if no towns nearby.
        distance_km: Distance from the query point to the town in km.
        elevation_m: Elevation of the town in meters, if available.
    """

    name: Optional[str] = None
    distance_km: float = Field(default=0.0, ge=0)
    elevation_m: Optional[float] = None
