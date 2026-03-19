"""Base HTTP client with retry, rate limiting, and structured logging."""

from __future__ import annotations

from typing import Any, Self

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mtb_mcp.utils.rate_limiter import TokenBucketRateLimiter

logger = structlog.get_logger(__name__)

# Default request timeout in seconds
DEFAULT_TIMEOUT: float = 30.0

# Human-readable messages for common HTTP error codes
_HTTP_ERROR_MESSAGES: dict[int, str] = {
    400: "Bad request — check parameters",
    401: "Authentication failed — check API credentials",
    403: "Access denied — insufficient permissions or quota exceeded",
    404: "Resource not found",
    429: "Rate limited — too many requests, backing off",
    500: "Server error — the upstream API is having issues",
    502: "Bad gateway — upstream server unreachable",
    503: "Service unavailable — upstream API is down",
    504: "Gateway timeout — upstream server too slow",
}


class APIError(httpx.HTTPStatusError):
    """Raised when an API request fails with a clear, human-readable message.

    Extends ``httpx.HTTPStatusError`` so existing ``except HTTPStatusError``
    handlers continue to work while providing richer error context.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        request: httpx.Request,
        response: httpx.Response,
    ) -> None:
        self.status_code = status_code
        self.detail = message
        super().__init__(
            f"HTTP {status_code} for {request.url}: {message}",
            request=request,
            response=response,
        )


class BaseClient:
    """Base async HTTP client for all API integrations.

    Features:
    - httpx async client with configurable base_url and headers
    - Automatic retry with exponential backoff (3 attempts)
    - Rate limiting via token bucket
    - Enhanced error handling with clear error messages
    - Structured logging at DEBUG level for request/response details
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        rate_limit: float = 10.0,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url
        self._headers = headers or {}
        self._timeout = timeout
        self._rate_limiter = TokenBucketRateLimiter(rate=rate_limit)
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Return the httpx client, creating it lazily if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=self._timeout,
            )
        return self._client

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        """Check response for HTTP errors and raise clear error messages.

        Translates common HTTP status codes into human-readable error messages
        wrapped in :class:`APIError`. For non-error responses, returns the
        response unchanged.

        Args:
            response: The httpx response to check.

        Returns:
            The response if successful.

        Raises:
            APIError: For 4xx/5xx status codes with a descriptive message.
        """
        if response.is_success:
            return response

        status = response.status_code
        url = str(response.url)
        message = _HTTP_ERROR_MESSAGES.get(status, f"Unexpected HTTP error ({status})")

        # Try to extract error detail from JSON response body
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = body.get("error") or body.get("message") or body.get("detail")
                if detail:
                    message = f"{message}: {detail}"
        except Exception:  # noqa: BLE001
            pass

        logger.warning(
            "http_error",
            status_code=status,
            url=url,
            message=message,
        )
        raise APIError(
            status_code=status,
            message=message,
            request=response.request,
            response=response,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with retry and rate limiting."""
        await self._rate_limiter.acquire()
        client = self._get_client()

        log = logger.bind(
            method=method,
            path=path,
            base_url=self._base_url,
            timeout=self._timeout,
        )
        log.debug("http_request_start", params=params)

        try:
            response = await client.request(
                method=method,
                url=path,
                params=params,
                data=data,
                json=json,
            )
        except httpx.TimeoutException:
            log.warning("http_request_timeout")
            raise
        except httpx.TransportError as exc:
            log.warning("http_transport_error", error=str(exc))
            raise

        log.debug(
            "http_request_complete",
            status_code=response.status_code,
            content_length=len(response.content),
        )
        return self._handle_response(response)

    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """GET request with retry and rate limiting, returning parsed JSON."""
        response = await self._request("GET", path, params=params)
        result: dict[str, Any] = response.json()
        return result

    async def _post(
        self,
        path: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST request with retry and rate limiting, returning parsed JSON."""
        response = await self._request("POST", path, data=data, json=json)
        result: dict[str, Any] = response.json()
        return result

    async def _get_raw(
        self, path: str, params: dict[str, Any] | None = None
    ) -> bytes:
        """GET request returning raw bytes (for GPX downloads etc)."""
        response = await self._request("GET", path, params=params)
        return response.content

    async def _get_text(
        self, path: str, params: dict[str, Any] | None = None
    ) -> str:
        """GET request returning text (for HTML scraping etc)."""
        response = await self._request("GET", path, params=params)
        return response.text

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager."""
        await self.close()
