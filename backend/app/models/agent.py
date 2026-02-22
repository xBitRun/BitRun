"""
Agent models for execution instances.

An Agent is a running instance of a Strategy, binding it to:
- AI model (for AI strategies)
- Exchange account (for live mode) or mock config (for simulation)
- Capital allocation and execution settings

One Strategy can have multiple Agents with different configurations.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field, model_validator

from ..traders.exchange_capabilities import AssetType

if TYPE_CHECKING:
    from ..traders.base import AccountState


class AgentStatus(str, Enum):
    """Agent lifecycle status"""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    WARNING = "warning"


class ExecutionMode(str, Enum):
    """Agent execution mode"""

    LIVE = "live"
    MOCK = "mock"


# =============================================================================
# Agent Entity & Request/Response Models
# =============================================================================


class Agent(BaseModel):
    """
    Execution agent entity (read model).

    Represents a running instance of a strategy with specific
    runtime bindings (model, account, capital).
    """

    id: str
    user_id: str
    name: str = Field(..., min_length=1, max_length=100)

    # Strategy binding
    strategy_id: str

    # AI model (required for AI strategies, null for quant)
    ai_model: Optional[str] = None

    # Execution mode
    execution_mode: ExecutionMode = Field(default=ExecutionMode.MOCK)
    account_id: Optional[str] = None
    mock_initial_balance: Optional[float] = None

    # Capital allocation
    allocated_capital: Optional[float] = None
    allocated_capital_percent: Optional[float] = None

    # Execution config
    execution_interval_minutes: int = Field(default=15)
    auto_execute: bool = Field(default=True)

    # Trade type configuration
    trade_type: AssetType = Field(default=AssetType.CRYPTO_PERP)

    # Multi-model debate configuration (for AI strategies)
    debate_enabled: bool = Field(default=False)
    debate_models: list[str] = Field(default_factory=list)
    debate_consensus_mode: str = Field(default="majority_vote")
    debate_min_participants: int = Field(default=2, ge=2, le=5)

    # Quant runtime state
    runtime_state: Optional[dict] = None

    # Status
    status: AgentStatus = Field(default=AgentStatus.DRAFT)
    error_message: Optional[str] = None

    # Performance
    total_pnl: float = Field(default=0.0)
    total_trades: int = Field(default=0)
    winning_trades: int = Field(default=0)
    losing_trades: int = Field(default=0)
    max_drawdown: float = Field(default=0.0)

    # Execution tracking
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100


class AgentCreate(BaseModel):
    """Request model for creating an agent"""

    name: str = Field(..., min_length=1, max_length=100)
    strategy_id: str

    # AI model (validated at API layer - required for AI strategies)
    ai_model: Optional[str] = Field(
        default=None,
        description="AI model in format 'provider:model_id'. Required for AI strategies.",
    )

    # Execution mode
    execution_mode: ExecutionMode = Field(default=ExecutionMode.MOCK)
    account_id: Optional[str] = Field(
        default=None, description="Exchange account ID. Required for live mode."
    )
    mock_initial_balance: Optional[float] = Field(
        default=10000.0, ge=100, description="Initial balance for mock mode (USD)"
    )

    # Capital allocation (pick one)
    allocated_capital: Optional[float] = Field(default=None, ge=0)
    allocated_capital_percent: Optional[float] = Field(default=None, ge=0, le=1.0)

    # Execution config
    execution_interval_minutes: int = Field(
        default=15, ge=1, le=43200, description="Execution intervals in minutes"
    )
    auto_execute: bool = Field(
        default=True,
        description="Automatically execute decisions above confidence threshold",
    )

    # Trade type configuration
    trade_type: AssetType = Field(
        default=AssetType.CRYPTO_PERP,
        description="Market type: crypto_perp, crypto_spot, forex, metals",
    )

    # Multi-model debate configuration (for AI strategies)
    debate_enabled: bool = Field(
        default=False, description="Enable multi-model debate for decisions"
    )
    debate_models: list[str] = Field(
        default_factory=list,
        description="List of model IDs for debate (e.g., ['deepseek:deepseek-chat', 'qwen:qwen-plus'])",
    )
    debate_consensus_mode: str = Field(
        default="majority_vote",
        description="Consensus mode: majority_vote, highest_confidence, weighted_average, unanimous",
    )
    debate_min_participants: int = Field(
        default=2,
        ge=2,
        le=5,
        description="Minimum successful model responses required for valid debate",
    )

    @model_validator(mode="after")
    def validate_execution_mode(self):
        """Validate that live mode has an account and mock mode has balance."""
        if self.execution_mode == ExecutionMode.LIVE and not self.account_id:
            raise ValueError("account_id is required for live execution mode")
        if (
            self.execution_mode == ExecutionMode.MOCK
            and self.mock_initial_balance is None
        ):
            self.mock_initial_balance = 10000.0
        return self

    @model_validator(mode="after")
    def validate_capital_allocation(self):
        """Cannot set both capital allocation modes."""
        if (
            self.allocated_capital is not None
            and self.allocated_capital_percent is not None
        ):
            raise ValueError(
                "Cannot set both allocated_capital and allocated_capital_percent. "
                "Choose one allocation mode."
            )
        return self


class AgentUpdate(BaseModel):
    """Request model for updating an agent"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    ai_model: Optional[str] = None
    execution_mode: Optional[ExecutionMode] = None
    account_id: Optional[str] = None
    mock_initial_balance: Optional[float] = Field(None, ge=100)
    allocated_capital: Optional[float] = Field(None, ge=0)
    allocated_capital_percent: Optional[float] = Field(None, ge=0, le=1.0)
    execution_interval_minutes: Optional[int] = Field(None, ge=1, le=43200)
    auto_execute: Optional[bool] = None
    # Multi-model debate configuration
    debate_enabled: Optional[bool] = None
    debate_models: Optional[list[str]] = None
    debate_consensus_mode: Optional[str] = None
    debate_min_participants: Optional[int] = Field(None, ge=2, le=5)

    # Trade type configuration
    trade_type: Optional[AssetType] = None

    @model_validator(mode="after")
    def validate_capital_allocation(self):
        if (
            self.allocated_capital is not None
            and self.allocated_capital_percent is not None
        ):
            raise ValueError(
                "Cannot set both allocated_capital and allocated_capital_percent. "
                "Choose one allocation mode."
            )
        return self


