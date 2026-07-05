"""Telescope optics endpoints — presets and FOV calculation.

These are thin wrappers around ``stargazing-core``.  No astropy required.
"""

from fastapi import APIRouter
from stargazing_core import TELESCOPE_PRESETS, TelescopeConfig, TelescopeOptics

router = APIRouter(tags=["telescope"])


@router.get("/api/telescope/presets")
async def get_presets() -> dict:
    """Return all built-in telescope + camera presets."""
    return {name: cfg.model_dump() for name, cfg in TELESCOPE_PRESETS.items()}


@router.post("/api/telescope/optics")
async def compute_optics(config: TelescopeConfig) -> TelescopeOptics:
    """Compute derived optical parameters (FOV, limiting mag, sampling …)."""
    return config.compute_optics()
