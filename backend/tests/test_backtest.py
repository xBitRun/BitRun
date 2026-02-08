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
