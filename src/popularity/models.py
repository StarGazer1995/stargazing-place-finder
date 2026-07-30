"""Popularity heuristic result models."""

from pydantic import BaseModel, Field


class PopularityResult(BaseModel):
    """Normalized popularity / temporal heuristic output for one location."""

    static_popularity_risk_score: float = Field(ge=0, le=100)
    night_quiet_likelihood_score: float = Field(ge=0, le=100)
    temporal_popularity_confidence: float = Field(ge=0, le=100)
    nearby_popular_poi_count: int = Field(default=0, ge=0)
    nearby_night_active_poi_count: int = Field(default=0, ge=0)
    nearby_day_only_poi_count: int = Field(default=0, ge=0)
    popularity_signals: list[str] = Field(default_factory=list)
    temporal_popularity_signals: list[str] = Field(default_factory=list)
    popularity_notes: str | None = None
