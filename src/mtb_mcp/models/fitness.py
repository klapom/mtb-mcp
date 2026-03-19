"""Fitness and training data models."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel


class GoalType(str, Enum):
    """Types of training goals."""

    alpencross = "alpencross"
    xc_race = "xc_race"
    enduro_race = "enduro_race"
    marathon = "marathon"
    personal_challenge = "personal_challenge"


class TrainingZone(str, Enum):
    """Heart rate / power training zones."""

    recovery = "recovery"
    base = "base"
    tempo = "tempo"
    threshold = "threshold"
    vo2max = "vo2max"


class TrainingPhase(str, Enum):
    """Periodization phases."""

    base = "base"
    build = "build"
    peak = "peak"
    taper = "taper"


class TrainingGoal(BaseModel):
    """A training goal with target date and metrics."""

    id: str
    name: str
    type: GoalType
    target_date: date
    target_distance_km: float | None = None
    target_elevation_m: float | None = None
    target_ctl: int | None = None
    description: str | None = None
    status: str = "active"


class TrainingWeek(BaseModel):
    """A single week in a periodized training plan."""

    goal_id: str
    week_number: int
    phase: TrainingPhase
    planned_hours: float
    planned_km: float
    planned_elevation_m: float
    intensity_focus: TrainingZone
    key_workout: str | None = None
    notes: str | None = None


class FitnessSnapshot(BaseModel):
    """Point-in-time fitness metrics (CTL/ATL/TSB + weekly volume)."""

    date: date
    ctl: float
    atl: float
    tsb: float
    weekly_km: float = 0.0
    weekly_elevation_m: float = 0.0
    weekly_hours: float = 0.0
    weekly_rides: int = 0
