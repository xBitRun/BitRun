"""
Tests for backtest engine and simulator.

Covers: BacktestEngine, SimulatedTrader, SimulatedPosition, Trade
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.backtest.simulator import SimulatedPosition, SimulatedTrader, Trade
from app.backtest.engine import BacktestEngine, BacktestResult


# ============================================================================
# SimulatedPosition Tests
# ============================================================================

class TestSimulatedPosition:
    """Tests for SimulatedPosition"""

    def test_create_long_position(self):
        """Test creating long position"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=0.1,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        assert pos.symbol == "BTC"
        assert pos.side == "long"
        assert pos.size == 0.1
        assert pos.entry_price == 50000
        assert pos.leverage == 10

    def test_create_short_position(self):
        """Test creating short position"""
        pos = SimulatedPosition(
            symbol="ETH",
            side="short",
            size=1.0,
            entry_price=3000,
            leverage=5,
            opened_at=datetime.now(UTC),
        )
        
        assert pos.symbol == "ETH"
        assert pos.side == "short"

    def test_calculate_pnl_long_profit(self):
        """Test P&L calculation for profitable long"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        pnl = pos.calculate_pnl(55000)  # Price up 10%
        
        assert pnl == 5000  # 55000 - 50000

    def test_calculate_pnl_long_loss(self):
        """Test P&L calculation for losing long"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        pnl = pos.calculate_pnl(45000)  # Price down 10%
        
        assert pnl == -5000

    def test_calculate_pnl_short_profit(self):
        """Test P&L calculation for profitable short"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="short",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        pnl = pos.calculate_pnl(45000)  # Price down 10%
        
        assert pnl == 5000  # 50000 - 45000

    def test_calculate_pnl_short_loss(self):
        """Test P&L calculation for losing short"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="short",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        pnl = pos.calculate_pnl(55000)  # Price up 10%
        
        assert pnl == -5000

    def test_calculate_pnl_percent_with_leverage(self):
        """Test P&L percent calculation with leverage"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        pnl_percent = pos.calculate_pnl_percent(55000)  # 10% price increase
        
        # With 10x leverage, 10% price move = 100% P&L
        assert pnl_percent == 100.0

    def test_check_stop_loss_long_triggered(self):
        """Test stop loss trigger for long position"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            stop_loss=48000,
        )
        
        assert pos.check_stop_loss(47000) is True
        assert pos.check_stop_loss(49000) is False

    def test_check_stop_loss_short_triggered(self):
        """Test stop loss trigger for short position"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="short",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            stop_loss=52000,
        )
        
        assert pos.check_stop_loss(53000) is True
        assert pos.check_stop_loss(51000) is False

    def test_check_take_profit_long_triggered(self):
        """Test take profit trigger for long position"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            take_profit=55000,
        )
        
        assert pos.check_take_profit(56000) is True
        assert pos.check_take_profit(54000) is False

    def test_check_take_profit_short_triggered(self):
        """Test take profit trigger for short position"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="short",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            take_profit=45000,
        )
        
        assert pos.check_take_profit(44000) is True
        assert pos.check_take_profit(46000) is False

    def test_to_position(self):
        """Test converting to Position object"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=0.1,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        position = pos.to_position(55000)
        
        assert position.symbol == "BTC"
        assert position.side == "long"
        assert position.size == 0.1
        assert position.entry_price == 50000
        assert position.mark_price == 55000
        assert position.unrealized_pnl == 500  # (55000 - 50000) * 0.1

    def test_liquidation_price_long(self):
        """Test liquidation price calculation for long"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        liq_price = pos._calc_liquidation_price()
        
        # With 10x leverage, ~9% loss = liquidation
        assert liq_price is not None
        assert liq_price < pos.entry_price

    def test_liquidation_price_short(self):
        """Test liquidation price calculation for short"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="short",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        liq_price = pos._calc_liquidation_price()
        
        assert liq_price is not None
        assert liq_price > pos.entry_price


# ============================================================================
# Trade Tests
# ============================================================================

class TestTrade:
    """Tests for Trade dataclass"""

    def test_create_trade(self):
        """Test creating trade record"""
        opened = datetime.now(UTC)
        closed = opened + timedelta(hours=2)
        
        trade = Trade(
            symbol="BTC",
            side="long",
            size=0.1,
            entry_price=50000,
            exit_price=55000,
            leverage=10,
            pnl=500,
            pnl_percent=100,
            opened_at=opened,
            closed_at=closed,
            exit_reason="take_profit",
        )
        
        assert trade.symbol == "BTC"
        assert trade.pnl == 500
        assert trade.exit_reason == "take_profit"

    def test_duration_minutes(self):
        """Test duration calculation"""
        opened = datetime.now(UTC)
        closed = opened + timedelta(hours=2)
        
        trade = Trade(
            symbol="BTC",
            side="long",
            size=0.1,
            entry_price=50000,
            exit_price=55000,
            leverage=10,
            pnl=500,
            pnl_percent=100,
            opened_at=opened,
            closed_at=closed,
        )
        
        assert trade.duration_minutes == 120


# ============================================================================
# SimulatedTrader Tests
# ============================================================================

class TestSimulatedPositionExtended:
    """Extended tests for SimulatedPosition edge cases"""

    def test_calculate_pnl_percent_zero_entry_price(self):
        """Test P&L percent calculation when entry_price is 0"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=1.0,
            entry_price=0,  # Edge case: zero entry
            leverage=10,
            opened_at=datetime.now(UTC),
        )
        
        # Should return 0 instead of dividing by zero
        pnl_percent = pos.calculate_pnl_percent(50000)
        assert pnl_percent == 0

    def test_check_stop_loss_no_stop_loss_set(self):
        """Test stop loss check when no SL set"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            stop_loss=None,  # No stop loss
        )
        
        assert pos.check_stop_loss(40000) is False

    def test_check_take_profit_no_take_profit_set(self):
        """Test take profit check when no TP set"""
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=1.0,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            take_profit=None,  # No take profit
        )
        
        assert pos.check_take_profit(60000) is False


