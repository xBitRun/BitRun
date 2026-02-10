"""
Tests for Quantitative Strategy Engines.

Covers:
- GridEngine: grid level calculation, buy/sell signals, state persistence
- DCAEngine: order placement, take profit, budget/order limits, running average
- RSIEngine: oversold/overbought signals, RSI calculation, insufficient data
- create_engine() factory function
"""

import pytest
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.quant_engine import (
    GridEngine,
    DCAEngine,
    RSIEngine,
    QuantEngineBase,
    create_engine,
)
from app.traders.base import TradeError, OrderResult


# ── Helpers ──────────────────────────────────────────────────────────


@dataclass
class MockKline:
    """Lightweight kline stub with a .close attribute."""
    close: float


def _mock_trader(mark_price: float = 50000.0):
    """Create a mock trader with configured market data."""
    trader = AsyncMock()
    market_data = MagicMock()
    market_data.mark_price = mark_price
    trader.get_market_data = AsyncMock(return_value=market_data)
    trader.open_long = AsyncMock(return_value=OrderResult(success=True))
    trader.close_position = AsyncMock(return_value=OrderResult(success=True))
    trader.get_klines = AsyncMock(return_value=[])
    return trader


# ── GridEngine ───────────────────────────────────────────────────────


class TestGridEngine:
    """Tests for GridEngine."""

    @pytest.fixture
    def grid_config(self):
        return {
            "upper_price": 110.0,
            "lower_price": 90.0,
            "grid_count": 4,
            "total_investment": 400.0,
            "leverage": 2.0,
        }

    @pytest.mark.asyncio
    async def test_initial_setup_calculates_grid_levels(self, grid_config):
        """First run initializes grid levels correctly."""
        trader = _mock_trader(mark_price=100.0)
        engine = GridEngine(
            strategy_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        state = result["updated_state"]
        assert state["initialized"] is True
        # step = (110-90)/4 = 5 → levels: [90, 95, 100, 105, 110]
        assert state["grid_levels"] == [90.0, 95.0, 100.0, 105.0, 110.0]

    @pytest.mark.asyncio
    async def test_buy_signal_below_all_levels(self, grid_config):
        """Price below all grid levels triggers buys at every level."""
        trader = _mock_trader(mark_price=88.0)
        engine = GridEngine(
            strategy_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        # 88 <= all 5 levels → 5 buys
        assert result["trades_executed"] == 5
        assert trader.open_long.call_count == 5

    @pytest.mark.asyncio
    async def test_sell_signal_triggered(self, grid_config):
        """Pre-filled buys + high price → sells fire."""
        trader = _mock_trader(mark_price=120.0)
        runtime_state = {
            "initialized": True,
            "config_hash": "110.0:90.0:4",
            "grid_levels": [90.0, 95.0, 100.0, 105.0, 110.0],
            "filled_buys": ["0", "1"],
            "filled_sells": [],
            "total_invested": 200.0,
            "total_returned": 0.0,
        }
        engine = GridEngine(
            strategy_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        # 120 >= 90+5=95 (sell 0), 120 >= 95+5=100 (sell 1) → 2 sells
        assert result["trades_executed"] == 2
        assert trader.close_position.call_count == 2

    @pytest.mark.asyncio
    async def test_no_trades_when_price_above_grid_no_buys(self, grid_config):
        """Price above all levels, no filled buys → zero trades."""
        trader = _mock_trader(mark_price=112.0)
        runtime_state = {
            "initialized": True,
            "config_hash": "110.0:90.0:4",
            "grid_levels": [90.0, 95.0, 100.0, 105.0, 110.0],
            "filled_buys": [],
            "filled_sells": [],
            "total_invested": 0.0,
            "total_returned": 0.0,
        }
        engine = GridEngine(
            strategy_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0

    @pytest.mark.asyncio
    async def test_state_persistence(self, grid_config):
        """Runtime state records last_price and last_check."""
        trader = _mock_trader(mark_price=100.0)
        engine = GridEngine(
            strategy_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state={},
        )

        result = await engine.run_cycle()

        state = result["updated_state"]
        assert state["last_price"] == 100.0
        assert "last_check" in state

    @pytest.mark.asyncio
    async def test_trade_error_continues_cycle(self, grid_config):
        """TradeError on open_long is caught per level; cycle still succeeds."""
        trader = _mock_trader(mark_price=88.0)
        trader.open_long = AsyncMock(side_effect=TradeError("Insufficient margin"))

        engine = GridEngine(
            strategy_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0

    @pytest.mark.asyncio
    async def test_general_error_returns_failure(self):
        """Missing config keys → KeyError → failure result."""
        trader = _mock_trader()
        engine = GridEngine(
            strategy_id="g1", trader=trader, symbol="BTC",
            config={},  # missing upper_price, lower_price, etc.
            runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is False
        assert "Error" in result["message"]

    @pytest.mark.asyncio
    async def test_pnl_positive_on_sell(self, grid_config):
        """Selling a previously bought grid level yields positive PnL."""
        trader = _mock_trader(mark_price=120.0)
        runtime_state = {
            "initialized": True,
            "config_hash": "110.0:90.0:4",
            "grid_levels": [90.0, 95.0, 100.0, 105.0, 110.0],
            "filled_buys": ["0"],
            "filled_sells": [],
            "total_invested": 100.0,
            "total_returned": 0.0,
        }
        engine = GridEngine(
            strategy_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        assert result["pnl_change"] > 0


# ── DCAEngine ────────────────────────────────────────────────────────


class TestDCAEngine:
    """Tests for DCAEngine."""

    @pytest.fixture
    def dca_config(self):
        return {
            "order_amount": 100.0,
            "interval_minutes": 60,
            "take_profit_percent": 5.0,
            "total_budget": 1000.0,
            "max_orders": 10,
        }

    @pytest.mark.asyncio
    async def test_first_order_placed(self, dca_config):
        """First cycle initializes state and places a buy."""
        trader = _mock_trader(mark_price=50000.0)
        engine = DCAEngine(
            strategy_id="d1", trader=trader, symbol="BTC",
            config=dca_config, runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 1
        trader.open_long.assert_called_once()
        state = result["updated_state"]
        assert state["orders_placed"] == 1
        assert state["total_invested"] == 100.0

    @pytest.mark.asyncio
    async def test_take_profit_triggered(self, dca_config):
        """Price above avg_cost + TP% → sell all, positive PnL."""
        trader = _mock_trader(mark_price=55000.0)  # +10% from avg
        runtime_state = {
            "initialized": True,
            "orders_placed": 5,
            "total_invested": 500.0,
            "total_quantity": 0.01,  # bought at ~50000
            "avg_cost": 50000.0,
            "last_order_time": None,
        }
        engine = DCAEngine(
            strategy_id="d1", trader=trader, symbol="BTC",
            config=dca_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 1
        assert result["pnl_change"] > 0
        trader.close_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_take_profit_below_threshold(self, dca_config):
        """Price slightly up but below TP% → buy, no sell."""
        trader = _mock_trader(mark_price=51000.0)  # +2% < 5% TP
        runtime_state = {
            "initialized": True,
            "orders_placed": 1,
            "total_invested": 100.0,
            "total_quantity": 0.002,
            "avg_cost": 50000.0,
            "last_order_time": None,
        }
        engine = DCAEngine(
            strategy_id="d1", trader=trader, symbol="BTC",
            config=dca_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        assert result["trades_executed"] == 1  # only buy
        trader.open_long.assert_called_once()
        trader.close_position.assert_not_called()

    @pytest.mark.asyncio
    async def test_budget_limit_reached(self, dca_config):
        """Total invested >= budget → no more orders."""
        trader = _mock_trader(mark_price=50000.0)
        runtime_state = {
            "initialized": True,
            "orders_placed": 10,
            "total_invested": 1000.0,  # == total_budget
            "total_quantity": 0.02,
            "avg_cost": 50000.0,
            "last_order_time": None,
        }
        engine = DCAEngine(
            strategy_id="d1", trader=trader, symbol="BTC",
            config=dca_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0
        assert "Budget limit" in result["message"]

    @pytest.mark.asyncio
    async def test_max_orders_reached(self, dca_config):
        """Max orders reached → no more buys."""
        trader = _mock_trader(mark_price=50000.0)
        runtime_state = {
            "initialized": True,
            "orders_placed": 10,  # == max_orders
            "total_invested": 500.0,
            "total_quantity": 0.01,
            "avg_cost": 50000.0,
            "last_order_time": None,
        }
        engine = DCAEngine(
            strategy_id="d1", trader=trader, symbol="BTC",
            config=dca_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0
        assert "Max orders" in result["message"]

    @pytest.mark.asyncio
    async def test_running_average_calculation(self, dca_config):
        """Average cost updates correctly after a second buy."""
        trader = _mock_trader(mark_price=50000.0)
        runtime_state = {
            "initialized": True,
            "orders_placed": 1,
            "total_invested": 100.0,
            "total_quantity": 0.002,  # 100/50000
            "avg_cost": 50000.0,
            "last_order_time": None,
        }
        engine = DCAEngine(
            strategy_id="d1", trader=trader, symbol="BTC",
            config=dca_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        state = result["updated_state"]
        assert state["orders_placed"] == 2
        assert state["total_invested"] == 200.0
        assert state["total_quantity"] == pytest.approx(0.004, rel=1e-3)
        assert state["avg_cost"] == pytest.approx(50000.0, rel=1e-3)

    @pytest.mark.asyncio
    async def test_trade_error_on_buy(self, dca_config):
        """TradeError during buy → trades_executed stays 0."""
        trader = _mock_trader(mark_price=50000.0)
        trader.open_long = AsyncMock(side_effect=TradeError("Insufficient margin"))

        engine = DCAEngine(
            strategy_id="d1", trader=trader, symbol="BTC",
            config=dca_config, runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0

    @pytest.mark.asyncio
    async def test_general_error_returns_failure(self):
        """Missing config key → exception → failure result."""
        trader = _mock_trader()
        engine = DCAEngine(
            strategy_id="d1", trader=trader, symbol="BTC",
            config={},  # missing "order_amount"
            runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is False
        assert "Error" in result["message"]


# ── RSIEngine ────────────────────────────────────────────────────────


class TestRSIEngine:
    """Tests for RSIEngine."""

    @pytest.fixture
    def rsi_config(self):
        return {
            "rsi_period": 14,
            "overbought_threshold": 70.0,
            "oversold_threshold": 30.0,
            "order_amount": 100.0,
            "timeframe": "1h",
            "leverage": 2.0,
        }

    @pytest.mark.asyncio
    async def test_buy_signal_oversold(self, rsi_config):
        """RSI below oversold threshold → open long."""
        trader = _mock_trader(mark_price=50000.0)
        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=25.0,
        ):
            result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 1
        trader.open_long.assert_called_once()
        state = result["updated_state"]
        assert state["has_position"] is True
        assert state["last_signal"] == "buy"

    @pytest.mark.asyncio
    async def test_sell_signal_overbought(self, rsi_config):
        """RSI above overbought with existing position → close with profit."""
        trader = _mock_trader(mark_price=55000.0)
        runtime_state = {
            "initialized": True,
            "has_position": True,
            "entry_price": 50000.0,
            "position_size_usd": 100.0,
            "last_rsi": None,
            "last_signal": "buy",
        }
        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state=runtime_state,
        )

        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=75.0,
        ):
            result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 1
        assert result["pnl_change"] > 0
        trader.close_position.assert_called_once()
        state = result["updated_state"]
        assert state["has_position"] is False
        assert state["last_signal"] == "sell"

    @pytest.mark.asyncio
    async def test_no_signal_neutral_rsi(self, rsi_config):
        """RSI in neutral zone → no trades."""
        trader = _mock_trader(mark_price=50000.0)
        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=50.0,
        ):
            result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0

    @pytest.mark.asyncio
    async def test_no_buy_when_already_has_position(self, rsi_config):
        """RSI oversold but already has position → no buy."""
        trader = _mock_trader(mark_price=50000.0)
        runtime_state = {
            "initialized": True,
            "has_position": True,
            "entry_price": 48000.0,
            "position_size_usd": 100.0,
            "last_rsi": None,
            "last_signal": "buy",
        }
        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state=runtime_state,
        )

        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=25.0,
        ):
            result = await engine.run_cycle()

        assert result["trades_executed"] == 0
        trader.open_long.assert_not_called()

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_early(self, rsi_config):
        """_calculate_rsi returns None → graceful early return."""
        trader = _mock_trader(mark_price=50000.0)
        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=None,
        ):
            result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0
        assert "Insufficient" in result["message"]

    @pytest.mark.asyncio
    async def test_rsi_calculation_all_up(self, rsi_config):
        """All prices rising → RSI = 100."""
        trader = _mock_trader(mark_price=125.0)
        klines = [MockKline(close=float(100 + i)) for i in range(25)]
        trader.get_klines = AsyncMock(return_value=klines)

        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        rsi = await engine._calculate_rsi("1h", 14)

        assert rsi == 100.0

    @pytest.mark.asyncio
    async def test_rsi_calculation_all_down(self, rsi_config):
        """All prices falling → RSI ≈ 0."""
        trader = _mock_trader(mark_price=75.0)
        klines = [MockKline(close=float(200 - i)) for i in range(25)]
        trader.get_klines = AsyncMock(return_value=klines)

        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        rsi = await engine._calculate_rsi("1h", 14)

        assert rsi is not None
        assert rsi == pytest.approx(0.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_rsi_calculation_insufficient_klines(self, rsi_config):
        """Not enough klines → returns None."""
        trader = _mock_trader()
        klines = [MockKline(close=100.0) for _ in range(5)]
        trader.get_klines = AsyncMock(return_value=klines)

        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        rsi = await engine._calculate_rsi("1h", 14)

        assert rsi is None

    @pytest.mark.asyncio
    async def test_state_persistence_after_buy(self, rsi_config):
        """After buy, state records entry_price and position_size_usd."""
        trader = _mock_trader(mark_price=50000.0)
        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=25.0,
        ):
            result = await engine.run_cycle()

        state = result["updated_state"]
        assert state["entry_price"] == 50000.0
        assert state["position_size_usd"] == 100.0
        assert "last_check" in state

    @pytest.mark.asyncio
    async def test_error_handling(self, rsi_config):
        """Market data error → exception → failure result."""
        trader = _mock_trader()
        trader.get_market_data = AsyncMock(
            side_effect=Exception("Connection error")
        )

        engine = RSIEngine(
            strategy_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is False
        assert "Error" in result["message"]


# ── create_engine() Factory ──────────────────────────────────────────


class TestCreateEngine:
    """Tests for create_engine() factory function."""

    def test_create_grid_engine(self):
        trader = _mock_trader()
        engine = create_engine("grid", "s1", trader, "BTC", {"upper_price": 100}, {})

        assert isinstance(engine, GridEngine)
        assert engine.strategy_id == "s1"

    def test_create_dca_engine(self):
        trader = _mock_trader()
        engine = create_engine("dca", "s2", trader, "ETH", {"order_amount": 50}, {})

        assert isinstance(engine, DCAEngine)
        assert engine.symbol == "ETH"

    def test_create_rsi_engine(self):
        trader = _mock_trader()
        engine = create_engine("rsi", "s3", trader, "BTC", {"order_amount": 100}, {})

        assert isinstance(engine, RSIEngine)

    def test_unknown_type_raises_error(self):
        trader = _mock_trader()
        with pytest.raises(ValueError, match="Unknown strategy type"):
            create_engine("unknown", "s4", trader, "BTC", {}, {})
