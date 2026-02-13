"""
Unified strategy models for trading strategies.

A strategy is a PURE LOGIC TEMPLATE that defines trading rules.
It does NOT bind to any exchange account or AI model - those
bindings are on the Agent (execution instance).

Supports multiple strategy types via polymorphic config:
- ai: AI-driven with LLM prompt, indicators, risk controls
- grid: Grid trading with price ranges
- dca: Dollar-cost averaging
- rsi: RSI indicator-based trading
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field, model_validator

from .decision import RiskControls


# =============================================================================
# Enums
# =============================================================================

class StrategyType(str, Enum):
    """Strategy type discriminator"""
    AI = "ai"
    GRID = "grid"
    DCA = "dca"
    RSI = "rsi"


class TradingMode(str, Enum):
    """Trading style/mode (AI strategies only)"""
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"


class StrategyVisibility(str, Enum):
    """Strategy visibility in marketplace"""
    PRIVATE = "private"
    PUBLIC = "public"


class PricingModel(str, Enum):
    """Strategy pricing model"""
    FREE = "free"
    ONE_TIME = "one_time"
    MONTHLY = "monthly"


# =============================================================================
# AI Strategy Config
# =============================================================================

class PromptSections(BaseModel):
    """
    Customizable sections of the system prompt.

    These allow users to fine-tune AI behavior without rewriting the entire prompt.
    Based on NoFx's 8-section prompt structure.
    """
    role_definition: str = Field(
        default="You are an expert cryptocurrency trader with deep market analysis skills.",
        description="AI role and persona definition"
    )
    trading_frequency: str = Field(
        default="Analyze market every 30-60 minutes. Only trade when high-confidence setups appear.",
        description="How often to trade"
    )
    entry_standards: str = Field(
        default="Enter positions only when multiple indicators align and risk/reward is favorable.",
        description="Criteria for entering trades"
    )
    decision_process: str = Field(
        default="1. Assess overall market trend\n2. Identify key support/resistance\n3. Check momentum indicators\n4. Evaluate risk/reward\n5. Make decision",
        description="Step-by-step decision process"
    )


class AIStrategyConfig(BaseModel):
    """
    Configuration for AI-driven strategies.

    Contains all the settings that were previously split between
    StrategyDB top-level fields and StrategyConfig.
    """
    # Prompt (the user's natural language trading instructions)
    prompt: str = Field(
        default="",
        description="Natural language trading instructions"
    )

    # Trading mode
    trading_mode: TradingMode = Field(default=TradingMode.CONSERVATIVE)

    # Symbols (kept here for PromptBuilder compatibility;
    # also stored at StrategyDB.symbols top level)
    symbols: list[str] = Field(
        default=["BTC", "ETH"],
        description="Trading symbols to analyze"
    )

    # Prompt language (auto-set from frontend locale)
    language: str = Field(default="en", description="Prompt language: 'en' or 'zh'")

    # Indicator settings
    indicators: dict = Field(
        default_factory=lambda: {
            "ema_periods": [9, 21, 55],
            "rsi_period": 14,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "atr_period": 14,
        },
        description="Technical indicator settings"
    )

    # Timeframes
    timeframes: list[str] = Field(
        default=["15m", "1h", "4h"],
        description="Timeframes to analyze"
    )

    # Risk controls (hard limits)
    risk_controls: RiskControls = Field(
        default_factory=RiskControls,
        description="Risk control parameters"
    )

    # Prompt customization
    prompt_mode: str = Field(
        default="simple",
        description="Prompt editing mode: 'simple' (section-based) or 'advanced' (full markdown editor)"
    )
    prompt_sections: PromptSections = Field(
        default_factory=PromptSections,
        description="Customizable prompt sections (used in simple mode)"
    )

    # Custom prompt addition
    custom_prompt: str = Field(
        default="",
        description="Additional custom instructions appended to system prompt (used in simple mode, deprecated)"
    )

    # Advanced prompt (full markdown content for sections 1-6)
    advanced_prompt: str = Field(
        default="",
        description="Full custom prompt content for advanced mode (replaces sections 1-6)"
    )

    # Multi-model debate settings
    debate_enabled: bool = Field(
        default=False,
        description="Enable multi-model debate for decisions"
    )
    debate_models: list[str] = Field(
        default_factory=list,
        description="List of model IDs for debate (e.g., ['deepseek:deepseek-chat', 'qwen:qwen-plus'])"
    )
    debate_consensus_mode: str = Field(
        default="majority_vote",
        description="Consensus mode: majority_vote, highest_confidence, weighted_average, unanimous"
    )
    debate_min_participants: int = Field(
        default=2,
        ge=2,
        le=5,
        description="Minimum successful model responses required for valid debate"
    )


# =============================================================================
# Quant Strategy Configs (reuse existing, no changes)
# =============================================================================

class GridConfig(BaseModel):
    """Configuration for Grid trading strategy"""
    upper_price: float = Field(..., gt=0, description="Upper price boundary of the grid")
    lower_price: float = Field(..., gt=0, description="Lower price boundary of the grid")
    grid_count: int = Field(..., ge=2, le=200, description="Number of grid levels")
    total_investment: float = Field(..., gt=0, description="Total investment amount (USD)")
    leverage: float = Field(default=1.0, ge=1.0, le=50.0, description="Leverage multiplier")

    @model_validator(mode="after")
    def validate_price_range(self):
        if self.upper_price <= self.lower_price:
            raise ValueError("upper_price must be greater than lower_price")
        return self


class DCAConfig(BaseModel):
    """Configuration for DCA (Dollar-Cost Averaging) strategy"""
    order_amount: float = Field(..., gt=0, description="Amount per order (USD)")
    interval_minutes: int = Field(..., ge=1, le=43200, description="Time between orders (minutes)")
    take_profit_percent: float = Field(default=5.0, ge=0.1, le=100.0, description="Take profit percentage")
    total_budget: float = Field(default=0, ge=0, description="Total budget limit (0 = unlimited)")
    max_orders: int = Field(default=0, ge=0, description="Max number of orders (0 = unlimited)")


class RSIConfig(BaseModel):
    """Configuration for RSI-based trading strategy"""
    rsi_period: int = Field(default=14, ge=2, le=100, description="RSI calculation period")
    overbought_threshold: float = Field(default=70.0, ge=50.0, le=95.0, description="RSI overbought level (sell signal)")
    oversold_threshold: float = Field(default=30.0, ge=5.0, le=50.0, description="RSI oversold level (buy signal)")
    order_amount: float = Field(..., gt=0, description="Amount per order (USD)")
    timeframe: str = Field(default="1h", description="Timeframe for RSI calculation (e.g., 15m, 1h, 4h)")
    leverage: float = Field(default=1.0, ge=1.0, le=50.0, description="Leverage multiplier")

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.overbought_threshold <= self.oversold_threshold:
            raise ValueError("overbought_threshold must be greater than oversold_threshold")
        return self


# Strategy type -> config model mapping
STRATEGY_CONFIG_MODELS: dict[str, type[BaseModel]] = {
    "ai": AIStrategyConfig,
    "grid": GridConfig,
    "dca": DCAConfig,
    "rsi": RSIConfig,
}


# =============================================================================
# Strategy Entity & Request/Response Models
# =============================================================================

class Strategy(BaseModel):
    """
    Trading strategy entity (read model).

    Represents a user-created strategy template that can be
    instantiated as one or more Agents.
    """
    id: str
    user_id: str
    type: StrategyType
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    symbols: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)

    # Marketplace
    visibility: StrategyVisibility = Field(default=StrategyVisibility.PRIVATE)
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    forked_from: Optional[str] = None
    fork_count: int = Field(default=0)

    # Pricing
    is_paid: bool = Field(default=False)
    price_monthly: Optional[float] = None
    revenue_share_percent: float = Field(default=0.0)
    pricing_model: PricingModel = Field(default=PricingModel.FREE)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyCreate(BaseModel):
    """Request model for creating a strategy"""
    type: StrategyType
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    symbols: list[str] = Field(default_factory=list)
    config: dict = Field(..., description="Strategy-specific configuration")

    # Optional marketplace fields
    visibility: StrategyVisibility = Field(default=StrategyVisibility.PRIVATE)
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    # Optional pricing fields
    is_paid: bool = Field(default=False)
    price_monthly: Optional[float] = None
    pricing_model: PricingModel = Field(default=PricingModel.FREE)

    @model_validator(mode="after")
    def validate_config(self):
        """Validate config against the strategy type's config model."""
        config_model = STRATEGY_CONFIG_MODELS.get(self.type.value)
        if config_model:
            try:
                config_model(**self.config)
            except Exception as e:
                raise ValueError(f"Invalid config for strategy type '{self.type.value}': {e}")
        return self

    @model_validator(mode="after")
    def validate_symbols(self):
        """Ensure at least one symbol is provided."""
        if not self.symbols:
            raise ValueError("At least one trading symbol is required")
        return self

    @model_validator(mode="after")
    def validate_ai_prompt(self):
        """AI strategies must have a prompt in config."""
        if self.type == StrategyType.AI:
            prompt = self.config.get("prompt", "")
            if not prompt or len(prompt.strip()) < 10:
                raise ValueError("AI strategy requires a prompt with at least 10 characters")
        return self


class StrategyUpdate(BaseModel):
    """Request model for updating a strategy"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    symbols: Optional[list[str]] = None
    config: Optional[dict] = None
    visibility: Optional[StrategyVisibility] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    is_paid: Optional[bool] = None
    price_monthly: Optional[float] = None
    pricing_model: Optional[PricingModel] = None


class StrategyFork(BaseModel):
    """Request model for forking a strategy from marketplace"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Override name (defaults to source name)")


# =============================================================================
# Backward compatibility - keep StrategyConfig as alias for AIStrategyConfig
# =============================================================================

# These are used by PromptBuilder and other services that specifically
# deal with AI strategy configuration.
StrategyConfig = AIStrategyConfig
StrategyStatus = None  # Removed - status is on Agent now
