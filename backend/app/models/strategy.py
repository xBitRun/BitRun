"""
Strategy models for trading strategies.

A strategy combines:
- User prompt (natural language trading instructions)
- Trading mode (aggressive/balanced/conservative)
- Risk controls (hard limits enforced by code)
- Account binding (which exchange account to use)
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .decision import RiskControls


class StrategyStatus(str, Enum):
    """Strategy lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class TradingMode(str, Enum):
    """Trading style/mode"""
    AGGRESSIVE = "aggressive"  # Higher risk, higher reward
    BALANCED = "balanced"  # Balanced risk/reward
    CONSERVATIVE = "conservative"  # Lower risk, steady returns


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


class StrategyConfig(BaseModel):
    """
    Complete strategy configuration.

    Includes coin selection, indicators, risk controls, and prompt customization.
    """
    # Prompt language (auto-set from frontend locale)
    language: str = Field(
        default="en",
        description="Prompt language: 'en' or 'zh'"
    )

    # Coin selection
    symbols: list[str] = Field(
        default=["BTC", "ETH"],
        description="Symbols to trade"
    )

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
    prompt_sections: PromptSections = Field(
        default_factory=PromptSections,
        description="Customizable prompt sections"
    )

    # Custom prompt addition
    custom_prompt: str = Field(
        default="",
        description="Additional custom instructions appended to system prompt"
    )

    # Execution settings
    execution_interval_minutes: int = Field(
        default=30,
        ge=5,
        le=1440,
        description="How often to run the strategy (minutes)"
    )
    auto_execute: bool = Field(
        default=True,
        description="Automatically execute decisions above confidence threshold"
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


class Strategy(BaseModel):
    """
    Trading strategy entity.

    Represents a user-created strategy that can be activated to trade.
    """
    id: str
    user_id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")

    # Core configuration
    prompt: str = Field(
        ...,
        min_length=10,
        description="Natural language trading instructions"
    )
    trading_mode: TradingMode = Field(default=TradingMode.CONSERVATIVE)
    config: StrategyConfig = Field(default_factory=StrategyConfig)

    # AI Model selection
    # Format: "provider:model_id" (e.g., "anthropic:claude-sonnet-4-5-20250514")
    ai_model: Optional[str] = Field(
        default=None,
        description="AI model to use. If None, uses global default."
    )

    # Account binding
    account_id: str = Field(..., description="Exchange account to use")

    # Status
    status: StrategyStatus = Field(default=StrategyStatus.DRAFT)
    error_message: Optional[str] = None

    # Performance tracking
    total_pnl: float = Field(default=0.0)
    total_trades: int = Field(default=0)
    winning_trades: int = Field(default=0)
    losing_trades: int = Field(default=0)
    max_drawdown: float = Field(default=0.0)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_run_at: Optional[datetime] = None

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100


class StrategyCreate(BaseModel):
    """Request model for creating a strategy"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    prompt: str = Field(..., min_length=10)
    trading_mode: TradingMode = Field(default=TradingMode.CONSERVATIVE)
    config: StrategyConfig = Field(default_factory=StrategyConfig)
    account_id: str
    ai_model: Optional[str] = Field(
        default=None,
        description="AI model in format 'provider:model_id'. If None, uses global default."
    )


class StrategyUpdate(BaseModel):
    """Request model for updating a strategy"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    prompt: Optional[str] = Field(None, min_length=10)
    trading_mode: Optional[TradingMode] = None
    config: Optional[StrategyConfig] = None
    account_id: Optional[str] = None
    ai_model: Optional[str] = Field(
        default=None,
        description="AI model in format 'provider:model_id'. Set to empty string to use global default."
    )
    status: Optional[StrategyStatus] = None