class AgentStatusUpdate(BaseModel):
    """Request model for changing agent status"""

    status: str = Field(..., description="New status: active, paused, stopped")
    close_positions: bool = Field(
        default=False, description="If True, close all open positions when stopping"
    )


# =============================================================================
# Agent Position Models
# =============================================================================


class AgentPosition(BaseModel):
    """Agent position entity (read model)"""

    id: str
    agent_id: str
    account_id: Optional[str] = None
    symbol: str
    side: str  # "long" | "short"
    size: float
    size_usd: float
    entry_price: float
    leverage: int
    status: str  # "pending" | "open" | "closed"
    realized_pnl: float = 0.0
    close_price: Optional[float] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class AgentAccountState(BaseModel):
    """
    Virtual account state for an agent.

    Provides agent-isolated view of positions and balance,
    preventing cross-agent interference in prompt building
    and trade execution.
    """

    agent_id: str
    positions: list[AgentPosition] = Field(default_factory=list)
    equity: float = Field(
        default=0.0, description="allocated_capital + sum(unrealized_pnl)"
    )
    available_balance: float = Field(
        default=0.0, description="equity - sum(position_margin)"
    )
    total_unrealized_pnl: float = Field(default=0.0)

    def to_account_state(
        self, current_prices: Optional[dict[str, float]] = None
    ) -> "AccountState":
        """
        Convert to the AccountState dataclass expected by PromptBuilder.

        Maps AgentPosition fields to the Position dataclass, computing
        derived fields (mark_price, unrealized_pnl_percent, margin_used)
        so the prompt sees the same format as a real exchange account.
        """
        from ..traders.base import AccountState, Position

        prices = current_prices or {}
        trader_positions: list[Position] = []
        total_margin_used = 0.0

        for pos in self.positions:
            mark = prices.get(pos.symbol, pos.entry_price)
            if pos.side == "long":
                unrealized = (mark - pos.entry_price) * pos.size
            else:
                unrealized = (pos.entry_price - mark) * pos.size
            pnl_pct = (unrealized / pos.size_usd * 100) if pos.size_usd else 0.0
            margin = pos.size_usd / max(pos.leverage, 1)
            total_margin_used += margin

            trader_positions.append(
                Position(
                    symbol=pos.symbol,
                    side=pos.side,
                    size=pos.size,
                    size_usd=pos.size_usd,
                    entry_price=pos.entry_price,
                    mark_price=mark,
                    leverage=pos.leverage,
                    unrealized_pnl=unrealized,
                    unrealized_pnl_percent=pnl_pct,
                    liquidation_price=None,
                    margin_used=margin,
                )
            )

        return AccountState(
            equity=self.equity,
            available_balance=self.available_balance,
            total_margin_used=total_margin_used,
            unrealized_pnl=self.total_unrealized_pnl,
            positions=trader_positions,
        )
