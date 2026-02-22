"""
Data Access Layer - Unified data access for trading strategies.

Provides a single interface for:
- Fetching K-line data from exchanges
- Caching data with Redis
- Calculating technical indicators
- Building complete market context for AI prompts
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from ..models.market_context import (
    CACHE_TTL,
    OHLCV,
    TIMEFRAME_LIMITS,
    FundingRate,
    MarketContext,
    TechnicalIndicators,
)
from ..models.strategy import StrategyConfig
from ..traders.base import BaseTrader, MarketData
from .indicator_calculator import IndicatorCalculator
from .market_data_cache import MarketDataCache
from .redis_service import get_redis_service

logger = logging.getLogger(__name__)


class DataAccessLayer:
    """
    Unified data access layer for trading strategies.

    Responsibilities:
    1. Fetch K-line data from exchanges (via trader adapters)
    2. Cache data with Redis for performance
    3. Calculate technical indicators
    4. Build complete MarketContext for AI prompts

    Usage:
        dal = DataAccessLayer(trader, cache, config)
        context = await dal.get_market_context("BTC/USDT")
        contexts = await dal.get_market_contexts(["BTC/USDT", "ETH/USDT"])
    """

    # Cache key prefixes
    KLINE_CACHE_PREFIX = "dal:kline:"
    INDICATOR_CACHE_PREFIX = "dal:indicator:"
    FUNDING_CACHE_PREFIX = "dal:funding:"

    def __init__(
        self,
        trader: BaseTrader,
        cache: Optional[MarketDataCache] = None,
        config: Optional[StrategyConfig] = None,
    ):
        """
        Initialize Data Access Layer.

        Args:
            trader: Exchange trader adapter (Binance, Bybit, etc.)
            cache: Market data cache (optional, creates one if not provided)
            config: Strategy configuration with timeframes and indicator settings
        """
        self.trader = trader
        self.cache = cache
        self.config = config or StrategyConfig()

        # Initialize indicator calculator with config
        self.indicator_calc = IndicatorCalculator(self.config.indicators)

        # Redis connection (lazy init)
        self._redis = None

    async def _get_redis(self):
        """Get Redis connection lazily"""
        if self._redis is None:
            self._redis = await get_redis_service()
        return self._redis

    # ==================== Main API ====================

    async def get_market_context(
        self,
        symbol: str,
        timeframes: Optional[list[str]] = None,
    ) -> MarketContext:
        """
        Get complete market context for a symbol.

        Fetches real-time data, K-lines for all timeframes,
        calculates indicators, and builds MarketContext.

        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            timeframes: Optional list of timeframes to fetch.
                       Uses config.timeframes if not provided.

        Returns:
            MarketContext with all data populated
        """
        timeframes = timeframes or self.config.timeframes

        # 1. Fetch real-time market data
        try:
            current = await self.trader.get_market_data(symbol)
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            # Create minimal MarketData on failure
            current = MarketData(
                symbol=symbol,
                mid_price=0.0,
                bid_price=0.0,
                ask_price=0.0,
                volume_24h=0.0,
            )

        # 2. Fetch K-lines for all timeframes (parallel)
        klines: dict[str, list[OHLCV]] = {}
        kline_tasks = {tf: self._get_klines_cached(symbol, tf) for tf in timeframes}

        kline_results = await asyncio.gather(
            *kline_tasks.values(),
            return_exceptions=True,
        )

        for tf, result in zip(kline_tasks.keys(), kline_results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to get klines for {symbol} {tf}: {result}")
                klines[tf] = []
            else:
                klines[tf] = result

        # 3. Calculate technical indicators for each timeframe
        indicators: dict[str, TechnicalIndicators] = {}
        for tf, candles in klines.items():
            if candles:
                indicators[tf] = self.indicator_calc.calculate(candles)
            else:
                indicators[tf] = TechnicalIndicators()

        # 4. Fetch funding rate history
        funding_history = await self._get_funding_cached(symbol)

        # 5. Build and return MarketContext
        return MarketContext(
            symbol=symbol,
            current=current,
            exchange_name=self.trader.exchange_name,
            klines=klines,
            indicators=indicators,
            funding_history=funding_history,
        )

    async def get_market_contexts(
        self,
        symbols: list[str],
        timeframes: Optional[list[str]] = None,
    ) -> dict[str, MarketContext]:
        """
        Get market contexts for multiple symbols (parallel).

        Args:
            symbols: List of trading symbols
            timeframes: Optional list of timeframes

        Returns:
            Dict mapping symbol to MarketContext
        """
        tasks = {
            symbol: self.get_market_context(symbol, timeframes) for symbol in symbols
        }

        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True,
        )

        contexts = {}
        for symbol, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get context for {symbol}: {result}")
                # Create empty context
                contexts[symbol] = MarketContext(
                    symbol=symbol,
                    current=MarketData(
                        symbol=symbol,
                        mid_price=0.0,
                        bid_price=0.0,
                        ask_price=0.0,
                        volume_24h=0.0,
                    ),
                    exchange_name=self.trader.exchange_name,
                )
            else:
                contexts[symbol] = result

        return contexts

    # ==================== K-line Data ====================

    async def _get_klines_cached(
        self,
        symbol: str,
        timeframe: str,
    ) -> list[OHLCV]:
        """
        Get K-line data with caching.

        Checks cache first, fetches from exchange if not cached.
        """
        cache_key = (
            f"{self.KLINE_CACHE_PREFIX}{self.trader.exchange_name}:{symbol}:{timeframe}"
        )

        # Try cache first
        try:
            redis = await self._get_redis()
            cached = await redis.get(cache_key)

            if cached:
                data = json.loads(cached)
                return [
                    OHLCV(
                        timestamp=datetime.fromisoformat(k["timestamp"]),
                        open=k["open"],
                        high=k["high"],
                        low=k["low"],
                        close=k["close"],
                        volume=k["volume"],
                    )
                    for k in data
                ]
        except Exception as e:
            logger.debug(f"Cache miss for klines {symbol} {timeframe}: {e}")

        # Fetch from exchange
        limit = TIMEFRAME_LIMITS.get(timeframe, 100)
        klines = await self.trader.get_klines(symbol, timeframe, limit)

        if not klines:
            return []

        # Cache the result
        try:
            redis = await self._get_redis()
            ttl = CACHE_TTL.get(timeframe, 300)

            cache_data = json.dumps([k.to_dict() for k in klines])
            await redis.set(cache_key, cache_data, ex=ttl)
        except Exception as e:
            logger.debug(f"Failed to cache klines: {e}")

        return klines

    async def get_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: Optional[int] = None,
        use_cache: bool = True,
    ) -> list[OHLCV]:
        """
        Get K-line data for a symbol.

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            limit: Number of candles (uses TIMEFRAME_LIMITS if not specified)
            use_cache: Whether to use caching

        Returns:
            List of OHLCV objects
        """
        if use_cache:
            return await self._get_klines_cached(symbol, timeframe)

        # Direct fetch without cache
        limit = limit or TIMEFRAME_LIMITS.get(timeframe, 100)
        return await self.trader.get_klines(symbol, timeframe, limit)

    # ==================== Funding Rate ====================

    async def _get_funding_cached(
        self,
        symbol: str,
        limit: int = 24,
    ) -> list[FundingRate]:
        """
        Get funding rate history with caching.
        """
        cache_key = f"{self.FUNDING_CACHE_PREFIX}{self.trader.exchange_name}:{symbol}"

        # Try cache first
        try:
            redis = await self._get_redis()
            cached = await redis.get(cache_key)

            if cached:
                data = json.loads(cached)
                return [
                    FundingRate(
                        timestamp=datetime.fromisoformat(f["timestamp"]),
                        rate=f["rate"],
                    )
                    for f in data
                ]
        except Exception as e:
            logger.debug(f"Cache miss for funding {symbol}: {e}")

        # Fetch from exchange
        funding_history = await self.trader.get_funding_history(symbol, limit)

        if not funding_history:
            return []

        # Cache the result (funding rates update every 8 hours)
        try:
            redis = await self._get_redis()
            cache_data = json.dumps([f.to_dict() for f in funding_history])
            await redis.set(cache_key, cache_data, ex=3600)  # 1 hour TTL
        except Exception as e:
            logger.debug(f"Failed to cache funding: {e}")

        return funding_history

    # ==================== Indicator Calculation ====================

    async def get_indicators(
        self,
        symbol: str,
        timeframe: str,
    ) -> TechnicalIndicators:
        """
        Get calculated indicators for a symbol and timeframe.

        Fetches K-lines and calculates indicators.
        """
        klines = await self._get_klines_cached(symbol, timeframe)

        if not klines:
            return TechnicalIndicators()

        return self.indicator_calc.calculate(klines)

    async def get_indicators_multi(
        self,
        symbol: str,
        timeframes: Optional[list[str]] = None,
    ) -> dict[str, TechnicalIndicators]:
        """
        Get indicators for multiple timeframes.

        Args:
            symbol: Trading symbol
            timeframes: List of timeframes (uses config if not provided)

        Returns:
            Dict mapping timeframe to TechnicalIndicators
        """
        timeframes = timeframes or self.config.timeframes

        tasks = {tf: self.get_indicators(symbol, tf) for tf in timeframes}

        results = await asyncio.gather(*tasks.values())

        return dict(zip(tasks.keys(), results))

    # ==================== Cache Management ====================

    async def invalidate_cache(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> int:
        """
        Invalidate cached data.

        Args:
            symbol: Specific symbol to invalidate (None = all)
            timeframe: Specific timeframe to invalidate (None = all)

        Returns:
            Number of keys deleted
        """
        try:
            redis = await self._get_redis()

            # Build pattern
            if symbol and timeframe:
                pattern = f"{self.KLINE_CACHE_PREFIX}*:{symbol}:{timeframe}"
            elif symbol:
                pattern = f"{self.KLINE_CACHE_PREFIX}*:{symbol}:*"
            else:
                pattern = f"{self.KLINE_CACHE_PREFIX}*"

            keys = await redis.keys(pattern)

            if keys:
                return await redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return 0

    async def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        try:
            redis = await self._get_redis()

            kline_keys = await redis.keys(f"{self.KLINE_CACHE_PREFIX}*")
            funding_keys = await redis.keys(f"{self.FUNDING_CACHE_PREFIX}*")
            indicator_keys = await redis.keys(f"{self.INDICATOR_CACHE_PREFIX}*")

            return {
                "kline_entries": len(kline_keys),
                "funding_entries": len(funding_keys),
                "indicator_entries": len(indicator_keys),
                "total_entries": len(kline_keys)
                + len(funding_keys)
                + len(indicator_keys),
                "exchange": self.trader.exchange_name,
            }
        except Exception as e:
            return {"error": str(e)}

    # ==================== Preloading ====================

    async def preload_data(
        self,
        symbols: list[str],
        timeframes: Optional[list[str]] = None,
    ) -> dict:
        """
        Preload data for multiple symbols.

        Useful for warming up cache before strategy execution.

        Args:
            symbols: List of symbols to preload
            timeframes: List of timeframes (uses config if not provided)

        Returns:
            Summary of preloaded data
        """
        timeframes = timeframes or self.config.timeframes

        results = {
            "symbols": len(symbols),
            "timeframes": len(timeframes),
            "klines_loaded": 0,
            "funding_loaded": 0,
            "errors": [],
        }

        for symbol in symbols:
            try:
                # Preload klines for all timeframes
                for tf in timeframes:
                    klines = await self._get_klines_cached(symbol, tf)
                    if klines:
                        results["klines_loaded"] += 1

                # Preload funding
                funding = await self._get_funding_cached(symbol)
                if funding:
                    results["funding_loaded"] += 1

            except Exception as e:
                results["errors"].append(
                    {
                        "symbol": symbol,
                        "error": str(e),
                    }
                )

        return results


# Factory function
def create_data_access_layer(
    trader: BaseTrader,
    config: Optional[StrategyConfig] = None,
) -> DataAccessLayer:
    """
    Create a DataAccessLayer instance.

    Args:
        trader: Exchange trader adapter
        config: Strategy configuration

    Returns:
        Configured DataAccessLayer
    """
    from .market_data_cache import get_market_data_cache

    cache = get_market_data_cache()
    return DataAccessLayer(trader=trader, cache=cache, config=config)
