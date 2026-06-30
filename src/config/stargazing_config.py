# -*- coding: utf-8 -*-
"""
Centralised configuration model for stargazing-place-finder.

All default parameter values live here so they can be changed in one
place instead of being scattered as magic numbers across every module
constructor.
"""

from typing import Optional

from pydantic import BaseModel, Field


class StargazingConfig(BaseModel):
    """Centralised configuration for the stargazing place finder pipeline.

    Every field has a sensible default.  Pass an instance to any module
    constructor (e.g. ``RoadConnectivityChecker(config=cfg)``) to override
    all defaults at once.
    """

    # ── Search / location parameters ──────────────────────────────
    max_locations: int = Field(
        default=50,
        ge=1,
        description="Maximum number of locations to return from a query.",
    )
    min_height_difference: float = Field(
        default=100.0,
        ge=0,
        description="Minimum height difference (m) from nearest town.",
    )

    # ── Road connectivity ─────────────────────────────────────────
    road_search_radius_km: float = Field(
        default=10.0,
        gt=0,
        description="Road network download / search radius (km).",
    )
    max_distance_to_road_km: float = Field(
        default=0.2,
        ge=0,
        description=("Maximum acceptable distance to a road (km). Used as the accessibility threshold."),
    )
    road_network_tile_max_area_km2: float = Field(
        default=500.0,
        gt=0,
        description=(
            "Maximum bbox area (km²) to download as a single OSM road-network tile. "
            "Larger areas are automatically split into tiles, downloaded individually, "
            "and merged.  Lower = more tiles, smaller downloads, fewer timeouts."
        ),
    )
    min_distance_to_road_km: Optional[float] = Field(
        default=None,
        ge=0,
        description=(
            "Optional minimum distance to road filter (km). When set, places *closer* than this are excluded."
        ),
    )

    # ── Light pollution ───────────────────────────────────────────
    skyglow_sigma_km: float = Field(
        default=15.0,
        ge=0,
        description="Gaussian sigma (km) for skyglow diffusion.  0 disables.",
    )
    skyglow_weight: float = Field(
        default=0.4,
        ge=0,
        le=1.0,
        description="How much skyglow to add back (0 – 1).",
    )

    # ── Scoring weights (total 100 points) ────────────────────────
    weight_light_pollution: float = Field(
        default=35.0,
        ge=0,
        le=100,
        description="Weight for light pollution sub-score (0-35 default).",
    )
    weight_town_isolation: float = Field(
        default=20.0,
        ge=0,
        le=100,
        description="Weight for town isolation sub-score (0-20 default).",
    )
    weight_road_access: float = Field(
        default=20.0,
        ge=0,
        le=100,
        description="Weight for road accessibility sub-score (0-20 default).",
    )
    weight_elevation: float = Field(
        default=15.0,
        ge=0,
        le=100,
        description="Weight for elevation + terrain sub-score (0-15 default).",
    )
    weight_location_type: float = Field(
        default=10.0,
        ge=0,
        le=100,
        description="Weight for location-type sub-score (0-10 default).",
    )

    # ── Smooth scoring parameters ─────────────────────────────────
    road_distance_decay_km: float = Field(
        default=0.2,
        gt=0,
        description=(
            "Half-decay distance (km) for road accessibility sigmoid. "
            "At this distance the score is 50% of maximum. "
            "Replaces the hard 200m accessible/inaccessible threshold."
        ),
    )

    # ── Cache ─────────────────────────────────────────────────────
    cache_expiry_hours: int = Field(
        default=24,
        gt=0,
        description="Cache entry time-to-live (hours).",
    )

    model_config = {"extra": "forbid"}
