"""
Tests for MarketDataCache service.

Covers: get/set_klines, get/set_price, invalidate_klines, get_cache_stats.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.market_data_cache import MarketDataCache


# ==================== Helpers ====================


def _make_cache(mock_redis=None) -> MarketDataCache:
    """Create a MarketDataCache with mocked settings and optional mock redis."""
    with patch("app.services.market_data_cache.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock()
        cache = MarketDataCache()

    if mock_redis is not None:
        cache._redis = mock_redis

    return cache


def _mock_redis() -> AsyncMock:
    """Create a mock RedisService with common async methods."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.keys = AsyncMock(return_value=[])
    redis.delete = AsyncMock(return_value=0)
    return redis


# ==================== TestMarketDataCache ====================


class TestMarketDataCache:
    """Tests for MarketDataCache."""

    @pytest.fixture
    def redis(self):
        return _mock_redis()

    @pytest.fixture
    def cache(self, redis):
        return _make_cache(mock_redis=redis)

    # ---------- K-line Cache ----------

    @pytest.mark.asyncio
    async def test_get_klines_cached(self, cache, redis):
        """Return cached K-line data when present."""
        klines = [{"open": 50000, "close": 51000}]
        redis.get.return_value = json.dumps(klines)

        result = await cache.get_klines(
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
        )

        assert result == klines
        redis.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_klines_not_cached(self, cache, redis):
        """Return None when K-line data is not in cache."""
        redis.get.return_value = None

        result = await cache.get_klines(
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_klines_redis_error(self, cache, redis):
        """Return None gracefully on Redis error."""
        redis.get.side_effect = Exception("connection lost")

        result = await cache.get_klines(
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_set_klines(self, cache, redis):
        """Cache K-line data with default TTL."""
        klines = [{"open": 50000, "close": 51000}]

        result = await cache.set_klines(
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
            klines=klines,
        )

        assert result is True
        redis.set.assert_awaited_once()
        call_kwargs = redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == MarketDataCache.KLINE_TTL

    @pytest.mark.asyncio
    async def test_set_klines_custom_ttl(self, cache, redis):
        """Cache K-line data with custom TTL."""
        result = await cache.set_klines(
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
            klines=[],
            ttl=7200,
        )

        assert result is True
        call_kwargs = redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == 7200

    @pytest.mark.asyncio
    async def test_set_klines_redis_error(self, cache, redis):
        """Return False gracefully on Redis error."""
        redis.set.side_effect = Exception("write fail")

        result = await cache.set_klines(
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
            klines=[{"o": 1}],
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_kline_key_format(self, cache):
        """Verify the generated cache key format."""
        key = cache._kline_key(
            symbol="BTC/USDT",
            timeframe="4h",
            exchange="binance",
            start_time=datetime(2025, 3, 15),
            end_time=datetime(2025, 3, 20),
        )

        assert key == "kline:binance:BTC/USDT:4h:20250315:20250320"

    # ---------- Price Cache ----------

    @pytest.mark.asyncio
    async def test_get_price_cached(self, cache, redis):
        price_data = {"price": 50123.45, "timestamp": "2025-01-01T00:00:00"}
        redis.get.return_value = json.dumps(price_data)

        result = await cache.get_price(symbol="BTC/USDT")

        assert result == price_data

    @pytest.mark.asyncio
    async def test_get_price_not_cached(self, cache, redis):
        redis.get.return_value = None
        result = await cache.get_price(symbol="BTC/USDT")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_price_redis_error(self, cache, redis):
        redis.get.side_effect = Exception("timeout")
        result = await cache.get_price(symbol="BTC/USDT")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_price(self, cache, redis):
        price_data = {"price": 50000.0, "timestamp": "2025-01-01T00:00:00"}

        result = await cache.set_price(symbol="BTC/USDT", price_data=price_data)

        assert result is True
        redis.set.assert_awaited_once()
        call_kwargs = redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == MarketDataCache.PRICE_TTL

    @pytest.mark.asyncio
    async def test_set_price_custom_ttl(self, cache, redis):
        result = await cache.set_price(
            symbol="BTC/USDT",
            price_data={"price": 50000},
            ttl=120,
        )

        assert result is True
        call_kwargs = redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == 120

    @pytest.mark.asyncio
    async def test_set_price_redis_error(self, cache, redis):
        redis.set.side_effect = Exception("write fail")
        result = await cache.set_price(symbol="BTC/USDT", price_data={"price": 1})
        assert result is False

    # ---------- Cache Management ----------

    @pytest.mark.asyncio
    async def test_invalidate_klines_all(self, cache, redis):
        """Invalidate all kline entries when no filters."""
        redis.keys.return_value = ["kline:binance:BTC:1h:a:b", "kline:binance:ETH:1h:a:b"]
        redis.delete.return_value = 2

        count = await cache.invalidate_klines()

        assert count == 2
        redis.keys.assert_awaited_once_with("kline:*")
        redis.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalidate_klines_by_symbol_and_exchange(self, cache, redis):
        redis.keys.return_value = ["kline:binance:BTC/USDT:1h:a:b"]
        redis.delete.return_value = 1

        count = await cache.invalidate_klines(symbol="BTC/USDT", exchange="binance")

        assert count == 1
        redis.keys.assert_awaited_once_with("kline:binance:BTC/USDT:*")

    @pytest.mark.asyncio
    async def test_invalidate_klines_by_exchange_only(self, cache, redis):
        redis.keys.return_value = ["k1", "k2"]
        redis.delete.return_value = 2

        count = await cache.invalidate_klines(exchange="binance")

        redis.keys.assert_awaited_once_with("kline:binance:*")
        assert count == 2

    @pytest.mark.asyncio
    async def test_invalidate_klines_no_keys(self, cache, redis):
        redis.keys.return_value = []
        count = await cache.invalidate_klines()
        assert count == 0
        redis.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalidate_klines_redis_error(self, cache, redis):
        redis.keys.side_effect = Exception("error")
        count = await cache.invalidate_klines()
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache, redis):
        redis.keys.side_effect = [
            ["k1", "k2"],       # kline keys
            ["p1"],             # price keys
            ["s1", "s2", "s3"], # symbol keys
        ]

        stats = await cache.get_cache_stats()

        assert stats["kline_entries"] == 2
        assert stats["price_entries"] == 1
        assert stats["symbol_entries"] == 3
        assert stats["total_entries"] == 6

    @pytest.mark.asyncio
    async def test_get_cache_stats_redis_error(self, cache, redis):
        redis.keys.side_effect = Exception("connection error")

        stats = await cache.get_cache_stats()

        assert "error" in stats
