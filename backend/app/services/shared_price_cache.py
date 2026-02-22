"""
Shared Price Cache Service - Global price caching across all traders.

Provides:
- Local in-memory L1 cache (microsecond access)
- Redis L2 cache for cross-Agent/cross-process sharing
- Request coalescing to prevent thundering herd
- Automatic TTL-based expiration

Architecture:
                    +------------------+
                    |  L1 Memory Cache |
                    |  (per-instance)  |
                    +--------+---------+
                             ^ (miss)
         +-------------------+-------------------+
         |                   |                   |
    MockTrader          CCXTTrader          CCXTTrader
    (Agent 1)           (Agent 2)           (Agent N)
         |                   |                   |
         v                   v                   v
    +----------------------------------------------+
    |              L2 Redis Cache                  |
    |         (cross-Agent shared)                 |
    +----------------------+-----------------------+
                           ^ (miss)
                           |
    +----------------------+-----------------------+
    |              Exchange API                   |
    +----------------------------------------------+
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CachedPrice:
    """Cached price entry with metadata."""

    price: float
    timestamp: float  # monotonic time for TTL checks
    exchange: str
    symbol: str
    bid: Optional[float] = None
    ask: Optional[float] = None


class SharedPriceCache:
    """
    Global price cache with L1 (memory) and L2 (Redis) tiers.

    Features:
    - L1 in-memory cache for ultra-fast access (<1μs)
    - L2 Redis cache for cross-Agent sharing (~1ms)
    - Request coalescing: concurrent requests share a single API call
    - Configurable TTL per data type
    - Graceful degradation when Redis unavailable
    """

    # Default TTLs in seconds
    DEFAULT_PRICE_TTL = 5.0  # Price ticker TTL
    DEFAULT_KLINE_TTL = 60.0  # K-line data TTL

    # Cache key prefixes
    PRICE_KEY_PREFIX = "price_cache:"

    def __init__(
        self,
        price_ttl: float = DEFAULT_PRICE_TTL,
        enable_l2: bool = True,
    ):
        """
        Initialize the shared price cache.

        Args:
            price_ttl: TTL for price data in seconds (default: 5s)
            enable_l2: Whether to use Redis L2 cache (default: True)
        """
        self._price_ttl = price_ttl
        self._enable_l2 = enable_l2

        # L1 cache: symbol -> CachedPrice
        self._l1_cache: Dict[str, CachedPrice] = {}

        # Request coalescing: symbol -> asyncio.Future
        # Prevents multiple concurrent requests for the same symbol
        self._pending_requests: Dict[str, asyncio.Future] = {}

        # Redis client (lazy initialization)
        self._redis = None

        # Metrics
        self._l1_hits = 0
        self._l1_misses = 0
        self._l2_hits = 0
        self._l2_misses = 0
        self._api_calls = 0

    async def _get_redis(self):
        """Get Redis connection lazily."""
        if self._redis is None and self._enable_l2:
            try:
                from .redis_service import get_redis_service

                self._redis = await get_redis_service()
            except Exception as e:
                logger.warning(f"Redis unavailable, using L1 cache only: {e}")
                self._enable_l2 = False
        return self._redis

    def _make_key(self, exchange: str, symbol: str) -> str:
        """Generate cache key for a symbol."""
        return f"{self.PRICE_KEY_PREFIX}{exchange}:{symbol.upper()}"

    # =========================================================================
    # Public API
    # =========================================================================

    async def get_price(
        self,
        exchange: str,
        symbol: str,
        fetcher: Optional[
            Callable[[], Tuple[float, Optional[float], Optional[float]]]
        ] = None,
    ) -> Optional[float]:
        """
        Get cached price, optionally fetching if not cached.

        Args:
            exchange: Exchange identifier (e.g., "hyperliquid")
            symbol: Trading symbol (e.g., "BTC")
            fetcher: Async function to fetch price if not cached.
                     Returns (price, bid, ask) tuple.

        Returns:
            Cached price or None if unavailable
        """
        symbol = symbol.upper()
        key = self._make_key(exchange, symbol)

        # 1. Check L1 cache
        cached = self._l1_cache.get(key)
        now = time.monotonic()

        if cached and (now - cached.timestamp) < self._price_ttl:
            self._l1_hits += 1
            logger.debug(f"L1 cache HIT for {exchange}:{symbol}")
            return cached.price

        self._l1_misses += 1

        # 2. Check L2 cache (Redis)
        if self._enable_l2:
            l2_price = await self._get_from_l2(key)
            if l2_price is not None:
                self._l2_hits += 1
                # Promote to L1
                self._l1_cache[key] = CachedPrice(
                    price=l2_price["price"],
                    timestamp=now,
                    exchange=exchange,
                    symbol=symbol,
                    bid=l2_price.get("bid"),
                    ask=l2_price.get("ask"),
                )
                logger.debug(f"L2 cache HIT for {exchange}:{symbol}")
                return l2_price["price"]

        self._l2_misses += 1

        # 3. Fetch if provider available
        if fetcher is not None:
            return await self._fetch_with_coalescing(exchange, symbol, key, fetcher)

        # 4. Return stale L1 data if available (graceful degradation)
        if cached:
            logger.debug(f"Using stale L1 cache for {exchange}:{symbol}")
            return cached.price

        return None

    async def set_price(
        self,
        exchange: str,
        symbol: str,
        price: float,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ) -> None:
        """
        Cache a price value.

        Args:
            exchange: Exchange identifier
            symbol: Trading symbol
            price: Current price
            bid: Bid price (optional)
            ask: Ask price (optional)
        """
        symbol = symbol.upper()
        key = self._make_key(exchange, symbol)
        now = time.monotonic()

        # Update L1
        self._l1_cache[key] = CachedPrice(
            price=price,
            timestamp=now,
            exchange=exchange,
            symbol=symbol,
            bid=bid,
            ask=ask,
        )

        # Update L2
        if self._enable_l2:
            await self._set_in_l2(
                key,
                {
                    "price": price,
                    "bid": bid,
                    "ask": ask,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )

        logger.debug(f"Cached price for {exchange}:{symbol}: {price}")

    async def get_prices_batch(
        self,
        exchange: str,
        symbols: list[str],
        fetcher: Optional[
            Callable[
                [list[str]], Dict[str, Tuple[float, Optional[float], Optional[float]]]
            ]
        ] = None,
    ) -> Dict[str, float]:
        """
        Get prices for multiple symbols efficiently.

        Args:
            exchange: Exchange identifier
            symbols: List of symbols to fetch
            fetcher: Async function to fetch multiple prices at once

        Returns:
            Dict mapping symbol -> price
        """
        results = {}
        uncached = []

        for symbol in symbols:
            price = await self.get_price(exchange, symbol)
            if price is not None:
                results[symbol] = price
            else:
                uncached.append(symbol)

        # Fetch uncached symbols
        if uncached and fetcher is not None:
            try:
                fetched = await fetcher(uncached)
                for symbol, (price, bid, ask) in fetched.items():
                    await self.set_price(exchange, symbol, price, bid, ask)
                    results[symbol] = price
            except Exception as e:
                logger.warning(f"Batch fetch failed: {e}")

        return results

    def invalidate(self, exchange: str, symbol: Optional[str] = None) -> int:
        """
        Invalidate cached entries.

        Args:
            exchange: Exchange to invalidate
            symbol: Specific symbol or None for all

        Returns:
            Number of entries invalidated
        """
        count = 0
        prefix = self._make_key(exchange, symbol or "*")

        # Invalidate L1
        keys_to_remove = [
            k
            for k in self._l1_cache
            if symbol is None or k == prefix.replace("*", symbol.upper())
        ]
        for k in keys_to_remove:
            del self._l1_cache[k]
            count += 1

        # Note: L2 invalidation is async and happens lazily via TTL
        logger.debug(f"Invalidated {count} L1 entries for {exchange}:{symbol or '*'}")
        return count

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self._l1_hits + self._l1_misses
        l1_hit_rate = self._l1_hits / total_requests if total_requests > 0 else 0

        l2_requests = self._l2_hits + self._l2_misses
        l2_hit_rate = self._l2_hits / l2_requests if l2_requests > 0 else 0

        return {
            "l1_entries": len(self._l1_cache),
            "l1_hits": self._l1_hits,
            "l1_misses": self._l1_misses,
            "l1_hit_rate": l1_hit_rate,
            "l2_hits": self._l2_hits,
            "l2_misses": self._l2_misses,
            "l2_hit_rate": l2_hit_rate,
            "api_calls": self._api_calls,
            "pending_requests": len(self._pending_requests),
        }

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _get_from_l2(self, key: str) -> Optional[dict]:
        """Get price from L2 (Redis) cache."""
        redis = await self._get_redis()
        if redis is None:
            return None

        try:
            data = await redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.debug(f"L2 get failed for {key}: {e}")

        return None

    async def _set_in_l2(self, key: str, data: dict) -> bool:
        """Set price in L2 (Redis) cache."""
        redis = await self._get_redis()
        if redis is None:
            return False

        try:
            await redis.set(key, json.dumps(data), ex=int(self._price_ttl * 2))
            return True
        except Exception as e:
            logger.debug(f"L2 set failed for {key}: {e}")
            return False

    async def _fetch_with_coalescing(
        self,
        exchange: str,
        symbol: str,
        key: str,
        fetcher: Callable,
    ) -> Optional[float]:
        """
        Fetch price with request coalescing.

        Multiple concurrent requests for the same symbol share a single API call.
        """
        # Check if there's already a pending request for this symbol
        if key in self._pending_requests:
            logger.debug(f"Coalescing request for {exchange}:{symbol}")
            try:
                # Wait for the existing request to complete
                return await self._pending_requests[key]
            except Exception:
                return None

        # Create a future for this request
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[key] = future

        try:
            self._api_calls += 1
            result = await fetcher()

            if result is not None:
                price, bid, ask = (
                    result if len(result) == 3 else (result[0], None, None)
                )
                await self.set_price(exchange, symbol, price, bid, ask)
                future.set_result(price)
                return price
            else:
                future.set_result(None)
                return None

        except Exception as e:
            logger.warning(f"Fetch failed for {exchange}:{symbol}: {e}")
            future.set_exception(e)
            return None

        finally:
            # Clean up pending request
            self._pending_requests.pop(key, None)


# =============================================================================
# Singleton Instance
# =============================================================================

_shared_price_cache: Optional[SharedPriceCache] = None


def get_shared_price_cache(
    price_ttl: float = SharedPriceCache.DEFAULT_PRICE_TTL,
    enable_l2: bool = True,
) -> SharedPriceCache:
    """
    Get or create the shared price cache singleton.

    Args:
        price_ttl: TTL for price data in seconds
        enable_l2: Whether to enable Redis L2 cache

    Returns:
        SharedPriceCache singleton instance
    """
    global _shared_price_cache
    if _shared_price_cache is None:
        _shared_price_cache = SharedPriceCache(
            price_ttl=price_ttl,
            enable_l2=enable_l2,
        )
    return _shared_price_cache


def reset_shared_price_cache() -> None:
    """Reset the shared price cache (for testing)."""
    global _shared_price_cache
    _shared_price_cache = None
