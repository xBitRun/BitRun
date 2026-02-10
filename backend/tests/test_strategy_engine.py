"""
Tests for the strategy engine.
"""

import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime
from uuid import uuid4

from app.services.strategy_engine import StrategyEngine, StrategyExecutionError
from app.services.decision_parser import DecisionParser
from app.models.decision import ActionType, DecisionResponse, TradingDecision
from app.models.strategy import StrategyConfig, TradingMode
from app.traders.base import AccountState, MarketData, Position


class TestStrategyEngine:
    """Tests for StrategyEngine class."""

    @pytest.fixture
    def mock_strategy(self):
        """Create a mock strategy database model."""
        strategy = MagicMock()
        strategy.id = uuid4()
        strategy.user_id = uuid4()
        strategy.name = "Test Strategy"
        strategy.prompt = "Trade BTC based on momentum"
        strategy.trading_mode = "conservative"
        strategy.config = {
            "symbols": ["BTC"],
            "execution_interval_minutes": 30,
            "risk_controls": {
                "max_leverage": 10,
                "max_position_size_usd": 5000,
                "min_confidence": 60,
            }
        }
        strategy.status = "active"
        strategy.account_id = uuid4()
        strategy.ai_model = "openai:gpt-4o"
        strategy.get_effective_capital = MagicMock(return_value=None)
        return strategy

    @pytest.fixture
    def mock_trader(self):
        """Create a mock trader."""
        trader = AsyncMock()
        trader.get_account_state = AsyncMock(return_value=AccountState(
            equity=10000.0,
            available_balance=8000.0,
            total_margin_used=2000.0,
            unrealized_pnl=500.0,
            positions=[],
        ))
        trader.get_market_data = AsyncMock(return_value=MarketData(
            symbol="BTC",
            mid_price=50000.0,
            bid_price=49990.0,
            ask_price=50010.0,
            volume_24h=1000000000.0,
            timestamp=datetime.now(UTC),
        ))
        trader.open_long = AsyncMock()
        trader.open_short = AsyncMock()
        trader.close_position = AsyncMock()
        return trader

    @pytest.fixture
    def mock_ai_client(self, sample_decision_response):
        """Create a mock AI client."""
        client = AsyncMock()
        ai_response = MagicMock()
        ai_response.content = json.dumps(sample_decision_response)
        ai_response.tokens_used = 500
        client.generate = AsyncMock(return_value=ai_response)
        return client

    @pytest_asyncio.fixture
    async def strategy_engine(self, mock_strategy, mock_trader, mock_ai_client):
        """Create a strategy engine for testing."""
        return StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=False,  # Disable auto execution for testing
            use_enhanced_context=False,
        )

    @pytest.mark.asyncio
    async def test_run_cycle_success(self, strategy_engine, mock_trader, mock_ai_client):
        """Test successful strategy cycle execution."""
        result = await strategy_engine.run_cycle()

        assert result["success"] is True
        assert result["error"] is None
        assert result["tokens_used"] > 0
        assert result["latency_ms"] >= 0

        # Verify decision content (not just "is not None")
        decision = result["decision"]
        assert decision is not None
        assert decision.chain_of_thought == "Market shows bullish momentum..."
        assert decision.overall_confidence == 75
        assert len(decision.decisions) == 1
        assert decision.decisions[0].symbol == "BTC"
        assert decision.decisions[0].action == ActionType.OPEN_LONG

        # Verify AI client was called
        mock_ai_client.generate.assert_called_once()

        # Verify trader methods were called
        mock_trader.get_account_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_cycle_ai_error(self, mock_strategy, mock_trader):
        """Test strategy cycle with AI error."""
        mock_ai_client = AsyncMock()
        mock_ai_client.generate = AsyncMock(side_effect=Exception("AI service unavailable"))

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=False,
            use_enhanced_context=False,
        )

        result = await engine.run_cycle()

        assert result["success"] is False
        assert "AI service unavailable" in result["error"]

    @pytest.mark.asyncio
    async def test_run_cycle_parse_error(self, mock_strategy, mock_trader):
        """Test strategy cycle with invalid AI response."""
        mock_ai_client = AsyncMock()
        ai_response = MagicMock()
        ai_response.content = "Invalid JSON response"
        ai_response.tokens_used = 100
        mock_ai_client.generate = AsyncMock(return_value=ai_response)

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=False,
            use_enhanced_context=False,
        )

        result = await engine.run_cycle()

        assert result["success"] is False
        assert "parse" in result["error"].lower() or result["decision"] is None

    @pytest.mark.asyncio
    async def test_auto_execution_open_long(
        self, mock_strategy, mock_trader, mock_ai_client, sample_decision_response
    ):
        """Test auto execution of open_long decision."""
        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=True,
            use_enhanced_context=False,
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        # open_long should be called based on sample_decision_response
        mock_trader.open_long.assert_called()

    @pytest.mark.asyncio
    async def test_risk_limit_check(self, mock_strategy, mock_trader, mock_ai_client):
        """Test that risk limits are checked before execution."""
        # Set up trader with high margin usage
        mock_trader.get_account_state = AsyncMock(return_value=AccountState(
            equity=10000.0,
            available_balance=500.0,  # Very low available balance
            total_margin_used=9500.0,
            unrealized_pnl=-500.0,
            positions=[
                Position(
                    symbol="BTC",
                    side="long",
                    size=1.0,
                    size_usd=50000.0,
                    entry_price=50000.0,
                    mark_price=49000.0,
                    unrealized_pnl=-1000.0,
                    unrealized_pnl_percent=-2.0,
                    leverage=10,
                ),
                Position(
                    symbol="ETH",
                    side="long",
                    size=10.0,
                    size_usd=30000.0,
                    entry_price=3000.0,
                    mark_price=2900.0,
                    unrealized_pnl=-1000.0,
                    unrealized_pnl_percent=-3.33,
                    leverage=5,
                ),
                Position(
                    symbol="SOL",
                    side="short",
                    size=100.0,
                    size_usd=10000.0,
                    entry_price=100.0,
                    mark_price=95.0,
                    unrealized_pnl=500.0,
                    unrealized_pnl_percent=5.0,
                    leverage=3,
                ),
            ],
        ))

        # Set max positions to 3 (already at limit)
        mock_strategy.config = {
            "symbols": ["BTC"],
            "risk_controls": {
                "max_positions": 3,
                "max_leverage": 10,
            }
        }

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=True,
        )

        result = await engine.run_cycle()

        # Should fail due to risk limits
        assert "risk" in result.get("error", "").lower() or result["success"] is False

    @pytest.mark.asyncio
    async def test_hold_decision_no_execution(self, mock_strategy, mock_trader):
        """Test that hold decisions don't trigger trades."""
        hold_response = {
            "chain_of_thought": "Market uncertain",
            "market_assessment": "Sideways",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "hold",
                    "leverage": 1,
                    "position_size_usd": 0,
                    "confidence": 50,
                    "risk_usd": 0,
                    "reasoning": "Wait for signal"
                }
            ],
            "overall_confidence": 50
        }

        mock_ai_client = AsyncMock()
        ai_response = MagicMock()
        ai_response.content = json.dumps(hold_response)
        ai_response.tokens_used = 100
        mock_ai_client.generate = AsyncMock(return_value=ai_response)

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=True,
            use_enhanced_context=False,
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        # No trades should be executed for hold
        mock_trader.open_long.assert_not_called()
        mock_trader.open_short.assert_not_called()


    @pytest.mark.asyncio
    async def test_risk_limit_zero_equity_blocks_cycle(self, mock_strategy, mock_trader, mock_ai_client):
        """Zero equity triggers risk limit and blocks the entire cycle."""
        mock_trader.get_account_state = AsyncMock(return_value=AccountState(
            equity=0.0,
            available_balance=0.0,
            total_margin_used=0.0,
            unrealized_pnl=0.0,
            positions=[],
        ))

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=True,
            use_enhanced_context=False,
        )

        result = await engine.run_cycle()

        assert result["success"] is False
        assert "equity" in result["error"].lower() or "risk" in result["error"].lower()
        # AI should NOT be called when equity is zero
        mock_ai_client.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_capital_exceeded_error_returns_failure(self, mock_strategy, mock_trader, mock_ai_client):
        """CapitalExceededError during position claim returns order failure."""
        from app.services.position_service import PositionService, CapitalExceededError
        from app.traders.base import OrderResult

        mock_ps = AsyncMock(spec=PositionService)
        mock_ps.claim_position_with_capital_check = AsyncMock(
            side_effect=CapitalExceededError("Exceeds allocated capital limit")
        )

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=True,
            use_enhanced_context=False,
            position_service=mock_ps,
        )

        result = await engine.run_cycle()

        assert result["success"] is True  # Cycle succeeds; order rejected
        # The executed item should show the failure
        executed = result.get("executed", [])
        assert len(executed) >= 1
        btc_exec = next((e for e in executed if e["symbol"] == "BTC"), None)
        assert btc_exec is not None
        assert btc_exec["executed"] is False
        assert "capital" in btc_exec.get("reason", "").lower() or "capital" in str(btc_exec.get("order_result", "")).lower()

    @pytest.mark.asyncio
    async def test_position_conflict_error_returns_failure(self, mock_strategy, mock_trader, mock_ai_client):
        """PositionConflictError during position claim returns order failure."""
        from app.services.position_service import PositionService, PositionConflictError

        mock_ps = AsyncMock(spec=PositionService)
        mock_ps.claim_position_with_capital_check = AsyncMock(
            side_effect=PositionConflictError("BTC", uuid4())
        )

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=True,
            use_enhanced_context=False,
            position_service=mock_ps,
        )

        result = await engine.run_cycle()

        assert result["success"] is True
        executed = result.get("executed", [])
        assert len(executed) >= 1
        btc_exec = next((e for e in executed if e["symbol"] == "BTC"), None)
        assert btc_exec is not None
        assert btc_exec["executed"] is False
        # Error is in order_result.error (PositionConflictError caught in _execute_single_decision)
        order_error = btc_exec.get("order_result", {}).get("error", "")
        assert "conflict" in order_error.lower() or "occupied" in order_error.lower()

    @pytest.mark.asyncio
    async def test_order_exception_releases_claim(self, mock_strategy, mock_trader, mock_ai_client):
        """When order placement raises exception, the claim is released."""
        from app.services.position_service import PositionService

        mock_claim = MagicMock()
        mock_claim.id = uuid4()

        mock_ps = AsyncMock(spec=PositionService)
        mock_ps.claim_position_with_capital_check = AsyncMock(return_value=mock_claim)
        mock_ps.release_claim = AsyncMock()

        # Make trader.open_long raise
        mock_trader.open_long = AsyncMock(side_effect=Exception("Exchange timeout"))
        mock_trader.get_position = AsyncMock(return_value=None)

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=True,
            use_enhanced_context=False,
            position_service=mock_ps,
        )

        result = await engine.run_cycle()

        assert result["success"] is True  # Cycle itself succeeds
        # Claim should have been released
        mock_ps.release_claim.assert_called_once_with(mock_claim.id)

    @pytest.mark.asyncio
    async def test_unexpected_exception_in_cycle(self, mock_strategy, mock_trader):
        """Non-DecisionParseError exception in run_cycle is caught."""
        mock_ai_client = AsyncMock()
        mock_ai_client.generate = AsyncMock(side_effect=RuntimeError("Unexpected internal error"))

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=False,
            use_enhanced_context=False,
        )

        result = await engine.run_cycle()

        assert result["success"] is False
        assert "Unexpected internal error" in result["error"]


