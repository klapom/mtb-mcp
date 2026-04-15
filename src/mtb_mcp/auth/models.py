"""Auth Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel


class User(BaseModel):
    """Authenticated user."""

    id: str
    email: str | None = None
    display_name: str
    avatar_url: str | None = None
    home_lat: float | None = None
    home_lon: float | None = None
    strava_athlete_id: int | None = None
    onboarding_done: bool = False


class TokenPair(BaseModel):
    """Access + refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class StravaCallbackData(BaseModel):
    """Data from Strava OAuth callback."""

    code: str
    state: str | None = None


class RegisterRequest(BaseModel):
    """Email/password registration."""

    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    """Email/password login."""

    email: str
    password: str


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class OnboardingRequest(BaseModel):
    """Onboarding completion."""

    home_lat: float
    home_lon: float
    bike_name: str | None = None
    bike_type: str | None = None


class ProfileUpdateRequest(BaseModel):
    """Profile update."""

    display_name: str | None = None
    home_lat: float | None = None
    home_lon: float | None = None
    avatar_url: str | None = None
