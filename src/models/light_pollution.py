"""Light pollution info model — structured output from LightPollutionAnalyzer."""

from pydantic import Field
from stargazing_core import GeoPoint


class LightPollutionInfo(GeoPoint):
    """Structured light pollution data at a coordinate point.

    Replaces the raw dict previously returned by
    LightPollutionAnalyzer.get_light_pollution_color().
    """

    radiance: float = Field(ge=0, description="VIIRS DNB radiance (nW/cm²/sr)")
    rgb: tuple[int, int, int]
    hex: str
    brightness: int = Field(ge=0, le=255)
    bortle: int = Field(ge=1, le=9)
    pollution_level: str
    overlay_name: str = "VIIRS-DNB-2025"
