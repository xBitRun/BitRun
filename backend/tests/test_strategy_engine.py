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
    def mock_agent(self, mock_strategy):
        """Create a mock agent database model."""
        agent = MagicMock()
        agent.id = uuid4()
        agent.user_id = uuid4()
        agent.strategy_id = mock_strategy.id
        agent.strategy = mock_strategy
        agent.ai_model = "deepseek:deepseek-chat"
        agent.execution_mode = "mock"
        agent.mock_initial_balance = 10000.0
        agent.status = "active"
        agent.account_id = uuid4()
        agent.allocated_capital = None
        agent.allocated_capital_percent = None
        agent.total_pnl = 0.0
        agent.total_trades = 0
        agent.winning_trades = 0
        agent.losing_trades = 0
        agent.max_drawdown = 0.0
        agent.execution_interval_minutes = 30
        agent.auto_execute = True
        agent.get_effective_capital = MagicMock(return_value=None)
        return agent

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
    async def strategy_engine(self, mock_agent, mock_trader, mock_ai_client):
        """Create a strategy engine for testing."""
        return StrategyEngine(
            agent=mock_agent,
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
    async def test_run_cycle_ai_error(self, mock_agent, mock_trader):
        """Test strategy cycle with AI error."""
        mock_ai_client = AsyncMock()
        mock_ai_client.generate = AsyncMock(side_effect=Exception("AI service unavailable"))

        engine = StrategyEngine(
            agent=mock_agent,
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
    async def test_run_cycle_parse_error(self, mock_agent, mock_trader):
        """Test strategy cycle with invalid AI response."""
        mock_ai_client = AsyncMock()
        ai_response = MagicMock()
        ai_response.content = "Invalid JSON response"
        ai_response.tokens_used = 100
        mock_ai_client.generate = AsyncMock(return_value=ai_response)

        engine = StrategyEngine(
            agent=mock_agent,
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
        self, mock_agent, mock_trader, mock_ai_client, sample_decision_response
    ):
        """Test auto execution of open_long decision."""
        engine = StrategyEngine(
            agent=mock_agent,
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
    async def test_risk_limit_check(self, mock_agent, mock_strategy, mock_trader, mock_ai_client):
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
            agent=mock_agent,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=True,
        )

        result = await engine.run_cycle()

        # Cycle succeeds, but the open position is blocked (max positions reached)
        assert result["success"] is True
        executed = result.get("executed", [])
        assert len(executed) >= 1
        btc_exec = next((e for e in executed if e["symbol"] == "BTC"), None)
        assert btc_exec is not None
        assert btc_exec["executed"] is False
        assert "max positions" in btc_exec.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_hold_decision_no_execution(self, mock_agent, mock_trader):
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
            agent=mock_agent,
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
    async def test_risk_limit_zero_equity_blocks_cycle(self, mock_agent, mock_trader, mock_ai_client):
        """Zero equity triggers risk limit and blocks the entire cycle."""
        mock_trader.get_account_state = AsyncMock(return_value=AccountState(
            equity=0.0,
            available_balance=0.0,
            total_margin_used=0.0,
            unrealized_pnl=0.0,
            positions=[],
        ))

        engine = StrategyEngine(
            agent=mock_agent,
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
    async def test_capital_exceeded_error_returns_failure(self, mock_agent, mock_trader, mock_ai_client):
        """CapitalExceededError during position claim returns order failure."""
        from app.services.agent_position_service import CapitalExceededError
        from app.traders.base import OrderResult

        # Build a mock position service with proper get_agent_account_state
        agent_state_mock = MagicMock()
        agent_state_mock.to_account_state.return_value = AccountState(
            equity=10000.0, available_balance=8000.0,
            total_margin_used=2000.0, unrealized_pnl=0.0, positions=[],
        )
        agent_state_mock.positions = []

        mock_ps = AsyncMock()
        mock_ps.get_agent_account_state = AsyncMock(return_value=agent_state_mock)
        mock_ps.claim_position_with_capital_check = AsyncMock(
            side_effect=CapitalExceededError("Exceeds allocated capital limit")
        )

        engine = StrategyEngine(
            agent=mock_agent,
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
    async def test_position_conflict_error_returns_failure(self, mock_agent, mock_trader, mock_ai_client):
        """PositionConflictError during position claim returns order failure."""
        from app.services.agent_position_service import PositionConflictError

        # Build a mock position service with proper get_agent_account_state
        agent_state_mock = MagicMock()
        agent_state_mock.to_account_state.return_value = AccountState(
            equity=10000.0, available_balance=8000.0,
            total_margin_used=2000.0, unrealized_pnl=0.0, positions=[],
        )
        agent_state_mock.positions = []

        mock_ps = AsyncMock()
        mock_ps.get_agent_account_state = AsyncMock(return_value=agent_state_mock)
        mock_ps.claim_position_with_capital_check = AsyncMock(
            side_effect=PositionConflictError("BTC", uuid4())
        )

        engine = StrategyEngine(
            agent=mock_agent,
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
    async def test_order_exception_releases_claim(self, mock_agent, mock_trader, mock_ai_client):
        """When order placement raises exception, the claim is released."""

        # Build a mock position service with proper get_agent_account_state
        agent_state_mock = MagicMock()
        agent_state_mock.to_account_state.return_value = AccountState(
            equity=10000.0, available_balance=8000.0,
            total_margin_used=2000.0, unrealized_pnl=0.0, positions=[],
        )
        agent_state_mock.positions = []

        mock_claim = MagicMock()
        mock_claim.id = uuid4()

        mock_ps = AsyncMock()
        mock_ps.get_agent_account_state = AsyncMock(return_value=agent_state_mock)
        mock_ps.claim_position_with_capital_check = AsyncMock(return_value=mock_claim)
        mock_ps.release_claim = AsyncMock()

        # Make trader.open_long raise
        mock_trader.open_long = AsyncMock(side_effect=Exception("Exchange timeout"))
        mock_trader.get_position = AsyncMock(return_value=None)

        engine = StrategyEngine(
            agent=mock_agent,
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
    async def test_unexpected_exception_in_cycle(self, mock_agent, mock_trader):
        """Non-DecisionParseError exception in run_cycle is caught."""
        mock_ai_client = AsyncMock()
        mock_ai_client.generate = AsyncMock(side_effect=RuntimeError("Unexpected internal error"))

        engine = StrategyEngine(
            agent=mock_agent,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=False,
            use_enhanced_context=False,
        )

        result = await engine.run_cycle()

        assert result["success"] is False
        assert "Unexpected internal error" in result["error"]

    @pytest.mark.asyncio
    async def test_close_action_recalculates_realized_pnl_from_db(
        self, mock_agent, mock_trader
    ):
        """
        Test that close action recalculates realized_pnl from DB when
        account.positions has stale state (unrealized_pnl = 0).

        This tests the fix for the issue where mock mode trading execution
        was missing PnL values because the unrealized_pnl was 0 from stale
        MockTrader state.
        """
        from app.traders.base import OrderResult
        from app.models.agent import AgentAccountState, AgentPosition

        # Set up a close_long decision
        close_response = {
            "chain_of_thought": "Taking profit on BTC position",
            "market_assessment": "Price reached target",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "close_long",
                    "leverage": 5,
                    "position_size_usd": 5000,
                    "confidence": 80,
                    "reasoning": "Take profit at 55k"
                }
            ],
            "overall_confidence": 80
        }

        mock_ai_client = AsyncMock()
        ai_response = MagicMock()
        ai_response.content = json.dumps(close_response)
        ai_response.tokens_used = 100
        mock_ai_client.generate = AsyncMock(return_value=ai_response)

        # Account state with stale unrealized_pnl = 0 (simulating MockTrader state issue)
        stale_account = AccountState(
            equity=10000.0,
            available_balance=8000.0,
            total_margin_used=2000.0,
            unrealized_pnl=0.0,  # Stale - should be positive
            positions=[
                Position(
                    symbol="BTC",
                    side="long",
                    size=0.1,
                    size_usd=5000.0,
                    entry_price=50000.0,
                    mark_price=50000.0,  # Same as entry, so unrealized_pnl = 0
                    unrealized_pnl=0.0,  # Stale state
                    unrealized_pnl_percent=0.0,
                    leverage=5,
                ),
            ],
        )
        mock_trader.get_account_state = AsyncMock(return_value=stale_account)

        # Mock market data returning current price (higher than entry)
        mock_trader.get_market_data = AsyncMock(return_value=MarketData(
            symbol="BTC",
            mid_price=55000.0,  # 10% higher than entry
            bid_price=54990.0,
            ask_price=55010.0,
            volume_24h=1000000000.0,
            timestamp=datetime.now(UTC),
        ))

        # Mock successful close position
        mock_trader.close_position = AsyncMock(return_value=OrderResult(
            success=True,
            order_id="test-order-123",
            filled_size=0.1,
            filled_price=55000.0,
            status="filled",
        ))

        # Mock position service with DB position record
        mock_position_service = AsyncMock()
        mock_db_position = MagicMock()
        mock_db_position.symbol = "BTC"
        mock_db_position.side = "long"
        mock_db_position.size = 0.1
        mock_db_position.entry_price = 50000.0
        mock_db_position.leverage = 5
        mock_db_position.size_usd = 5000.0
        mock_position_service.get_agent_position_for_symbol = AsyncMock(
            return_value=mock_db_position
        )

        # Mock get_agent_account_state to return an AgentAccountState
        agent_account_state = AgentAccountState(
            agent_id=str(mock_agent.id),
            positions=[
                AgentPosition(
                    id="test-pos-id",
                    agent_id=str(mock_agent.id),
                    symbol="BTC",
                    side="long",
                    size=0.1,
                    size_usd=5000.0,
                    entry_price=50000.0,
                    leverage=5,
                    status="open",
                    realized_pnl=0.0,
                )
            ],
            equity=10000.0,
            available_balance=8000.0,
            total_unrealized_pnl=0.0,  # Will be recalculated with current price
        )
        mock_position_service.get_agent_account_state = AsyncMock(
            return_value=agent_account_state
        )

        engine = StrategyEngine(
            agent=mock_agent,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=True,
            use_enhanced_context=False,
        )
        engine.position_service = mock_position_service

        result = await engine.run_cycle()

        assert result["success"] is True
        executed = result.get("executed", [])
        assert len(executed) >= 1

        btc_exec = next((e for e in executed if e["symbol"] == "BTC"), None)
        assert btc_exec is not None
        assert btc_exec["executed"] is True

        # The key assertion: realized_pnl should be recalculated
        # Entry: 50000, Current: 55000, Size: 0.1
        # unrealized_pnl = (55000 - 50000) * 0.1 = 500
        assert "realized_pnl" in btc_exec
        assert btc_exec["realized_pnl"] == 500.0

        # Verify the position service was called to get DB position
        mock_position_service.get_agent_position_for_symbol.assert_called()


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
            "trading_mode": "aggressive",
            "risk_controls": {}
        }
        strategy.status = "active"
        strategy.ai_model = "openai:gpt-4o"
        strategy.get_effective_capital = MagicMock(return_value=None)
        return strategy

    @pytest.fixture
    def mock_agent(self, mock_strategy):
        """Create a mock agent database model."""
        agent = MagicMock()
        agent.id = uuid4()
        agent.user_id = uuid4()
        agent.strategy_id = mock_strategy.id
        agent.strategy = mock_strategy
        agent.ai_model = "deepseek:deepseek-chat"
        agent.execution_mode = "mock"
        agent.mock_initial_balance = 10000.0
        agent.status = "active"
        agent.account_id = uuid4()
        agent.allocated_capital = None
        agent.allocated_capital_percent = None
        agent.total_pnl = 0.0
        agent.total_trades = 0
        agent.winning_trades = 0
        agent.losing_trades = 0
        agent.max_drawdown = 0.0
        agent.execution_interval_minutes = 30
        agent.auto_execute = True
        agent.get_effective_capital = MagicMock(return_value=None)
        return agent

    @pytest.mark.asyncio
    async def test_prompt_includes_custom_prompt(self, mock_agent):
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
            agent=mock_agent,
            trader=mock_trader,
            ai_client=mock_ai_client,
            db_session=None,
            auto_execute=False,
            use_enhanced_context=False,
        )

        await engine.run_cycle()

        assert captured_prompt is not None
        # Check that trading mode is reflected in the system prompt
        assert "aggressive" in captured_prompt["system"].lower()
