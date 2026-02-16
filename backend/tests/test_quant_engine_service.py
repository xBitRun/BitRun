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
            agent_id="g1", trader=trader, symbol="BTC",
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
            agent_id="g1", trader=trader, symbol="BTC",
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
            agent_id="g1", trader=trader, symbol="BTC",
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
            agent_id="g1", trader=trader, symbol="BTC",
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
            agent_id="g1", trader=trader, symbol="BTC",
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
            agent_id="g1", trader=trader, symbol="BTC",
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
            agent_id="g1", trader=trader, symbol="BTC",
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
            agent_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        assert result["pnl_change"] > 0


    @pytest.mark.asyncio
    async def test_sell_trade_error_continues(self, grid_config):
        """TradeError during sell is caught per level; cycle still succeeds."""
        trader = _mock_trader(mark_price=120.0)
        trader.close_position = AsyncMock(side_effect=TradeError("Insufficient margin"))
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
            agent_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state=runtime_state,
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0  # Sells failed but cycle succeeded

    @pytest.mark.asyncio
    async def test_capital_exceeded_on_buy(self, grid_config):
        """CapitalExceededError during open_with_isolation returns failed order."""
        from app.services.position_service import CapitalExceededError

        trader = _mock_trader(mark_price=88.0)
        # Patch _open_with_isolation to simulate CapitalExceededError
        # CapitalExceededError is caught inside _open_with_isolation and returns
        # OrderResult(success=False), so open_long never fires but the engine
        # sees success=False and skips the level.
        trader.open_long = AsyncMock(
            return_value=OrderResult(success=False, error="Capital exceeded")
        )

        engine = GridEngine(
            agent_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0


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
            agent_id="d1", trader=trader, symbol="BTC",
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
            agent_id="d1", trader=trader, symbol="BTC",
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
            agent_id="d1", trader=trader, symbol="BTC",
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
            agent_id="d1", trader=trader, symbol="BTC",
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
            agent_id="d1", trader=trader, symbol="BTC",
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
            agent_id="d1", trader=trader, symbol="BTC",
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
            agent_id="d1", trader=trader, symbol="BTC",
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
            agent_id="d1", trader=trader, symbol="BTC",
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
            agent_id="r1", trader=trader, symbol="BTC",
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
            agent_id="r1", trader=trader, symbol="BTC",
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
            agent_id="r1", trader=trader, symbol="BTC",
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
            agent_id="r1", trader=trader, symbol="BTC",
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
            agent_id="r1", trader=trader, symbol="BTC",
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
            agent_id="r1", trader=trader, symbol="BTC",
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
            agent_id="r1", trader=trader, symbol="BTC",
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
            agent_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        rsi = await engine._calculate_rsi("1h", 14)

        assert rsi is None

    @pytest.mark.asyncio
    async def test_state_persistence_after_buy(self, rsi_config):
        """After buy, state records entry_price and position_size_usd."""
        trader = _mock_trader(mark_price=50000.0)
        engine = RSIEngine(
            agent_id="r1", trader=trader, symbol="BTC",
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
            agent_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        result = await engine.run_cycle()

        assert result["success"] is False
        assert "Error" in result["message"]

    @pytest.mark.asyncio
    async def test_trade_error_on_sell(self, rsi_config):
        """TradeError during sell (close_position) is caught; cycle succeeds."""
        trader = _mock_trader(mark_price=55000.0)
        trader.close_position = AsyncMock(side_effect=TradeError("Exchange error"))
        trader.get_position = AsyncMock(return_value=None)
        runtime_state = {
            "initialized": True,
            "has_position": True,
            "entry_price": 50000.0,
            "position_size_usd": 100.0,
            "last_rsi": None,
            "last_signal": "buy",
        }
        engine = RSIEngine(
            agent_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state=runtime_state,
        )

        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=75.0,
        ):
            result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0  # Sell failed, caught by TradeError

    @pytest.mark.asyncio
    async def test_trade_error_on_buy(self, rsi_config):
        """TradeError during buy is caught; cycle succeeds with zero trades."""
        trader = _mock_trader(mark_price=50000.0)
        trader.open_long = AsyncMock(side_effect=TradeError("Insufficient margin"))
        trader.get_position = AsyncMock(return_value=None)
        engine = RSIEngine(
            agent_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )

        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=25.0,
        ):
            result = await engine.run_cycle()

        assert result["success"] is True
        assert result["trades_executed"] == 0