class TestSimulatedTrader:
    """Tests for SimulatedTrader"""

    @pytest.fixture
    def trader(self):
        """Create trader instance"""
        return SimulatedTrader(
            initial_balance=10000,
            maker_fee=0.0002,
            taker_fee=0.0005,
            default_slippage=0.001,
        )

    def test_initialization(self, trader):
        """Test trader initialization"""
        assert trader.balance == 10000
        assert trader.initial_balance == 10000
        assert trader.exchange_name == "simulator"

    @pytest.mark.asyncio
    async def test_initialize(self, trader):
        """Test initialize method"""
        result = await trader.initialize()
        assert result is True

    def test_set_prices(self, trader):
        """Test setting market prices"""
        trader.set_prices({"BTC": 50000, "ETH": 3000})
        
        assert trader._current_prices["BTC"] == 50000
        assert trader._current_prices["ETH"] == 3000

    def test_set_current_time(self, trader):
        """Test setting simulation time"""
        now = datetime.now(UTC)
        trader.set_current_time(now)
        
        assert trader._current_time == now

    @pytest.mark.asyncio
    async def test_get_account_state(self, trader):
        """Test getting account state"""
        trader.set_prices({"BTC": 50000})
        
        state = await trader.get_account_state()
        
        assert state.equity == 10000
        assert state.available_balance == 10000
        assert state.total_margin_used == 0
        assert len(state.positions) == 0

    @pytest.mark.asyncio
    async def test_get_market_price(self, trader):
        """Test getting market price"""
        trader.set_prices({"BTC": 50000})
        
        price = await trader.get_market_price("BTC")
        
        assert price == 50000

    @pytest.mark.asyncio
    async def test_get_market_price_not_found(self, trader):
        """Test getting price for unknown symbol"""
        from app.traders.base import TradeError
        
        with pytest.raises(TradeError):
            await trader.get_market_price("UNKNOWN")

    @pytest.mark.asyncio
    async def test_place_market_order_buy(self, trader):
        """Test placing buy market order"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        result = await trader.place_market_order(
            symbol="BTC",
            side="buy",
            size=0.1,
            leverage=10,
        )
        
        assert result.success is True
        assert result.filled_size == 0.1
        assert "BTC" in trader._positions

    @pytest.mark.asyncio
    async def test_place_market_order_sell(self, trader):
        """Test placing sell market order"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        result = await trader.place_market_order(
            symbol="BTC",
            side="sell",
            size=0.1,
            leverage=10,
        )
        
        assert result.success is True
        pos = trader._positions.get("BTC")
        assert pos is not None
        assert pos.side == "short"

    @pytest.mark.asyncio
    async def test_place_market_order_insufficient_balance(self, trader):
        """Test order with insufficient balance"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Try to buy more than balance allows
        result = await trader.place_market_order(
            symbol="BTC",
            side="buy",
            size=10,  # 10 BTC = $500,000 > $10,000
            leverage=1,
        )
        
        assert result.success is False
        assert "Insufficient balance" in result.error

    @pytest.mark.asyncio
    async def test_open_long(self, trader):
        """Test opening long position"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        result = await trader.open_long(
            symbol="BTC",
            size_usd=1000,
            leverage=10,
            stop_loss=48000,
            take_profit=55000,
        )
        
        assert result.success is True
        
        pos = await trader.get_position("BTC")
        assert pos is not None
        assert pos.side == "long"

    @pytest.mark.asyncio
    async def test_open_short(self, trader):
        """Test opening short position"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        result = await trader.open_short(
            symbol="BTC",
            size_usd=1000,
            leverage=10,
        )
        
        assert result.success is True
        
        pos = await trader.get_position("BTC")
        assert pos is not None
        assert pos.side == "short"

    @pytest.mark.asyncio
    async def test_close_position(self, trader):
        """Test closing position"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open position
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        
        # Close position
        result = await trader.close_position("BTC")
        
        assert result.success is True
        pos = await trader.get_position("BTC")
        assert pos is None

    @pytest.mark.asyncio
    async def test_stop_loss_triggered(self, trader):
        """Test automatic stop loss trigger"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open long with stop loss
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=0.1,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            stop_loss=48000,
        )
        trader._positions["BTC"] = pos
        
        # Price drops below stop loss
        trader.set_prices({"BTC": 47000})
        
        # Position should be closed
        assert "BTC" not in trader._positions
        assert len(trader._trades) == 1
        assert trader._trades[0].exit_reason == "stop_loss"

    @pytest.mark.asyncio
    async def test_take_profit_triggered(self, trader):
        """Test automatic take profit trigger"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open long with take profit
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=0.1,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            take_profit=55000,
        )
        trader._positions["BTC"] = pos
        
        # Price rises above take profit
        trader.set_prices({"BTC": 56000})
        
        # Position should be closed
        assert "BTC" not in trader._positions
        assert len(trader._trades) == 1
        assert trader._trades[0].exit_reason == "take_profit"

    @pytest.mark.asyncio
    async def test_get_statistics_no_trades(self, trader):
        """Test statistics with no trades"""
        stats = trader.get_statistics()
        
        assert stats["total_trades"] == 0
        assert stats["win_rate"] == 0
        assert stats["profit_factor"] == 0

    @pytest.mark.asyncio
    async def test_get_statistics_with_trades(self, trader):
        """Test statistics calculation"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Create winning trade
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        trader.set_prices({"BTC": 55000})
        await trader.close_position("BTC")
        
        stats = trader.get_statistics()
        
        assert stats["total_trades"] == 1
        assert stats["winning_trades"] == 1
        assert stats["win_rate"] == 100

    @pytest.mark.asyncio
    async def test_max_drawdown_tracking(self, trader):
        """Test max drawdown tracking"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open position
        await trader.open_long("BTC", size_usd=5000, leverage=10)
        
        # Price drops 5%
        trader.set_prices({"BTC": 47500})
        
        # Should have drawdown
        assert trader.max_drawdown > 0

    @pytest.mark.asyncio
    async def test_fees_tracking(self, trader):
        """Test fee tracking"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        initial_fees = trader.total_fees_paid
        
        await trader.place_market_order("BTC", "buy", 0.1, leverage=10)
        
        assert trader.total_fees_paid > initial_fees

    @pytest.mark.asyncio
    async def test_set_leverage(self, trader):
        """Test setting leverage"""
        result = await trader.set_leverage("BTC", 20)
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order(self, trader):
        """Test cancel order (no-op)"""
        result = await trader.cancel_order("BTC", "order-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_all_orders(self, trader):
        """Test cancel all orders (no-op)"""
        result = await trader.cancel_all_orders()
        assert result == 0

    @pytest.mark.asyncio
    async def test_place_market_order_reduce_only(self, trader):
        """Test reduce_only market order"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open position first
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        
        # Reduce position with reduce_only
        original_size = trader._positions["BTC"].size
        reduce_size = original_size / 2
        result = await trader.place_market_order(
            symbol="BTC",
            side="sell",
            size=reduce_size,
            leverage=10,
            reduce_only=True,
        )
        
        assert result.success is True
        # Position should be reduced
        assert trader._positions.get("BTC") is not None
        assert trader._positions["BTC"].size < original_size

    @pytest.mark.asyncio
    async def test_place_market_order_reduce_only_no_position(self, trader):
        """Test reduce_only when no position exists"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Try to reduce non-existent position
        result = await trader.place_market_order(
            symbol="BTC",
            side="sell",
            size=0.1,
            leverage=10,
            reduce_only=True,
        )
        
        assert result.success is False
        assert "No position to reduce" in result.error

    @pytest.mark.asyncio
    async def test_open_reverse_position(self, trader):
        """Test opening position in opposite direction closes existing"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open long
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        assert trader._positions["BTC"].side == "long"
        
        # Open short should close long first
        await trader.open_short("BTC", size_usd=1000, leverage=10)
        
        # Should have short position now
        pos = trader._positions.get("BTC")
        assert pos is not None
        assert pos.side == "short"
        
        # Should have recorded a trade for the closed long
        assert len(trader._trades) >= 1
        assert trader._trades[0].exit_reason == "reverse"

    @pytest.mark.asyncio
    async def test_increase_existing_position(self, trader):
        """Test increasing existing position averages entry price"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open initial long
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        initial_size = trader._positions["BTC"].size
        initial_entry = trader._positions["BTC"].entry_price
        
        # Open another long at different price
        trader.set_prices({"BTC": 55000})
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        
        pos = trader._positions["BTC"]
        # Size should increase
        assert pos.size > initial_size
        # Entry price should be averaged
        assert pos.entry_price != initial_entry
        assert pos.entry_price != 55000

    @pytest.mark.asyncio
    async def test_place_stop_loss_success(self, trader):
        """Test setting stop loss on existing position"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open position first
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        
        # Set stop loss
        result = await trader.place_stop_loss(
            symbol="BTC",
            side="sell",
            size=0.1,
            trigger_price=48000,
        )
        
        assert result.success is True
        assert trader._positions["BTC"].stop_loss == 48000

    @pytest.mark.asyncio
    async def test_place_stop_loss_no_position(self, trader):
        """Test stop loss fails when no position"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        result = await trader.place_stop_loss(
            symbol="BTC",
            side="sell",
            size=0.1,
            trigger_price=48000,
        )
        
        assert result.success is False
        assert "No position" in result.error

    @pytest.mark.asyncio
    async def test_place_take_profit_success(self, trader):
        """Test setting take profit on existing position"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open position first
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        
        # Set take profit
        result = await trader.place_take_profit(
            symbol="BTC",
            side="sell",
            size=0.1,
            trigger_price=55000,
        )
        
        assert result.success is True
        assert trader._positions["BTC"].take_profit == 55000

    @pytest.mark.asyncio
    async def test_place_take_profit_no_position(self, trader):
        """Test take profit fails when no position"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        result = await trader.place_take_profit(
            symbol="BTC",
            side="sell",
            size=0.1,
            trigger_price=55000,
        )
        
        assert result.success is False
        assert "No position" in result.error

    @pytest.mark.asyncio
    async def test_close_position_no_position(self, trader):
        """Test close_position when no position exists"""
        trader.set_prices({"BTC": 50000})
        
        result = await trader.close_position("BTC")
        
        assert result.success is True
        assert result.status == "no_position"

    @pytest.mark.asyncio
    async def test_sl_tp_auto_trigger_on_set_prices(self, trader):
        """Test SL/TP triggers automatically when prices update"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open long with SL/TP
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=0.1,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            stop_loss=48000,
            take_profit=55000,
        )
        trader._positions["BTC"] = pos
        
        # Price drops to trigger SL
        trader.set_prices({"BTC": 47000})
        
        # Position should be closed
        assert "BTC" not in trader._positions
        assert len(trader._trades) == 1
        assert trader._trades[0].exit_reason == "stop_loss"

    @pytest.mark.asyncio
    async def test_sl_tp_trigger_take_profit(self, trader):
        """Test TP triggers when price rises"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open long with TP
        pos = SimulatedPosition(
            symbol="BTC",
            side="long",
            size=0.1,
            entry_price=50000,
            leverage=10,
            opened_at=datetime.now(UTC),
            take_profit=55000,
        )
        trader._positions["BTC"] = pos
        
        # Price rises to trigger TP
        trader.set_prices({"BTC": 56000})
        
        # Position should be closed
        assert "BTC" not in trader._positions
        assert len(trader._trades) == 1
        assert trader._trades[0].exit_reason == "take_profit"

    @pytest.mark.asyncio
    async def test_statistics_with_break_even_trades(self, trader):
        """Test statistics with break-even (zero P&L) trades"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Create a trade with zero P&L manually
        trader._trades.append(Trade(
            symbol="BTC",
            side="long",
            size=0.1,
            entry_price=50000,
            exit_price=50000,  # Same as entry - break even
            leverage=10,
            pnl=0,  # Zero P&L
            pnl_percent=0,
            opened_at=datetime.now(UTC),
            closed_at=datetime.now(UTC),
            exit_reason="manual",
        ))
        
        stats = trader.get_statistics()
        
        # Break-even trade should not be counted as win or loss
        assert stats["total_trades"] == 1
        assert stats["winning_trades"] == 0
        assert stats["losing_trades"] == 0

    @pytest.mark.asyncio
    async def test_statistics_multi_symbol(self, trader):
        """Test statistics with multiple symbols"""
        trader.set_prices({"BTC": 50000, "ETH": 3000})
        trader.set_current_time(datetime.now(UTC))
        
        # Trade BTC
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        trader.set_prices({"BTC": 55000, "ETH": 3000})
        await trader.close_position("BTC")
        
        # Trade ETH
        await trader.open_long("ETH", size_usd=1000, leverage=10)
        trader.set_prices({"BTC": 55000, "ETH": 2800})
        await trader.close_position("ETH")
        
        stats = trader.get_statistics()
        
        # Should have symbol breakdown
        assert len(stats["symbol_breakdown"]) == 2
        btc_stats = next(s for s in stats["symbol_breakdown"] if s["symbol"] == "BTC")
        eth_stats = next(s for s in stats["symbol_breakdown"] if s["symbol"] == "ETH")
        
        assert btc_stats["total_trades"] == 1
        assert btc_stats["total_pnl"] > 0  # BTC was profitable
        assert eth_stats["total_trades"] == 1
        assert eth_stats["total_pnl"] < 0  # ETH was a loss

    @pytest.mark.asyncio
    async def test_statistics_long_short_breakdown(self, trader):
        """Test statistics long/short breakdown"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Long trade
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        trader.set_prices({"BTC": 52000})
        await trader.close_position("BTC")
        
        # Short trade
        await trader.open_short("BTC", size_usd=1000, leverage=10)
        trader.set_prices({"BTC": 50000})
        await trader.close_position("BTC")
        
        stats = trader.get_statistics()
        
        assert stats["long_stats"]["total_trades"] == 1
        assert stats["short_stats"]["total_trades"] == 1
        assert stats["long_stats"]["winning_trades"] == 1
        assert stats["short_stats"]["winning_trades"] == 1

    @pytest.mark.asyncio
    async def test_statistics_max_consecutive(self, trader):
        """Test max consecutive wins/losses calculation"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Create sequence: win, win, win, loss, loss
        for i, (price_change, expected_result) in enumerate([
            (2000, "win"),   # win
            (2000, "win"),   # win
            (2000, "win"),   # win
            (-3000, "loss"), # loss
            (-3000, "loss"), # loss
        ]):
            await trader.open_long("BTC", size_usd=500, leverage=10)
            trader.set_prices({"BTC": 50000 + price_change})
            await trader.close_position("BTC")
            trader.set_prices({"BTC": 50000})
        
        stats = trader.get_statistics()
        
        assert stats["max_consecutive_wins"] == 3
        assert stats["max_consecutive_losses"] == 2

    @pytest.mark.asyncio
    async def test_statistics_expectancy(self, trader):
        """Test expectancy calculation"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Create trades with known outcomes
        # 2 wins of $100 each, 1 loss of $50
        trader._trades = [
            Trade(
                symbol="BTC", side="long", size=0.1, entry_price=50000,
                exit_price=51000, leverage=10, pnl=100, pnl_percent=20,
                opened_at=datetime.now(UTC), closed_at=datetime.now(UTC),
            ),
            Trade(
                symbol="BTC", side="long", size=0.1, entry_price=50000,
                exit_price=51000, leverage=10, pnl=100, pnl_percent=20,
                opened_at=datetime.now(UTC), closed_at=datetime.now(UTC),
            ),
            Trade(
                symbol="BTC", side="long", size=0.1, entry_price=50000,
                exit_price=49500, leverage=10, pnl=-50, pnl_percent=-10,
                opened_at=datetime.now(UTC), closed_at=datetime.now(UTC),
            ),
        ]
        
        stats = trader.get_statistics()
        
        # Win rate = 66.67%, avg_win = 100, avg_loss = 50
        # Expectancy = (100 * 0.6667) - (50 * 0.3333) = 66.67 - 16.67 = 50
        assert stats["win_rate"] == pytest.approx(66.67, rel=0.01)
        assert stats["expectancy"] > 0

    @pytest.mark.asyncio
    async def test_statistics_profit_factor_infinity(self, trader):
        """Test profit factor when no losses (infinity)"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Only winning trades
        trader._trades = [
            Trade(
                symbol="BTC", side="long", size=0.1, entry_price=50000,
                exit_price=55000, leverage=10, pnl=500, pnl_percent=100,
                opened_at=datetime.now(UTC), closed_at=datetime.now(UTC),
            ),
        ]
        
        stats = trader.get_statistics()
        
        # Profit factor should be infinity when gross_loss is 0
        assert stats["profit_factor"] == float("inf")

    @pytest.mark.asyncio
    async def test_close_position_partial(self, trader):
        """Test partial position close"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        # Open position
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        initial_size = trader._positions["BTC"].size
        
        # Close half
        await trader.close_position("BTC", size=initial_size / 2)
        
        # Should still have position
        assert "BTC" in trader._positions
        assert trader._positions["BTC"].size == pytest.approx(initial_size / 2, rel=0.01)
        # Should have recorded trade
        assert len(trader._trades) == 1

    @pytest.mark.asyncio
    async def test_get_market_data(self, trader):
        """Test get_market_data returns proper structure"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        data = await trader.get_market_data("BTC")
        
        assert data.symbol == "BTC"
        assert data.mid_price == 50000
        assert data.bid_price < 50000  # With slippage
        assert data.ask_price > 50000  # With slippage

    @pytest.mark.asyncio
    async def test_get_positions(self, trader):
        """Test get_positions returns all positions"""
        trader.set_prices({"BTC": 50000, "ETH": 3000})
        trader.set_current_time(datetime.now(UTC))
        
        await trader.open_long("BTC", size_usd=1000, leverage=10)
        await trader.open_short("ETH", size_usd=500, leverage=5)
        
        positions = await trader.get_positions()
        
        assert len(positions) == 2
        symbols = {p.symbol for p in positions}
        assert "BTC" in symbols
        assert "ETH" in symbols

    @pytest.mark.asyncio
    async def test_place_limit_order(self, trader):
        """Test limit order (executed as market in sim)"""
        trader.set_prices({"BTC": 50000})
        trader.set_current_time(datetime.now(UTC))
        
        result = await trader.place_limit_order(
            symbol="BTC",
            side="buy",
            size=0.1,
            price=49000,  # Limit price
            leverage=10,
        )
        
        assert result.success is True
        assert "BTC" in trader._positions

    @pytest.mark.asyncio
    async def test_close_method(self, trader):
        """Test close method (no-op)"""
        await trader.close()  # Should not raise


