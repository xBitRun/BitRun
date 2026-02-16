"""Data management routes"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...core.dependencies import CurrentUserDep
from ...services.market_data_cache import (
    get_market_data_cache,
    get_backtest_preloader,
)

router = APIRouter(prefix="/data", tags=["Data Management"])
logger = logging.getLogger(__name__)


# ==================== Request/Response Models ====================

class CacheStats(BaseModel):
    """Cache statistics"""
    kline_entries: int
    price_entries: int
    symbol_entries: int
    total_entries: int


class PreloadRequest(BaseModel):
    """Request to preload backtest data"""
    symbols: list[str] = Field(..., description="List of symbols to preload (e.g., ['BTC/USDT', 'ETH/USDT'])")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    timeframe: str = Field(default="1h", description="Candle timeframe")
    exchange: str = Field(default="binance", description="Exchange name")


class PreloadResponse(BaseModel):
    """Preload result"""
    symbols_requested: int
    symbols_cached: int
    symbols_fetched: int
    errors: list[dict]


class InvalidateCacheRequest(BaseModel):
    """Request to invalidate cache"""
    symbol: Optional[str] = Field(None, description="Specific symbol (None = all)")
    exchange: Optional[str] = Field(None, description="Specific exchange (None = all)")


class SymbolItem(BaseModel):
    """Single symbol with base and full format"""
    symbol: str = Field(..., description="Base symbol (e.g., 'BTC')")
    full_symbol: str = Field(..., description="Full CCXT symbol (e.g., 'BTC/USDT:USDT')")


class SymbolsResponse(BaseModel):
    """Response for symbols endpoint"""
    exchange: str = Field(..., description="Exchange name")
    symbols: list[SymbolItem] = Field(..., description="List of available symbols")
    cached: bool = Field(..., description="Whether result was from cache")


# ==================== Routes ====================

@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats(
    user_id: CurrentUserDep,
):
    """
    Get cache statistics.

    Returns the number of cached entries for klines, prices, and symbols.
    """
    cache = get_market_data_cache()
    stats = await cache.get_cache_stats()

    if "error" in stats:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {stats['error']}"
        )

    return CacheStats(**stats)


@router.post("/cache/preload", response_model=PreloadResponse)
async def preload_backtest_data(
    data: PreloadRequest,
    user_id: CurrentUserDep,
):
    """
    Preload historical data for backtesting.

    This fetches and caches K-line data for the specified symbols and date range.
    Cached data will be used automatically in subsequent backtest runs.
    """
    try:
        start_date = datetime.strptime(data.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(data.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )

    # Initialize data provider for fetching
    from ...backtest.data_provider import DataProvider

    provider = DataProvider(exchange=data.exchange, use_cache=True)

    try:
        await provider.initialize()

        preloader = get_backtest_preloader()
        result = await preloader.preload_for_backtest(
            symbols=data.symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe=data.timeframe,
            exchange=data.exchange,
            data_provider=provider,
        )

        return PreloadResponse(**result)
    finally:
        await provider.close()


@router.post("/cache/preload/common", response_model=PreloadResponse)
async def preload_common_symbols(
    user_id: CurrentUserDep,
    exchange: str = "binance",
    timeframe: str = "1h",
    days: int = 30,
):
    """
    Preload data for commonly traded symbols.

    This is a convenience endpoint to warm up the cache with popular trading pairs.
    """
    from ...backtest.data_provider import DataProvider

    provider = DataProvider(exchange=exchange, use_cache=True)

    try:
        await provider.initialize()

        preloader = get_backtest_preloader()
        result = await preloader.preload_common_symbols(
            exchange=exchange,
            timeframe=timeframe,
            days_back=days,
            data_provider=provider,
        )

        return PreloadResponse(**result)
    finally:
        await provider.close()


@router.post("/cache/invalidate")
async def invalidate_cache(
    data: InvalidateCacheRequest,
    user_id: CurrentUserDep,
):
    """
    Invalidate cache entries.

    Can invalidate all entries or filter by symbol/exchange.
    """
    cache = get_market_data_cache()
    deleted = await cache.invalidate_klines(
        symbol=data.symbol,
        exchange=data.exchange,
    )

    return {
        "message": f"Invalidated {deleted} cache entries",
        "deleted": deleted,
    }


def _extract_base_symbol(full_symbol: str) -> str:
    """Extract base symbol from CCXT format (e.g., 'BTC/USDT:USDT' -> 'BTC')"""
    if "/" in full_symbol:
        return full_symbol.split("/")[0]
    return full_symbol


def _is_valid_perpetual(symbol: str, market: dict, exchange: str) -> bool:
    """Check if symbol is a valid perpetual contract for the exchange"""
    if market.get("type") != "swap":
        return False

    # Hyperliquid uses USDC, others use USDT
    if exchange.lower() == "hyperliquid":
        return "/USDC" in symbol
    return "/USDT" in symbol


@router.get("/symbols", response_model=SymbolsResponse)
async def get_available_symbols(
    user_id: CurrentUserDep,
    exchange: str = "binance",
):
    """
    Get list of available trading symbols.

    Returns symbols in both base format (e.g., 'BTC') and full CCXT format
    (e.g., 'BTC/USDT:USDT'). Results are cached for 24 hours.

    Supported exchanges: binance, okx, bybit, bitget, kucoin, gate, hyperliquid
    """
    cache = get_market_data_cache()

    # Try cache first (cached as list of full symbols)
    cached_symbols = await cache.get_symbols(exchange)
    if cached_symbols:
        symbol_items = [
            SymbolItem(symbol=_extract_base_symbol(s), full_symbol=s)
            for s in cached_symbols
        ]
        return SymbolsResponse(
            exchange=exchange,
            symbols=symbol_items,
            cached=True,
        )

    # Fetch from exchange
    from ...backtest.data_provider import DataProvider

    provider = DataProvider(exchange=exchange, use_cache=False)

    try:
        await provider.initialize()
        markets = await provider.get_available_markets()

        # Filter for perpetual contracts
        symbols = [
            s for s in markets.keys()
            if _is_valid_perpetual(s, markets[s], exchange)
        ]
        symbols.sort()

        # Cache the result (as list of full symbols for backward compatibility)
        await cache.set_symbols(symbols, exchange)

        # Convert to SymbolItem format
        symbol_items = [
            SymbolItem(symbol=_extract_base_symbol(s), full_symbol=s)
            for s in symbols
        ]

        return SymbolsResponse(
            exchange=exchange,
            symbols=symbol_items,
            cached=False,
        )
    finally:
        await provider.close()