# ── create_engine() Factory ──────────────────────────────────────────


class TestCreateEngine:
    """Tests for create_engine() factory function."""

    def test_create_grid_engine(self):
        trader = _mock_trader()
        engine = create_engine("grid", "s1", trader, "BTC", {"upper_price": 100}, {})

        assert isinstance(engine, GridEngine)
        assert engine.agent_id == "s1"

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


# ── QuantEngineBase Tests ──────────────────────────────────────────


class TestQuantEngineBaseIsolation:
    """Tests for _open_with_isolation and _close_with_isolation."""

    @pytest.fixture
    def mock_position_service(self):
        """Create mock position service."""
        ps = AsyncMock()
        ps.claim_position_with_capital_check = AsyncMock()
        ps.claim_position = AsyncMock()
        ps.release_position = AsyncMock()
        ps.confirm_position_open = AsyncMock()
        return ps

    @pytest.fixture
    def mock_strategy(self):
        """Create mock strategy with capital check."""
        strategy = MagicMock()
        strategy.get_effective_capital = MagicMock(return_value=1000.0)
        return strategy

    @pytest.mark.asyncio
    async def test_open_with_isolation_capital_exceeded(self, mock_position_service, mock_strategy):
        """Test _open_with_isolation returns failure on CapitalExceededError."""
        from app.services.position_service import CapitalExceededError
        
        trader = _mock_trader(mark_price=50000.0)
        mock_position_service.claim_position_with_capital_check = AsyncMock(
            side_effect=CapitalExceededError("Budget exceeded")
        )
        
        engine = GridEngine(
            agent_id="00000000-0000-0000-0000-000000000001",
            trader=trader,
            symbol="BTC",
            config={"upper_price": 110.0, "lower_price": 90.0, "grid_count": 4, "total_investment": 400.0, "leverage": 2.0},
            runtime_state={},
            account_id="00000000-0000-0000-0000-000000000002",
            position_service=mock_position_service,
            strategy=mock_strategy,
        )
        
        result = await engine._open_with_isolation(size_usd=100.0, leverage=2)
        
        assert result.success is False
        assert "Capital exceeded" in result.error

    @pytest.mark.asyncio
    async def test_open_with_isolation_position_conflict(self, mock_position_service, mock_strategy):
        """Test _open_with_isolation returns failure on PositionConflictError."""
        from uuid import UUID
        from app.services.position_service import PositionConflictError
        
        trader = _mock_trader(mark_price=50000.0)
        mock_position_service.claim_position_with_capital_check = AsyncMock(
            side_effect=PositionConflictError("BTC", UUID("00000000-0000-0000-0000-000000000099"))
        )
        
        engine = DCAEngine(
            agent_id="00000000-0000-0000-0000-000000000001",
            trader=trader,
            symbol="BTC",
            config={"order_amount": 100.0, "interval_minutes": 60, "total_budget": 1000.0, "max_orders": 10},
            runtime_state={},
            account_id="00000000-0000-0000-0000-000000000002",
            position_service=mock_position_service,
            strategy=mock_strategy,
        )
        
        result = await engine._open_with_isolation(size_usd=100.0, leverage=1)
        
        assert result.success is False
        assert "Symbol conflict" in result.error

    @pytest.mark.asyncio
    async def test_open_with_isolation_fallback_no_capital_check(self, mock_position_service):
        """Test _open_with_isolation uses fallback when no strategy provided."""
        trader = _mock_trader(mark_price=50000.0)
        claim_mock = MagicMock()
        claim_mock.status = "claimed"
        mock_position_service.claim_position = AsyncMock(return_value=claim_mock)
        
        engine = RSIEngine(
            agent_id="00000000-0000-0000-0000-000000000001",
            trader=trader,
            symbol="BTC",
            config={"rsi_period": 14, "overbought_threshold": 70.0, "oversold_threshold": 30.0, "order_amount": 100.0},
            runtime_state={},
            account_id="00000000-0000-0000-0000-000000000002",
            position_service=mock_position_service,
            strategy=None,  # No strategy, use fallback
        )
        
        result = await engine._open_with_isolation(size_usd=100.0, leverage=1)
        
        assert result.success is True
        mock_position_service.claim_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_isolation_success(self, mock_position_service, mock_strategy):
        """Test _close_with_isolation marks position as closed."""
        trader = _mock_trader(mark_price=55000.0)
        claim_mock = MagicMock()
        claim_mock.status = "open"
        claim_mock.id = "test-claim-id"
        mock_position_service.get_open_position = AsyncMock(return_value=claim_mock)
        
        engine = RSIEngine(
            agent_id="00000000-0000-0000-0000-000000000001",
            trader=trader,
            symbol="BTC",
            config={"rsi_period": 14, "overbought_threshold": 70.0, "oversold_threshold": 30.0, "order_amount": 100.0},
            runtime_state={},
            account_id="00000000-0000-0000-0000-000000000002",
            position_service=mock_position_service,
            strategy=mock_strategy,
        )
        
        result = await engine._close_with_isolation()
        
        assert result.success is True


