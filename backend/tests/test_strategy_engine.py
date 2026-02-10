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
        assert result["decision"] is not None

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
