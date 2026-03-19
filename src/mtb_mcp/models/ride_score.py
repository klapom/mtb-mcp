"""Ride score data model for MCP tool output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RideScoreOutput(BaseModel):
    """Structured ride-score result returned by the ``ride_score`` MCP tool."""

    score: int = Field(ge=0, le=100, description="Overall ride score 0-100")
    verdict: str = Field(description="Human label: Perfect / Good / Fair / Poor / Stay Home")
    weather_score: int = Field(ge=0, le=40, description="Weather sub-score 0-40")
    trail_score: int = Field(ge=0, le=30, description="Trail condition sub-score 0-30")
    wind_score: int = Field(ge=0, le=15, description="Wind sub-score 0-15")
    daylight_score: int = Field(ge=0, le=15, description="Daylight sub-score 0-15")
    factors: list[str] = Field(default_factory=list, description="Penalty explanations")
    recommendation: str = Field(default="", description="Actionable ride recommendation")
