"""
MockTrader - Simulated trading with real-time market data.

Wraps SimulatedTrader with a public CCXT exchange connection
for live price feeds. Enables "paper trading" without exchange
credentials, using real market data for realistic simulation.

Usage:
    trader = MockTrader(initial_balance=10000.0, symbols=["BTC", "ETH"])
    await trader.initialize()
    state = await trader.get_account_state()  # fetches live prices first
    result = await trader.open_long("BTC", 1000, leverage=5)
"""

import logging
from datetime import UTC, datetime
from typing import Dict, List, Literal, Optional

import ccxt.async_support as ccxt

from ..core.config import get_ccxt_proxy_config
from .base import (
    AccountState,
    BaseTrader,
    FundingRate,
    MarketData,
    OHLCV,
    OrderResult,
    Position,
    TradeError,
    detect_market_type,
    MarketType,
)
from ..backtest.simulator import SimulatedTrader, SimulatedPosition

logger = logging.getLogger(__name__)


class MockTrader(BaseTrader):
    """
    Mock trader for paper-trading with real-time market data.

    Combines SimulatedTrader's execution engine with live CCXT
    public API prices. All trades execute against the simulator's
    in-memory state, but prices reflect the real market.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        symbols: Optional[List[str]] = None,
        exchange_id: str = "hyperliquid",  # more stable than binance
        maker_fee: float = 0.0002,
        taker_fee: float = 0.0005,
        default_slippage: float = 0.001,
    ):
        """
        Args:
            initial_balance: Starting virtual balance in USD.
            symbols: List of symbols to track (e.g. ["BTC", "ETH"]).
            exchange_id: CCXT exchange for public data (default: hyperliquid).
            maker_fee: Simulated maker fee rate.
            taker_fee: Simulated taker fee rate.
            default_slippage: Default slippage for market orders.
        """
        super().__init__(testnet=True, default_slippage=default_slippage)

        self._sim = SimulatedTrader(
            initial_balance=initial_balance,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            default_slippage=default_slippage,
        )
        self._symbols = [s.upper() for s in (symbols or ["BTC"])]
        self._exchange_id = exchange_id
        self._ccxt: Optional[ccxt.Exchange] = None
        self._last_prices: Dict[str, float] = {}

    @property
    def exchange_name(self) -> str:
        return "mock"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> bool:
        """Initialize public CCXT exchange connection."""
        try:
            exchange_class = getattr(ccxt, self._exchange_id, None)
            if exchange_class is None:
                logger.warning(
                    f"Unknown exchange '{self._exchange_id}', falling back to hyperliquid"
                )
                exchange_class = ccxt.hyperliquid

            self._ccxt = exchange_class({
                "enableRateLimit": True,
                "options": {"defaultType": "swap"},  # perpetual futures
                **get_ccxt_proxy_config(),  # proxy support for geo-restricted exchanges
            })

            # Warm up prices
            await self._refresh_prices()
            self._initialized = True
            logger.info(
                f"MockTrader initialized: balance=${self._sim.initial_balance:,.0f}, "
                f"symbols={self._symbols}, exchange={self._exchange_id}"
            )
            return True
        except Exception as e:
            logger.error(f"MockTrader initialization failed: {e}")
            # Still mark as initialized so we can fall back to cached prices
            self._initialized = True
            return True

    async def close(self) -> None:
        """Close CCXT connection."""
        if self._ccxt:
            try:
                await self._ccxt.close()
            except Exception:
                pass
            self._ccxt = None

    # ------------------------------------------------------------------
    # Price refresh
    # ------------------------------------------------------------------

    async def _refresh_prices(self) -> None:
        """Fetch latest prices from exchange public API for all tracked symbols."""
        if not self._ccxt:
            return

        for symbol in self._symbols:
            try:
                ccxt_symbol = self._to_ccxt_symbol(symbol)
                ticker = await self._ccxt.fetch_ticker(ccxt_symbol)
                if ticker and ticker.get("last"):
                    self._last_prices[symbol] = float(ticker["last"])
            except Exception as e:
                logger.debug(f"Failed to fetch price for {symbol}: {e}")

        if self._last_prices:
            self._sim.set_prices(self._last_prices)
            self._sim.set_current_time(datetime.now(UTC))

    def _to_ccxt_symbol(self, symbol: str) -> str:
        """Convert bare symbol to CCXT unified format."""
        symbol = symbol.upper().strip()

        mtype = detect_market_type(symbol)
        if mtype in (MarketType.FOREX, MarketType.METALS):
            return symbol if "/" in symbol else f"{symbol}/USD"

        # Already formatted
        if ":" in symbol:
            return symbol
        if "/" in symbol:
            return f"{symbol}:USDT"

        return f"{symbol}/USDT:USDT"

    # ------------------------------------------------------------------
    # Account Operations (delegated to SimulatedTrader)
    # ------------------------------------------------------------------

    async def get_account_state(self) -> AccountState:
        await self._refresh_prices()
        return await self._sim.get_account_state()

    async def get_positions(self) -> List[Position]:
        await self._refresh_prices()
        return await self._sim.get_positions()

    async def get_position(self, symbol: str) -> Optional[Position]:
        await self._refresh_prices()
        return await self._sim.get_position(symbol)

    # ------------------------------------------------------------------
    # Market Data (from public API)
    # ------------------------------------------------------------------

    async def get_market_price(self, symbol: str) -> float:
        """Get live market price."""
        symbol = symbol.upper().strip()

        # Try fetching live price
        if self._ccxt:
            try:
                ccxt_symbol = self._to_ccxt_symbol(symbol)
                ticker = await self._ccxt.fetch_ticker(ccxt_symbol)
                if ticker and ticker.get("last"):
                    price = float(ticker["last"])
                    self._last_prices[symbol] = price
                    self._sim.set_prices({symbol: price})
                    return price
            except Exception as e:
                logger.debug(f"Live price fetch failed for {symbol}: {e}")

        # Fallback to cached price
        if symbol in self._last_prices:
            return self._last_prices[symbol]

        raise TradeError(f"No price available for {symbol}")

    async def get_market_data(self, symbol: str) -> MarketData:
        """Get live market data."""
        symbol = symbol.upper().strip()

        if self._ccxt:
            try:
                ccxt_symbol = self._to_ccxt_symbol(symbol)
                ticker = await self._ccxt.fetch_ticker(ccxt_symbol)
                if ticker:
                    price = float(ticker.get("last", 0))
                    self._last_prices[symbol] = price
                    self._sim.set_prices({symbol: price})
                    return MarketData(
                        symbol=symbol,
                        mid_price=price,
                        bid_price=float(ticker.get("bid", price)),
                        ask_price=float(ticker.get("ask", price)),
                        volume_24h=float(ticker.get("quoteVolume", 0) or 0),
                        funding_rate=None,
                        timestamp=datetime.now(UTC),
                    )
            except Exception as e:
                logger.debug(f"Live market data fetch failed for {symbol}: {e}")

        # Fallback to simulator
        return await self._sim.get_market_data(symbol)

    async def get_klines(
        self, symbol: str, timeframe: str = "1h", limit: int = 100,
    ) -> list[OHLCV]:
        """Fetch K-line data from public API."""
        if not self._ccxt:
            return []

        ccxt_symbol = self._to_ccxt_symbol(symbol)
        try:
            data = await self._ccxt.fetch_ohlcv(
                ccxt_symbol, timeframe=timeframe, limit=min(limit, 1000),
            )
            if not data:
                return []
            return [OHLCV.from_ccxt(c) for c in data]
        except Exception as e:
            logger.warning(f"Failed to get klines for {symbol}: {e}")
            return []

    async def get_funding_history(
        self, symbol: str, limit: int = 24,
    ) -> list[FundingRate]:
        """Fetch funding rate history from public API."""
        if not self._ccxt:
            return []

        mtype = detect_market_type(symbol)
        if mtype in (MarketType.FOREX, MarketType.METALS):
            return []

        ccxt_symbol = self._to_ccxt_symbol(symbol)
        try:
            data = await self._ccxt.fetch_funding_rate_history(
                ccxt_symbol, limit=limit,
            )
            if not data:
                return []

            rates: list[FundingRate] = []
            for item in data:
                ts = item.get("timestamp") or item.get("datetime")
                if isinstance(ts, int):
                    timestamp = datetime.utcfromtimestamp(ts / 1000)
                elif isinstance(ts, str):
                    timestamp = datetime.fromisoformat(
                        ts.replace("Z", "+00:00").replace("+00:00", "")
                    )
                else:
                    timestamp = datetime.now(UTC)
                rate = float(item.get("fundingRate", 0) or 0)
                rates.append(FundingRate(timestamp=timestamp, rate=rate))

            rates.sort(key=lambda r: r.timestamp, reverse=True)
            return rates[:limit]
        except Exception as e:
            logger.warning(f"Failed to get funding history for {symbol}: {e}")
            return []

    # ------------------------------------------------------------------
    # Order Operations (delegated to SimulatedTrader with price refresh)
    # ------------------------------------------------------------------

    async def place_market_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        leverage: int = 1,
        reduce_only: bool = False,
        slippage: Optional[float] = None,
        price: Optional[float] = None,
    ) -> OrderResult:
        await self._refresh_prices()
        return await self._sim.place_market_order(
            symbol, side, size, leverage, reduce_only, slippage, price,
        )

    async def place_limit_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        price: float,
        leverage: int = 1,
        reduce_only: bool = False,
        post_only: bool = False,
    ) -> OrderResult:
        await self._refresh_prices()
        return await self._sim.place_limit_order(
            symbol, side, size, price, leverage, reduce_only, post_only,
        )

    async def place_stop_loss(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        return await self._sim.place_stop_loss(
            symbol, side, size, trigger_price, reduce_only,
        )

    async def place_take_profit(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        return await self._sim.place_take_profit(
            symbol, side, size, trigger_price, reduce_only,
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        return await self._sim.cancel_order(symbol, order_id)

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        return await self._sim.cancel_all_orders(symbol)

    async def close_position(
        self,
        symbol: str,
        size: Optional[float] = None,
        slippage: Optional[float] = None,
    ) -> OrderResult:
        await self._refresh_prices()
        return await self._sim.close_position(symbol, size, slippage)

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        return await self._sim.set_leverage(symbol, leverage)

    # ------------------------------------------------------------------
    # State Restoration (for persistence across restarts)
    # ------------------------------------------------------------------

    def restore_state(
        self,
        balance: float,
        positions: List[Dict],
    ) -> None:
        """
        Restore simulator state from persisted data (AgentPositionDB).

        Called on worker restart for mock agents to reconstruct
        SimulatedTrader's in-memory state.

        Args:
            balance: Reconstructed balance (initial_balance + sum(realized_pnl))
            positions: List of dicts with position data from AgentPositionDB
        """
        self._sim.balance = balance

        self._sim._positions.clear()
        for pos_data in positions:
            symbol = pos_data["symbol"].upper()
            self._sim._positions[symbol] = SimulatedPosition(
                symbol=symbol,
                side=pos_data["side"],
                size=pos_data["size"],
                entry_price=pos_data["entry_price"],
                leverage=pos_data.get("leverage", 1),
                opened_at=pos_data.get("opened_at", datetime.now(UTC)),
                stop_loss=pos_data.get("stop_loss"),
                take_profit=pos_data.get("take_profit"),
            )

        logger.info(
            f"MockTrader state restored: balance=${balance:,.2f}, "
            f"{len(positions)} open positions"
        )