class TestRSIEngineStateSync:
    """Tests for RSIEngine state synchronization with exchange."""

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
    async def test_state_sync_exchange_has_position_state_says_no(self, rsi_config):
        """Test sync when state says no position but exchange has one."""
        trader = _mock_trader(mark_price=50000.0)
        
        # Exchange shows position
        actual_position = MagicMock()
        actual_position.entry_price = 48000.0
        actual_position.size_usd = 150.0
        actual_position.size = 0.003  # Required: size > 0 to be considered as having position
        trader.get_position = AsyncMock(return_value=actual_position)
        
        runtime_state = {
            "initialized": True,
            "has_position": False,  # State says no position
            "entry_price": 0.0,
            "position_size_usd": 0.0,
            "last_rsi": None,
            "last_signal": None,
        }
        
        engine = RSIEngine(
            agent_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state=runtime_state,
        )
        
        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=50.0,  # Neutral RSI
        ):
            result = await engine.run_cycle()
        
        # State should be synced to reflect exchange position
        state = result["updated_state"]
        assert state["has_position"] is True
        assert state["entry_price"] == 48000.0
        assert state["position_size_usd"] == 150.0

    @pytest.mark.asyncio
    async def test_state_sync_state_has_position_exchange_says_no(self, rsi_config):
        """Test sync when state says has position but exchange doesn't."""
        trader = _mock_trader(mark_price=50000.0)
        
        # Exchange shows no position
        trader.get_position = AsyncMock(return_value=None)
        
        runtime_state = {
            "initialized": True,
            "has_position": True,  # State says has position
            "entry_price": 48000.0,
            "position_size_usd": 150.0,
            "last_rsi": None,
            "last_signal": "buy",
        }
        
        engine = RSIEngine(
            agent_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state=runtime_state,
        )
        
        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=50.0,  # Neutral RSI
        ):
            result = await engine.run_cycle()
        
        # State should be synced to reflect no position
        state = result["updated_state"]
        assert state["has_position"] is False
        assert state["entry_price"] == 0.0
        assert state["position_size_usd"] == 0.0

    @pytest.mark.asyncio
    async def test_state_sync_exception_continues(self, rsi_config):
        """Test that sync exception doesn't crash the engine."""
        trader = _mock_trader(mark_price=50000.0)
        
        # get_position raises exception
        trader.get_position = AsyncMock(side_effect=Exception("Exchange error"))
        
        runtime_state = {
            "initialized": True,
            "has_position": True,
            "entry_price": 48000.0,
            "position_size_usd": 150.0,
            "last_rsi": None,
            "last_signal": "buy",
        }
        
        engine = RSIEngine(
            agent_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state=runtime_state,
        )
        
        with patch.object(
            engine, "_calculate_rsi",
            new_callable=AsyncMock, return_value=75.0,  # Overbought - sell signal
        ):
            # Should not raise, and should continue with current state
            result = await engine.run_cycle()
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_rsi_calculation_exception_returns_none(self, rsi_config):
        """Test RSI calculation returns None on exception."""
        trader = _mock_trader(mark_price=50000.0)
        
        # get_klines raises exception
        trader.get_klines = AsyncMock(side_effect=Exception("API error"))
        
        engine = RSIEngine(
            agent_id="r1", trader=trader, symbol="BTC",
            config=rsi_config, runtime_state={},
        )
        
        rsi = await engine._calculate_rsi("1h", 14)
        
        assert rsi is None


