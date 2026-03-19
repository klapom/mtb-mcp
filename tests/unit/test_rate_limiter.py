"""Tests for mtb_mcp.utils.rate_limiter."""

from __future__ import annotations

import asyncio
import time

import pytest

from mtb_mcp.utils.rate_limiter import TokenBucketRateLimiter


class TestTokenBucketRateLimiter:
    """Test TokenBucketRateLimiter."""

    async def test_initial_tokens_equal_burst(self) -> None:
        """Limiter should start with tokens equal to burst size."""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=5.0)
        assert limiter.tokens == pytest.approx(5.0)

    async def test_burst_defaults_to_rate(self) -> None:
        """When burst is not specified, it should default to rate."""
        limiter = TokenBucketRateLimiter(rate=7.0)
        assert limiter.burst == pytest.approx(7.0)
        assert limiter.tokens == pytest.approx(7.0)

    async def test_acquire_consumes_token(self) -> None:
        """Each acquire() call should consume one token."""
        limiter = TokenBucketRateLimiter(rate=10.0, burst=10.0)
        initial = limiter.tokens
        await limiter.acquire()
        # Tokens should be less than initial (roughly initial - 1, plus tiny refill)
        assert limiter.tokens < initial

    async def test_burst_allows_rapid_requests(self) -> None:
        """Should allow burst-many requests without waiting."""
        burst = 5.0
        limiter = TokenBucketRateLimiter(rate=10.0, burst=burst)

        start = time.monotonic()
        for _ in range(int(burst)):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # All burst requests should complete nearly instantly (< 0.1s)
        assert elapsed < 0.1

    async def test_rate_limiting_slows_requests(self) -> None:
        """Requests beyond burst should be rate-limited."""
        rate = 50.0  # 50 requests/sec -> 20ms per token
        limiter = TokenBucketRateLimiter(rate=rate, burst=1.0)

        # First request is immediate (uses the burst token)
        await limiter.acquire()

        # Second request should wait ~20ms
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should have waited at least ~15ms (allow some timing slack)
        assert elapsed >= 0.01

    async def test_tokens_refill_over_time(self) -> None:
        """Tokens should refill based on elapsed time."""
        limiter = TokenBucketRateLimiter(rate=100.0, burst=10.0)

        # Consume all tokens
        for _ in range(10):
            await limiter.acquire()

        # Wait a bit for refill
        await asyncio.sleep(0.05)

        # Should have refilled some tokens (~5 at 100/sec over 50ms)
        limiter._refill()
        assert limiter.tokens > 0

    async def test_tokens_do_not_exceed_burst(self) -> None:
        """Tokens should never exceed the burst limit."""
        limiter = TokenBucketRateLimiter(rate=100.0, burst=5.0)

        # Wait for potential over-refill
        await asyncio.sleep(0.1)
        limiter._refill()

        assert limiter.tokens <= limiter.burst

    async def test_concurrent_acquires(self) -> None:
        """Multiple concurrent acquires should be safe."""
        limiter = TokenBucketRateLimiter(rate=100.0, burst=10.0)

        # Launch 10 concurrent acquires
        results = await asyncio.gather(
            *[limiter.acquire() for _ in range(10)]
        )

        assert len(results) == 10
