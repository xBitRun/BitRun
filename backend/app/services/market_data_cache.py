"""
Market Data Cache Service - K-line data caching and management.

Provides:
- Redis-based caching for market data
- Automatic data fetching and caching
- TTL-based cache invalidation
- Batch data preloading for backtests
"""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Optional

from ..core.config import get_settings
from ..services.redis_service import get_redis_service

logger = logging.getLogger(__name__)


class MarketDataCache:
    """
    Cache service for market data (K-lines, prices, etc.)

    Uses Redis for caching with configurable TTL.
    """

    # Cache key prefixes
    KLINE_PREFIX = "kline:"
    PRICE_PREFIX = "price:"
    SYMBOLS_PREFIX = "symbols:"

    # Default TTLs
    KLINE_TTL = 3600  # 1 hour for historical klines
    PRICE_TTL = 60  # 1 minute for current price
    SYMBOLS_TTL = 86400  # 24 hours for symbol list

    def __init__(self):
        self._redis = None
        self._settings = get_settings()

    async def _get_redis(self):
        """Get Redis connection lazily"""
        if self._redis is None:
            self._redis = await get_redis_service()
        return self._redis

    # ==================== K-line Cache ====================

    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        exchange: str = "binance",
    ) -> Optional[list[dict]]:
        """
        Get cached K-line data.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            timeframe: Candle timeframe (e.g., "1h", "4h", "1d")
            start_time: Start of data range
            end_time: End of data range
            exchange: Exchange name

        Returns:
            List of K-line dicts or None if not cached
        """
        redis = await self._get_redis()

        # Generate cache key
        key = self._kline_key(symbol, timeframe, exchange, start_time, end_time)

        try:
            data = await redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to get klines from cache: {e}")

        return None

    async def set_klines(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        klines: list[dict],
        exchange: str = "binance",
        ttl: int = None,
    ) -> bool:
        """
        Cache K-line data.

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            start_time: Start of data range
            end_time: End of data range
            klines: List of K-line dicts
            exchange: Exchange name
            ttl: Cache TTL in seconds (default: KLINE_TTL)

        Returns:
            True if cached successfully
        """
        redis = await self._get_redis()

        key = self._kline_key(symbol, timeframe, exchange, start_time, end_time)
        ttl = ttl or self.KLINE_TTL

        try:
            await redis.set(key, json.dumps(klines), ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Failed to cache klines: {e}")
            return False

    def _kline_key(
        self,
        symbol: str,
        timeframe: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime,
    ) -> str:
        """Generate cache key for K-line data"""
        start_str = start_time.strftime("%Y%m%d")
        end_str = end_time.strftime("%Y%m%d")
        return f"{self.KLINE_PREFIX}{exchange}:{symbol}:{timeframe}:{start_str}:{end_str}"

    # ==================== Price Cache ====================

    async def get_price(
        self,
        symbol: str,
        exchange: str = "binance",
    ) -> Optional[dict]:
        """
        Get cached current price.

        Returns:
            Price dict with 'price', 'timestamp', etc. or None
        """
        redis = await self._get_redis()

        key = f"{self.PRICE_PREFIX}{exchange}:{symbol}"

        try:
            data = await redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to get price from cache: {e}")

        return None

    async def set_price(
        self,
        symbol: str,
        price_data: dict,
        exchange: str = "binance",
        ttl: int = None,
    ) -> bool:
        """
        Cache current price.

        Args:
            symbol: Trading pair
            price_data: Dict with price info
            exchange: Exchange name
            ttl: Cache TTL in seconds
        """
        redis = await self._get_redis()

        key = f"{self.PRICE_PREFIX}{exchange}:{symbol}"
        ttl = ttl or self.PRICE_TTL

        try:
            await redis.set(key, json.dumps(price_data), ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Failed to cache price: {e}")
            return False

    # ==================== Symbol List Cache ====================

    async def get_symbols(
        self,
        exchange: str = "binance",
    ) -> Optional[list[str]]:
        """Get cached symbol list for an exchange"""
        redis = await self._get_redis()

        key = f"{self.SYMBOLS_PREFIX}{exchange}"

        try:
            data = await redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to get symbols from cache: {e}")

        return None

    async def set_symbols(
        self,
        symbols: list[str],
        exchange: str = "binance",
        ttl: int = None,
    ) -> bool:
        """Cache symbol list"""
        redis = await self._get_redis()

        key = f"{self.SYMBOLS_PREFIX}{exchange}"
        ttl = ttl or self.SYMBOLS_TTL

        try:
            await redis.set(key, json.dumps(symbols), ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Failed to cache symbols: {e}")
            return False

    # ==================== Cache Management ====================

    async def invalidate_klines(
        self,
        symbol: str = None,
        exchange: str = None,
    ) -> int:
        """
        Invalidate K-line cache entries.

        Args:
            symbol: Specific symbol to invalidate (None = all)
            exchange: Specific exchange (None = all)

        Returns:
            Number of keys deleted
        """
        redis = await self._get_redis()

        if symbol and exchange:
            pattern = f"{self.KLINE_PREFIX}{exchange}:{symbol}:*"
        elif exchange:
            pattern = f"{self.KLINE_PREFIX}{exchange}:*"
        else:
            pattern = f"{self.KLINE_PREFIX}*"

        try:
            keys = await redis.keys(pattern)
            if keys:
                return await redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate kline cache: {e}")
            return 0

    async def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        redis = await self._get_redis()

        try:
            kline_keys = await redis.keys(f"{self.KLINE_PREFIX}*")
            price_keys = await redis.keys(f"{self.PRICE_PREFIX}*")
            symbol_keys = await redis.keys(f"{self.SYMBOLS_PREFIX}*")

            return {
                "kline_entries": len(kline_keys),
                "price_entries": len(price_keys),
                "symbol_entries": len(symbol_keys),
                "total_entries": len(kline_keys) + len(price_keys) + len(symbol_keys),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}


class BacktestDataPreloader:
    """
    Preloader for backtest data.

    Pre-fetches and caches historical data needed for backtests.
    """

    def __init__(self, cache: MarketDataCache):
        self.cache = cache
        self._settings = get_settings()

    async def preload_for_backtest(
        self,
        symbols: list[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1h",
        exchange: str = "binance",
        data_provider = None,
    ) -> dict:
        """
        Preload data for a backtest run.

        Fetches and caches historical data for all specified symbols.

        Args:
            symbols: List of trading pairs
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Candle timeframe
            exchange: Exchange name
            data_provider: DataProvider instance (optional, for actual data fetching)

        Returns:
            Dict with preload results
        """
        results = {
            "symbols_requested": len(symbols),
            "symbols_cached": 0,
            "symbols_fetched": 0,
            "errors": [],
        }

        for symbol in symbols:
            try:
                # Check cache first
                cached = await self.cache.get_klines(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_date,
                    end_time=end_date,
                    exchange=exchange,
                )

                if cached:
                    results["symbols_cached"] += 1
                    logger.debug(f"Found cached data for {symbol}")
                    continue

                # Fetch if data provider available
                if data_provider:
                    klines = await data_provider.get_klines(
                        symbol=symbol,
                        timeframe=timeframe,
                        start_time=start_date,
                        end_time=end_date,
                    )

                    if klines:
                        # Cache the data
                        await self.cache.set_klines(
                            symbol=symbol,
                            timeframe=timeframe,
                            start_time=start_date,
                            end_time=end_date,
                            klines=klines,
                            exchange=exchange,
                        )
                        results["symbols_fetched"] += 1
                        logger.info(f"Fetched and cached {len(klines)} klines for {symbol}")

            except Exception as e:
                logger.error(f"Error preloading {symbol}: {e}")
                results["errors"].append({"symbol": symbol, "error": str(e)})

        return results

    async def preload_common_symbols(
        self,
        exchange: str = "binance",
        timeframe: str = "1h",
        days_back: int = 30,
        data_provider = None,
    ) -> dict:
        """
        Preload data for commonly traded symbols.

        Useful for warming up the cache on startup.
        """
        common_symbols = [
            "BTC/USDT",
            "ETH/USDT",
            "SOL/USDT",
            "BNB/USDT",
            "XRP/USDT",
            "ADA/USDT",
            "DOGE/USDT",
            "AVAX/USDT",
            "DOT/USDT",
            "LINK/USDT",
        ]

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days_back)

        return await self.preload_for_backtest(
            symbols=common_symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            exchange=exchange,
            data_provider=data_provider,
        )


# Global instances
_market_data_cache: Optional[MarketDataCache] = None
_backtest_preloader: Optional[BacktestDataPreloader] = None


def get_market_data_cache() -> MarketDataCache:
    """Get or create the market data cache singleton"""
    global _market_data_cache
    if _market_data_cache is None:
        _market_data_cache = MarketDataCache()
    return _market_data_cache


def get_backtest_preloader() -> BacktestDataPreloader:
    """Get or create the backtest preloader singleton"""
    global _backtest_preloader
    if _backtest_preloader is None:
        _backtest_preloader = BacktestDataPreloader(get_market_data_cache())
    return _backtest_preloader
