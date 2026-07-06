"""Stargazing area analysis endpoint."""

import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from light_pollution.public_api import _default_geotiff_path
from stargazing_analyzer.stargazing_location_analyzer import analyze_stargazing_area

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stargazing"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class StargazingAreaRequest(BaseModel):
    """Request body for POST /api/analyze_stargazing_area."""

    bbox: dict = Field(default_factory=lambda: {"south": 0, "west": 0, "north": 0, "east": 0})
    max_locations: int = Field(default=30, ge=1, le=200)
    min_height_diff: float = Field(default=100.0, ge=0)
    road_radius_km: float = Field(default=10.0, ge=0)
    max_distance_to_road_km: float = Field(default=0.2, ge=0)
    network_type: str = Field(default="drive")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _location_to_dict(loc) -> dict:
    """Convert a StargazingLocation to a JSON-compatible dictionary."""
    return {
        "name": loc.name,
        "lat": loc.lat,
        "lon": loc.lon,
        "elevation": loc.elevation,
        "prominence": loc.prominence,
        "distance_to_nearest_town": loc.distance_to_nearest_town,
        "nearest_town_name": loc.nearest_town_name,
        "height_difference": loc.height_difference,
        "light_pollution_rgb": loc.light_pollution_rgb,
        "light_pollution_hex": loc.light_pollution_hex,
        "light_pollution_brightness": loc.light_pollution_brightness,
        "light_pollution_level": loc.light_pollution_level,
        "light_pollution_overlay": loc.light_pollution_overlay,
        "road_accessible": loc.road_accessible,
        "distance_to_road_km": loc.distance_to_road_km,
        "road_network_type": loc.road_network_type,
        "road_check_error": loc.road_check_error,
        "stargazing_score": loc.stargazing_score,
        "recommendation_level": loc.recommendation_level,
        "analysis_notes": loc.analysis_notes,
    }


# ---------------------------------------------------------------------------
# POST /api/analyze_stargazing_area
# ---------------------------------------------------------------------------


@router.post("/api/analyze_stargazing_area")
async def analyze_stargazing_area_post(request: Request, body: StargazingAreaRequest) -> dict:
    """分析指定区域的观星地点（JSON POST 请求）。"""
    return await _run_stargazing_analysis(
        south=body.bbox.get("south", 0),
        west=body.bbox.get("west", 0),
        north=body.bbox.get("north", 0),
        east=body.bbox.get("east", 0),
        max_locations=body.max_locations,
        min_height_diff=body.min_height_diff,
        road_radius_km=body.road_radius_km,
        max_distance_to_road_km=body.max_distance_to_road_km,
        network_type=body.network_type,
    )


# ---------------------------------------------------------------------------
# GET /api/analyze_stargazing_area
# ---------------------------------------------------------------------------


@router.get("/api/analyze_stargazing_area")
async def analyze_stargazing_area_get(
    south: float = Query(0),
    west: float = Query(0),
    north: float = Query(0),
    east: float = Query(0),
    max_locations: int = Query(30, ge=1, le=200),
    min_height_diff: float = Query(100.0, ge=0),
    road_radius_km: float = Query(10.0, ge=0),
    max_distance_to_road_km: float = Query(0.2, ge=0),
    network_type: str = Query("drive"),
) -> dict:
    """分析指定区域的观星地点（GET 查询参数）。"""
    return await _run_stargazing_analysis(
        south=south,
        west=west,
        north=north,
        east=east,
        max_locations=max_locations,
        min_height_diff=min_height_diff,
        road_radius_km=road_radius_km,
        max_distance_to_road_km=max_distance_to_road_km,
        network_type=network_type,
    )


# ---------------------------------------------------------------------------
# OPTIONS /api/analyze_stargazing_area  (CORS preflight — handled by middleware)
# ---------------------------------------------------------------------------


@router.options("/api/analyze_stargazing_area")
async def analyze_stargazing_area_options():
    """CORS 预检请求（由 CORSMiddleware 处理，此端点作为显式回退）。"""
    return {}


# ---------------------------------------------------------------------------
# Shared analysis logic
# ---------------------------------------------------------------------------


async def _run_stargazing_analysis(
    south: float,
    west: float,
    north: float,
    east: float,
    max_locations: int,
    min_height_diff: float,
    road_radius_km: float,
    max_distance_to_road_km: float,
    network_type: str,
) -> dict:
    """Run the full stargazing area analysis in a thread pool."""
    logger.info(
        "Analyzing stargazing area: North%s° South%s° East%s° West%s°",
        north,
        south,
        east,
        west,
    )

    # Resolve GeoTIFF path
    geotiff_path = str(_default_geotiff_path())
    db_config_path = os.environ.get("STARGAZING_DB_CONFIG")

    if db_config_path:
        logger.info("Using DB config from: %s", db_config_path)

    # Run the CPU/intensive analysis in a thread
    try:
        locations = await asyncio.to_thread(
            analyze_stargazing_area,
            south=south,
            west=west,
            north=north,
            east=east,
            geotiff_path=geotiff_path if os.path.exists(geotiff_path) else None,
            max_locations=max_locations,
            min_height_diff=min_height_diff,
            road_radius_km=road_radius_km,
            max_distance_to_road_km=max_distance_to_road_km,
            network_type=network_type,
            db_config_path=db_config_path,
        )
    except Exception as exc:
        logger.error("❌ Stargazing area analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    locations_data = [_location_to_dict(loc) for loc in locations]
    logger.info("✅ Successfully analyzed %s stargazing locations", len(locations_data))

    return {
        "success": True,
        "count": len(locations_data),
        "locations": locations_data,
        "bounds": {
            "south": south,
            "west": west,
            "north": north,
            "east": east,
        },
    }