class TestDCAEngineExtended:
    """Extended tests for DCAEngine."""

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
    async def test_trade_error_on_take_profit(self, dca_config):
        """TradeError during take profit close is caught."""
        trader = _mock_trader(mark_price=55000.0)  # +10% from avg
        trader.close_position = AsyncMock(side_effect=TradeError("Exchange error"))
        
        # Set budget fully used so no new orders after TP failure
        runtime_state = {
            "initialized": True,
            "orders_placed": 10,  # Max orders reached
            "total_invested": 1000.0,  # Budget fully used
            "total_quantity": 0.02,
            "avg_cost": 50000.0,
            "last_order_time": None,
        }
        
        engine = DCAEngine(
            agent_id="d1", trader=trader, symbol="BTC",
            config=dca_config, runtime_state=runtime_state,
        )
        
        result = await engine.run_cycle()
        
        # Should succeed even if close failed (TP failed, but no new orders due to limits)
        assert result["success"] is True
        assert result["trades_executed"] == 0  # Close failed, no new orders

    @pytest.mark.asyncio
    async def test_buy_order_failed(self, dca_config):
        """Test when buy order returns success=False."""
        trader = _mock_trader(mark_price=50000.0)
        trader.open_long = AsyncMock(
            return_value=OrderResult(success=False, error="Insufficient balance")
        )
        
        engine = DCAEngine(
            agent_id="d1", trader=trader, symbol="BTC",
            config=dca_config, runtime_state={},
        )
        
        result = await engine.run_cycle()
        
        assert result["success"] is True
        assert result["trades_executed"] == 0


class TestGridEngineExtended:
    """Extended tests for GridEngine."""

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
    async def test_config_hash_mismatch_reinitializes(self, grid_config):
        """Config change resets grid levels."""
        trader = _mock_trader(mark_price=100.0)
        
        # Old state with different config hash
        runtime_state = {
            "initialized": True,
            "config_hash": "DIFFERENT_HASH",
            "grid_levels": [80.0, 85.0, 90.0],  # Old levels
            "filled_buys": [],
            "filled_sells": [],
            "total_invested": 0.0,
            "total_returned": 0.0,
        }
        
        engine = GridEngine(
            agent_id="g1", trader=trader, symbol="BTC",
            config=grid_config, runtime_state=runtime_state,
        )
        
        result = await engine.run_cycle()
        
        # Should have recalculated grid levels
        state = result["updated_state"]
        assert state["grid_levels"] == [90.0, 95.0, 100.0, 105.0, 110.0]
        assert state["config_hash"] == "110.0:90.0:4"
