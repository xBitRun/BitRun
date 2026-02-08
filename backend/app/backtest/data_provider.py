"""
Historical data provider for backtesting.

Supports multiple data sources:
- CCXT (exchange historical data)
- Redis cache (for faster repeated access)
- CSV files
- Database storage
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

import ccxt.async_support as ccxt

from ..services.market_data_cache import get_market_data_cache

logger = logging.getLogger(__name__)


@dataclass
class OHLCV:
    """OHLCV candle data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def mid(self) -> float:
        """Mid price (average of OHLC)"""
        return (self.open + self.high + self.low + self.close) / 4

    @property
    def typical(self) -> float:
        """Typical price (HLC average)"""
        return (self.high + self.low + self.close) / 3

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass
class MarketSnapshot:
    """Market snapshot at a point in time"""
    timestamp: datetime
    prices: Dict[str, float]  # symbol -> price
    candles: Dict[str, OHLCV] = field(default_factory=dict)  # symbol -> latest candle

    def get_price(self, symbol: str) -> Optional[float]:
        return self.prices.get(symbol)


class DataProvider:
    """
    Historical data provider for backtesting.

    Fetches and caches OHLCV data from exchanges.

    Usage:
        provider = DataProvider()
        await provider.load_data(
            symbols=["BTC", "ETH"],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            timeframe="1h"
        )

        for snapshot in provider.iterate():
            price = snapshot.get_price("BTC")
    """

    TIMEFRAME_MS = {
        "1m": 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
    }

    def __init__(
        self,
        exchange: str = "hyperliquid",
        data_dir: Optional[str] = None,
        use_cache: bool = True,
    ):
        """
        Initialize data provider.

        Args:
            exchange: Exchange to fetch data from
            data_dir: Directory to cache data (optional)
            use_cache: Whether to use Redis cache for data
        """
        self.exchange_name = exchange
        self.data_dir = data_dir
        self.use_cache = use_cache
        self._exchange: Optional[ccxt.Exchange] = None
        self._data: Dict[str, List[OHLCV]] = {}  # symbol -> list of candles
        self._snapshots: List[MarketSnapshot] = []
        self._cache = get_market_data_cache() if use_cache else None

    # Exchanges supported for backtesting (public OHLCV data, no API key needed)
    SUPPORTED_EXCHANGES = ("binance", "bybit", "okx", "hyperliquid")

    async def initialize(self) -> None:
        """Initialize exchange connection"""
        from ..core.config import get_ccxt_proxy_config

        proxy_cfg = get_ccxt_proxy_config()
        exchange_factories = {
            "binance": lambda: ccxt.binance({"enableRateLimit": True, **proxy_cfg}),
            "bybit": lambda: ccxt.bybit({"enableRateLimit": True, **proxy_cfg}),
            "okx": lambda: ccxt.okx({"enableRateLimit": True, **proxy_cfg}),
            "hyperliquid": lambda: ccxt.hyperliquid({"enableRateLimit": True, **proxy_cfg}),
        }

        factory = exchange_factories.get(self.exchange_name)
        if not factory:
            raise ValueError(
                f"Unsupported exchange for backtesting: {self.exchange_name}. "
                f"Supported: {', '.join(self.SUPPORTED_EXCHANGES)}"
            )

        self._exchange = factory()
        await self._exchange.load_markets()

    async def close(self) -> None:
        """Close exchange connection"""
        if self._exchange:
            await self._exchange.close()

    async def get_available_markets(self) -> Dict[str, Any]:
        """
        Get available markets from the exchange.

        Returns:
            Dictionary of market information keyed by symbol
        """
        if not self._exchange:
            await self.initialize()
        return self._exchange.markets

    async def load_data(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1h",
    ) -> int:
        """
        Load historical data for symbols.

        Args:
            symbols: List of symbols to load
            start_date: Start date
            end_date: End date
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)

        Returns:
            Total number of candles loaded
        """
        if not self._exchange:
            await self.initialize()

        self._data.clear()
        total_candles = 0

        for symbol in symbols:
            ccxt_symbol = self._normalize_symbol(symbol)

            try:
                # Try cache first
                candles = None
                if self._cache:
                    cached_data = await self._cache.get_klines(
                        symbol=symbol,
                        timeframe=timeframe,
                        start_time=start_date,
                        end_time=end_date,
                        exchange=self.exchange_name,
                    )
                    if cached_data:
                        candles = [OHLCV(
                            timestamp=datetime.fromisoformat(c["timestamp"]),
                            open=c["open"],
                            high=c["high"],
                            low=c["low"],
                            close=c["close"],
                            volume=c["volume"],
                        ) for c in cached_data]
                        logger.debug(f"Loaded {len(candles)} cached candles for {symbol}")

                # Fetch from exchange if not cached
                if not candles:
                    candles = await self._fetch_ohlcv(
                        ccxt_symbol, timeframe, start_date, end_date
                    )

                    # Cache the data
                    if self._cache and candles:
                        await self._cache.set_klines(
                            symbol=symbol,
                            timeframe=timeframe,
                            start_time=start_date,
                            end_time=end_date,
                            klines=[c.to_dict() for c in candles],
                            exchange=self.exchange_name,
                        )
                        logger.debug(f"Cached {len(candles)} candles for {symbol}")

                self._data[symbol] = candles
                total_candles += len(candles)
            except Exception as e:
                logger.warning(f"Failed to load data for {symbol}: {e}")
                continue

        # Build snapshots
        self._build_snapshots()

        return total_candles

    async def _fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[OHLCV]:
        """Fetch OHLCV data from exchange"""
        candles = []
        since = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)
        limit = 1000  # Most exchanges limit to 1000 candles per request

        while since < end_ms:
            try:
                raw_candles = await self._exchange.fetch_ohlcv(
                    symbol, timeframe, since=since, limit=limit
                )

                if not raw_candles:
                    break

                for c in raw_candles:
                    ts = datetime.utcfromtimestamp(c[0] / 1000)
                    if ts > end_date:
                        break

                    candles.append(OHLCV(
                        timestamp=ts,
                        open=float(c[1]),
                        high=float(c[2]),
                        low=float(c[3]),
                        close=float(c[4]),
                        volume=float(c[5]),
                    ))

                # Move to next batch
                since = raw_candles[-1][0] + self.TIMEFRAME_MS.get(timeframe, 3600000)

                # Rate limiting
                import asyncio
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching OHLCV for {symbol}: {e}")
                break

        return candles

    def _build_snapshots(self) -> None:
        """Build market snapshots from candle data"""
        self._snapshots.clear()

        if not self._data:
            return

        # Get all unique timestamps
        all_timestamps = set()
        for candles in self._data.values():
            for c in candles:
                all_timestamps.add(c.timestamp)

        # Sort timestamps
        sorted_timestamps = sorted(all_timestamps)

        # Build snapshots
        for ts in sorted_timestamps:
            prices = {}
            candles = {}

            for symbol, symbol_candles in self._data.items():
                # Find candle for this timestamp
                for c in symbol_candles:
                    if c.timestamp == ts:
                        prices[symbol] = c.close
                        candles[symbol] = c
                        break
                    elif c.timestamp > ts:
                        break

            if prices:  # Only add if we have at least one price
                self._snapshots.append(MarketSnapshot(
                    timestamp=ts,
                    prices=prices,
                    candles=candles,
                ))

    def iterate(self) -> List[MarketSnapshot]:
        """Get all market snapshots for iteration"""
        return self._snapshots

    def get_data(self, symbol: str) -> List[OHLCV]:
        """Get raw OHLCV data for a symbol"""
        return self._data.get(symbol, [])

    def get_symbols(self) -> List[str]:
        """Get list of loaded symbols"""
        return list(self._data.keys())

    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get date range of loaded data"""
        if not self._snapshots:
            return None, None
        return self._snapshots[0].timestamp, self._snapshots[-1].timestamp

    # Preferred quote currencies in priority order (no need to hardcode per-exchange)
    PREFERRED_QUOTES = ("USDT", "USDC")

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to CCXT format.

        Dynamically searches loaded markets by base currency, preferring
        swap/perp markets with stablecoin quotes.  This works for any
        exchange regardless of which quote currency it uses (e.g. Hyperliquid
        uses USDC, Binance/Bybit/OKX use USDT).

        Priority: swap > spot, USDT > USDC > other quotes.
        """
        symbol = symbol.upper().strip()
        if "/" in symbol:
            return symbol

        # Dynamically find best match from loaded markets
        if self._exchange and self._exchange.markets:
            best: str | None = None
            best_priority = (99, 99)  # (type_rank, quote_rank)

            for mkt_symbol, mkt in self._exchange.markets.items():
                if mkt.get("base") != symbol:
                    continue

                mkt_type = mkt.get("type", "")
                quote = mkt.get("quote", "")

                # type rank: swap/perp preferred for backtesting
                type_rank = 0 if mkt_type == "swap" else (1 if mkt_type == "spot" else 2)
                # quote rank: preferred stablecoins first
                try:
                    quote_rank = self.PREFERRED_QUOTES.index(quote)
                except ValueError:
                    quote_rank = len(self.PREFERRED_QUOTES)

                priority = (type_rank, quote_rank)
                if priority < best_priority:
                    best_priority = priority
                    best = mkt_symbol

            if best:
                return best

        # Fallback when markets not loaded
        return f"{symbol}/USDT"

    @staticmethod
    def from_csv(filepath: str, symbol: str) -> "DataProvider":
        """
        Load data from CSV file.

        Expected format: timestamp,open,high,low,close,volume
        """
        import csv

        provider = DataProvider()
        candles = []

        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                candles.append(OHLCV(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                ))

        provider._data[symbol] = candles
        provider._build_snapshots()

        return provider
