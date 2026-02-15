"""
Tests for trading adapters with mocked exchange APIs.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime

from app.traders.base import (
    BaseTrader,
    AccountState,
    MarketData,
    Position,
    OrderResult,
    TradeError,
)


class TestBaseTrader:
    """Tests for BaseTrader abstract class."""

    def test_base_trader_is_abstract(self):
        """Test that BaseTrader cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseTrader()


class MockTrader(BaseTrader):
    """Mock trader implementation for testing."""

    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self._initialized = False
        self._positions = []
        self._balance = 10000.0

    @property
    def exchange_name(self) -> str:
        return "mock"

    async def initialize(self) -> bool:
        self._initialized = True
        return True

    async def close(self) -> None:
        pass

    async def get_account_state(self) -> AccountState:
        total_unrealized = sum(p.unrealized_pnl for p in self._positions)
        margin_used = sum(
            abs(p.size * p.entry_price) / p.leverage
            for p in self._positions
        )
        return AccountState(
            equity=self._balance + total_unrealized,
            available_balance=self._balance - margin_used,
            total_margin_used=margin_used,
            unrealized_pnl=total_unrealized,
            positions=self._positions,
        )

    async def get_positions(self) -> list[Position]:
        return self._positions

    async def get_position(self, symbol: str):
        for p in self._positions:
            if p.symbol == symbol:
                return p
        return None

    async def get_market_price(self, symbol: str) -> float:
        return 50000.0

    async def get_market_data(self, symbol: str) -> MarketData:
        return MarketData(
            symbol=symbol,
            mid_price=50000.0,
            bid_price=49990.0,
            ask_price=50010.0,
            volume_24h=1000000000.0,
            timestamp=datetime.now(UTC),
        )

    async def open_long(
        self,
        symbol: str,
        size: float,
        leverage: int,
        stop_loss: float = None,
        take_profit: float = None,
    ) -> OrderResult:
        position = Position(
            symbol=symbol,
            side="long",
            size=size,
            size_usd=size * 50000.0,
            entry_price=50000.0,
            mark_price=50000.0,
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
            leverage=leverage,
        )
        self._positions.append(position)
        return OrderResult(
            success=True,
            order_id=f"order_{len(self._positions)}",
            filled_size=size,
            filled_price=50000.0,
            status="filled",
        )

    async def open_short(
        self,
        symbol: str,
        size: float,
        leverage: int,
        stop_loss: float = None,
        take_profit: float = None,
    ) -> OrderResult:
        position = Position(
            symbol=symbol,
            side="short",
            size=size,
            size_usd=size * 50000.0,
            entry_price=50000.0,
            mark_price=50000.0,
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
            leverage=leverage,
        )
        self._positions.append(position)
        return OrderResult(
            success=True,
            order_id=f"order_{len(self._positions)}",
            filled_size=size,
            filled_price=50000.0,
            status="filled",
        )

    async def close_position(self, symbol: str, size: float = None) -> OrderResult:
        self._positions = [p for p in self._positions if p.symbol != symbol]
        return OrderResult(
            success=True,
            order_id="close_order",
            filled_size=0.0,
            filled_price=50000.0,
            status="filled",
        )

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        size: float,
        leverage: int = 1,
    ) -> OrderResult:
        if side == "buy":
            return await self.open_long(symbol, size, leverage)
        else:
            return await self.open_short(symbol, size, leverage)

    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        leverage: int = 1,
    ) -> OrderResult:
        return OrderResult(
            success=True,
            order_id="limit_order",
            filled_size=size,
            filled_price=price,
            status="pending",
        )

    async def place_stop_loss(
        self,
        symbol: str,
        side: str,
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        return OrderResult(
            success=True,
            order_id="stop_loss_order",
            status="open",
        )

    async def place_take_profit(
        self,
        symbol: str,
        side: str,
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        return OrderResult(
            success=True,
            order_id="take_profit_order",
            status="open",
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        return True

    async def cancel_all_orders(self, symbol: str = None) -> int:
        return 0

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        return True


class TestMockTrader:
    """Tests using MockTrader."""

    @pytest_asyncio.fixture
    async def trader(self):
        """Create and initialize mock trader."""
        trader = MockTrader(testnet=True)
        await trader.initialize()
        return trader

    @pytest.mark.asyncio
    async def test_initialize(self, trader):
        """Test trader initialization."""
        assert trader._initialized is True

    @pytest.mark.asyncio
    async def test_get_account_state_initial(self, trader):
        """Test getting initial account state."""
        state = await trader.get_account_state()

        assert state.equity == 10000.0
        assert state.available_balance == 10000.0
        assert state.total_margin_used == 0.0
        assert state.unrealized_pnl == 0.0
        assert len(state.positions) == 0

    @pytest.mark.asyncio
    async def test_open_long(self, trader):
        """Test opening a long position."""
        result = await trader.open_long(
            symbol="BTC",
            size=0.1,
            leverage=5,
        )

        assert result.success is True
        assert result.filled_size == 0.1
        assert result.filled_price == 50000.0
        assert result.status == "filled"

        positions = await trader.get_positions()
        assert len(positions) == 1
        assert positions[0].side == "long"

    @pytest.mark.asyncio
    async def test_open_short(self, trader):
        """Test opening a short position."""
        result = await trader.open_short(
            symbol="ETH",
            size=1.0,
            leverage=3,
        )

        assert result.success is True
        assert result.filled_size == 1.0
        assert result.filled_price == 50000.0

        positions = await trader.get_positions()
        assert len(positions) == 1
        assert positions[0].side == "short"

    @pytest.mark.asyncio
    async def test_close_position(self, trader):
        """Test closing a position."""
        # Open position first
        await trader.open_long("BTC", 0.1, 5)
        positions = await trader.get_positions()
        assert len(positions) == 1

        # Close it
        result = await trader.close_position("BTC")
        assert result.success is True

        positions = await trader.get_positions()
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_account_state_with_position(self, trader):
        """Test account state updates with position."""
        await trader.open_long("BTC", 0.1, 5)

        state = await trader.get_account_state()

        # Margin should be used
        assert state.total_margin_used > 0
        assert state.available_balance < trader._balance

    @pytest.mark.asyncio
    async def test_get_market_data(self, trader):
        """Test getting market data."""
        data = await trader.get_market_data("BTC")

        assert data.symbol == "BTC"
        assert data.mid_price > 0
        assert data.volume_24h > 0
        assert data.timestamp is not None

    @pytest.mark.asyncio
    async def test_multiple_positions(self, trader):
        """Test managing multiple positions."""
        await trader.open_long("BTC", 0.1, 5)
        await trader.open_short("ETH", 1.0, 3)
        await trader.open_long("SOL", 10.0, 2)

        positions = await trader.get_positions()
        assert len(positions) == 3

        # Close one
        await trader.close_position("ETH")
        positions = await trader.get_positions()
        assert len(positions) == 2

        # Verify remaining positions
        symbols = [p.symbol for p in positions]
        assert "BTC" in symbols
        assert "SOL" in symbols
        assert "ETH" not in symbols


class TestCCXTTraderMocked:
    """Tests for CCXTTrader with mocked CCXT exchange."""

    @pytest.mark.asyncio
    async def test_ccxt_trader_initialization(self):
        """Test CCXTTrader initialization with mocked CCXT exchange."""
        from app.traders.ccxt_trader import CCXTTrader

        mock_exchange = MagicMock()
        mock_exchange.load_markets = AsyncMock()
        mock_exchange.set_sandbox_mode = MagicMock()

        with patch("app.traders.ccxt_trader.ExchangePool") as mock_pool:
            mock_pool.acquire = AsyncMock(return_value=mock_exchange)

            trader = CCXTTrader(
                exchange_id="bybit",
                credentials={"api_key": "test_key", "api_secret": "test_secret"},
                testnet=True,
            )

            await trader.initialize()

            mock_pool.acquire.assert_called_once()
            assert trader._initialized is True

    @pytest.mark.asyncio
    async def test_ccxt_trader_hyperliquid_initialization(self):
        """Test CCXTTrader for Hyperliquid with mocked CCXT exchange."""
        from app.traders.ccxt_trader import CCXTTrader

        mock_exchange = MagicMock()
        mock_exchange.load_markets = AsyncMock()
        mock_exchange.set_sandbox_mode = MagicMock()

        with patch("app.traders.ccxt_trader.ExchangePool") as mock_pool:
            mock_pool.acquire = AsyncMock(return_value=mock_exchange)

            trader = CCXTTrader(
                exchange_id="hyperliquid",
                credentials={"private_key": "0x" + "a" * 64},
                testnet=True,
            )

            await trader.initialize()

            mock_pool.acquire.assert_called_once()
            assert trader._initialized is True

    @pytest.mark.asyncio
    async def test_ccxt_trader_close(self):
        """Test CCXTTrader close cleans up."""
        from app.traders.ccxt_trader import CCXTTrader

        mock_exchange = MagicMock()
        mock_exchange.load_markets = AsyncMock()
        mock_exchange.close = AsyncMock()
        mock_exchange.set_sandbox_mode = MagicMock()

        with patch("app.traders.ccxt_trader.ExchangePool") as mock_pool:
            mock_pool.acquire = AsyncMock(return_value=mock_exchange)
            mock_pool.release = MagicMock()

            trader = CCXTTrader(
                exchange_id="okx",
                credentials={"api_key": "k", "api_secret": "s", "passphrase": "p"},
                testnet=True,
            )

            await trader.initialize()
            await trader.close()

            mock_pool.release.assert_called_once()
            assert trader._initialized is False


class TestCCXTTraderExceptions:
    """Tests for CCXTTrader exception handling with mocked ccxt errors."""

    @pytest.fixture
    def _make_trader(self):
        """Factory to create CCXTTrader with mocked exchange."""
        import ccxt
        from app.traders.ccxt_trader import CCXTTrader

        async def _factory():
            mock_exchange = MagicMock()
            mock_exchange.load_markets = AsyncMock()
            mock_exchange.set_sandbox_mode = MagicMock()
            mock_exchange.set_leverage = AsyncMock()
            mock_exchange.markets = {"BTC/USDT:USDT": {"limits": {"amount": {"min": 0.001}}, "precision": {"amount": 3}}}
            mock_exchange.market = MagicMock(return_value={"limits": {"amount": {"min": 0.001}}, "precision": {"amount": 3}})
            mock_exchange.amount_to_precision = MagicMock(side_effect=lambda s, a: a)

            with patch("app.traders.ccxt_trader.ExchangePool") as mock_pool:
                mock_pool.acquire = AsyncMock(return_value=mock_exchange)
                trader = CCXTTrader(
                    exchange_id="bybit",
                    credentials={"api_key": "k", "api_secret": "s"},
                    testnet=True,
                )
                await trader.initialize()
            return trader, mock_exchange

        return _factory

    @pytest.mark.asyncio
    async def test_auth_error_on_initialize(self):
        """ccxt.AuthenticationError during initialize raises TradeError."""
        import ccxt as ccxt_lib
        from app.traders.ccxt_trader import CCXTTrader

        with patch("app.traders.ccxt_trader.ExchangePool") as mock_pool:
            mock_pool.acquire = AsyncMock(
                side_effect=ccxt_lib.AuthenticationError("Invalid API key")
            )
            trader = CCXTTrader(
                exchange_id="bybit",
                credentials={"api_key": "bad", "api_secret": "bad"},
                testnet=True,
            )
            with pytest.raises(TradeError) as exc_info:
                await trader.initialize()
            assert "authentication" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_exchange_error_on_initialize(self):
        """ccxt.ExchangeError during initialize raises TradeError."""
        import ccxt as ccxt_lib
        from app.traders.ccxt_trader import CCXTTrader

        with patch("app.traders.ccxt_trader.ExchangePool") as mock_pool:
            mock_pool.acquire = AsyncMock(
                side_effect=ccxt_lib.ExchangeError("Exchange maintenance")
            )
            trader = CCXTTrader(
                exchange_id="bybit",
                credentials={"api_key": "k", "api_secret": "s"},
                testnet=True,
            )
            with pytest.raises(TradeError) as exc_info:
                await trader.initialize()
            assert "exchange error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_insufficient_funds_on_market_order(self, _make_trader):
        """ccxt.InsufficientFunds returns failed OrderResult."""
        import ccxt as ccxt_lib

        trader, mock_exchange = await _make_trader()
        mock_exchange.create_market_order = AsyncMock(
            side_effect=ccxt_lib.InsufficientFunds("Not enough USDT")
        )

        result = await trader.place_market_order(
            symbol="BTC", side="buy", size=0.1, leverage=5,
        )

        assert result.success is False
        assert "insufficient funds" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_order_on_market_order(self, _make_trader):
        """ccxt.InvalidOrder returns failed OrderResult."""
        import ccxt as ccxt_lib

        trader, mock_exchange = await _make_trader()
        mock_exchange.create_market_order = AsyncMock(
            side_effect=ccxt_lib.InvalidOrder("Order size too small")
        )

        result = await trader.place_market_order(
            symbol="BTC", side="buy", size=0.1, leverage=5,
        )

        assert result.success is False
        assert "invalid order" in result.error.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_retries(self, _make_trader):
        """ccxt.RateLimitExceeded retries once then returns failure."""
        import ccxt as ccxt_lib

        trader, mock_exchange = await _make_trader()
        mock_exchange.create_market_order = AsyncMock(
            side_effect=ccxt_lib.RateLimitExceeded("429 Too Many Requests")
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await trader.place_market_order(
                symbol="BTC", side="buy", size=0.1, leverage=5,
            )

        assert result.success is False
        assert "rate limit" in result.error.lower()
        # Should have been called twice (initial + retry)
        assert mock_exchange.create_market_order.call_count == 2


class TestTradeError:
    """Tests for TradeError exception."""

    def test_trade_error_creation(self):
        """Test TradeError creation."""
        error = TradeError(
            message="Order failed",
            code="INSUFFICIENT_BALANCE",
            details={"available": 100, "required": 500},
        )

        assert error.message == "Order failed"
        assert error.code == "INSUFFICIENT_BALANCE"
        assert error.details["available"] == 100

    def test_trade_error_str(self):
        """Test TradeError string representation."""
        error = TradeError(message="Test error")
        assert "Test error" in str(error)


class TestOrderResult:
    """Tests for OrderResult model."""

    def test_order_result_success(self):
        """Test successful order result."""
        result = OrderResult(
            success=True,
            order_id="12345",
            filled_size=0.1,
            filled_price=50000.0,
            status="filled",
        )

        assert result.success is True
        assert result.order_id == "12345"
        assert result.filled_size == 0.1
        assert result.filled_price == 50000.0

    def test_order_result_failure(self):
        """Test failed order result."""
        result = OrderResult(
            success=False,
            order_id=None,
            filled_size=None,
            filled_price=None,
            status="rejected",
            error="Insufficient margin",
        )

        assert result.success is False
        assert result.error == "Insufficient margin"


class TestAccountState:
    """Tests for AccountState model."""

    def test_account_state_creation(self):
        """Test AccountState creation."""
        state = AccountState(
            equity=10000.0,
            available_balance=8000.0,
            total_margin_used=2000.0,
            unrealized_pnl=500.0,
            positions=[],
        )

        assert state.equity == 10000.0
        assert state.available_balance == 8000.0
        assert len(state.positions) == 0

    def test_account_state_with_positions(self):
        """Test AccountState with positions."""
        positions = [
            Position(
                symbol="BTC",
                side="long",
                size=0.1,
                size_usd=5000.0,
                entry_price=50000.0,
                mark_price=51000.0,
                unrealized_pnl=100.0,
                unrealized_pnl_percent=2.0,
                leverage=5,
            ),
        ]

        state = AccountState(
            equity=10100.0,
            available_balance=9000.0,
            total_margin_used=1000.0,
            unrealized_pnl=100.0,
            positions=positions,
        )

        assert len(state.positions) == 1
        assert state.positions[0].symbol == "BTC"


class TestPosition:
    """Tests for Position model."""

    def test_position_long(self):
        """Test long position."""
        position = Position(
            symbol="BTC",
            side="long",
            size=0.1,
            size_usd=5000.0,
            entry_price=50000.0,
            mark_price=51000.0,
            unrealized_pnl=100.0,
            unrealized_pnl_percent=2.0,
            leverage=5,
        )

        assert position.side == "long"
        assert position.unrealized_pnl == 100.0
        assert position.is_profitable is True

    def test_position_short(self):
        """Test short position."""
        position = Position(
            symbol="ETH",
            side="short",
            size=1.0,
            size_usd=3000.0,
            entry_price=3000.0,
            mark_price=2900.0,
            unrealized_pnl=100.0,
            unrealized_pnl_percent=3.33,
            leverage=3,
        )

        assert position.side == "short"
        assert position.unrealized_pnl == 100.0
        assert position.is_profitable is True


class TestMarketData:
    """Tests for MarketData model."""

    def test_market_data_creation(self):
        """Test MarketData creation."""
        data = MarketData(
            symbol="BTC",
            mid_price=50000.0,
            bid_price=49990.0,
            ask_price=50010.0,
            volume_24h=1000000000.0,
            timestamp=datetime.now(UTC),
        )

        assert data.symbol == "BTC"
        assert data.mid_price == 50000.0
        assert data.bid_price == 49990.0
        assert data.ask_price == 50010.0


class TestBaseTraderExtended:
    """Extended tests for BaseTrader methods."""

    @pytest_asyncio.fixture
    async def trader(self):
        """Create and initialize mock trader."""
        trader = MockTrader(testnet=True)
        await trader.initialize()
        return trader

    @pytest.mark.asyncio
    async def test_get_klines_default(self, trader):
        """Test default get_klines returns empty list."""
        result = await trader.get_klines("BTC", "1h", 100)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_funding_history_default(self, trader):
        """Test default get_funding_history returns empty list."""
        result = await trader.get_funding_history("BTC", 24)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_open_interest_default(self, trader):
        """Test default get_open_interest returns None."""
        result = await trader.get_open_interest("BTC")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_order_default(self, trader):
        """Test default get_order returns None."""
        from app.traders.base import BaseTrader
        # Use base class method directly
        result = await BaseTrader.get_order(trader, "BTC", "order_123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_open_orders_default(self, trader):
        """Test default get_open_orders returns empty list."""
        from app.traders.base import BaseTrader
        result = await BaseTrader.get_open_orders(trader, "BTC")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_order_history_default(self, trader):
        """Test default get_order_history returns empty list."""
        from app.traders.base import BaseTrader
        result = await BaseTrader.get_order_history(trader, "BTC", 50)
        assert result == []


class TestWaitForFill:
    """Tests for wait_for_fill method."""

    @pytest.mark.asyncio
    async def test_wait_for_fill_order_not_found(self):
        """Test wait_for_fill raises when order not found."""
        trader = MockTrader(testnet=True)
        await trader.initialize()
        
        # get_order returns None by default
        with pytest.raises(TradeError) as exc_info:
            await trader.wait_for_fill("BTC", "nonexistent_order", timeout_seconds=1)
        
        assert exc_info.value.code == "ORDER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_wait_for_fill_timeout(self):
        """Test wait_for_fill raises on timeout."""
        from app.traders.base import BaseTrader, Order, OrderStatus, OrderType
        
        class SlowFillTrader(MockTrader):
            async def get_order(self, symbol: str, order_id: str):
                # Return pending order that never completes
                return Order(
                    order_id=order_id,
                    client_order_id=None,
                    symbol=symbol,
                    side="buy",
                    order_type=OrderType.MARKET,
                    size=0.1,
                    filled_size=0,
                    status=OrderStatus.PENDING,
                )
        
        trader = SlowFillTrader(testnet=True)
        await trader.initialize()
        
        with pytest.raises(TradeError) as exc_info:
            await trader.wait_for_fill("BTC", "slow_order", timeout_seconds=0.1, poll_interval=0.05)
        
        assert exc_info.value.code == "ORDER_TIMEOUT"

    @pytest.mark.asyncio
    async def test_wait_for_fill_success(self):
        """Test wait_for_fill returns when order completes."""
        from app.traders.base import BaseTrader, Order, OrderStatus, OrderType
        
        class QuickFillTrader(MockTrader):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._call_count = 0
            
            async def get_order(self, symbol: str, order_id: str):
                self._call_count += 1
                # First call: pending, second call: filled
                status = OrderStatus.PENDING if self._call_count == 1 else OrderStatus.FILLED
                return Order(
                    order_id=order_id,
                    client_order_id=None,
                    symbol=symbol,
                    side="buy",
                    order_type=OrderType.MARKET,
                    size=0.1,
                    price=50000.0,
                    filled_size=0.1 if status == OrderStatus.FILLED else 0,
                    status=status,
                )
        
        trader = QuickFillTrader(testnet=True)
        await trader.initialize()
        
        order = await trader.wait_for_fill("BTC", "quick_order", timeout_seconds=5, poll_interval=0.05)
        
        assert order.status == OrderStatus.FILLED
        assert order.filled_size == 0.1


class TestPositionIsProfitable:
    """Tests for Position.is_profitable property."""

    def test_is_profitable_positive_pnl(self):
        """Test is_profitable returns True for positive unrealized P&L."""
        position = Position(
            symbol="BTC",
            side="long",
            size=0.1,
            size_usd=5000.0,
            entry_price=50000.0,
            mark_price=51000.0,
            unrealized_pnl=100.0,
            unrealized_pnl_percent=2.0,
            leverage=5,
        )
        assert position.is_profitable is True

    def test_is_profitable_negative_pnl(self):
        """Test is_profitable returns False for negative unrealized P&L."""
        position = Position(
            symbol="BTC",
            side="long",
            size=0.1,
            size_usd=5000.0,
            entry_price=50000.0,
            mark_price=49000.0,
            unrealized_pnl=-100.0,
            unrealized_pnl_percent=-2.0,
            leverage=5,
        )
        assert position.is_profitable is False

    def test_is_profitable_zero_pnl(self):
        """Test is_profitable returns False for zero unrealized P&L."""
        position = Position(
            symbol="BTC",
            side="long",
            size=0.1,
            size_usd=5000.0,
            entry_price=50000.0,
            mark_price=50000.0,
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
            leverage=5,
        )
        assert position.is_profitable is False


# ============================================================================
# detect_market_type
# ============================================================================

class TestDetectMarketType:
    """Tests for detect_market_type function."""

    def test_forex_exact_match(self):
        from app.traders.base import detect_market_type, MarketType
        assert detect_market_type("EUR/USD") == MarketType.FOREX

    def test_metals_exact_match(self):
        from app.traders.base import detect_market_type, MarketType
        assert detect_market_type("XAU/USD") == MarketType.METALS

    def test_forex_base_detection(self):
        from app.traders.base import detect_market_type, MarketType
        assert detect_market_type("GBP/BTC") == MarketType.FOREX

    def test_metals_base_detection(self):
        from app.traders.base import detect_market_type, MarketType
        assert detect_market_type("XAG/BTC") == MarketType.METALS

    def test_crypto_default(self):
        from app.traders.base import detect_market_type, MarketType
        assert detect_market_type("BTC/USDT") == MarketType.CRYPTO_PERP

    def test_uppercase_normalization(self):
        from app.traders.base import detect_market_type, MarketType
        assert detect_market_type("eur/usd") == MarketType.FOREX


# ============================================================================
# AccountState.margin_usage_percent
# ============================================================================

class TestAccountStateMarginUsage:
    def test_zero_equity(self):
        state = AccountState(
            equity=0.0, available_balance=0.0,
            total_margin_used=0.0, unrealized_pnl=0.0,
        )
        assert state.margin_usage_percent == 0.0

    def test_normal_usage(self):
        state = AccountState(
            equity=10000.0, available_balance=8000.0,
            total_margin_used=2000.0, unrealized_pnl=0.0,
        )
        assert state.margin_usage_percent == pytest.approx(20.0)


# ============================================================================
# Order.is_successful, Order.fill_percent
# ============================================================================

class TestOrderProperties:
    def test_is_successful_filled(self):
        from app.traders.base import Order, OrderStatus, OrderType
        order = Order(
            order_id="1", client_order_id="c1", symbol="BTC",
            side="buy", order_type=OrderType.MARKET,
            status=OrderStatus.FILLED, size=0.1, filled_size=0.1,
        )
        assert order.is_successful is True

    def test_is_successful_cancelled_with_fills(self):
        from app.traders.base import Order, OrderStatus, OrderType
        order = Order(
            order_id="1", client_order_id="c1", symbol="BTC",
            side="buy", order_type=OrderType.MARKET,
            status=OrderStatus.CANCELLED, size=0.1, filled_size=0.05,
        )
        assert order.is_successful is True

    def test_is_successful_cancelled_no_fills(self):
        from app.traders.base import Order, OrderStatus, OrderType
        order = Order(
            order_id="1", client_order_id="c1", symbol="BTC",
            side="buy", order_type=OrderType.MARKET,
            status=OrderStatus.CANCELLED, size=0.1, filled_size=0.0,
        )
        assert order.is_successful is False

    def test_fill_percent_zero_size(self):
        from app.traders.base import Order, OrderStatus, OrderType
        order = Order(
            order_id="1", client_order_id="c1", symbol="BTC",
            side="buy", order_type=OrderType.MARKET,
            status=OrderStatus.SUBMITTED, size=0, filled_size=0,
        )
        assert order.fill_percent == 0.0

    def test_fill_percent_partial(self):
        from app.traders.base import Order, OrderStatus, OrderType
        order = Order(
            order_id="1", client_order_id="c1", symbol="BTC",
            side="buy", order_type=OrderType.MARKET,
            status=OrderStatus.PARTIALLY_FILLED, size=1.0, filled_size=0.5,
        )
        assert order.fill_percent == pytest.approx(50.0)


# ============================================================================
# OHLCV.change_percent
# ============================================================================

class TestOHLCVChangePercent:
    def test_zero_open(self):
        from app.traders.base import OHLCV
        candle = OHLCV(
            timestamp=datetime.now(UTC), open=0, high=10, low=0, close=10, volume=100,
        )
        assert candle.change_percent == 0.0

    def test_bullish(self):
        from app.traders.base import OHLCV
        candle = OHLCV(
            timestamp=datetime.now(UTC), open=100, high=110, low=95, close=105, volume=100,
        )
        assert candle.change_percent == pytest.approx(5.0)

    def test_bearish(self):
        from app.traders.base import OHLCV
        candle = OHLCV(
            timestamp=datetime.now(UTC), open=100, high=105, low=90, close=95, volume=100,
        )
        assert candle.change_percent == pytest.approx(-5.0)


# ============================================================================
# BaseTrader.open_long, open_short, _ensure_initialized
# ============================================================================

class TestBaseTraderOpenLongShort:
    """Test the BaseTrader convenience methods (not the MockTrader overrides)."""

    @pytest.fixture
    def base_trader(self):
        """Create a BaseTrader subclass that uses the base open_long/open_short."""
        class RealBaseTrader(BaseTrader):
            def __init__(self):
                self.testnet = True
                self._initialized = True

            @property
            def exchange_name(self): return "test"
            async def initialize(self): return True
            async def close(self): pass
            async def get_account_state(self): pass
            async def get_positions(self): return []
            async def get_position(self, symbol): return None
            async def get_market_price(self, symbol): return 50000.0
            async def get_market_data(self, symbol): return None
            async def place_market_order(self, symbol, side, size, leverage=1, **kw):
                return OrderResult(
                    success=True, order_id="o1",
                    filled_size=size, filled_price=50000.0, status="filled",
                )
            async def place_limit_order(self, *a, **kw): pass
            async def place_stop_loss(self, *a, **kw): pass
            async def place_take_profit(self, *a, **kw): pass
            async def cancel_order(self, *a, **kw): return True
            async def cancel_all_orders(self, *a, **kw): return 0
            async def close_position(self, *a, **kw):
                return OrderResult(success=True)
            async def set_leverage(self, *a, **kw): return True

        return RealBaseTrader()

    @pytest.mark.asyncio
    async def test_open_long_success(self, base_trader):
        result = await base_trader.open_long("BTC", size_usd=5000.0, leverage=5)
        assert result.success is True
        assert result.filled_size == pytest.approx(0.1)

    @pytest.mark.asyncio
    async def test_open_long_with_sl_tp(self, base_trader):
        result = await base_trader.open_long(
            "BTC", size_usd=5000.0, leverage=5,
            stop_loss=45000.0, take_profit=60000.0,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_open_long_sl_error_does_not_affect_entry(self, base_trader):
        """SL placement failure should not affect the main order."""
        base_trader.place_stop_loss = AsyncMock(side_effect=Exception("SL failed"))
        result = await base_trader.open_long(
            "BTC", size_usd=5000.0, leverage=5, stop_loss=45000.0,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_open_long_tp_error_does_not_affect_entry(self, base_trader):
        """TP placement failure should not affect the main order."""
        base_trader.place_take_profit = AsyncMock(side_effect=Exception("TP failed"))
        result = await base_trader.open_long(
            "BTC", size_usd=5000.0, leverage=5, take_profit=60000.0,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_open_long_invalid_price(self, base_trader):
        base_trader.get_market_price = AsyncMock(return_value=0.0)
        with pytest.raises(TradeError, match="Invalid market price"):
            await base_trader.open_long("BTC", size_usd=5000.0)

    @pytest.mark.asyncio
    async def test_open_short_success(self, base_trader):
        result = await base_trader.open_short("BTC", size_usd=5000.0, leverage=5)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_open_short_with_sl_tp(self, base_trader):
        result = await base_trader.open_short(
            "BTC", size_usd=5000.0, leverage=5,
            stop_loss=55000.0, take_profit=40000.0,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_open_short_sl_error_does_not_affect_entry(self, base_trader):
        base_trader.place_stop_loss = AsyncMock(side_effect=Exception("SL failed"))
        result = await base_trader.open_short(
            "BTC", size_usd=5000.0, leverage=5, stop_loss=55000.0,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_open_short_tp_error_does_not_affect_entry(self, base_trader):
        base_trader.place_take_profit = AsyncMock(side_effect=Exception("TP failed"))
        result = await base_trader.open_short(
            "BTC", size_usd=5000.0, leverage=5, take_profit=40000.0,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_open_short_invalid_price(self, base_trader):
        base_trader.get_market_price = AsyncMock(return_value=None)
        with pytest.raises(TradeError, match="Invalid market price"):
            await base_trader.open_short("BTC", size_usd=5000.0)

    def test_ensure_initialized_raises(self, base_trader):
        base_trader._initialized = False
        with pytest.raises(TradeError, match="not initialized"):
            base_trader._ensure_initialized()

    def test_ensure_initialized_ok(self, base_trader):
        base_trader._initialized = True
        base_trader._ensure_initialized()  # Should not raise

    def test_validate_symbol(self, base_trader):
        assert base_trader._validate_symbol("  btc  ") == "BTC"
