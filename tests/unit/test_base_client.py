"""Tests for mtb_mcp.clients.base."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from mtb_mcp.clients.base import BaseClient


class TestBaseClientInit:
    """Test BaseClient instantiation."""

    def test_creates_with_defaults(self) -> None:
        """BaseClient should be instantiable with just a base_url."""
        client = BaseClient(base_url="https://api.example.com")
        assert client._base_url == "https://api.example.com"
        assert client._timeout == 30.0
        assert client._client is None

    def test_creates_with_custom_config(self) -> None:
        """BaseClient should accept custom headers, rate_limit, and timeout."""
        client = BaseClient(
            base_url="https://api.example.com",
            headers={"Authorization": "Bearer token"},
            rate_limit=5.0,
            timeout=60.0,
        )
        assert client._headers == {"Authorization": "Bearer token"}
        assert client._timeout == 60.0
        assert client._rate_limiter.rate == 5.0

    def test_lazy_client_creation(self) -> None:
        """HTTP client should not be created until first use."""
        client = BaseClient(base_url="https://api.example.com")
        assert client._client is None


class TestBaseClientRequests:
    """Test BaseClient HTTP request methods."""

    @respx.mock
    async def test_get_json(self) -> None:
        """_get should return parsed JSON from a GET request."""
        respx.get("https://api.example.com/data").mock(
            return_value=httpx.Response(200, json={"key": "value"})
        )

        async with BaseClient(base_url="https://api.example.com") as client:
            result = await client._get("/data")

        assert result == {"key": "value"}

    @respx.mock
    async def test_get_with_params(self) -> None:
        """_get should pass query parameters."""
        route = respx.get("https://api.example.com/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        async with BaseClient(base_url="https://api.example.com") as client:
            result = await client._get("/search", params={"q": "trails"})

        assert result == {"results": []}
        assert route.called

    @respx.mock
    async def test_post_json(self) -> None:
        """_post should send JSON and return parsed response."""
        respx.post("https://api.example.com/items").mock(
            return_value=httpx.Response(201, json={"id": 1, "name": "test"})
        )

        async with BaseClient(base_url="https://api.example.com") as client:
            result = await client._post("/items", json={"name": "test"})

        assert result == {"id": 1, "name": "test"}

    @respx.mock
    async def test_get_raw(self) -> None:
        """_get_raw should return raw bytes."""
        content = b"<gpx>some gpx data</gpx>"
        respx.get("https://api.example.com/track.gpx").mock(
            return_value=httpx.Response(200, content=content)
        )

        async with BaseClient(base_url="https://api.example.com") as client:
            result = await client._get_raw("/track.gpx")

        assert result == content

    @respx.mock
    async def test_get_text(self) -> None:
        """_get_text should return response text."""
        html = "<html><body>Trail info</body></html>"
        respx.get("https://api.example.com/page").mock(
            return_value=httpx.Response(200, text=html)
        )

        async with BaseClient(base_url="https://api.example.com") as client:
            result = await client._get_text("/page")

        assert result == html

    @respx.mock
    async def test_http_error_raised(self) -> None:
        """HTTP errors should be raised after retries are exhausted."""
        respx.get("https://api.example.com/fail").mock(
            return_value=httpx.Response(500, json={"error": "server error"})
        )

        async with BaseClient(base_url="https://api.example.com") as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client._get("/fail")


class TestBaseClientRetry:
    """Test retry behavior."""

    @respx.mock
    async def test_retries_on_transport_error(self) -> None:
        """Should retry on transport errors and succeed if a later attempt works."""
        route = respx.get("https://api.example.com/flaky")
        route.side_effect = [
            httpx.ConnectError("connection refused"),
            httpx.Response(200, json={"ok": True}),
        ]

        async with BaseClient(base_url="https://api.example.com") as client:
            result = await client._get("/flaky")

        assert result == {"ok": True}
        assert route.call_count == 2

    @respx.mock
    async def test_gives_up_after_max_retries(self) -> None:
        """Should give up after 3 attempts."""
        route = respx.get("https://api.example.com/down")
        route.side_effect = httpx.ConnectError("connection refused")

        async with BaseClient(base_url="https://api.example.com") as client:
            with pytest.raises(httpx.ConnectError):
                await client._get("/down")

        assert route.call_count == 3


class TestBaseClientRateLimiting:
    """Test rate limiting integration."""

    @respx.mock
    async def test_rate_limiter_acquire_called(self) -> None:
        """Rate limiter acquire should be called for each request."""
        respx.get("https://api.example.com/data").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        client = BaseClient(base_url="https://api.example.com", rate_limit=10.0)
        client._rate_limiter.acquire = AsyncMock()  # type: ignore[method-assign]

        async with client:
            await client._get("/data")

        client._rate_limiter.acquire.assert_called_once()  # type: ignore[union-attr]


class TestBaseClientContextManager:
    """Test async context manager behavior."""

    async def test_context_manager_closes_client(self) -> None:
        """Exiting context should close the underlying httpx client."""
        async with BaseClient(base_url="https://api.example.com") as client:
            # Force client creation
            http_client = client._get_client()
            assert not http_client.is_closed

        assert client._client is None

    async def test_close_is_idempotent(self) -> None:
        """Calling close multiple times should be safe."""
        client = BaseClient(base_url="https://api.example.com")
        await client.close()
        await client.close()  # Should not raise
