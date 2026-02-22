"""
Tests for Pydantic/dataclass models.

Covers:
- app.models.decision (ActionType, RiskControls, TradingDecision, DecisionResponse, DecisionRecord)
- app.models.strategy (StrategyType, TradingMode, PromptSections, AIStrategyConfig, Strategy, StrategyCreate, StrategyUpdate, StrategyFork, StrategyVisibility, PricingModel, GridConfig, DCAConfig, RSIConfig)
- app.models.agent (AgentStatus, ExecutionMode, Agent, AgentCreate, AgentUpdate, AgentStatusUpdate, AgentPosition, AgentAccountState)
- app.models.market_context (TechnicalIndicators, MarketContext, TIMEFRAME_LIMITS, CACHE_TTL)
- app.models.quant_strategy (backward compat: QuantStrategyType, QuantStrategyCreate, etc.)
- app.models.debate (ConsensusMode, DebateParticipant, DebateVote, DebateResult, DebateConfig)
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.decision import (
    ActionType,
    DecisionRecord,
    DecisionResponse,
    RiskControls,
    TradingDecision,
    get_decision_json_schema,
    DECISION_JSON_SCHEMA,
)
from app.models.strategy import (
    AIStrategyConfig,
    DCAConfig,
    GridConfig,
    PricingModel,
    PromptSections,
    RSIConfig,
    Strategy,
    StrategyConfig,
    StrategyCreate,
    StrategyFork,
    StrategyType,
    StrategyUpdate,
    StrategyVisibility,
    TradingMode,
)
from app.models.agent import (
    Agent,
    AgentAccountState,
    AgentCreate,
    AgentPosition,
    AgentStatus,
    AgentStatusUpdate,
    AgentUpdate,
    ExecutionMode,
)
from app.models.market_context import (
    CACHE_TTL,
    MarketContext,
    TIMEFRAME_LIMITS,
    TechnicalIndicators,
)
from app.models.quant_strategy import (
    QuantStrategyCreate,
    QuantStrategyResponse,
    QuantStrategyStatus,
    QuantStrategyStatusUpdate,
    QuantStrategyType,
    QuantStrategyUpdate,
)
from app.models.debate import (
    ConsensusMode,
    DebateConfig,
    DebateParticipant,
    DebateResult,
    DebateVote,
)
from app.traders.base import FundingRate, MarketData, OHLCV


# ======================== ActionType ========================

class TestActionType:
    def test_values(self):
        assert ActionType.OPEN_LONG == "open_long"
        assert ActionType.OPEN_SHORT == "open_short"
        assert ActionType.CLOSE_LONG == "close_long"
        assert ActionType.CLOSE_SHORT == "close_short"
        assert ActionType.HOLD == "hold"
        assert ActionType.WAIT == "wait"

    def test_all_members(self):
        assert len(ActionType) == 6


# ======================== RiskControls ========================

class TestRiskControls:
    def test_defaults(self):
        rc = RiskControls()
        assert rc.max_leverage == 5
        assert rc.max_position_ratio == 0.2
        assert rc.max_total_exposure == 0.8
        assert rc.min_risk_reward_ratio == 2.0
        assert rc.max_drawdown_percent == 0.1
        assert rc.min_confidence == 60

    def test_custom_values(self):
        rc = RiskControls(max_leverage=10, max_position_ratio=0.5, min_confidence=80)
        assert rc.max_leverage == 10
        assert rc.max_position_ratio == 0.5
        assert rc.min_confidence == 80

    def test_leverage_bounds(self):
        with pytest.raises(ValidationError):
            RiskControls(max_leverage=0)
        with pytest.raises(ValidationError):
            RiskControls(max_leverage=51)

    def test_position_ratio_bounds(self):
        with pytest.raises(ValidationError):
            RiskControls(max_position_ratio=0.0)
        with pytest.raises(ValidationError):
            RiskControls(max_position_ratio=1.1)

    def test_drawdown_bounds(self):
        with pytest.raises(ValidationError):
            RiskControls(max_drawdown_percent=0.0)
        with pytest.raises(ValidationError):
            RiskControls(max_drawdown_percent=0.6)

    def test_confidence_bounds(self):
        RiskControls(min_confidence=0)   # lower bound ok
        RiskControls(min_confidence=100) # upper bound ok
        with pytest.raises(ValidationError):
            RiskControls(min_confidence=-1)
        with pytest.raises(ValidationError):
            RiskControls(min_confidence=101)

    def test_total_exposure_bounds(self):
        RiskControls(max_total_exposure=0.1)   # lower bound ok
        RiskControls(max_total_exposure=1.0)   # upper bound ok
        with pytest.raises(ValidationError):
            RiskControls(max_total_exposure=0.09)
        with pytest.raises(ValidationError):
            RiskControls(max_total_exposure=1.1)

    def test_min_risk_reward_ratio_bounds(self):
        RiskControls(min_risk_reward_ratio=1.0)   # lower bound ok
        RiskControls(min_risk_reward_ratio=5.0)   # valid
        with pytest.raises(ValidationError):
            RiskControls(min_risk_reward_ratio=0.0)
        with pytest.raises(ValidationError):
            RiskControls(min_risk_reward_ratio=0.99)


# ======================== TradingDecision ========================

class TestTradingDecision:
    def _make(self, **overrides):
        defaults = dict(
            symbol="btc",
            action=ActionType.OPEN_LONG,
            confidence=80,
            reasoning="This is a strong bullish setup with clear support levels",
        )
        defaults.update(overrides)
        return TradingDecision(**defaults)

    def test_basic_creation(self):
        d = self._make()
        assert d.symbol == "BTC"  # normalised to uppercase
        assert d.action == ActionType.OPEN_LONG
        assert d.confidence == 80
        assert d.leverage == 1  # default

    def test_symbol_normalization(self):
        d = self._make(symbol="  eth  ")
        assert d.symbol == "ETH"

    def test_should_execute_above_threshold(self):
        d = self._make(confidence=75)
        assert d.should_execute(min_confidence=60) is True

    def test_should_execute_below_threshold(self):
        d = self._make(confidence=50)
        assert d.should_execute(min_confidence=60) is False

    def test_should_execute_hold_never_executes(self):
        d = self._make(action=ActionType.HOLD, confidence=99)
        assert d.should_execute(min_confidence=0) is False

    def test_should_execute_wait_never_executes(self):
        d = self._make(action=ActionType.WAIT, confidence=99)
        assert d.should_execute(min_confidence=0) is False

    def test_should_execute_exact_threshold(self):
        d = self._make(confidence=60)
        assert d.should_execute(min_confidence=60) is True

    def test_optional_fields(self):
        d = self._make(entry_price=50000, stop_loss=48000, take_profit=55000)
        assert d.entry_price == 50000
        assert d.stop_loss == 48000
        assert d.take_profit == 55000

    def test_optional_fields_default_none(self):
        d = self._make()
        assert d.entry_price is None
        assert d.stop_loss is None
        assert d.take_profit is None

    def test_confidence_bounds(self):
        self._make(confidence=0)    # lower bound ok
        self._make(confidence=100)  # upper bound ok
        with pytest.raises(ValidationError):
            self._make(confidence=-1)
        with pytest.raises(ValidationError):
            self._make(confidence=101)

    def test_reasoning_min_length(self):
        with pytest.raises(ValidationError):
            self._make(reasoning="short")
        # exactly 10 chars should pass
        self._make(reasoning="a" * 10)
        # 9 chars should fail
        with pytest.raises(ValidationError):
            self._make(reasoning="a" * 9)

    def test_leverage_bounds(self):
        self._make(leverage=1)   # lower bound ok
        self._make(leverage=50)  # upper bound ok
        with pytest.raises(ValidationError):
            self._make(leverage=0)
        with pytest.raises(ValidationError):
            self._make(leverage=51)
        with pytest.raises(ValidationError):
            self._make(leverage=-1)

    def test_position_size_non_negative(self):
        self._make(position_size_usd=0)  # boundary ok
        with pytest.raises(ValidationError):
            self._make(position_size_usd=-1)


# ======================== DecisionResponse ========================

class TestDecisionResponse:
    def test_basic_creation(self):
        dr = DecisionResponse(
            chain_of_thought="thinking...",
            market_assessment="bullish",
        )
        assert dr.chain_of_thought == "thinking..."
        assert dr.decisions == []
        assert dr.risk_controls.max_leverage == 5  # defaults
        assert dr.overall_confidence == 50
        assert dr.next_review_minutes == 60

    def test_with_decisions(self):
        decision = TradingDecision(
            symbol="BTC",
            action=ActionType.HOLD,
            confidence=50,
            reasoning="Waiting for clearer trend confirmation",
        )
        dr = DecisionResponse(
            chain_of_thought="analysis",
            market_assessment="neutral",
            decisions=[decision],
        )
        assert len(dr.decisions) == 1

    def test_next_review_minutes_bounds(self):
        with pytest.raises(ValidationError):
            DecisionResponse(
                chain_of_thought="t", market_assessment="m",
                next_review_minutes=4,
            )
        with pytest.raises(ValidationError):
            DecisionResponse(
                chain_of_thought="t", market_assessment="m",
                next_review_minutes=1441,
            )

    def test_overall_confidence_bounds(self):
        DecisionResponse(
            chain_of_thought="t", market_assessment="m",
            overall_confidence=0,
        )
        DecisionResponse(
            chain_of_thought="t", market_assessment="m",
            overall_confidence=100,
        )
        with pytest.raises(ValidationError):
            DecisionResponse(
                chain_of_thought="t", market_assessment="m",
                overall_confidence=-1,
            )
        with pytest.raises(ValidationError):
            DecisionResponse(
                chain_of_thought="t", market_assessment="m",
                overall_confidence=101,
            )


# ======================== DecisionRecord ========================

class TestDecisionRecord:
    def test_basic_creation(self):
        record = DecisionRecord(
            id="rec-1",
            agent_id="agent-1",
            timestamp=datetime.now(UTC),
            system_prompt="sys",
            user_prompt="usr",
            raw_response="raw",
            chain_of_thought="cot",
            market_assessment="bullish",
            decisions=[],
            overall_confidence=70,
            ai_model="claude-3",
        )
        assert record.executed is False
        assert record.execution_results == []
        assert record.tokens_used == 0
        assert record.latency_ms == 0


# ======================== get_decision_json_schema ========================

class TestDecisionJsonSchema:
    def test_english(self):
        schema = get_decision_json_schema("en")
        assert "chain_of_thought" in schema
        assert "Trading pair symbol" in schema

    def test_chinese(self):
        schema = get_decision_json_schema("zh")
        assert "交易对符号" in schema

    def test_default_is_english(self):
        assert get_decision_json_schema() == get_decision_json_schema("en")

    def test_backward_compat_alias(self):
        assert DECISION_JSON_SCHEMA == get_decision_json_schema("en")


# ======================== StrategyType / TradingMode / Visibility / PricingModel ========================

class TestStrategyEnums:
    def test_strategy_type_values(self):
        assert StrategyType.AI == "ai"
        assert StrategyType.GRID == "grid"
        assert StrategyType.DCA == "dca"
        assert StrategyType.RSI == "rsi"
        assert len(StrategyType) == 4

    def test_trading_mode_values(self):
        assert TradingMode.AGGRESSIVE == "aggressive"
        assert TradingMode.CONSERVATIVE == "conservative"
        assert TradingMode.BALANCED == "balanced"
        assert len(TradingMode) == 3

    def test_strategy_visibility_values(self):
        assert StrategyVisibility.PRIVATE == "private"
        assert StrategyVisibility.PUBLIC == "public"
        assert len(StrategyVisibility) == 2

    def test_pricing_model_values(self):
        assert PricingModel.FREE == "free"
        assert PricingModel.ONE_TIME == "one_time"
        assert PricingModel.MONTHLY == "monthly"
        assert len(PricingModel) == 3

    def test_strategy_status_removed(self):
        """StrategyStatus is removed - status lives on Agent now."""
        from app.models.strategy import StrategyStatus
        assert StrategyStatus is None


# ======================== PromptSections ========================

class TestPromptSections:
    def test_defaults(self):
        ps = PromptSections()
        assert "expert cryptocurrency trader" in ps.role_definition
        assert ps.trading_frequency != ""
        assert ps.entry_standards != ""
        assert ps.decision_process != ""

    def test_custom(self):
        ps = PromptSections(role_definition="custom role")
        assert ps.role_definition == "custom role"


# ======================== AIStrategyConfig (aliased as StrategyConfig) ========================

class TestAIStrategyConfig:
    def test_defaults(self):
        cfg = AIStrategyConfig()
        assert cfg.language == "en"
        assert cfg.symbols == ["BTC", "ETH"]
        assert cfg.timeframes == ["15m", "1h", "4h"]
        assert cfg.trading_mode == TradingMode.CONSERVATIVE
        assert cfg.prompt_mode == "simple"

    def test_strategy_config_alias(self):
        """StrategyConfig is an alias for AIStrategyConfig."""
        assert StrategyConfig is AIStrategyConfig

    def test_indicator_defaults(self):
        cfg = AIStrategyConfig()
        assert cfg.indicators["rsi_period"] == 14
        assert cfg.indicators["macd_fast"] == 12

    def test_debate_min_participants_bounds(self):
        """Debate config is on AgentCreate, not AIStrategyConfig."""
        # Debate config moved to Agent model - test there instead
        cfg = AIStrategyConfig()
        assert not hasattr(cfg, "debate_min_participants")

    def test_prompt_field(self):
        cfg = AIStrategyConfig(prompt="Custom AI prompt for trading")
        assert cfg.prompt == "Custom AI prompt for trading"

    def test_risk_controls_default(self):
        cfg = AIStrategyConfig()
        assert cfg.risk_controls.max_leverage == 5
        assert cfg.risk_controls.min_confidence == 60


# ======================== Strategy (new unified model) ========================

class TestStrategy:
    def _make(self, **overrides):
        defaults = dict(
            id="strat-1",
            user_id="user-1",
            type=StrategyType.AI,
            name="Test Strategy",
            symbols=["BTC", "ETH"],
            config={"prompt": "test prompt"},
        )
        defaults.update(overrides)
        return Strategy(**defaults)

    def test_basic_creation(self):
        s = self._make()
        assert s.type == StrategyType.AI
        assert s.visibility == StrategyVisibility.PRIVATE
        assert s.description == ""
        assert s.fork_count == 0
        assert s.is_paid is False
        assert s.pricing_model == PricingModel.FREE

    def test_quant_type(self):
        s = self._make(type=StrategyType.GRID, config={"upper_price": 100})
        assert s.type == StrategyType.GRID

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            self._make(name="x" * 101)

    def test_name_min_length(self):
        with pytest.raises(ValidationError):
            self._make(name="")

    def test_marketplace_fields(self):
        s = self._make(
            visibility=StrategyVisibility.PUBLIC,
            category="trend_following",
            tags=["BTC", "momentum"],
            is_paid=True,
            price_monthly=9.99,
            pricing_model=PricingModel.MONTHLY,
        )
        assert s.visibility == StrategyVisibility.PUBLIC
        assert s.category == "trend_following"
        assert len(s.tags) == 2
        assert s.is_paid is True
        assert s.price_monthly == 9.99

    def test_forked_from(self):
        s = self._make(forked_from="parent-strat-id")
        assert s.forked_from == "parent-strat-id"


# ======================== StrategyCreate ========================

class TestStrategyCreate:
    def _make(self, **overrides):
        defaults = dict(
            type=StrategyType.AI,
            name="New Strategy",
            symbols=["BTC"],
            config={"prompt": "A long enough prompt for testing purposes"},
        )
        defaults.update(overrides)
        return StrategyCreate(**defaults)

    def test_basic_ai_strategy(self):
        sc = self._make()
        assert sc.type == StrategyType.AI
        assert sc.description == ""
        assert sc.visibility == StrategyVisibility.PRIVATE

    def test_name_validation(self):
        with pytest.raises(ValidationError):
            self._make(name="")

    def test_symbols_required(self):
        with pytest.raises(ValidationError):
            self._make(symbols=[])

    def test_ai_prompt_min_length(self):
        with pytest.raises(ValidationError):
            self._make(config={"prompt": "short"})
        # 10 chars should pass
        self._make(config={"prompt": "a" * 10})

    def test_ai_strategy_with_prompt_sections(self):
        """Simple mode: strategy with only prompt_sections should be valid."""
        sc = self._make(config={"prompt_sections": {"role_definition": "test"}})
        assert sc.type == StrategyType.AI

    def test_ai_strategy_with_advanced_prompt(self):
        """Advanced mode: strategy with advanced_prompt should be valid."""
        sc = self._make(config={"advanced_prompt": "This is a custom advanced prompt"})
        assert sc.type == StrategyType.AI

    def test_ai_strategy_empty_config_fails(self):
        """No prompt, no prompt_sections, no advanced_prompt should fail."""
        with pytest.raises(ValidationError):
            self._make(config={})

    def test_ai_strategy_short_advanced_prompt_fails(self):
        """Advanced prompt under 10 chars should fail."""
        with pytest.raises(ValidationError):
            self._make(config={"advanced_prompt": "short"})

    def test_grid_strategy_config_validation(self):
        sc = self._make(
            type=StrategyType.GRID,
            symbols=["BTC"],
            config={"upper_price": 100, "lower_price": 50, "grid_count": 10, "total_investment": 1000},
        )
        assert sc.type == StrategyType.GRID

    def test_grid_invalid_config(self):
        with pytest.raises(ValidationError):
            self._make(
                type=StrategyType.GRID,
                symbols=["BTC"],
                config={"upper_price": 50, "lower_price": 100, "grid_count": 10, "total_investment": 1000},
            )

    def test_marketplace_fields(self):
        sc = self._make(
            visibility=StrategyVisibility.PUBLIC,
            category="mean_reversion",
            tags=["ETH", "grid"],
        )
        assert sc.visibility == StrategyVisibility.PUBLIC
        assert sc.category == "mean_reversion"

    def test_pricing_fields(self):
        sc = self._make(
            is_paid=True,
            price_monthly=19.99,
            pricing_model=PricingModel.MONTHLY,
        )
        assert sc.is_paid is True
        assert sc.price_monthly == 19.99


# ======================== StrategyUpdate ========================

class TestStrategyUpdate:
    def test_all_optional(self):
        su = StrategyUpdate()
        assert su.name is None
        assert su.description is None
        assert su.symbols is None
        assert su.config is None
        assert su.visibility is None

    def test_partial_update(self):
        su = StrategyUpdate(name="Updated", description="New description")
        assert su.name == "Updated"
        assert su.description == "New description"

    def test_name_bounds(self):
        with pytest.raises(ValidationError):
            StrategyUpdate(name="")
        with pytest.raises(ValidationError):
            StrategyUpdate(name="x" * 101)
        StrategyUpdate(name="x")          # min ok
        StrategyUpdate(name="x" * 100)    # max ok

    def test_visibility_update(self):
        su = StrategyUpdate(visibility=StrategyVisibility.PUBLIC)
        assert su.visibility == StrategyVisibility.PUBLIC

    def test_pricing_update(self):
        su = StrategyUpdate(is_paid=True, price_monthly=5.0, pricing_model=PricingModel.MONTHLY)
        assert su.is_paid is True


# ======================== StrategyFork ========================

class TestStrategyFork:
    def test_default(self):
        sf = StrategyFork()
        assert sf.name is None

    def test_name_override(self):
        sf = StrategyFork(name="My Fork")
        assert sf.name == "My Fork"

    def test_name_bounds(self):
        with pytest.raises(ValidationError):
            StrategyFork(name="")
        with pytest.raises(ValidationError):
            StrategyFork(name="x" * 101)


# ======================== AgentStatus / ExecutionMode ========================

class TestAgentEnums:
    def test_agent_status_values(self):
        assert AgentStatus.DRAFT == "draft"
        assert AgentStatus.ACTIVE == "active"
        assert AgentStatus.PAUSED == "paused"
        assert AgentStatus.STOPPED == "stopped"
        assert AgentStatus.ERROR == "error"
        assert AgentStatus.WARNING == "warning"
        assert len(AgentStatus) == 6

    def test_execution_mode_values(self):
        assert ExecutionMode.LIVE == "live"
        assert ExecutionMode.MOCK == "mock"
        assert len(ExecutionMode) == 2


# ======================== Agent ========================

class TestAgent:
    def _make(self, **overrides):
        defaults = dict(
            id="agent-1",
            user_id="user-1",
            name="Test Agent",
            strategy_id="strat-1",
        )
        defaults.update(overrides)
        return Agent(**defaults)

    def test_basic_creation(self):
        a = self._make()
        assert a.status == AgentStatus.DRAFT
        assert a.execution_mode == ExecutionMode.MOCK
        assert a.total_pnl == 0.0
        assert a.total_trades == 0
        assert a.ai_model is None

    def test_win_rate_zero_trades(self):
        a = self._make()
        assert a.win_rate == 0.0

    def test_win_rate_calculation(self):
        a = self._make(total_trades=10, winning_trades=7, losing_trades=3)
        assert a.win_rate == 70.0

    def test_win_rate_all_wins(self):
        a = self._make(total_trades=5, winning_trades=5)
        assert a.win_rate == 100.0

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            self._make(name="x" * 101)

    def test_name_min_length(self):
        with pytest.raises(ValidationError):
            self._make(name="")

    def test_with_ai_model(self):
        a = self._make(ai_model="deepseek:deepseek-chat")
        assert a.ai_model == "deepseek:deepseek-chat"

    def test_live_mode(self):
        a = self._make(execution_mode=ExecutionMode.LIVE, account_id="acc-1")
        assert a.execution_mode == ExecutionMode.LIVE
        assert a.account_id == "acc-1"

    def test_mock_mode_default_balance(self):
        a = self._make(mock_initial_balance=5000.0)
        assert a.mock_initial_balance == 5000.0

    def test_performance_fields(self):
        a = self._make(
            total_pnl=500.0,
            total_trades=20,
            winning_trades=14,
            losing_trades=6,
            max_drawdown=150.0,
        )
        assert a.total_pnl == 500.0
        assert a.max_drawdown == 150.0
        assert a.win_rate == 70.0

    def test_capital_allocation(self):
        a = self._make(allocated_capital=5000.0)
        assert a.allocated_capital == 5000.0
        assert a.allocated_capital_percent is None


# ======================== AgentCreate ========================

class TestAgentCreate:
    def _make(self, **overrides):
        defaults = dict(
            name="New Agent",
            strategy_id="strat-1",
        )
        defaults.update(overrides)
        return AgentCreate(**defaults)

    def test_basic_mock(self):
        ac = self._make()
        assert ac.execution_mode == ExecutionMode.MOCK
        assert ac.mock_initial_balance == 10000.0
        assert ac.auto_execute is True
        assert ac.execution_interval_minutes == 15  # default changed to 15

    def test_live_mode_requires_account(self):
        with pytest.raises(ValidationError):
            self._make(execution_mode=ExecutionMode.LIVE)

    def test_live_mode_with_account(self):
        ac = self._make(execution_mode=ExecutionMode.LIVE, account_id="acc-1")
        assert ac.account_id == "acc-1"

    def test_mock_initial_balance_bounds(self):
        self._make(mock_initial_balance=100)   # lower bound ok
        with pytest.raises(ValidationError):
            self._make(mock_initial_balance=99)  # below 100

    def test_capital_allocation_mutual_exclusion(self):
        with pytest.raises(ValidationError):
            self._make(allocated_capital=1000, allocated_capital_percent=0.5)

    def test_capital_percent_bounds(self):
        self._make(allocated_capital_percent=0.0)  # lower bound ok
        self._make(allocated_capital_percent=1.0)  # upper bound ok
        with pytest.raises(ValidationError):
            self._make(allocated_capital_percent=-0.1)
        with pytest.raises(ValidationError):
            self._make(allocated_capital_percent=1.1)

    def test_execution_interval_bounds(self):
        self._make(execution_interval_minutes=1)       # lower bound ok
        self._make(execution_interval_minutes=43200)   # upper bound ok
        with pytest.raises(ValidationError):
            self._make(execution_interval_minutes=0)
        with pytest.raises(ValidationError):
            self._make(execution_interval_minutes=43201)

    def test_name_bounds(self):
        with pytest.raises(ValidationError):
            self._make(name="")
        with pytest.raises(ValidationError):
            self._make(name="x" * 101)


# ======================== AgentUpdate ========================

class TestAgentUpdate:
    def test_all_optional(self):
        au = AgentUpdate()
        assert au.name is None
        assert au.ai_model is None
        assert au.execution_mode is None

    def test_partial_update(self):
        au = AgentUpdate(name="Updated Agent", ai_model="openai:gpt-4")
        assert au.name == "Updated Agent"
        assert au.ai_model == "openai:gpt-4"

    def test_name_bounds(self):
        with pytest.raises(ValidationError):
            AgentUpdate(name="")
        with pytest.raises(ValidationError):
            AgentUpdate(name="x" * 101)

    def test_capital_allocation_mutual_exclusion(self):
        with pytest.raises(ValidationError):
            AgentUpdate(allocated_capital=1000, allocated_capital_percent=0.5)

    def test_mock_initial_balance_bounds(self):
        AgentUpdate(mock_initial_balance=100)  # ok
        with pytest.raises(ValidationError):
            AgentUpdate(mock_initial_balance=99)

    def test_execution_interval_bounds(self):
        AgentUpdate(execution_interval_minutes=1)      # ok
        AgentUpdate(execution_interval_minutes=43200)  # ok
        with pytest.raises(ValidationError):
            AgentUpdate(execution_interval_minutes=0)
        with pytest.raises(ValidationError):
            AgentUpdate(execution_interval_minutes=43201)


# ======================== AgentStatusUpdate ========================

class TestAgentStatusUpdate:
    def test_basic(self):
        asu = AgentStatusUpdate(status="active")
        assert asu.status == "active"
        assert asu.close_positions is False

    def test_with_close_positions(self):
        asu = AgentStatusUpdate(status="stopped", close_positions=True)
        assert asu.close_positions is True


# ======================== AgentPosition ========================

class TestAgentPosition:
    def test_basic(self):
        pos = AgentPosition(
            id="pos-1",
            agent_id="agent-1",
            symbol="BTC",
            side="long",
            size=0.05,
            size_usd=5000.0,
            entry_price=100000.0,
            leverage=5,
            status="open",
        )
        assert pos.realized_pnl == 0.0
        assert pos.close_price is None
        assert pos.account_id is None

    def test_closed_position(self):
        pos = AgentPosition(
            id="pos-1",
            agent_id="agent-1",
            symbol="ETH",
            side="short",
            size=1.0,
            size_usd=3000.0,
            entry_price=3000.0,
            leverage=3,
            status="closed",
            realized_pnl=150.0,
            close_price=2850.0,
        )
        assert pos.status == "closed"
        assert pos.realized_pnl == 150.0


# ======================== AgentAccountState ========================

class TestAgentAccountState:
    def test_basic(self):
        state = AgentAccountState(
            agent_id="agent-1",
            equity=10000.0,
            available_balance=8000.0,
            total_unrealized_pnl=200.0,
        )
        assert state.positions == []
        assert state.equity == 10000.0

    def test_with_positions(self):
        pos = AgentPosition(
            id="pos-1",
            agent_id="agent-1",
            symbol="BTC",
            side="long",
            size=0.1,
            size_usd=10000.0,
            entry_price=100000.0,
            leverage=10,
            status="open",
        )
        state = AgentAccountState(
            agent_id="agent-1",
            positions=[pos],
            equity=15000.0,
            available_balance=5000.0,
            total_unrealized_pnl=500.0,
        )
        assert len(state.positions) == 1
        assert state.positions[0].symbol == "BTC"

    def test_to_account_state(self):
        pos = AgentPosition(
            id="pos-1",
            agent_id="agent-1",
            symbol="BTC",
            side="long",
            size=0.1,
            size_usd=10000.0,
            entry_price=100000.0,
            leverage=10,
            status="open",
        )
        state = AgentAccountState(
            agent_id="agent-1",
            positions=[pos],
            equity=15000.0,
            available_balance=5000.0,
            total_unrealized_pnl=500.0,
        )
        acct = state.to_account_state(current_prices={"BTC": 105000.0})
        assert acct.equity == 15000.0
        assert len(acct.positions) == 1
        assert acct.positions[0].symbol == "BTC"
        assert acct.positions[0].mark_price == 105000.0
        # unrealized pnl: (105000 - 100000) * 0.1 = 500
        assert acct.positions[0].unrealized_pnl == 500.0

    def test_to_account_state_no_prices(self):
        """Without current prices, mark_price falls back to entry_price."""
        pos = AgentPosition(
            id="pos-1",
            agent_id="agent-1",
            symbol="BTC",
            side="long",
            size=0.1,
            size_usd=10000.0,
            entry_price=100000.0,
            leverage=10,
            status="open",
        )
        state = AgentAccountState(
            agent_id="agent-1",
            positions=[pos],
            equity=10000.0,
            available_balance=9000.0,
        )
        acct = state.to_account_state()
        assert acct.positions[0].mark_price == 100000.0
        assert acct.positions[0].unrealized_pnl == 0.0  # no price change


# ======================== TechnicalIndicators ========================

class TestTechnicalIndicators:
    def test_defaults(self):
        ti = TechnicalIndicators()
        assert ti.ema == {}
        assert ti.rsi is None
        assert ti.atr is None

    def test_rsi_signal_overbought(self):
        ti = TechnicalIndicators(rsi=75)
        assert ti.rsi_signal == "overbought"

    def test_rsi_signal_oversold(self):
        ti = TechnicalIndicators(rsi=25)
        assert ti.rsi_signal == "oversold"

    def test_rsi_signal_bullish(self):
        ti = TechnicalIndicators(rsi=65)
        assert ti.rsi_signal == "bullish"

    def test_rsi_signal_bearish(self):
        ti = TechnicalIndicators(rsi=35)
        assert ti.rsi_signal == "bearish"

    def test_rsi_signal_neutral(self):
        ti = TechnicalIndicators(rsi=50)
        assert ti.rsi_signal == "neutral"

    def test_rsi_signal_unknown(self):
        ti = TechnicalIndicators(rsi=None)
        assert ti.rsi_signal == "unknown"

    def test_rsi_signal_boundary_70(self):
        ti = TechnicalIndicators(rsi=70)
        assert ti.rsi_signal == "overbought"

    def test_rsi_signal_boundary_30(self):
        ti = TechnicalIndicators(rsi=30)
        assert ti.rsi_signal == "oversold"

    def test_macd_signal_bullish(self):
        ti = TechnicalIndicators(macd={"macd": 1.0, "signal": 0.5, "histogram": 0.5})
        assert ti.macd_signal == "bullish"

    def test_macd_signal_bearish(self):
        ti = TechnicalIndicators(macd={"macd": 0.5, "signal": 1.0, "histogram": -0.5})
        assert ti.macd_signal == "bearish"

    def test_macd_signal_neutral(self):
        ti = TechnicalIndicators(macd={"macd": 1.0, "signal": 1.0, "histogram": 0.0})
        assert ti.macd_signal == "neutral"

    def test_ema_trend_bullish(self):
        ti = TechnicalIndicators(ema={9: 100, 21: 95, 55: 90})
        assert ti.ema_trend == "bullish"

    def test_ema_trend_bearish(self):
        ti = TechnicalIndicators(ema={9: 90, 21: 95, 55: 100})
        assert ti.ema_trend == "bearish"

    def test_ema_trend_mixed(self):
        ti = TechnicalIndicators(ema={9: 100, 21: 90, 55: 95})
        assert ti.ema_trend == "mixed"

    def test_ema_trend_unknown_insufficient(self):
        ti = TechnicalIndicators(ema={9: 100})
        assert ti.ema_trend == "unknown"

    def test_ema_trend_unknown_empty(self):
        ti = TechnicalIndicators(ema={})
        assert ti.ema_trend == "unknown"

    def test_to_dict(self):
        ti = TechnicalIndicators(rsi=50, ema={9: 100, 21: 95})
        d = ti.to_dict()
        assert d["rsi"] == 50
        assert d["rsi_signal"] == "neutral"
        assert d["ema_trend"] == "bullish"
        assert "macd_signal" in d


# ======================== MarketContext ========================

class TestMarketContext:
    def _make_market_data(self):
        return MarketData(
            symbol="BTC",
            mid_price=50000,
            bid_price=49990,
            ask_price=50010,
            volume_24h=1000000,
            funding_rate=0.0001,
        )

    def _make_ohlcv(self, close=50000, high=51000, low=49000, open_=49500):
        return OHLCV(
            timestamp=datetime.now(UTC),
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=100,
        )

    def test_basic_creation(self):
        mc = MarketContext(symbol="BTC", current=self._make_market_data())
        assert mc.symbol == "BTC"
        assert mc.available_timeframes == []

    def test_available_timeframes(self):
        mc = MarketContext(
            symbol="BTC",
            current=self._make_market_data(),
            klines={"15m": [], "1h": []},
        )
        assert set(mc.available_timeframes) == {"15m", "1h"}

    def test_latest_funding_rate_from_history(self):
        mc = MarketContext(
            symbol="BTC",
            current=self._make_market_data(),
            funding_history=[
                FundingRate(timestamp=datetime.now(UTC), rate=0.0002),
                FundingRate(timestamp=datetime.now(UTC), rate=0.0001),
            ],
        )
        assert mc.latest_funding_rate == 0.0002

    def test_latest_funding_rate_from_current(self):
        mc = MarketContext(symbol="BTC", current=self._make_market_data())
        assert mc.latest_funding_rate == 0.0001

    def test_avg_funding_rate_24h_three_periods(self):
        mc = MarketContext(
            symbol="BTC",
            current=self._make_market_data(),
            funding_history=[
                FundingRate(timestamp=datetime.now(UTC), rate=0.0003),
                FundingRate(timestamp=datetime.now(UTC), rate=0.0002),
                FundingRate(timestamp=datetime.now(UTC), rate=0.0001),
            ],
        )
        assert mc.avg_funding_rate_24h == pytest.approx(0.0002)

    def test_avg_funding_rate_24h_fewer_periods(self):
        mc = MarketContext(
            symbol="BTC",
            current=self._make_market_data(),
            funding_history=[
                FundingRate(timestamp=datetime.now(UTC), rate=0.0004),
                FundingRate(timestamp=datetime.now(UTC), rate=0.0002),
            ],
        )
        assert mc.avg_funding_rate_24h == pytest.approx(0.0003)

    def test_avg_funding_rate_24h_none(self):
        mc = MarketContext(symbol="BTC", current=self._make_market_data())
        assert mc.avg_funding_rate_24h is None

    def test_get_trend_summary_unavailable(self):
        mc = MarketContext(symbol="BTC", current=self._make_market_data())
        result = mc.get_trend_summary("15m")
        assert "error" in result

    def test_get_trend_summary_with_data(self):
        klines = [self._make_ohlcv() for _ in range(25)]
        mc = MarketContext(
            symbol="BTC",
            current=self._make_market_data(),
            klines={"1h": klines},
            indicators={"1h": TechnicalIndicators(rsi=55, ema={9: 100, 21: 95})},
        )
        summary = mc.get_trend_summary("1h")
        assert summary["timeframe"] == "1h"
        assert summary["rsi"] == 55
        assert "recent_high" in summary
        assert "current_price" in summary

    def test_to_dict(self):
        klines = [self._make_ohlcv() for _ in range(3)]
        mc = MarketContext(
            symbol="BTC",
            current=self._make_market_data(),
            klines={"1h": klines},
            indicators={"1h": TechnicalIndicators(rsi=50)},
            exchange_name="binance",
        )
        d = mc.to_dict(kline_limit=2)
        assert d["symbol"] == "BTC"
        assert d["exchange_name"] == "binance"
        assert len(d["klines"]["1h"]) == 2  # limited to 2
        assert "indicators" in d

    def test_to_dict_empty(self):
        mc = MarketContext(symbol="BTC", current=self._make_market_data())
        d = mc.to_dict()
        assert d["klines"] == {}
        assert d["indicators"] == {}


# ======================== TIMEFRAME_LIMITS / CACHE_TTL ========================

class TestConstants:
    def test_timeframe_limits_keys(self):
        expected = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
        assert set(TIMEFRAME_LIMITS.keys()) == expected

    def test_cache_ttl_keys(self):
        assert set(CACHE_TTL.keys()) == set(TIMEFRAME_LIMITS.keys())

    def test_cache_ttl_values_positive(self):
        for v in CACHE_TTL.values():
            assert v > 0


# ======================== QuantStrategyType / Status (backward compat) ========================

class TestQuantEnums:
    def test_strategy_type(self):
        assert QuantStrategyType.GRID == "grid"
        assert QuantStrategyType.DCA == "dca"
        assert QuantStrategyType.RSI == "rsi"

    def test_strategy_status(self):
        assert QuantStrategyStatus.DRAFT == "draft"
        assert QuantStrategyStatus.ACTIVE == "active"


# ======================== GridConfig (now in strategy.py) ========================

class TestGridConfig:
    def test_valid(self):
        gc = GridConfig(upper_price=100, lower_price=50, grid_count=10, total_investment=1000)
        assert gc.leverage == 1.0

    def test_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            GridConfig(upper_price=0, lower_price=50, grid_count=10, total_investment=1000)

    def test_grid_count_bounds(self):
        with pytest.raises(ValidationError):
            GridConfig(upper_price=100, lower_price=50, grid_count=1, total_investment=1000)
        with pytest.raises(ValidationError):
            GridConfig(upper_price=100, lower_price=50, grid_count=201, total_investment=1000)

    def test_lower_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            GridConfig(upper_price=100, lower_price=0, grid_count=10, total_investment=1000)
        with pytest.raises(ValidationError):
            GridConfig(upper_price=100, lower_price=-1, grid_count=10, total_investment=1000)

    def test_leverage_bounds(self):
        GridConfig(upper_price=100, lower_price=50, grid_count=10, total_investment=1000, leverage=1.0)
        GridConfig(upper_price=100, lower_price=50, grid_count=10, total_investment=1000, leverage=50.0)
        with pytest.raises(ValidationError):
            GridConfig(upper_price=100, lower_price=50, grid_count=10, total_investment=1000, leverage=0.9)
        with pytest.raises(ValidationError):
            GridConfig(upper_price=100, lower_price=50, grid_count=10, total_investment=1000, leverage=50.1)

    def test_total_investment_must_be_positive(self):
        with pytest.raises(ValidationError):
            GridConfig(upper_price=100, lower_price=50, grid_count=10, total_investment=0)
        with pytest.raises(ValidationError):
            GridConfig(upper_price=100, lower_price=50, grid_count=10, total_investment=-100)

    def test_upper_must_exceed_lower(self):
        with pytest.raises(ValidationError):
            GridConfig(upper_price=50, lower_price=100, grid_count=10, total_investment=1000)
        with pytest.raises(ValidationError):
            GridConfig(upper_price=100, lower_price=100, grid_count=10, total_investment=1000)


# ======================== DCAConfig ========================

class TestDCAConfig:
    def test_valid(self):
        dc = DCAConfig(order_amount=100, interval_minutes=60)
        assert dc.take_profit_percent == 5.0
        assert dc.total_budget == 0
        assert dc.max_orders == 0

    def test_order_amount_positive(self):
        with pytest.raises(ValidationError):
            DCAConfig(order_amount=0, interval_minutes=60)

    def test_interval_bounds(self):
        DCAConfig(order_amount=100, interval_minutes=1)       # lower bound ok
        DCAConfig(order_amount=100, interval_minutes=43200)   # upper bound ok
        with pytest.raises(ValidationError):
            DCAConfig(order_amount=100, interval_minutes=0)
        with pytest.raises(ValidationError):
            DCAConfig(order_amount=100, interval_minutes=43201)

    def test_take_profit_percent_bounds(self):
        DCAConfig(order_amount=100, interval_minutes=60, take_profit_percent=0.1)
        DCAConfig(order_amount=100, interval_minutes=60, take_profit_percent=100.0)
        with pytest.raises(ValidationError):
            DCAConfig(order_amount=100, interval_minutes=60, take_profit_percent=0.09)
        with pytest.raises(ValidationError):
            DCAConfig(order_amount=100, interval_minutes=60, take_profit_percent=100.1)

    def test_total_budget_non_negative(self):
        DCAConfig(order_amount=100, interval_minutes=60, total_budget=0)
        with pytest.raises(ValidationError):
            DCAConfig(order_amount=100, interval_minutes=60, total_budget=-1)

    def test_max_orders_non_negative(self):
        DCAConfig(order_amount=100, interval_minutes=60, max_orders=0)
        with pytest.raises(ValidationError):
            DCAConfig(order_amount=100, interval_minutes=60, max_orders=-1)


# ======================== RSIConfig ========================

class TestRSIConfig:
    def test_valid(self):
        rc = RSIConfig(order_amount=100)
        assert rc.rsi_period == 14
        assert rc.overbought_threshold == 70.0
        assert rc.oversold_threshold == 30.0

    def test_threshold_bounds(self):
        RSIConfig(order_amount=100, overbought_threshold=50.0, oversold_threshold=30.0)
        RSIConfig(order_amount=100, overbought_threshold=95.0)
        RSIConfig(order_amount=100, oversold_threshold=5.0)
        RSIConfig(order_amount=100, oversold_threshold=50.0, overbought_threshold=51.0)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, overbought_threshold=49)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, overbought_threshold=95.1)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, oversold_threshold=4.9)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, oversold_threshold=51)

    def test_rsi_period_bounds(self):
        RSIConfig(order_amount=100, rsi_period=2)
        RSIConfig(order_amount=100, rsi_period=100)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, rsi_period=1)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, rsi_period=101)

    def test_order_amount_positive(self):
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=0)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=-1)

    def test_leverage_bounds(self):
        RSIConfig(order_amount=100, leverage=1.0)
        RSIConfig(order_amount=100, leverage=50.0)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, leverage=0.9)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, leverage=50.1)

    def test_overbought_must_exceed_oversold(self):
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, overbought_threshold=60, oversold_threshold=60)
        with pytest.raises(ValidationError):
            RSIConfig(order_amount=100, overbought_threshold=50, oversold_threshold=50)


# ======================== QuantStrategyCreate ========================

class TestQuantStrategyCreate:
    def test_valid(self):
        qsc = QuantStrategyCreate(
            name="Grid Bot",
            strategy_type=QuantStrategyType.GRID,
            symbol="BTC",
            config={"upper_price": 100, "lower_price": 50},
        )
        assert qsc.description == ""
        assert qsc.account_id is None

    def test_name_bounds(self):
        with pytest.raises(ValidationError):
            QuantStrategyCreate(
                name="", strategy_type=QuantStrategyType.GRID,
                symbol="BTC", config={},
            )
        with pytest.raises(ValidationError):
            QuantStrategyCreate(
                name="x" * 101, strategy_type=QuantStrategyType.GRID,
                symbol="BTC", config={},
            )

    def test_symbol_bounds(self):
        with pytest.raises(ValidationError):
            QuantStrategyCreate(
                name="Bot", strategy_type=QuantStrategyType.GRID,
                symbol="", config={},
            )
        with pytest.raises(ValidationError):
            QuantStrategyCreate(
                name="Bot", strategy_type=QuantStrategyType.GRID,
                symbol="x" * 21, config={},
            )

    def test_allocated_capital_non_negative(self):
        with pytest.raises(ValidationError):
            QuantStrategyCreate(
                name="Bot", strategy_type=QuantStrategyType.GRID,
                symbol="BTC", config={}, allocated_capital=-1,
            )

    def test_allocated_capital_percent_bounds(self):
        with pytest.raises(ValidationError):
            QuantStrategyCreate(
                name="Bot", strategy_type=QuantStrategyType.GRID,
                symbol="BTC", config={}, allocated_capital_percent=-0.1,
            )
        with pytest.raises(ValidationError):
            QuantStrategyCreate(
                name="Bot", strategy_type=QuantStrategyType.GRID,
                symbol="BTC", config={}, allocated_capital_percent=1.1,
            )

    def test_capital_allocation_mutual_exclusion(self):
        with pytest.raises(ValidationError):
            QuantStrategyCreate(
                name="Bot", strategy_type=QuantStrategyType.GRID,
                symbol="BTC", config={},
                allocated_capital=1000, allocated_capital_percent=0.5,
            )


# ======================== QuantStrategyUpdate ========================

class TestQuantStrategyUpdate:
    def test_all_optional(self):
        qsu = QuantStrategyUpdate()
        assert qsu.name is None
        assert qsu.config is None

    def test_partial(self):
        qsu = QuantStrategyUpdate(name="Updated")
        assert qsu.name == "Updated"

    def test_name_bounds(self):
        with pytest.raises(ValidationError):
            QuantStrategyUpdate(name="")
        with pytest.raises(ValidationError):
            QuantStrategyUpdate(name="x" * 101)

    def test_symbol_bounds(self):
        with pytest.raises(ValidationError):
            QuantStrategyUpdate(symbol="")
        with pytest.raises(ValidationError):
            QuantStrategyUpdate(symbol="x" * 21)

    def test_allocated_capital_non_negative(self):
        with pytest.raises(ValidationError):
            QuantStrategyUpdate(allocated_capital=-1)

    def test_allocated_capital_percent_bounds(self):
        with pytest.raises(ValidationError):
            QuantStrategyUpdate(allocated_capital_percent=-0.1)
        with pytest.raises(ValidationError):
            QuantStrategyUpdate(allocated_capital_percent=1.1)

    def test_capital_allocation_mutual_exclusion(self):
        with pytest.raises(ValidationError):
            QuantStrategyUpdate(allocated_capital=1000, allocated_capital_percent=0.5)


# ======================== QuantStrategyStatusUpdate ========================

class TestQuantStrategyStatusUpdate:
    def test_valid(self):
        qssu = QuantStrategyStatusUpdate(status="active")
        assert qssu.status == "active"


# ======================== QuantStrategyResponse ========================

class TestQuantStrategyResponse:
    def test_valid(self):
        qsr = QuantStrategyResponse(
            id="qs-1",
            name="Grid",
            description="",
            strategy_type="grid",
            symbol="BTC",
            config={},
            runtime_state={},
            status="active",
            total_pnl=100.5,
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            win_rate=70.0,
            max_drawdown=5.0,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert qsr.error_message is None
        assert qsr.last_run_at is None


# ======================== ConsensusMode ========================

class TestConsensusMode:
    def test_values(self):
        assert ConsensusMode.MAJORITY_VOTE == "majority_vote"
        assert ConsensusMode.HIGHEST_CONFIDENCE == "highest_confidence"
        assert ConsensusMode.WEIGHTED_AVERAGE == "weighted_average"
        assert ConsensusMode.UNANIMOUS == "unanimous"
        assert len(ConsensusMode) == 4


# ======================== DebateParticipant ========================

class TestDebateParticipant:
    def test_succeeded_true(self):
        dp = DebateParticipant(
            model_id="openai:gpt-4",
            decisions=[TradingDecision(
                symbol="BTC", action=ActionType.HOLD, confidence=50,
                reasoning="Market is sideways, waiting for confirmation",
            )],
        )
        assert dp.succeeded is True

    def test_succeeded_false_no_decisions(self):
        dp = DebateParticipant(model_id="openai:gpt-4")
        assert dp.succeeded is False

    def test_succeeded_false_with_error(self):
        dp = DebateParticipant(
            model_id="openai:gpt-4",
            error="timeout",
            decisions=[TradingDecision(
                symbol="BTC", action=ActionType.HOLD, confidence=50,
                reasoning="Market is sideways, waiting for confirmation",
            )],
        )
        assert dp.succeeded is False

    def test_overall_confidence_bounds(self):
        DebateParticipant(model_id="m", overall_confidence=0)
        DebateParticipant(model_id="m", overall_confidence=100)
        with pytest.raises(ValidationError):
            DebateParticipant(model_id="m", overall_confidence=-1)
        with pytest.raises(ValidationError):
            DebateParticipant(model_id="m", overall_confidence=101)

    def test_latency_ms_non_negative(self):
        DebateParticipant(model_id="m", latency_ms=0)
        with pytest.raises(ValidationError):
            DebateParticipant(model_id="m", latency_ms=-1)

    def test_tokens_used_non_negative(self):
        DebateParticipant(model_id="m", tokens_used=0)
        with pytest.raises(ValidationError):
            DebateParticipant(model_id="m", tokens_used=-1)


# ======================== DebateVote ========================

class TestDebateVote:
    def test_creation(self):
        dv = DebateVote(
            symbol="BTC",
            action=ActionType.OPEN_LONG,
            vote_count=3,
            total_confidence=240,
            average_confidence=80.0,
            voters=["model-a", "model-b", "model-c"],
        )
        assert dv.vote_count == 3
        assert dv.average_confidence == 80.0


# ======================== DebateResult ========================

class TestDebateResult:
    def test_is_valid_enough_participants(self):
        dr = DebateResult(
            successful_participants=3,
            min_participants=2,
        )
        assert dr.is_valid is True

    def test_is_valid_not_enough(self):
        dr = DebateResult(
            successful_participants=1,
            min_participants=2,
        )
        assert dr.is_valid is False

    def test_to_decision_response(self):
        decision = TradingDecision(
            symbol="BTC", action=ActionType.OPEN_LONG, confidence=85,
            reasoning="Strong bullish momentum confirmed by all participants",
        )
        dr = DebateResult(
            final_decisions=[decision],
            final_confidence=85,
            combined_chain_of_thought="thinking",
            combined_market_assessment="bullish",
        )
        resp = dr.to_decision_response()
        assert isinstance(resp, DecisionResponse)
        assert len(resp.decisions) == 1
        assert resp.overall_confidence == 85
        assert resp.chain_of_thought == "thinking"

    def test_agreement_score_bounds(self):
        DebateResult(agreement_score=0.0)
        DebateResult(agreement_score=1.0)
        with pytest.raises(ValidationError):
            DebateResult(agreement_score=-0.1)
        with pytest.raises(ValidationError):
            DebateResult(agreement_score=1.1)

    def test_final_confidence_bounds(self):
        DebateResult(final_confidence=0)
        DebateResult(final_confidence=100)
        with pytest.raises(ValidationError):
            DebateResult(final_confidence=-1)
        with pytest.raises(ValidationError):
            DebateResult(final_confidence=101)


# ======================== DebateConfig ========================

class TestDebateConfig:
    def test_defaults(self):
        dc = DebateConfig()
        assert dc.enabled is False
        assert dc.model_ids == []
        assert dc.consensus_mode == ConsensusMode.MAJORITY_VOTE
        assert dc.min_participants == 2
        assert dc.timeout_seconds == 120

    def test_validate_disabled(self):
        dc = DebateConfig(enabled=False)
        ok, msg = dc.validate_config()
        assert ok is True

    def test_validate_too_few_models(self):
        dc = DebateConfig(enabled=True, model_ids=["model-a"])
        ok, msg = dc.validate_config()
        assert ok is False
        assert "2 models" in msg

    def test_validate_too_many_models(self):
        dc = DebateConfig(enabled=True, model_ids=[f"m{i}" for i in range(6)])
        ok, msg = dc.validate_config()
        assert ok is False
        assert "5 models" in msg

    def test_validate_min_exceeds_count(self):
        dc = DebateConfig(enabled=True, model_ids=["a", "b"], min_participants=3)
        ok, msg = dc.validate_config()
        assert ok is False

    def test_validate_ok(self):
        dc = DebateConfig(enabled=True, model_ids=["a", "b", "c"], min_participants=2)
        ok, msg = dc.validate_config()
        assert ok is True
        assert msg == "Valid configuration"

    def test_timeout_bounds(self):
        with pytest.raises(ValidationError):
            DebateConfig(timeout_seconds=29)
        with pytest.raises(ValidationError):
            DebateConfig(timeout_seconds=301)

    def test_min_participants_bounds(self):
        with pytest.raises(ValidationError):
            DebateConfig(min_participants=1)
        with pytest.raises(ValidationError):
            DebateConfig(min_participants=6)
