"""
Base trader abstract class.

Defines the interface for all exchange adapters.
Each exchange (Hyperliquid, Binance, etc.) implements this interface.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Literal, Optional

logger = logging.getLogger(__name__)


class MarketType(str, Enum):
    """Market / asset class type"""
    CRYPTO_PERP = "crypto_perp"    # Crypto perpetual futures (default)
    CRYPTO_SPOT = "crypto_spot"    # Crypto spot
    FOREX = "forex"                # Foreign exchange (EUR/USD, etc.)
    METALS = "metals"              # Precious metals (XAU/USD, XAG/USD)


# Well-known Forex major & minor pairs
FOREX_SYMBOLS: set[str] = {
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "NZD/USD",
    "USD/CAD", "EUR/GBP", "EUR/JPY", "GBP/JPY", "AUD/JPY", "EUR/AUD",
    "EUR/CHF", "GBP/CHF", "CAD/JPY", "NZD/JPY",
}

# Well-known metal pairs
METALS_SYMBOLS: set[str] = {
    "XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD",
}

# All known FX / metals base codes (used for quick detection)
_FX_BASES = {"EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"}
_METAL_BASES = {"XAU", "XAG", "XPT", "XPD"}


def detect_market_type(symbol: str) -> MarketType:
    """
    Heuristically determine the market type from a symbol string.

    Examples:
        "BTC" / "BTC/USDT:USDT" → CRYPTO_PERP
        "EUR/USD"                → FOREX
        "XAU/USD"                → METALS
    """
    s = symbol.upper().strip()

    # Exact match first
    if s in FOREX_SYMBOLS:
        return MarketType.FOREX
    if s in METALS_SYMBOLS:
        return MarketType.METALS

    # Check base part
    base = s.split("/")[0] if "/" in s else s
    if base in _FX_BASES:
        return MarketType.FOREX
    if base in _METAL_BASES:
        return MarketType.METALS

    # Default to crypto perpetuals
    return MarketType.CRYPTO_PERP


class OrderType(str, Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(str, Enum):
    """Order lifecycle status"""
    PENDING = "pending"          # Order created but not submitted
    SUBMITTED = "submitted"      # Order submitted to exchange
    OPEN = "open"                # Order accepted and open
    PARTIALLY_FILLED = "partially_filled"  # Partially executed
    FILLED = "filled"            # Fully executed
    CANCELLED = "cancelled"      # Cancelled by user
    REJECTED = "rejected"        # Rejected by exchange
    EXPIRED = "expired"          # Order expired
    FAILED = "failed"            # Failed to submit


class TradeError(Exception):
    """Trading error with context"""
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


@dataclass
class Position:
    """Current position information"""
    symbol: str
    side: Literal["long", "short"]
    size: float  # Contract size
    size_usd: float  # USD value
    entry_price: float
    mark_price: float
    leverage: int
    unrealized_pnl: float
    unrealized_pnl_percent: float
    liquidation_price: Optional[float] = None
    margin_used: float = 0.0
    
    @property
    def is_profitable(self) -> bool:
        return self.unrealized_pnl > 0


@dataclass
class AccountState:
    """Account state and balance information"""
    equity: float  # Total account value
    available_balance: float  # Available for trading
    total_margin_used: float
    unrealized_pnl: float
    positions: list[Position] = field(default_factory=list)
    
    @property
    def margin_usage_percent(self) -> float:
        if self.equity == 0:
            return 0.0
        return (self.total_margin_used / self.equity) * 100
    
    @property
    def position_count(self) -> int:
        return len(self.positions)


@dataclass
class OrderResult:
    """Order execution result"""
    success: bool
    order_id: Optional[str] = None
    filled_size: Optional[float] = None
    filled_price: Optional[float] = None
    status: str = ""
    error: Optional[str] = None
    raw_response: Optional[dict] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Order:
    """
    Complete order information for lifecycle tracking.
    
    Represents an order throughout its entire lifecycle, from
    creation to completion or cancellation.
    """
    order_id: str
    client_order_id: Optional[str]  # Client-provided ID for tracking
    symbol: str
    side: Literal["buy", "sell"]
    order_type: OrderType
    status: OrderStatus
    
    # Quantities
    size: float                      # Original order size
    filled_size: float = 0.0         # How much has been filled
    remaining_size: float = 0.0      # How much remains
    
    # Prices
    price: Optional[float] = None    # Limit price (if limit order)
    trigger_price: Optional[float] = None  # Stop/TP trigger price
    avg_fill_price: Optional[float] = None  # Average fill price
    
    # Flags
    reduce_only: bool = False
    post_only: bool = False
    leverage: int = 1
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Execution details
    fee: float = 0.0
    fee_currency: str = "USDT"
    
    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Raw exchange data
    raw_data: Optional[dict] = None
    
    @property
    def is_open(self) -> bool:
        """Check if order is still open (can be filled or cancelled)"""
        return self.status in (
            OrderStatus.SUBMITTED,
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        )
    
    @property
    def is_complete(self) -> bool:
        """Check if order has reached a terminal state"""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
            OrderStatus.FAILED,
        )
    
    @property
    def is_successful(self) -> bool:
        """Check if order was successfully filled (fully or partially)"""
        return self.status == OrderStatus.FILLED or (
            self.status == OrderStatus.CANCELLED and self.filled_size > 0
        )
    
    @property
    def fill_percent(self) -> float:
        """Get fill percentage"""
        if self.size == 0:
            return 0.0
        return (self.filled_size / self.size) * 100
    
    @property
    def can_retry(self) -> bool:
        """Check if order can be retried"""
        return (
            self.status == OrderStatus.FAILED and
            self.retry_count < self.max_retries
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization"""
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "size": self.size,
            "filled_size": self.filled_size,
            "remaining_size": self.remaining_size,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "avg_fill_price": self.avg_fill_price,
            "reduce_only": self.reduce_only,
            "post_only": self.post_only,
            "leverage": self.leverage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "fee": self.fee,
            "fee_currency": self.fee_currency,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Order":
        """Create Order from dictionary"""
        return cls(
            order_id=data["order_id"],
            client_order_id=data.get("client_order_id"),
            symbol=data["symbol"],
            side=data["side"],
            order_type=OrderType(data["order_type"]),
            status=OrderStatus(data["status"]),
            size=data["size"],
            filled_size=data.get("filled_size", 0.0),
            remaining_size=data.get("remaining_size", data["size"]),
            price=data.get("price"),
            trigger_price=data.get("trigger_price"),
            avg_fill_price=data.get("avg_fill_price"),
            reduce_only=data.get("reduce_only", False),
            post_only=data.get("post_only", False),
            leverage=data.get("leverage", 1),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now(UTC)),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.now(UTC)),
            filled_at=datetime.fromisoformat(data["filled_at"]) if data.get("filled_at") else None,
            cancelled_at=datetime.fromisoformat(data["cancelled_at"]) if data.get("cancelled_at") else None,
            fee=data.get("fee", 0.0),
            fee_currency=data.get("fee_currency", "USDT"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
        )


