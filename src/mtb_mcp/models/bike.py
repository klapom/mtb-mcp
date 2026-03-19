"""Bike and component data models for the Bike Garage."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    """Supported bike component types for wear tracking."""

    chain = "chain"
    cassette = "cassette"
    brake_pads_front = "brake_pads_front"
    brake_pads_rear = "brake_pads_rear"
    tire_front = "tire_front"
    tire_rear = "tire_rear"
    fork = "fork"
    shock = "shock"
    brake_fluid = "brake_fluid"
    tubeless_sealant = "tubeless_sealant"
    bottom_bracket = "bottom_bracket"


class Component(BaseModel):
    """A trackable bike component with wear data."""

    id: str
    type: ComponentType
    brand: str | None = None
    model: str | None = None
    installed_date: date
    installed_km: float = 0.0
    current_effective_km: float = 0.0
    current_hours: float = 0.0


class Bike(BaseModel):
    """A bike in the garage with its components."""

    id: str
    name: str
    brand: str | None = None
    model: str | None = None
    bike_type: str = "mtb"  # mtb, emtb, gravel, road
    total_km: float = 0.0
    strava_gear_id: str | None = None
    components: list[Component] = Field(default_factory=list)


class WearStatus(BaseModel):
    """Wear status for a single component."""

    component_type: str
    brand_model: str
    wear_pct: float  # 0-100+
    effective_km: float
    hours: float
    service_interval_km: float | None = None
    service_interval_hours: float | None = None
    service_interval_months: int | None = None
    km_remaining: float | None = None
    status: str  # "good", "warning", "critical", "overdue"
    installed_date: date
    next_service: str | None = None  # Human-readable


class ServiceLog(BaseModel):
    """A maintenance service event."""

    id: str
    bike_id: str
    component_type: str
    service_type: str  # "replace", "service", "clean"
    date: date
    notes: str | None = None
