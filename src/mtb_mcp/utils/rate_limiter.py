"""Token bucket rate limiter for API clients."""

from __future__ import annotations

import asyncio
import time


class TokenBucketRateLimiter:
    """Token bucket rate limiter.

    Tokens are refilled at a constant rate. Each request consumes one token.
    If no tokens are available, the caller waits until one is refilled.

    Args:
        rate: Maximum requests per second.
        burst: Maximum burst size (defaults to rate).
    """

    def __init__(self, rate: float, burst: float | None = None) -> None:
        self.rate = rate
        self.burst = burst if burst is not None else rate
        self.tokens = self.burst
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        while True:
            async with self._lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                # Calculate wait time for next token
                wait_time = (1.0 - self.tokens) / self.rate

            await asyncio.sleep(wait_time)
