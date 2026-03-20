"""API response models — envelope, errors, shared types."""

from __future__ import annotations

import time
import uuid
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiMeta(BaseModel):
    """Metadata included in every API response."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    duration_ms: int = 0
    timestamp: str = ""


class ApiError(BaseModel):
    """Structured error payload."""

    code: str
    message: str
    details: Any = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""

    status: str = "ok"
    data: T | None = None
    error: ApiError | None = None
    meta: ApiMeta = Field(default_factory=ApiMeta)


class ApiListResponse(BaseModel, Generic[T]):
    """List response with total count for pagination."""

    status: str = "ok"
    data: list[T] = Field(default_factory=list)
    total: int = 0
    meta: ApiMeta = Field(default_factory=ApiMeta)


def ok(data: Any, start_time: float | None = None) -> dict[str, Any]:
    """Build a success response dict."""
    meta: dict[str, Any] = {
        "request_id": str(uuid.uuid4()),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if start_time is not None:
        meta["duration_ms"] = int((time.monotonic() - start_time) * 1000)
    return {"status": "ok", "data": data, "meta": meta}


def ok_list(
    items: list[Any], total: int, start_time: float | None = None,
) -> dict[str, Any]:
    """Build a list success response dict."""
    meta: dict[str, Any] = {
        "request_id": str(uuid.uuid4()),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if start_time is not None:
        meta["duration_ms"] = int((time.monotonic() - start_time) * 1000)
    return {"status": "ok", "data": items, "total": total, "meta": meta}


def err(code: str, message: str, details: Any = None) -> dict[str, Any]:
    """Build an error response dict."""
    return {
        "status": "error",
        "error": {"code": code, "message": message, "details": details},
        "meta": {
            "request_id": str(uuid.uuid4()),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }
