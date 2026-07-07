"""Telescope optics endpoints — presets, FOV calculation, and target matching.

These are thin wrappers around ``stargazing-core``.  No astropy required.
"""

import astropy.units as u
from astropy.coordinates import EarthLocation
from astropy.time import Time
from fastapi import APIRouter
from stargazing_core import (
    TELESCOPE_PRESETS,
    TelescopeConfig,
    TelescopeOptics,
    generate_shooting_schedule,
    match_telescope_targets,
)

router = APIRouter(tags=["telescope"])


@router.get("/api/telescope/presets")
async def get_presets() -> dict:
    """Return all built-in telescope + camera presets."""
    return {name: cfg.model_dump() for name, cfg in TELESCOPE_PRESETS.items()}


@router.post("/api/telescope/optics")
async def compute_optics(config: TelescopeConfig) -> TelescopeOptics:
    """Compute derived optical parameters (FOV, limiting mag, sampling …)."""
    return config.compute_optics()


@router.post("/api/telescope/targets")
async def get_targets(body: dict) -> dict:
    """Recommend astrophotography targets for a telescope setup.

    Request body:
        config: TelescopeConfig fields (focal_length_mm, aperture_mm, …)
        lon: Observer longitude
        lat: Observer latitude
        time: ISO time string
        time_zone: IANA timezone string (optional, defaults to 'UTC')
        limit: Max results (default 20)
    """
    cfg = body.get("config", body)
    lon = body["lon"]
    lat = body["lat"]
    time_str = body["time"]
    time_zone = body.get("time_zone", "UTC")
    limit = body.get("limit", 20)

    config = TelescopeConfig(**cfg)
    observer = EarthLocation(lat=lat * u.deg, lon=lon * u.deg)

    # Parse timezone-aware datetime or use ISO string
    try:
        from datetime import datetime

        import pytz

        tz = pytz.timezone(time_zone)
        dt = tz.localize(datetime.fromisoformat(time_str))
    except Exception:
        dt = Time(time_str)
        t = dt
    else:
        t = Time(dt)

    results = match_telescope_targets(config, observer, t, limit)
    return {
        "targets": results["targets"],
        "moon": results["moon"],
        "config": config.model_dump(exclude_none=True),
        "total": len(results["targets"]),
    }


@router.post("/api/telescope/plan")
async def get_plan(body: dict) -> dict:
    """Generate a single-night shooting schedule.

    Runs match_telescope_targets then generate_shooting_schedule,
    returning targets + moon + timed shooting slots.
    """
    cfg = body.get("config", body)
    lon = body["lon"]
    lat = body["lat"]
    time_str = body["time"]
    time_zone = body.get("time_zone", "UTC")
    limit = body.get("limit", 20)
    min_altitude = body.get("min_altitude", 25.0)

    config = TelescopeConfig(**cfg)
    observer = EarthLocation(lat=lat * u.deg, lon=lon * u.deg)

    try:
        from datetime import datetime

        import pytz

        tz = pytz.timezone(time_zone)
        dt = tz.localize(datetime.fromisoformat(time_str))
    except Exception:
        dt = Time(time_str)
        t = dt
    else:
        t = Time(dt)

    results = match_telescope_targets(config, observer, t, limit)
    targets = results["targets"]
    moon = results["moon"]
    dusk = targets[0]["civil_dusk"] if targets else t.iso
    dawn = targets[0]["civil_dawn"] if targets else t.iso

    plan = generate_shooting_schedule(targets, moon, dusk, dawn, min_alt=min_altitude)

    return {
        "targets": targets,
        "moon": moon,
        "plan": plan.model_dump(),
        "config": config.model_dump(exclude_none=True),
        "total": len(targets),
    }
