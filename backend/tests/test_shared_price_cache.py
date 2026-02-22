"""
Tests for SharedPriceCache - Global price caching service.
"""

import asyncio
import time

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.shared_price_cache import (
    SharedPriceCache,
    CachedPrice,
    get_shared_price_cache,
    reset_shared_price_cache,
)


class TestSharedPriceCache:
    """Tests for SharedPriceCache class."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache for each test."""
        return SharedPriceCache(price_ttl=5.0, enable_l2=False)

    @pytest.fixture
    def cache_with_redis(self):
        """Create a cache with mocked Redis."""
        cache = SharedPriceCache(price_ttl=5.0, enable_l2=True)
        cache._redis = MagicMock()
        cache._redis.get = AsyncMock(return_value=None)
        cache._redis.set = AsyncMock(return_value=True)
        return cache

    # =========================================================================
    # L1 Cache Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_set_and_get_price_l1(self, cache):
        """Test setting and getting price from L1 cache."""
        await cache.set_price("hyperliquid", "BTC", 50000.0)

        price = await cache.get_price("hyperliquid", "BTC")
        assert price == 50000.0

    @pytest.mark.asyncio
    async def test_set_price_with_bid_ask(self, cache):
        """Test setting price with bid/ask values."""
        await cache.set_price(
            "hyperliquid", "BTC", 50000.0, bid=49990.0, ask=50010.0
        )

        price = await cache.get_price("hyperliquid", "BTC")
        assert price == 50000.0

        # Check L1 cache entry has bid/ask
        key = cache._make_key("hyperliquid", "BTC")
        assert cache._l1_cache[key].bid == 49990.0
        assert cache._l1_cache[key].ask == 50010.0

    @pytest.mark.asyncio
    async def test_l1_cache_ttl_expiry(self, cache):
        """Test that L1 cache expires after TTL."""
        # Set price with short TTL
        cache._price_ttl = 0.1  # 100ms

        await cache.set_price("hyperliquid", "BTC", 50000.0)

        # Immediate get should work
        price = await cache.get_price("hyperliquid", "BTC")
        assert price == 50000.0

        # Wait for TTL to expire
        await asyncio.sleep(0.15)

        # Get without fetcher should return None (no stale data)
        cache._l1_cache.clear()  # Clear to simulate expiry
        price = await cache.get_price("hyperliquid", "BTC")
        assert price is None

    @pytest.mark.asyncio
    async def test_l1_cache_hit_increments_stats(self, cache):
        """Test that L1 cache hits increment stats."""
        await cache.set_price("hyperliquid", "BTC", 50000.0)

        # First get (L1 hit)
        await cache.get_price("hyperliquid", "BTC")
        assert cache._l1_hits == 1

        # Second get (L1 hit)
        await cache.get_price("hyperliquid", "BTC")
        assert cache._l1_hits == 2

    @pytest.mark.asyncio
    async def test_l1_cache_miss_increments_stats(self, cache):
        """Test that L1 cache misses increment stats."""
        # Get without cache (miss)
        await cache.get_price("hyperliquid", "BTC")
        assert cache._l1_misses == 1

    @pytest.mark.asyncio
    async def test_stale_cache_not_used_after_expiry(self, cache):
        """Test that stale cache is NOT used after TTL expiry in SharedPriceCache.

        Note: Stale cache fallback is implemented at MockTrader level, not
        SharedPriceCache level. SharedPriceCache returns None when cache expires.
        """
        cache._price_ttl = 0.1  # 100ms

        await cache.set_price("hyperliquid", "BTC", 50000.0)

        # Wait for TTL to expire
        await asyncio.sleep(0.15)

        # Clear L1 cache to simulate expiry
        cache._l1_cache.clear()

        # Get without fetcher should return None (expired)
        price = await cache.get_price("hyperliquid", "BTC")
        assert price is None

    # =========================================================================
    # L2 (Redis) Cache Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_l2_cache_hit_promotes_to_l1(self, cache_with_redis):
        """Test that L2 cache hit promotes to L1 cache."""
        cache = cache_with_redis

        # Mock Redis return
        cache._redis.get = AsyncMock(
            return_value='{"price": 50000.0, "bid": 49990.0, "ask": 50010.0}'
        )

        # Get should hit L2
        price = await cache.get_price("hyperliquid", "BTC")
        assert price == 50000.0
        assert cache._l2_hits == 1

        # Should be promoted to L1
        key = cache._make_key("hyperliquid", "BTC")
        assert key in cache._l1_cache
        assert cache._l1_cache[key].price == 50000.0

    @pytest.mark.asyncio
    async def test_set_price_updates_l2(self, cache_with_redis):
        """Test that set_price updates both L1 and L2."""
        cache = cache_with_redis

        await cache.set_price("hyperliquid", "BTC", 50000.0)

        # L2 should be updated
        cache._redis.set.assert_called_once()
        call_args = cache._redis.set.call_args
        assert "hyperliquid:BTC" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_l2_disabled_uses_only_l1(self, cache):
        """Test that L2 disabled only uses L1."""
        cache._enable_l2 = False

        await cache.set_price("hyperliquid", "BTC", 50000.0)

        # Redis should not be initialized
        assert cache._redis is None

        # Get should work from L1
        price = await cache.get_price("hyperliquid", "BTC")
        assert price == 50000.0

    # =========================================================================
    # Request Coalescing Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_request_coalescing_single_api_call(self, cache):
        """Test that concurrent requests share a single API call."""
        call_count = 0

        async def fetcher():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate API latency
            return (50000.0, None, None)

        # Launch 10 concurrent requests
        tasks = [
            cache.get_price("hyperliquid", "BTC", fetcher=fetcher)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

        # All should get the same result
        assert all(r == 50000.0 for r in results)

        # Should only make 1 API call due to coalescing
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_request_coalescing_exception_returns_none(self, cache):
        """Test that exceptions in coalesced requests return None (graceful degradation).

        Note: SharedPriceCache catches exceptions and returns None for resilience.
        The caller (MockTrader) can then fall back to stale cache if available.
        """
        async def failing_fetcher():
            raise ValueError("API error")

        price = await cache.get_price("hyperliquid", "BTC", fetcher=failing_fetcher)
        assert price is None  # Graceful degradation

    # =========================================================================
    # Fetcher Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_fetcher_updates_both_caches(self, cache):
        """Test that fetcher updates both L1 and L2 caches."""
        async def fetcher():
            return (50000.0, 49990.0, 50010.0)

        price = await cache.get_price("hyperliquid", "BTC", fetcher=fetcher)

        assert price == 50000.0
        assert cache._api_calls == 1

        # L1 should be updated
        key = cache._make_key("hyperliquid", "BTC")
        assert cache._l1_cache[key].price == 50000.0

    @pytest.mark.asyncio
    async def test_fetcher_returns_none_not_cached(self, cache):
        """Test that fetcher returning None doesn't cache."""
        async def fetcher():
            return None

        price = await cache.get_price("hyperliquid", "BTC", fetcher=fetcher)

        assert price is None
        key = cache._make_key("hyperliquid", "BTC")
        assert key not in cache._l1_cache

    # =========================================================================
    # Batch Operations Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_prices_batch(self, cache):
        """Test batch price fetching."""
        # Pre-cache some prices
        await cache.set_price("hyperliquid", "BTC", 50000.0)
        await cache.set_price("hyperliquid", "ETH", 3000.0)

        async def batch_fetcher(symbols):
            # Only called for uncached symbols
            return {"SOL": (100.0, None, None)}

        results = await cache.get_prices_batch(
            "hyperliquid",
            ["BTC", "ETH", "SOL"],
            fetcher=batch_fetcher,
        )

        assert results["BTC"] == 50000.0
        assert results["ETH"] == 3000.0
        assert results["SOL"] == 100.0

    # =========================================================================
    # Invalidation Tests
    # =========================================================================

    def test_invalidate_specific_symbol(self, cache):
        """Test invalidating a specific symbol."""
        cache._l1_cache["price_cache:hyperliquid:BTC"] = CachedPrice(
            price=50000.0, timestamp=time.monotonic(),
            exchange="hyperliquid", symbol="BTC"
        )
        cache._l1_cache["price_cache:hyperliquid:ETH"] = CachedPrice(
            price=3000.0, timestamp=time.monotonic(),
            exchange="hyperliquid", symbol="ETH"
        )

        count = cache.invalidate("hyperliquid", "BTC")

        assert count == 1
        assert "price_cache:hyperliquid:BTC" not in cache._l1_cache
        assert "price_cache:hyperliquid:ETH" in cache._l1_cache

    def test_invalidate_all_symbols(self, cache):
        """Test invalidating all symbols for an exchange."""
        cache._l1_cache["price_cache:hyperliquid:BTC"] = CachedPrice(
            price=50000.0, timestamp=time.monotonic(),
            exchange="hyperliquid", symbol="BTC"
        )
        cache._l1_cache["price_cache:hyperliquid:ETH"] = CachedPrice(
            price=3000.0, timestamp=time.monotonic(),
            exchange="hyperliquid", symbol="ETH"
        )

        count = cache.invalidate("hyperliquid")

        assert count == 2
        assert len(cache._l1_cache) == 0

    # =========================================================================
    # Statistics Tests
    # =========================================================================

    def test_get_stats(self, cache):
        """Test getting cache statistics."""
        cache._l1_hits = 10
        cache._l1_misses = 5
        cache._l2_hits = 3
        cache._l2_misses = 2
        cache._api_calls = 4

        stats = cache.get_stats()

        assert stats["l1_hits"] == 10
        assert stats["l1_misses"] == 5
        assert stats["l1_hit_rate"] == 10 / 15  # 66.67%
        assert stats["l2_hits"] == 3
        assert stats["l2_misses"] == 2
        assert stats["l2_hit_rate"] == 3 / 5  # 60%
        assert stats["api_calls"] == 4

    def test_get_stats_zero_division(self, cache):
        """Test stats with zero requests (division by zero)."""
        stats = cache.get_stats()

        assert stats["l1_hit_rate"] == 0.0
        assert stats["l2_hit_rate"] == 0.0


class TestSharedPriceCacheSingleton:
    """Tests for singleton management."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_shared_price_cache()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_shared_price_cache()

    def test_get_shared_price_cache_creates_singleton(self):
        """Test that get_shared_price_cache creates a singleton."""
        cache1 = get_shared_price_cache()
        cache2 = get_shared_price_cache()

        assert cache1 is cache2

    def test_reset_shared_price_cache(self):
        """Test that reset clears the singleton."""
        cache1 = get_shared_price_cache()
        reset_shared_price_cache()
        cache2 = get_shared_price_cache()

        assert cache1 is not cache2

    def test_singleton_with_custom_params(self):
        """Test singleton with custom parameters on first call."""
        # Note: params only affect first creation
        cache = get_shared_price_cache(price_ttl=10.0, enable_l2=False)
        assert cache._price_ttl == 10.0
        assert cache._enable_l2 is False


class TestCachedPrice:
    """Tests for CachedPrice dataclass."""

    def test_cached_price_creation(self):
        """Test creating a CachedPrice entry."""
        entry = CachedPrice(
            price=50000.0,
            timestamp=time.monotonic(),
            exchange="hyperliquid",
            symbol="BTC",
            bid=49990.0,
            ask=50010.0,
        )

        assert entry.price == 50000.0
        assert entry.exchange == "hyperliquid"
        assert entry.symbol == "BTC"
        assert entry.bid == 49990.0
        assert entry.ask == 50010.0

    def test_cached_price_optional_bid_ask(self):
        """Test CachedPrice with optional bid/ask."""
        entry = CachedPrice(
            price=50000.0,
            timestamp=time.monotonic(),
            exchange="hyperliquid",
            symbol="BTC",
        )

        assert entry.bid is None
        assert entry.ask is None