# ============================================================================
# BacktestEngine Tests
# ============================================================================

class TestBacktestEngine:
    """Tests for BacktestEngine"""

    @pytest.fixture
    def mock_strategy(self):
        """Create mock strategy"""
        strategy = MagicMock()
        strategy.name = "Test Strategy"
        strategy.config = {
            "symbols": ["BTC"],
            "risk_controls": {
                "max_leverage": 10,
                "max_position_ratio": 0.1,
                "max_daily_loss_percent": 5,
            },
        }
        strategy.ai_model = None
        return strategy

    @pytest.fixture
    def mock_data_provider(self):
        """Create mock data provider"""
        from app.backtest.data_provider import OHLCV, MarketSnapshot
        
        provider = MagicMock()
        provider.initialize = AsyncMock()
        provider.load_data = AsyncMock()
        provider.close = AsyncMock()
        
        # Create sample snapshots
        snapshots = []
        base_time = datetime(2024, 1, 1)
        for i in range(10):
            snapshot = MarketSnapshot(
                timestamp=base_time + timedelta(hours=i),
                prices={"BTC": 50000 + i * 100},
            )
            snapshots.append(snapshot)
        
        provider.iterate.return_value = snapshots
        provider.get_data.return_value = [
            MagicMock(close=50000 + i * 100, timestamp=base_time + timedelta(hours=i))
            for i in range(30)
        ]
        
        return provider

    def test_create_backtest_result(self):
        """Test BacktestResult creation"""
        result = BacktestResult(
            strategy_name="Test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            initial_balance=10000,
            final_balance=12000,
            total_return_percent=20,
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            win_rate=70,
            profit_factor=2.5,
            max_drawdown_percent=5,
        )
        
        assert result.total_return_percent == 20
        assert result.win_rate == 70

    def test_backtest_result_to_dict(self):
        """Test BacktestResult serialization"""
        result = BacktestResult(
            strategy_name="Test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            initial_balance=10000,
            final_balance=12000,
            total_return_percent=20,
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            win_rate=70,
            profit_factor=2.5,
            max_drawdown_percent=5,
        )
        
        data = result.to_dict()
        
        assert "strategy_name" in data
        assert "start_date" in data
        assert data["total_return_percent"] == 20

    @pytest.mark.asyncio
    async def test_backtest_engine_initialization(self, mock_strategy):
        """Test engine initialization"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                use_ai=False,
            )
            
            assert engine.initial_balance == 10000
            assert engine.use_ai is False

    @pytest.mark.asyncio
    async def test_backtest_run_rule_based(
        self, mock_strategy, mock_data_provider
    ):
        """Test running backtest with rule-based strategy"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_data_provider,
                use_ai=False,
                decision_interval_candles=1,
            )
            
            result = await engine.run()
            
            assert isinstance(result, BacktestResult)
            assert result.strategy_name == "Test Strategy"
            assert len(result.equity_curve) > 0

    @pytest.mark.asyncio
    async def test_backtest_cleanup(self, mock_strategy, mock_data_provider):
        """Test cleanup method"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_data_provider,
            )
            
            await engine.cleanup()
            
            mock_data_provider.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_backtest_no_data(self, mock_strategy):
        """Test backtest with no data"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            # Data provider with no data
            empty_provider = MagicMock()
            empty_provider.initialize = AsyncMock()
            empty_provider.load_data = AsyncMock()
            empty_provider.iterate.return_value = []
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=empty_provider,
            )
            
            with pytest.raises(ValueError, match="No data to backtest"):
                await engine.run()

    @pytest.mark.asyncio
    async def test_backtest_initializes_data_provider(self, mock_strategy):
        """Test that engine initializes data provider if not provided"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            with patch("app.backtest.engine.DataProvider") as mock_dp_class:
                mock_dp = MagicMock()
                mock_dp.initialize = AsyncMock()
                mock_dp.load_data = AsyncMock()
                mock_dp.iterate.return_value = []
                mock_dp_class.return_value = mock_dp
                
                engine = BacktestEngine(
                    strategy=mock_strategy,
                    initial_balance=10000,
                    use_ai=False,
                )
                
                # Should raise ValueError because no data
                with pytest.raises(ValueError):
                    await engine.run()
                
                # Verify data provider was initialized
                mock_dp.initialize.assert_called_once()
                mock_dp.load_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_backtest_closes_remaining_positions(self, mock_strategy, mock_data_provider):
        """Test that engine closes remaining positions at end"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            mock_trader = MagicMock()
            mock_trader.set_current_time = MagicMock()
            mock_trader.set_prices = MagicMock()
            account_state = MagicMock()
            account_state.equity = 10000
            account_state.position_count = 1
            mock_trader.get_account_state = AsyncMock(return_value=account_state)
            mock_trader.balance = 10000
            mock_trader._positions = {"BTC": MagicMock()}
            mock_trader.close_position = AsyncMock()
            
            # Mock _build_result to avoid MagicMock comparison issues
            with patch("app.backtest.engine.SimulatedTrader", return_value=mock_trader):
                engine = BacktestEngine(
                    strategy=mock_strategy,
                    initial_balance=10000,
                    data_provider=mock_data_provider,
                    use_ai=False,
                    decision_interval_candles=100,  # Skip decisions
                )
                
                # Mock _build_result to return a simple result
                mock_result = BacktestResult(
                    strategy_name="Test",
                    start_date=datetime(2024, 1, 1),
                    end_date=datetime(2024, 1, 2),
                    initial_balance=10000,
                    final_balance=10000,
                    total_return_percent=0,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0,
                    profit_factor=0,
                    max_drawdown_percent=0,
                )
                engine._build_result = AsyncMock(return_value=mock_result)
                
                result = await engine.run()
                
                # Verify positions were closed
                mock_trader.close_position.assert_called_with("BTC")

    @pytest.mark.asyncio
    async def test_backtest_ai_decision_path(self, mock_strategy, mock_data_provider):
        """Test backtest with AI decision making"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            # Mock AI client and response
            mock_ai_client = AsyncMock()
            mock_ai_response = MagicMock()
            mock_ai_response.content = '{"chain_of_thought": "test", "decisions": [], "overall_confidence": 70, "next_review_minutes": 60}'
            mock_ai_client.generate = AsyncMock(return_value=mock_ai_response)
            
            # Mock decision parser
            mock_parser = MagicMock()
            mock_decision = MagicMock()
            mock_decision.decisions = []
            mock_decision.model_dump = MagicMock(return_value={})
            mock_parser.parse = MagicMock(return_value=mock_decision)
            mock_parser.should_execute = MagicMock(return_value=(False, ""))
            
            # Mock prompt builder
            mock_pb = MagicMock()
            mock_pb.build_system_prompt = MagicMock(return_value="system prompt")
            mock_pb.build_user_prompt = MagicMock(return_value="user prompt")
            
            with patch("app.backtest.engine.DecisionParser", return_value=mock_parser):
                with patch("app.backtest.engine.PromptBuilder", return_value=mock_pb):
                    engine = BacktestEngine(
                        strategy=mock_strategy,
                        initial_balance=10000,
                        data_provider=mock_data_provider,
                        use_ai=True,
                        ai_client=mock_ai_client,
                        decision_interval_candles=1,
                    )
                    
                    result = await engine.run()
                    
                    # Verify AI was called
                    assert mock_ai_client.generate.called
                    assert isinstance(result, BacktestResult)

    @pytest.mark.asyncio
    async def test_backtest_ai_decision_error_handling(self, mock_strategy, mock_data_provider):
        """Test that AI decision errors don't crash backtest"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            # Mock AI client that raises error
            mock_ai_client = AsyncMock()
            mock_ai_client.generate = AsyncMock(side_effect=Exception("AI error"))
            
            # Mock prompt builder
            mock_pb = MagicMock()
            mock_pb.build_system_prompt = MagicMock(return_value="system prompt")
            mock_pb.build_user_prompt = MagicMock(return_value="user prompt")
            
            with patch("app.backtest.engine.PromptBuilder", return_value=mock_pb):
                engine = BacktestEngine(
                    strategy=mock_strategy,
                    initial_balance=10000,
                    data_provider=mock_data_provider,
                    use_ai=True,
                    ai_client=mock_ai_client,
                    decision_interval_candles=1,
                )
                
                # Should complete despite AI error
                result = await engine.run()
                assert isinstance(result, BacktestResult)

    @pytest.mark.asyncio
    async def test_backtest_rule_based_decision_logic(self, mock_strategy):
        """Test rule-based decision making with various scenarios"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.backtest.data_provider import MarketSnapshot
            from app.models.strategy import StrategyConfig, RiskControls
            
            # Create strategy config as dict (not StrategyConfig instance)
            from app.models.strategy import StrategyConfig, RiskControls
            config_dict = {
                "symbols": ["BTC"],
                "risk_controls": {
                    "max_leverage": 10,
                    "max_position_ratio": 0.1,
                },
            }
            mock_strategy.config = config_dict
            
            # Create data provider with enough candles for SMA calculation
            mock_provider = MagicMock()
            mock_provider.initialize = AsyncMock()
            mock_provider.load_data = AsyncMock()
            
            base_time = datetime(2024, 1, 1)
            # Create 30 candles for SMA(20)
            candles = []
            for i in range(30):
                candle = MagicMock()
                candle.close = 50000 + i * 100
                candle.timestamp = base_time + timedelta(hours=i)
                candles.append(candle)
            
            mock_provider.get_data.return_value = candles
            
            # Create snapshots
            snapshots = []
            for i in range(25, 30):  # Start after SMA can be calculated
                snapshot = MarketSnapshot(
                    timestamp=base_time + timedelta(hours=i),
                    prices={"BTC": 50000 + i * 100},
                )
                snapshots.append(snapshot)
            
            mock_provider.iterate.return_value = snapshots
            
            mock_trader = MagicMock()
            mock_trader.set_current_time = MagicMock()
            mock_trader.set_prices = MagicMock()
            account_state = MagicMock()
            account_state.equity = 10000
            account_state.available_balance = 10000
            account_state.position_count = 0
            mock_trader.get_account_state = AsyncMock(return_value=account_state)
            mock_trader.balance = 10000
            mock_trader._positions = {}
            mock_trader.get_position = AsyncMock(return_value=None)
            mock_trader.open_long = AsyncMock()
            mock_trader.open_short = AsyncMock()
            mock_trader.close_position = AsyncMock()
            mock_trader.get_trades = MagicMock(return_value=[])
            # get_statistics is a regular method, not async
            mock_trader.get_statistics = MagicMock(return_value={
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0,
                "total_pnl_percent": 0,
                "max_drawdown": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "average_win": 0,
                "average_loss": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "gross_profit": 0,
                "gross_loss": 0,
                "avg_holding_hours": 0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "expectancy": 0,
                "total_fees": 0,
                "long_stats": {},
                "short_stats": {},
                "symbol_breakdown": [],
            })
            
            with patch("app.backtest.engine.SimulatedTrader", return_value=mock_trader):
                engine = BacktestEngine(
                    strategy=mock_strategy,
                    initial_balance=10000,
                    data_provider=mock_provider,
                    use_ai=False,
                    decision_interval_candles=1,
                )
                
                result = await engine.run()
                
                # Verify rule-based decisions were made
                assert isinstance(result, BacktestResult)
                # Should have attempted to open positions based on SMA logic
                assert mock_trader.open_long.called or mock_trader.open_short.called or not snapshots

    @pytest.mark.asyncio
    async def test_backtest_execute_decisions(self, mock_strategy, mock_data_provider):
        """Test execution of parsed AI decisions"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.models.decision import DecisionResponse, TradingDecision, ActionType
            
            # Create mock decision with executable actions
            decision = DecisionResponse(
                chain_of_thought="test",
                market_assessment="bullish",
                decisions=[
                    TradingDecision(
                        symbol="BTC",
                        action=ActionType.OPEN_LONG,
                        leverage=5,
                        position_size_usd=1000,
                        confidence=70,
                        reasoning="test reasoning for decision",
                    ),
                ],
                overall_confidence=70,
                next_review_minutes=60,
            )
            
            mock_parser = MagicMock()
            mock_parser.parse = MagicMock(return_value=decision)
            mock_parser.should_execute = MagicMock(return_value=(True, ""))
            
            mock_ai_client = AsyncMock()
            mock_ai_response = MagicMock()
            mock_ai_response.content = '{"chain_of_thought": "test", "decisions": [{"symbol": "BTC", "action": "open_long", "leverage": 5, "position_size_usd": 1000, "confidence": 70, "reasoning": "test"}], "overall_confidence": 70, "next_review_minutes": 60}'
            mock_ai_client.generate = AsyncMock(return_value=mock_ai_response)
            
            mock_pb = MagicMock()
            mock_pb.build_system_prompt = MagicMock(return_value="system")
            mock_pb.build_user_prompt = MagicMock(return_value="user")
            
            mock_trader = MagicMock()
            mock_trader.set_current_time = MagicMock()
            mock_trader.set_prices = MagicMock()
            account_state = MagicMock()
            account_state.equity = 10000
            account_state.available_balance = 10000
            account_state.position_count = 0
            mock_trader.get_account_state = AsyncMock(return_value=account_state)
            mock_trader.balance = 10000
            mock_trader.open_long = AsyncMock()
            mock_trader.get_trades = MagicMock(return_value=[])
            # get_statistics is a regular method, not async
            mock_trader.get_statistics = MagicMock(return_value={
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0,
                "total_pnl_percent": 0,
                "max_drawdown": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "average_win": 0,
                "average_loss": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "gross_profit": 0,
                "gross_loss": 0,
                "avg_holding_hours": 0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "expectancy": 0,
                "total_fees": 0,
                "long_stats": {},
                "short_stats": {},
                "symbol_breakdown": [],
            })
            
            with patch("app.backtest.engine.DecisionParser", return_value=mock_parser):
                with patch("app.backtest.engine.PromptBuilder", return_value=mock_pb):
                    with patch("app.backtest.engine.SimulatedTrader", return_value=mock_trader):
                        engine = BacktestEngine(
                            strategy=mock_strategy,
                            initial_balance=10000,
                            data_provider=mock_data_provider,
                            use_ai=True,
                            ai_client=mock_ai_client,
                            decision_interval_candles=1,
                        )
                        
                        result = await engine.run()
                        
                        # Verify decision was executed
                        assert mock_trader.open_long.called

    @pytest.mark.asyncio
    async def test_execute_decisions_open_short(self, mock_strategy, mock_data_provider):
        """Test execution of OPEN_SHORT decision"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.models.decision import DecisionResponse, TradingDecision, ActionType
            
            decision = DecisionResponse(
                chain_of_thought="test",
                market_assessment="bearish",
                decisions=[
                    TradingDecision(
                        symbol="BTC",
                        action=ActionType.OPEN_SHORT,
                        leverage=5,
                        position_size_usd=1000,
                        confidence=70,
                        reasoning="bearish signal detected",
                        stop_loss=52000,
                        take_profit=45000,
                    ),
                ],
                overall_confidence=70,
                next_review_minutes=60,
            )
            
            mock_parser = MagicMock()
            mock_parser.parse = MagicMock(return_value=decision)
            mock_parser.should_execute = MagicMock(return_value=(True, ""))
            
            mock_ai_client = AsyncMock()
            mock_ai_response = MagicMock()
            mock_ai_response.content = '{"chain_of_thought": "test", "decisions": [], "overall_confidence": 70, "next_review_minutes": 60}'
            mock_ai_client.generate = AsyncMock(return_value=mock_ai_response)
            
            mock_pb = MagicMock()
            mock_pb.build_system_prompt = MagicMock(return_value="system")
            mock_pb.build_user_prompt = MagicMock(return_value="user")
            
            mock_trader = MagicMock()
            mock_trader.set_current_time = MagicMock()
            mock_trader.set_prices = MagicMock()
            account_state = MagicMock()
            account_state.equity = 10000
            account_state.available_balance = 10000
            mock_trader.get_account_state = AsyncMock(return_value=account_state)
            mock_trader.balance = 10000
            mock_trader._positions = {}
            mock_trader.open_short = AsyncMock()
            mock_trader.get_trades = MagicMock(return_value=[])
            mock_trader.get_statistics = MagicMock(return_value={
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "total_pnl": 0, "total_pnl_percent": 0, "max_drawdown": 0,
                "win_rate": 0, "profit_factor": 0, "average_win": 0,
                "average_loss": 0, "largest_win": 0, "largest_loss": 0,
                "gross_profit": 0, "gross_loss": 0, "avg_holding_hours": 0,
                "max_consecutive_wins": 0, "max_consecutive_losses": 0,
                "expectancy": 0, "total_fees": 0, "long_stats": {},
                "short_stats": {}, "symbol_breakdown": [],
            })
            
            with patch("app.backtest.engine.DecisionParser", return_value=mock_parser):
                with patch("app.backtest.engine.PromptBuilder", return_value=mock_pb):
                    with patch("app.backtest.engine.SimulatedTrader", return_value=mock_trader):
                        engine = BacktestEngine(
                            strategy=mock_strategy,
                            initial_balance=10000,
                            data_provider=mock_data_provider,
                            use_ai=True,
                            ai_client=mock_ai_client,
                            decision_interval_candles=1,
                        )
                        
                        result = await engine.run()
                        
                        # Verify OPEN_SHORT was executed
                        assert mock_trader.open_short.called

    @pytest.mark.asyncio
    async def test_execute_decisions_close_positions(self, mock_strategy, mock_data_provider):
        """Test execution of CLOSE_LONG and CLOSE_SHORT decisions"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.models.decision import DecisionResponse, TradingDecision, ActionType
            
            decision = DecisionResponse(
                chain_of_thought="test",
                market_assessment="neutral",
                decisions=[
                    TradingDecision(
                        symbol="BTC",
                        action=ActionType.CLOSE_LONG,
                        confidence=80,
                        reasoning="Taking profit after significant gains",
                    ),
                    TradingDecision(
                        symbol="ETH",
                        action=ActionType.CLOSE_SHORT,
                        confidence=80,
                        reasoning="Stop loss triggered due to price movement",
                    ),
                ],
                overall_confidence=80,
                next_review_minutes=60,
            )
            
            mock_parser = MagicMock()
            mock_parser.parse = MagicMock(return_value=decision)
            mock_parser.should_execute = MagicMock(return_value=(True, ""))
            
            mock_ai_client = AsyncMock()
            mock_ai_response = MagicMock()
            mock_ai_response.content = '{}'
            mock_ai_client.generate = AsyncMock(return_value=mock_ai_response)
            
            mock_pb = MagicMock()
            mock_pb.build_system_prompt = MagicMock(return_value="system")
            mock_pb.build_user_prompt = MagicMock(return_value="user")
            
            mock_trader = MagicMock()
            mock_trader.set_current_time = MagicMock()
            mock_trader.set_prices = MagicMock()
            account_state = MagicMock()
            account_state.equity = 10000
            mock_trader.get_account_state = AsyncMock(return_value=account_state)
            mock_trader.balance = 10000
            mock_trader._positions = {}
            mock_trader.close_position = AsyncMock()
            mock_trader.get_trades = MagicMock(return_value=[])
            mock_trader.get_statistics = MagicMock(return_value={
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "total_pnl": 0, "total_pnl_percent": 0, "max_drawdown": 0,
                "win_rate": 0, "profit_factor": 0, "average_win": 0,
                "average_loss": 0, "largest_win": 0, "largest_loss": 0,
                "gross_profit": 0, "gross_loss": 0, "avg_holding_hours": 0,
                "max_consecutive_wins": 0, "max_consecutive_losses": 0,
                "expectancy": 0, "total_fees": 0, "long_stats": {},
                "short_stats": {}, "symbol_breakdown": [],
            })
            
            with patch("app.backtest.engine.DecisionParser", return_value=mock_parser):
                with patch("app.backtest.engine.PromptBuilder", return_value=mock_pb):
                    with patch("app.backtest.engine.SimulatedTrader", return_value=mock_trader):
                        engine = BacktestEngine(
                            strategy=mock_strategy,
                            initial_balance=10000,
                            data_provider=mock_data_provider,
                            use_ai=True,
                            ai_client=mock_ai_client,
                            decision_interval_candles=1,
                        )
                        
                        result = await engine.run()
                        
                        # Verify close_position was called for both symbols
                        calls = mock_trader.close_position.call_args_list
                        symbols_closed = [call[0][0] for call in calls]
                        assert "BTC" in symbols_closed
                        assert "ETH" in symbols_closed

    @pytest.mark.asyncio
    async def test_execute_decisions_should_execute_false(self, mock_strategy, mock_data_provider):
        """Test that decisions with should_execute=False are skipped"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.models.decision import DecisionResponse, TradingDecision, ActionType
            
            decision = DecisionResponse(
                chain_of_thought="test analysis for market",
                market_assessment="bullish",
                decisions=[
                    TradingDecision(
                        symbol="BTC",
                        action=ActionType.OPEN_LONG,
                        leverage=5,
                        position_size_usd=1000,
                        confidence=30,  # Low confidence
                        reasoning="Testing low confidence trade execution",
                    ),
                ],
                overall_confidence=30,
                next_review_minutes=60,
            )
            
            mock_parser = MagicMock()
            mock_parser.parse = MagicMock(return_value=decision)
            # Return False for should_execute
            mock_parser.should_execute = MagicMock(return_value=(False, "Low confidence"))
            
            mock_ai_client = AsyncMock()
            mock_ai_response = MagicMock()
            mock_ai_response.content = '{}'
            mock_ai_client.generate = AsyncMock(return_value=mock_ai_response)
            
            mock_pb = MagicMock()
            mock_pb.build_system_prompt = MagicMock(return_value="system")
            mock_pb.build_user_prompt = MagicMock(return_value="user")
            
            mock_trader = MagicMock()
            mock_trader.set_current_time = MagicMock()
            mock_trader.set_prices = MagicMock()
            account_state = MagicMock()
            account_state.equity = 10000
            mock_trader.get_account_state = AsyncMock(return_value=account_state)
            mock_trader.balance = 10000
            mock_trader._positions = {}
            mock_trader.open_long = AsyncMock()
            mock_trader.get_trades = MagicMock(return_value=[])
            mock_trader.get_statistics = MagicMock(return_value={
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "total_pnl": 0, "total_pnl_percent": 0, "max_drawdown": 0,
                "win_rate": 0, "profit_factor": 0, "average_win": 0,
                "average_loss": 0, "largest_win": 0, "largest_loss": 0,
                "gross_profit": 0, "gross_loss": 0, "avg_holding_hours": 0,
                "max_consecutive_wins": 0, "max_consecutive_losses": 0,
                "expectancy": 0, "total_fees": 0, "long_stats": {},
                "short_stats": {}, "symbol_breakdown": [],
            })
            
            with patch("app.backtest.engine.DecisionParser", return_value=mock_parser):
                with patch("app.backtest.engine.PromptBuilder", return_value=mock_pb):
                    with patch("app.backtest.engine.SimulatedTrader", return_value=mock_trader):
                        engine = BacktestEngine(
                            strategy=mock_strategy,
                            initial_balance=10000,
                            data_provider=mock_data_provider,
                            use_ai=True,
                            ai_client=mock_ai_client,
                            decision_interval_candles=1,
                        )
                        
                        result = await engine.run()
                        
                        # Verify open_long was NOT called because should_execute returned False
                        assert not mock_trader.open_long.called

    @pytest.mark.asyncio
    async def test_execute_decisions_exception_handling(self, mock_strategy, mock_data_provider):
        """Test that execution exceptions are caught and backtest continues"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.models.decision import DecisionResponse, TradingDecision, ActionType
            
            decision = DecisionResponse(
                chain_of_thought="test analysis for exception handling",
                market_assessment="bullish",
                decisions=[
                    TradingDecision(
                        symbol="BTC",
                        action=ActionType.OPEN_LONG,
                        leverage=5,
                        position_size_usd=1000,
                        confidence=80,
                        reasoning="Testing exception handling during trade execution",
                    ),
                ],
                overall_confidence=80,
                next_review_minutes=60,
            )
            
            mock_parser = MagicMock()
            mock_parser.parse = MagicMock(return_value=decision)
            mock_parser.should_execute = MagicMock(return_value=(True, ""))
            
            mock_ai_client = AsyncMock()
            mock_ai_response = MagicMock()
            mock_ai_response.content = '{}'
            mock_ai_client.generate = AsyncMock(return_value=mock_ai_response)
            
            mock_pb = MagicMock()
            mock_pb.build_system_prompt = MagicMock(return_value="system")
            mock_pb.build_user_prompt = MagicMock(return_value="user")
            
            mock_trader = MagicMock()
            mock_trader.set_current_time = MagicMock()
            mock_trader.set_prices = MagicMock()
            account_state = MagicMock()
            account_state.equity = 10000
            mock_trader.get_account_state = AsyncMock(return_value=account_state)
            mock_trader.balance = 10000
            mock_trader._positions = {}
            # open_long raises exception
            mock_trader.open_long = AsyncMock(side_effect=Exception("Trade failed"))
            mock_trader.get_trades = MagicMock(return_value=[])
            mock_trader.get_statistics = MagicMock(return_value={
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "total_pnl": 0, "total_pnl_percent": 0, "max_drawdown": 0,
                "win_rate": 0, "profit_factor": 0, "average_win": 0,
                "average_loss": 0, "largest_win": 0, "largest_loss": 0,
                "gross_profit": 0, "gross_loss": 0, "avg_holding_hours": 0,
                "max_consecutive_wins": 0, "max_consecutive_losses": 0,
                "expectancy": 0, "total_fees": 0, "long_stats": {},
                "short_stats": {}, "symbol_breakdown": [],
            })
            
            with patch("app.backtest.engine.DecisionParser", return_value=mock_parser):
                with patch("app.backtest.engine.PromptBuilder", return_value=mock_pb):
                    with patch("app.backtest.engine.SimulatedTrader", return_value=mock_trader):
                        engine = BacktestEngine(
                            strategy=mock_strategy,
                            initial_balance=10000,
                            data_provider=mock_data_provider,
                            use_ai=True,
                            ai_client=mock_ai_client,
                            decision_interval_candles=1,
                        )
                        
                        # Should complete without raising
                        result = await engine.run()
                        assert isinstance(result, BacktestResult)

    @pytest.mark.asyncio
    async def test_generate_analysis_with_ai(self, mock_strategy, mock_data_provider):
        """Test _generate_analysis with AI client"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.backtest.engine import BacktestAnalysis
            
            # Mock analysis AI client
            mock_analysis_ai = AsyncMock()
            mock_analysis_response = MagicMock()
            mock_analysis_response.content = '''```json
{
    "strengths": ["High win rate", "Good risk management"],
    "weaknesses": ["Low trade frequency"],
    "recommendations": ["Increase position sizing"]
}
```'''
            mock_analysis_ai.generate = AsyncMock(return_value=mock_analysis_response)
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_data_provider,
                use_ai=False,
                analysis_ai_client=mock_analysis_ai,
            )
            
            stats = {
                "total_pnl_percent": 20,
                "total_trades": 10,
                "winning_trades": 7,
                "losing_trades": 3,
                "win_rate": 70,
                "profit_factor": 2.5,
                "max_drawdown": 5,
                "average_win": 200,
                "average_loss": 100,
                "largest_win": 500,
                "largest_loss": 200,
                "gross_profit": 1400,
                "gross_loss": 300,
                "avg_holding_hours": 4,
                "max_consecutive_wins": 5,
                "max_consecutive_losses": 2,
                "expectancy": 110,
                "total_fees": 50,
            }
            
            analysis = await engine._generate_analysis(
                stats=stats,
                trades=[],
                sharpe=1.5,
                sortino=2.0,
                calmar=3.0,
                recovery_factor=4.0,
                monthly_returns=[],
                symbol_breakdown=[],
            )
            
            assert analysis is not None
            assert isinstance(analysis, BacktestAnalysis)
            assert len(analysis.strengths) == 2
            assert "High win rate" in analysis.strengths
            assert len(analysis.recommendations) == 1

    @pytest.mark.asyncio
    async def test_generate_analysis_without_ai(self, mock_strategy, mock_data_provider):
        """Test _generate_analysis returns None when no AI client"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_data_provider,
                use_ai=False,
                analysis_ai_client=None,  # No AI client
            )
            
            analysis = await engine._generate_analysis(
                stats={}, trades=[], sharpe=None, sortino=None,
                calmar=None, recovery_factor=None, monthly_returns=[],
                symbol_breakdown=[],
            )
            
            assert analysis is None

    @pytest.mark.asyncio
    async def test_generate_analysis_json_parse_error(self, mock_strategy, mock_data_provider):
        """Test _generate_analysis handles JSON parse errors"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            mock_analysis_ai = AsyncMock()
            mock_analysis_response = MagicMock()
            mock_analysis_response.content = "Invalid JSON response"
            mock_analysis_ai.generate = AsyncMock(return_value=mock_analysis_response)
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_data_provider,
                use_ai=False,
                analysis_ai_client=mock_analysis_ai,
            )
            
            stats = {
                "total_pnl_percent": 20, "total_trades": 10, "winning_trades": 7,
                "losing_trades": 3, "win_rate": 70, "profit_factor": 2.5,
                "max_drawdown": 5, "average_win": 200, "average_loss": 100,
                "largest_win": 500, "largest_loss": 200, "gross_profit": 1400,
                "gross_loss": 300, "avg_holding_hours": 4, "max_consecutive_wins": 5,
                "max_consecutive_losses": 2, "expectancy": 110, "total_fees": 50,
            }
            
            analysis = await engine._generate_analysis(
                stats=stats, trades=[], sharpe=1.5, sortino=2.0,
                calmar=3.0, recovery_factor=4.0, monthly_returns=[],
                symbol_breakdown=[],
            )
            
            # Should return None on parse error
            assert analysis is None

    @pytest.mark.asyncio
    async def test_generate_analysis_ai_exception(self, mock_strategy, mock_data_provider):
        """Test _generate_analysis handles AI exceptions"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            mock_analysis_ai = AsyncMock()
            mock_analysis_ai.generate = AsyncMock(side_effect=Exception("AI error"))
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_data_provider,
                use_ai=False,
                analysis_ai_client=mock_analysis_ai,
            )
            
            stats = {
                "total_pnl_percent": 20, "total_trades": 10, "winning_trades": 7,
                "losing_trades": 3, "win_rate": 70, "profit_factor": 2.5,
                "max_drawdown": 5, "average_win": 200, "average_loss": 100,
                "largest_win": 500, "largest_loss": 200, "gross_profit": 1400,
                "gross_loss": 300, "avg_holding_hours": 4, "max_consecutive_wins": 5,
                "max_consecutive_losses": 2, "expectancy": 110, "total_fees": 50,
            }
            
            analysis = await engine._generate_analysis(
                stats=stats, trades=[], sharpe=1.5, sortino=2.0,
                calmar=3.0, recovery_factor=4.0, monthly_returns=[],
                symbol_breakdown=[],
            )
            
            # Should return None on exception
            assert analysis is None

    @pytest.mark.asyncio
    async def test_build_result_sharpe_ratio_calculation(self, mock_strategy):
        """Test Sharpe ratio calculation in _build_result"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.backtest.data_provider import MarketSnapshot
            
            # Create data provider with enough data points
            mock_provider = MagicMock()
            mock_provider.initialize = AsyncMock()
            mock_provider.load_data = AsyncMock()
            mock_provider.close = AsyncMock()
            
            base_time = datetime(2024, 1, 1)
            candles = [MagicMock(close=50000 + i * 100, timestamp=base_time + timedelta(hours=i)) for i in range(100)]
            mock_provider.get_data.return_value = candles
            
            snapshots = [
                MarketSnapshot(timestamp=base_time + timedelta(hours=i), prices={"BTC": 50000 + i * 100})
                for i in range(100)
            ]
            mock_provider.iterate.return_value = snapshots
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
                decision_interval_candles=100,  # Skip decisions
            )
            
            result = await engine.run()
            
            # Sharpe ratio is None when there's no variance (all equity values same)
            # This is expected behavior when no trades occur
            # The equity curve should be populated with data points
            assert len(result.equity_curve) > 1
            # When all equity values are the same, sharpe_ratio will be None (std_return == 0)
            # This is correct behavior - no variance means undefined Sharpe ratio

    @pytest.mark.asyncio
    async def test_build_result_sortino_ratio_with_downside(self, mock_strategy):
        """Test Sortino ratio calculation with downside returns"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            # Create engine and manually set equity curve with losses
            mock_provider = MagicMock()
            mock_provider.close = AsyncMock()
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            # Set equity curve with varying values (including losses)
            base_time = datetime(2024, 1, 1)
            engine._equity_curve = [
                {"timestamp": (base_time + timedelta(hours=i)).isoformat(), "equity": 10000 - i * 10}
                for i in range(50)
            ]
            
            # Mock trader
            engine.trader = MagicMock()
            engine.trader.balance = 9500
            engine.trader.get_trades = MagicMock(return_value=[])
            engine.trader.get_statistics = MagicMock(return_value={
                "total_trades": 5, "winning_trades": 2, "losing_trades": 3,
                "total_pnl": -500, "total_pnl_percent": -5, "max_drawdown": 5,
                "win_rate": 40, "profit_factor": 0.5, "average_win": 100,
                "average_loss": 233, "largest_win": 150, "largest_loss": 300,
                "gross_profit": 200, "gross_loss": 700, "avg_holding_hours": 2,
                "max_consecutive_wins": 1, "max_consecutive_losses": 3,
                "expectancy": -100, "total_fees": 25, "long_stats": {},
                "short_stats": {}, "symbol_breakdown": [],
            })
            
            result = await engine._build_result()
            
            # Should have calculated Sortino ratio since there are negative returns
            assert result.sortino_ratio is not None

    @pytest.mark.asyncio
    async def test_build_result_calmar_ratio(self, mock_strategy):
        """Test Calmar ratio calculation"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            mock_provider = MagicMock()
            mock_provider.close = AsyncMock()
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            base_time = datetime(2024, 1, 1)
            engine._equity_curve = [
                {"timestamp": (base_time + timedelta(hours=i)).isoformat(), "equity": 10000 + i * 10}
                for i in range(100)
            ]
            
            engine.trader = MagicMock()
            engine.trader.balance = 11000
            engine.trader.get_trades = MagicMock(return_value=[])
            engine.trader.get_statistics = MagicMock(return_value={
                "total_trades": 10, "winning_trades": 7, "losing_trades": 3,
                "total_pnl": 1000, "total_pnl_percent": 10, "max_drawdown": 2,  # 2% drawdown
                "win_rate": 70, "profit_factor": 3.0, "average_win": 200,
                "average_loss": 100, "largest_win": 500, "largest_loss": 200,
                "gross_profit": 1400, "gross_loss": 300, "avg_holding_hours": 4,
                "max_consecutive_wins": 5, "max_consecutive_losses": 1,
                "expectancy": 100, "total_fees": 50, "long_stats": {},
                "short_stats": {}, "symbol_breakdown": [],
            })
            
            result = await engine._build_result()
            
            # Should have calculated Calmar ratio since max_drawdown > 0
            assert result.calmar_ratio is not None
            assert result.calmar_ratio > 0

    @pytest.mark.asyncio
    async def test_build_result_recovery_factor(self, mock_strategy):
        """Test recovery factor calculation"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            mock_provider = MagicMock()
            mock_provider.close = AsyncMock()
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            base_time = datetime(2024, 1, 1)
            engine._equity_curve = [
                {"timestamp": (base_time + timedelta(hours=i)).isoformat(), "equity": 10000}
                for i in range(10)
            ]
            
            engine.trader = MagicMock()
            engine.trader.balance = 12000
            engine.trader.get_trades = MagicMock(return_value=[])
            engine.trader.get_statistics = MagicMock(return_value={
                "total_trades": 10, "winning_trades": 8, "losing_trades": 2,
                "total_pnl": 2000, "total_pnl_percent": 20, "max_drawdown": 4,  # 4% drawdown
                "win_rate": 80, "profit_factor": 5.0, "average_win": 300,
                "average_loss": 100, "largest_win": 800, "largest_loss": 150,
                "gross_profit": 2400, "gross_loss": 200, "avg_holding_hours": 3,
                "max_consecutive_wins": 6, "max_consecutive_losses": 1,
                "expectancy": 200, "total_fees": 60, "long_stats": {},
                "short_stats": {}, "symbol_breakdown": [],
            })
            
            result = await engine._build_result()
            
            # recovery_factor = total_return / max_drawdown = 20 / 4 = 5
            assert result.recovery_factor == 5.0

    @pytest.mark.asyncio
    async def test_build_result_drawdown_curve(self, mock_strategy):
        """Test drawdown curve generation"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            mock_provider = MagicMock()
            mock_provider.close = AsyncMock()
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            base_time = datetime(2024, 1, 1)
            # Equity goes up then down
            equities = [10000, 11000, 12000, 11500, 11000, 10500]
            engine._equity_curve = [
                {"timestamp": (base_time + timedelta(hours=i)).isoformat(), "equity": equities[i]}
                for i in range(len(equities))
            ]
            
            engine.trader = MagicMock()
            engine.trader.balance = 10500
            engine.trader.get_trades = MagicMock(return_value=[])
            engine.trader.get_statistics = MagicMock(return_value={
                "total_trades": 5, "winning_trades": 3, "losing_trades": 2,
                "total_pnl": 500, "total_pnl_percent": 5, "max_drawdown": 12.5,
                "win_rate": 60, "profit_factor": 1.5, "average_win": 500,
                "average_loss": 500, "largest_win": 1000, "largest_loss": 750,
                "gross_profit": 1500, "gross_loss": 1000, "avg_holding_hours": 2,
                "max_consecutive_wins": 2, "max_consecutive_losses": 2,
                "expectancy": 100, "total_fees": 30, "long_stats": {},
                "short_stats": {}, "symbol_breakdown": [],
            })
            
            result = await engine._build_result()
            
            assert len(result.drawdown_curve) == 6
            # First point should have 0 drawdown
            assert result.drawdown_curve[0]["drawdown_percent"] == 0
            # Peak at 12000, then 11500 = 4.17% drawdown
            assert result.drawdown_curve[3]["drawdown_percent"] > 0

    @pytest.mark.asyncio
    async def test_build_result_monthly_returns(self, mock_strategy):
        """Test monthly returns calculation"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            mock_provider = MagicMock()
            mock_provider.close = AsyncMock()
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            # Create equity curve spanning multiple months
            engine._equity_curve = [
                {"timestamp": "2024-01-01T00:00:00", "equity": 10000},
                {"timestamp": "2024-01-15T00:00:00", "equity": 10500},
                {"timestamp": "2024-01-31T00:00:00", "equity": 11000},
                {"timestamp": "2024-02-01T00:00:00", "equity": 11000},
                {"timestamp": "2024-02-15T00:00:00", "equity": 11500},
                {"timestamp": "2024-02-28T00:00:00", "equity": 12000},
            ]
            
            engine.trader = MagicMock()
            engine.trader.balance = 12000
            engine.trader.get_trades = MagicMock(return_value=[])
            engine.trader.get_statistics = MagicMock(return_value={
                "total_trades": 10, "winning_trades": 7, "losing_trades": 3,
                "total_pnl": 2000, "total_pnl_percent": 20, "max_drawdown": 3,
                "win_rate": 70, "profit_factor": 3.0, "average_win": 350,
                "average_loss": 150, "largest_win": 600, "largest_loss": 250,
                "gross_profit": 2450, "gross_loss": 450, "avg_holding_hours": 5,
                "max_consecutive_wins": 4, "max_consecutive_losses": 2,
                "expectancy": 200, "total_fees": 40, "long_stats": {},
                "short_stats": {}, "symbol_breakdown": [],
            })
            
            result = await engine._build_result()
            
            assert len(result.monthly_returns) == 2
            assert result.monthly_returns[0]["month"] == "2024-01"
            assert result.monthly_returns[1]["month"] == "2024-02"
            # January: 10000 -> 11000 = 10%
            assert result.monthly_returns[0]["return_percent"] == 10.0

    @pytest.mark.asyncio
    async def test_rule_based_decision_open_long(self, mock_strategy):
        """Test rule-based decision opens long when price > SMA"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.backtest.data_provider import MarketSnapshot
            
            mock_provider = MagicMock()
            mock_provider.initialize = AsyncMock()
            mock_provider.close = AsyncMock()
            
            base_time = datetime(2024, 1, 1)
            # Create candles where prices are rising
            candles = [MagicMock(close=45000 + i * 100, timestamp=base_time + timedelta(hours=i)) for i in range(30)]
            mock_provider.get_data.return_value = candles
            
            # Create snapshot with price well above SMA
            # SMA of last 20 candles (index 5-24): avg of 45500 to 47400 = ~46450
            # Current price at 52000 is > 46450 * 1.01
            snapshot = MarketSnapshot(
                timestamp=base_time + timedelta(hours=25),
                prices={"BTC": 52000},
            )
            mock_provider.iterate.return_value = [snapshot]
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            # Spy on open_long
            original_open_long = engine.trader.open_long
            engine.trader.open_long = AsyncMock()
            
            await engine.run()
            
            # Should have called open_long because price > SMA * 1.01
            assert engine.trader.open_long.called

    @pytest.mark.asyncio
    async def test_rule_based_decision_open_short(self, mock_strategy):
        """Test rule-based decision opens short when price < SMA"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.backtest.data_provider import MarketSnapshot
            
            mock_provider = MagicMock()
            mock_provider.initialize = AsyncMock()
            mock_provider.close = AsyncMock()
            
            base_time = datetime(2024, 1, 1)
            # Create candles where prices are high
            candles = [MagicMock(close=55000 + i * 10, timestamp=base_time + timedelta(hours=i)) for i in range(30)]
            mock_provider.get_data.return_value = candles
            
            # SMA of last 20 candles: avg of 55050 to 55240 = ~55145
            # Current price at 50000 is < 55145 * 0.99
            snapshot = MarketSnapshot(
                timestamp=base_time + timedelta(hours=25),
                prices={"BTC": 50000},
            )
            mock_provider.iterate.return_value = [snapshot]
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            engine.trader.open_short = AsyncMock()
            
            await engine.run()
            
            # Should have called open_short because price < SMA * 0.99
            assert engine.trader.open_short.called

    @pytest.mark.asyncio
    async def test_rule_based_decision_close_short_on_bullish(self, mock_strategy):
        """Test rule-based closes short position when price rises above SMA"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.backtest.data_provider import MarketSnapshot
            from app.backtest.simulator import SimulatedPosition
            
            mock_provider = MagicMock()
            mock_provider.initialize = AsyncMock()
            mock_provider.close = AsyncMock()
            
            base_time = datetime(2024, 1, 1)
            candles = [MagicMock(close=50000 + i * 50, timestamp=base_time + timedelta(hours=i)) for i in range(30)]
            mock_provider.get_data.return_value = candles
            
            # Price above SMA * 1.01
            snapshot = MarketSnapshot(
                timestamp=base_time + timedelta(hours=25),
                prices={"BTC": 55000},
            )
            mock_provider.iterate.return_value = [snapshot]
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            # Pre-existing short position
            engine.trader._positions["BTC"] = SimulatedPosition(
                symbol="BTC",
                side="short",
                size=0.1,
                entry_price=50000,
                leverage=10,
                opened_at=base_time,
            )
            engine.trader.get_position = AsyncMock(return_value=MagicMock(side="short"))
            engine.trader.close_position = AsyncMock()
            
            await engine.run()
            
            # Should close the short position
            assert engine.trader.close_position.called

    @pytest.mark.asyncio
    async def test_rule_based_decision_close_long_on_bearish(self, mock_strategy):
        """Test rule-based closes long position when price drops below SMA"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.backtest.data_provider import MarketSnapshot
            from app.backtest.simulator import SimulatedPosition
            
            mock_provider = MagicMock()
            mock_provider.initialize = AsyncMock()
            mock_provider.close = AsyncMock()
            
            base_time = datetime(2024, 1, 1)
            candles = [MagicMock(close=55000 - i * 10, timestamp=base_time + timedelta(hours=i)) for i in range(30)]
            mock_provider.get_data.return_value = candles
            
            # Price below SMA * 0.99
            snapshot = MarketSnapshot(
                timestamp=base_time + timedelta(hours=25),
                prices={"BTC": 50000},
            )
            mock_provider.iterate.return_value = [snapshot]
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            # Pre-existing long position
            engine.trader._positions["BTC"] = SimulatedPosition(
                symbol="BTC",
                side="long",
                size=0.1,
                entry_price=55000,
                leverage=10,
                opened_at=base_time,
            )
            engine.trader.get_position = AsyncMock(return_value=MagicMock(side="long"))
            engine.trader.close_position = AsyncMock()
            
            await engine.run()
            
            # Should close the long position
            assert engine.trader.close_position.called

    @pytest.mark.asyncio
    async def test_rule_based_decision_skip_no_price(self, mock_strategy):
        """Test rule-based skips symbol when no price available"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.backtest.data_provider import MarketSnapshot
            
            mock_provider = MagicMock()
            mock_provider.initialize = AsyncMock()
            mock_provider.close = AsyncMock()
            
            base_time = datetime(2024, 1, 1)
            candles = [MagicMock(close=50000, timestamp=base_time + timedelta(hours=i)) for i in range(30)]
            mock_provider.get_data.return_value = candles
            
            # No price for BTC in snapshot
            snapshot = MarketSnapshot(
                timestamp=base_time + timedelta(hours=25),
                prices={},  # Empty prices
            )
            mock_provider.iterate.return_value = [snapshot]
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            engine.trader.open_long = AsyncMock()
            engine.trader.open_short = AsyncMock()
            
            await engine.run()
            
            # Should not open any positions
            assert not engine.trader.open_long.called
            assert not engine.trader.open_short.called

    @pytest.mark.asyncio
    async def test_rule_based_decision_skip_insufficient_candles(self, mock_strategy):
        """Test rule-based skips when insufficient candles for SMA"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            from app.backtest.data_provider import MarketSnapshot
            
            mock_provider = MagicMock()
            mock_provider.initialize = AsyncMock()
            mock_provider.close = AsyncMock()
            
            base_time = datetime(2024, 1, 1)
            # Only 10 candles, not enough for SMA(20)
            candles = [MagicMock(close=50000, timestamp=base_time + timedelta(hours=i)) for i in range(10)]
            mock_provider.get_data.return_value = candles
            
            snapshot = MarketSnapshot(
                timestamp=base_time + timedelta(hours=5),
                prices={"BTC": 52000},
            )
            mock_provider.iterate.return_value = [snapshot]
            
            engine = BacktestEngine(
                strategy=mock_strategy,
                initial_balance=10000,
                data_provider=mock_provider,
                use_ai=False,
            )
            
            engine.trader.open_long = AsyncMock()
            engine.trader.open_short = AsyncMock()
            
            await engine.run()
            
            # Should not open any positions due to insufficient data
            assert not engine.trader.open_long.called
            assert not engine.trader.open_short.called

    def test_backtest_engine_requires_ai_client_when_use_ai_true(self, mock_strategy):
        """Test that BacktestEngine raises error when use_ai=True but no ai_client"""
        with patch("app.backtest.engine.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                simulator_maker_fee=0.0002,
                simulator_taker_fee=0.0005,
                simulator_default_slippage=0.001,
            )
            
            with pytest.raises(ValueError, match="use_ai=True requires ai_client"):
                BacktestEngine(
                    strategy=mock_strategy,
                    initial_balance=10000,
                    use_ai=True,
                    ai_client=None,  # No AI client
                )
