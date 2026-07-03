"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from light_pollution.public_api import _require_analyzer

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    analyzer_initialized: bool


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Check API health and analyzer status."""
    try:
        _require_analyzer()
        initialized = True
    except Exception:
        initialized = False

    return HealthResponse(status="healthy", analyzer_initialized=initialized)