@dataclass
class MarketData:
    """Market data for a symbol"""
    symbol: str
    mid_price: float
    bid_price: float
    ask_price: float
    volume_24h: float
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class OHLCV:
    """
    Single K-line (candlestick) data.
    
    Represents one candle with open, high, low, close prices and volume.
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def change_percent(self) -> float:
        """Calculate percentage change from open to close"""
        if self.open == 0:
            return 0.0
        return ((self.close - self.open) / self.open) * 100
    
    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)"""
        return self.close > self.open
    
    @property
    def body_size(self) -> float:
        """Calculate candle body size"""
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self) -> float:
        """Calculate upper wick size"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        """Calculate lower wick size"""
        return min(self.open, self.close) - self.low
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
    
    @classmethod
    def from_ccxt(cls, data: list) -> "OHLCV":
        """
        Create OHLCV from CCXT format.
        
        CCXT format: [timestamp_ms, open, high, low, close, volume]
        """
        return cls(
            timestamp=datetime.utcfromtimestamp(data[0] / 1000),
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5]),
        )


@dataclass
class FundingRate:
    """Funding rate data point"""
    timestamp: datetime
    rate: float  # Funding rate as decimal (e.g., 0.0001 = 0.01%)
    
    @property
    def rate_percent(self) -> float:
        """Get rate as percentage"""
        return self.rate * 100
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "rate": self.rate,
            "rate_percent": self.rate_percent,
        }


class BaseTrader(ABC):
    """
    Abstract base class for exchange trading adapters.
    
    All exchange-specific implementations (Hyperliquid, Binance, etc.)
    must implement this interface.
    
    Usage:
        trader = CCXTTrader("hyperliquid", {"private_key": "0x..."}, testnet=True)
        await trader.initialize()
        account = await trader.get_account_state()
        result = await trader.place_market_order("ETH", "buy", 0.1, leverage=5)
    """
    
    def __init__(
        self,
        testnet: bool = True,
        default_slippage: float = 0.01,
    ):
        """
        Initialize trader.
        
        Args:
            testnet: Use testnet if True
            default_slippage: Default slippage tolerance (1% = 0.01)
        """
        self.testnet = testnet
        self.default_slippage = default_slippage
        self._initialized = False
    
    @property
    @abstractmethod
    def exchange_name(self) -> str:
        """Return exchange name (e.g., 'hyperliquid', 'binance')"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize connection to exchange.
        
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connection and cleanup"""
        pass
    
    # ==================== Account Operations ====================
    
    @abstractmethod
    async def get_account_state(self) -> AccountState:
        """
        Get current account state including balance and positions.
        
        Returns:
            AccountState with equity, positions, etc.
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """
        Get all open positions.
        
        Returns:
            List of Position objects
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for a specific symbol.
        
        Args:
            symbol: Trading symbol (e.g., "ETH")
            
        Returns:
            Position if exists, None otherwise
        """
        pass
    
    # ==================== Market Data ====================
    
    @abstractmethod
    async def get_market_price(self, symbol: str) -> float:
        """
        Get current mid price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current mid price
        """
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> MarketData:
        """
        Get full market data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            MarketData with prices, volume, funding, etc.
        """
        pass
    
    # ==================== K-line / OHLCV Data ====================
    
    async def get_klines(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> list:
        """
        Get K-line (candlestick) data for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            timeframe: Candle timeframe ("1m", "5m", "15m", "1h", "4h", "1d")
            limit: Number of candles to fetch (default: 100)
            
        Returns:
            List of OHLCV objects
            
        Note: Default implementation returns empty list. Override in subclasses
        that support K-line data fetching.
        """
        return []
    
    async def get_funding_history(
        self,
        symbol: str,
        limit: int = 24,
    ) -> list:
        """
        Get funding rate history for a perpetual contract.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            limit: Number of funding rate records to fetch (default: 24 = ~8 days)
            
        Returns:
            List of FundingRate objects (most recent first)
            
        Note: Default implementation returns empty list. Override in subclasses
        that support funding rate history.
        """
        return []
    
    async def get_open_interest(
        self,
        symbol: str,
    ) -> Optional[float]:
        """
        Get current open interest for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Open interest value or None if not available
            
        Note: Default implementation returns None. Override in subclasses
        that support open interest data.
        """
        return None
    
    # ==================== Order Operations ====================
    
    @abstractmethod
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
        """
        Place a market order.
        
        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            size: Order size in contracts
            leverage: Leverage multiplier
            reduce_only: If True, only reduces existing position
            slippage: Slippage tolerance (default uses self.default_slippage)
            
        Returns:
            OrderResult with execution details
        """
        pass
    
    @abstractmethod
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
        """
        Place a limit order.
        
        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            size: Order size
            price: Limit price
            leverage: Leverage multiplier
            reduce_only: If True, only reduces existing position
            post_only: If True, only posts to orderbook (no taker)
            
        Returns:
            OrderResult with order details
        """
        pass
    
    @abstractmethod
    async def place_stop_loss(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        """
        Place a stop loss order.
        
        Args:
            symbol: Trading symbol
            side: "buy" or "sell" (opposite of position)
            size: Order size
            trigger_price: Price at which to trigger
            reduce_only: Usually True for stop loss
            
        Returns:
            OrderResult
        """
        pass
    
    @abstractmethod
    async def place_take_profit(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        """
        Place a take profit order.
        
        Args:
            symbol: Trading symbol
            side: "buy" or "sell" (opposite of position)
            size: Order size
            trigger_price: Price at which to trigger
            reduce_only: Usually True for take profit
            
        Returns:
            OrderResult
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        pass
    
    @abstractmethod
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """
        Cancel all open orders.
        
        Args:
            symbol: If provided, only cancel orders for this symbol
            
        Returns:
            Number of orders cancelled
        """
        pass
    
    # ==================== Order Tracking ====================
    
    async def get_order(self, symbol: str, order_id: str) -> Optional[Order]:
        """
        Get order information by ID.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID
            
        Returns:
            Order object if found, None otherwise
            
        Note: Default implementation returns None. Override in subclasses
        that support order tracking.
        """
        return None
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> list[Order]:
        """
        Get all open orders.
        
        Args:
            symbol: If provided, only return orders for this symbol
            
        Returns:
            List of open Order objects
            
        Note: Default implementation returns empty list. Override in subclasses
        that support order tracking.
        """
        return []
    
    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
    ) -> list[Order]:
        """
        Get historical orders.
        
        Args:
            symbol: If provided, only return orders for this symbol
            limit: Maximum number of orders to return
            
        Returns:
            List of Order objects (most recent first)
            
        Note: Default implementation returns empty list. Override in subclasses
        that support order history.
        """
        return []
    
    async def wait_for_fill(
        self,
        symbol: str,
        order_id: str,
        timeout_seconds: float = 30.0,
        poll_interval: float = 1.0,
    ) -> Order:
        """
        Wait for an order to fill or reach terminal state.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to wait for
            timeout_seconds: Maximum time to wait
            poll_interval: Time between status checks
            
        Returns:
            Final Order state
            
        Raises:
            TradeError: If order not found or timeout exceeded
        """
        import asyncio
        
        start_time = datetime.now(UTC)
        timeout = timeout_seconds
        
        while True:
            order = await self.get_order(symbol, order_id)
            
            if order is None:
                raise TradeError(
                    f"Order {order_id} not found",
                    code="ORDER_NOT_FOUND",
                )
            
            if order.is_complete:
                return order
            
            elapsed = (datetime.now(UTC) - start_time).total_seconds()
            if elapsed >= timeout:
                raise TradeError(
                    f"Timeout waiting for order {order_id} to fill",
                    code="ORDER_TIMEOUT",
                    details={"order": order.to_dict()},
                )
            
            await asyncio.sleep(poll_interval)
    
    # ==================== Position Operations ====================
    
    @abstractmethod
    async def close_position(
        self,
        symbol: str,
        size: Optional[float] = None,
        slippage: Optional[float] = None,
    ) -> OrderResult:
        """
        Close a position (fully or partially).
        
        Args:
            symbol: Trading symbol
            size: Size to close (None = close all)
            slippage: Slippage tolerance
            
        Returns:
            OrderResult
        """
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a symbol.
        
        Args:
            symbol: Trading symbol
            leverage: Leverage multiplier
            
        Returns:
            True if successful
        """
        pass
    
    # ==================== Utility Methods ====================
    
    async def open_long(
        self,
        symbol: str,
        size_usd: float,
        leverage: int = 1,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> OrderResult:
        """
        Convenience method to open a long position with optional SL/TP.
        
        Args:
            symbol: Trading symbol
            size_usd: Position size in USD (notional value)
            leverage: Leverage multiplier
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            
        Returns:
            OrderResult for the entry order
        """
        # Get current price to calculate size
        price = await self.get_market_price(symbol)
        if not price or price <= 0:
            raise TradeError(
                f"Invalid market price for {symbol}: {price}",
                code="INVALID_PRICE",
            )
        size = size_usd / price
        
        # Set leverage
        await self.set_leverage(symbol, leverage)
        
        # Place entry order (pass price so Hyperliquid can calculate slippage
        # without an extra fetch_ticker call)
        result = await self.place_market_order(symbol, "buy", size, leverage, price=price)
        
        if result.success and result.filled_size:
            filled_price = result.filled_price or price
            adjusted_sl = stop_loss
            adjusted_tp = take_profit

            # Validate SL/TP relative to actual fill price
            # For LONG: SL < filled_price, TP > filled_price
            if stop_loss and stop_loss >= filled_price:
                # Calculate SL based on leverage to avoid liquidation
                # SL should be placed before liquidation price
                # Liquidation price for long = entry * (1 - 1/leverage)
                # Use 50% of max loss to stay safe
                max_loss_pct = 0.5 / leverage  # 50% of margin
                adjusted_sl = filled_price * (1 - max_loss_pct)
                logger.warning(
                    f"[open_long] Invalid stop_loss {stop_loss} >= fill_price {filled_price} "
                    f"for {symbol} (leverage={leverage}x), adjusted to {adjusted_sl:.2f} "
                    f"(liquidation at {filled_price * (1 - 1/leverage):.2f})"
                )
            if take_profit and take_profit <= filled_price:
                # Calculate TP based on risk-reward ratio (1:1.5)
                # Use the SL distance to determine TP distance
                sl_distance = (filled_price - (adjusted_sl or filled_price * 0.99)) / filled_price
                risk_reward_ratio = 1.5
                adjusted_tp = filled_price * (1 + sl_distance * risk_reward_ratio)
                logger.warning(
                    f"[open_long] Invalid take_profit {take_profit} <= fill_price {filled_price} "
                    f"for {symbol}, adjusted to {adjusted_tp:.2f} (RR={risk_reward_ratio})"
                )

            # Place SL/TP if specified — errors must not affect the main order
            if adjusted_sl:
                try:
                    await self.place_stop_loss(symbol, "sell", result.filled_size, adjusted_sl)
                except Exception as e:
                    logger.error(
                        f"[open_long] Failed to place stop-loss for {symbol} "
                        f"at {adjusted_sl}: {e}  (entry order succeeded)"
                    )
            if adjusted_tp:
                try:
                    await self.place_take_profit(symbol, "sell", result.filled_size, adjusted_tp)
                except Exception as e:
                    logger.error(
                        f"[open_long] Failed to place take-profit for {symbol} "
                        f"at {adjusted_tp}: {e}  (entry order succeeded)"
                    )

        return result
    
    async def open_short(
        self,
        symbol: str,
        size_usd: float,
        leverage: int = 1,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> OrderResult:
        """
        Convenience method to open a short position with optional SL/TP.
        """
        price = await self.get_market_price(symbol)
        if not price or price <= 0:
            raise TradeError(
                f"Invalid market price for {symbol}: {price}",
                code="INVALID_PRICE",
            )
        size = size_usd / price
        
        await self.set_leverage(symbol, leverage)
        
        # Pass price so Hyperliquid can calculate slippage without an extra
        # fetch_ticker call
        result = await self.place_market_order(symbol, "sell", size, leverage, price=price)
        
        if result.success and result.filled_size:
            filled_price = result.filled_price or price
            adjusted_sl = stop_loss
            adjusted_tp = take_profit

            # Validate SL/TP relative to actual fill price
            # For SHORT: SL > filled_price, TP < filled_price
            if stop_loss and stop_loss <= filled_price:
                # Calculate SL based on leverage to avoid liquidation
                # Liquidation price for short = entry * (1 + 1/leverage)
                # Use 50% of max loss to stay safe
                max_loss_pct = 0.5 / leverage  # 50% of margin
                adjusted_sl = filled_price * (1 + max_loss_pct)
                logger.warning(
                    f"[open_short] Invalid stop_loss {stop_loss} <= fill_price {filled_price} "
                    f"for {symbol} (leverage={leverage}x), adjusted to {adjusted_sl:.2f} "
                    f"(liquidation at {filled_price * (1 + 1/leverage):.2f})"
                )
            if take_profit and take_profit >= filled_price:
                # Calculate TP based on risk-reward ratio (1:1.5)
                sl_distance = ((adjusted_sl or filled_price * 1.01) - filled_price) / filled_price
                risk_reward_ratio = 1.5
                adjusted_tp = filled_price * (1 - sl_distance * risk_reward_ratio)
                logger.warning(
                    f"[open_short] Invalid take_profit {take_profit} >= fill_price {filled_price} "
                    f"for {symbol}, adjusted to {adjusted_tp:.2f} (RR={risk_reward_ratio})"
                )

            # Place SL/TP if specified — errors must not affect the main order
            if adjusted_sl:
                try:
                    await self.place_stop_loss(symbol, "buy", result.filled_size, adjusted_sl)
                except Exception as e:
                    logger.error(
                        f"[open_short] Failed to place stop-loss for {symbol} "
                        f"at {adjusted_sl}: {e}  (entry order succeeded)"
                    )
            if adjusted_tp:
                try:
                    await self.place_take_profit(symbol, "buy", result.filled_size, adjusted_tp)
                except Exception as e:
                    logger.error(
                        f"[open_short] Failed to place take-profit for {symbol} "
                        f"at {adjusted_tp}: {e}  (entry order succeeded)"
                    )

        return result
    
    def _validate_symbol(self, symbol: str) -> str:
        """Normalize and validate symbol"""
        return symbol.upper().strip()
    
    def _ensure_initialized(self) -> None:
        """Ensure trader is initialized"""
        if not self._initialized:
            raise TradeError("Trader not initialized. Call initialize() first.")