class TestStrategyEnginePromptBuilding:
    """Tests for prompt building in strategy engine."""

    @pytest.fixture
    def mock_strategy(self):
        """Create a mock strategy."""
        strategy = MagicMock()
        strategy.id = uuid4()
        strategy.user_id = uuid4()
        strategy.name = "Custom Strategy"
        strategy.prompt = "Focus on momentum indicators"
        strategy.trading_mode = "aggressive"
        strategy.config = {
            "symbols": ["BTC", "ETH"],
            "custom_prompt": "Always consider volume",
            "risk_controls": {}
        }
        strategy.status = "active"
        strategy.ai_model = "openai:gpt-4o"
        strategy.get_effective_capital = MagicMock(return_value=None)
        return strategy

    @pytest.mark.asyncio
    async def test_prompt_includes_custom_prompt(self, mock_strategy):
        """Test that custom prompts are included."""
        mock_trader = AsyncMock()
        mock_trader.get_account_state = AsyncMock(return_value=AccountState(
            equity=10000.0,
            available_balance=10000.0,
            total_margin_used=0.0,
            unrealized_pnl=0.0,
            positions=[],
        ))
        mock_trader.get_market_data = AsyncMock(return_value=MarketData(
            symbol="BTC",
            mid_price=50000.0,
            bid_price=49990.0,
            ask_price=50010.0,
            volume_24h=1000000000.0,
            timestamp=datetime.now(UTC),
        ))

        mock_ai_client = AsyncMock()
        captured_prompt = None

        async def capture_generate(system_prompt, user_prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = {"system": system_prompt, "user": user_prompt}
            response = MagicMock()
            response.content = json.dumps({
                "chain_of_thought": "test",
                "market_assessment": "test",
                "decisions": [],
                "overall_confidence": 50
            })
            response.tokens_used = 100
            return response

        mock_ai_client.generate = capture_generate

        engine = StrategyEngine(
            strategy=mock_strategy,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=False,
            use_enhanced_context=False,
        )

        await engine.run_cycle()

        assert captured_prompt is not None
        # Check that custom prompt or trading mode is reflected
        assert "aggressive" in captured_prompt["system"].lower() or "volume" in captured_prompt["system"].lower()
