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
