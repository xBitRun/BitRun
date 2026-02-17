"""
SQLAlchemy ORM Models

Database schema for BITRUN trading agent platform.
All sensitive credentials are encrypted using CryptoService before storage.

Architecture (v2 - Strategy/Agent decoupling):
- Strategy: Pure trading logic template (AI or Quant), no runtime bindings
- Agent: Execution instance = Strategy + AI Model + Account/Mock
- AgentPosition: Per-agent position tracking with isolation
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


class UserDB(Base):
    """
    User model for authentication and ownership.

    Stores user credentials and profile information.
    Password is hashed with bcrypt before storage.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    accounts: Mapped[list["ExchangeAccountDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    strategies: Mapped[list["StrategyDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    agents: Mapped[list["AgentDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    ai_providers: Mapped[list["AIProviderConfigDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    backtest_results: Mapped[list["BacktestResultDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class ExchangeAccountDB(Base):
    """
    Exchange account model for storing API credentials.

    SECURITY: All credentials (api_key, api_secret, private_key) are
    encrypted using AES-256-GCM before storage via CryptoService.
    """
    __tablename__ = "exchange_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Account info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # hyperliquid, binance, bybit, okx
    is_testnet: Mapped[bool] = mapped_column(Boolean, default=False)

    # Encrypted credentials (stored as base64 encoded AES-256-GCM ciphertext)
    # For CEX: api_key + api_secret
    # For DEX (Hyperliquid): private_key only
    encrypted_api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_api_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_private_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_passphrase: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Connection status
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    connection_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="accounts")
    agents: Mapped[list["AgentDB"]] = relationship(back_populates="account")

    def __repr__(self) -> str:
        return f"<ExchangeAccount {self.name} ({self.exchange})>"


# =============================================================================
# Strategy Layer - Pure trading logic, no runtime bindings
# =============================================================================

class StrategyDB(Base):
    """
    Unified trading strategy model (pure logic template).

    Supports multiple strategy types via polymorphic config:
    - ai: AI-driven strategy with LLM prompt, indicators, risk controls
    - grid: Grid trading with price range and grid levels
    - dca: Dollar-cost averaging with scheduled buys
    - rsi: RSI indicator-based trading

    Strategies are DECOUPLED from execution - they don't reference any
    exchange account or AI model. Those bindings live on Agent.
    """
    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Strategy type discriminator
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )  # "ai", "grid", "dca", "rsi"

    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    # Trading symbols (unified: AI = multi-symbol, Quant = typically single)
    symbols: Mapped[list] = mapped_column(JSON, default=list)

    # Polymorphic configuration (structure depends on type)
    # AI: {prompt, trading_mode, indicators, timeframes, risk_controls,
    #       prompt_sections, prompt_mode, advanced_prompt, custom_prompt, language,
    #       debate_enabled, debate_models, debate_consensus_mode, debate_min_participants}
    # Grid: {upper_price, lower_price, grid_count, total_investment, leverage}
    # DCA: {order_amount, interval_minutes, take_profit_percent, total_budget, max_orders}
    # RSI: {rsi_period, overbought_threshold, oversold_threshold, order_amount, timeframe, leverage}
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Strategy marketplace fields
    visibility: Mapped[str] = mapped_column(
        String(20),
        default="private"
    )  # "private", "public"
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    forked_from: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True
    )
    fork_count: Mapped[int] = mapped_column(Integer, default=0)

    # Pricing fields (paid strategies)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    price_monthly: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    revenue_share_percent: Mapped[float] = mapped_column(Float, default=0.0)
    # "free", "one_time", "monthly"
    pricing_model: Mapped[str] = mapped_column(String(20), default="free")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="strategies")
    agents: Mapped[list["AgentDB"]] = relationship(
        back_populates="strategy",
        cascade="all, delete-orphan"
    )
    source_strategy: Mapped[Optional["StrategyDB"]] = relationship(
        remote_side="StrategyDB.id",
        foreign_keys=[forked_from],
    )
    versions: Mapped[list["StrategyVersionDB"]] = relationship(
        back_populates="strategy",
        cascade="all, delete-orphan",
        order_by="StrategyVersionDB.version.desc()"
    )

    def __repr__(self) -> str:
        return f"<Strategy {self.name} (type={self.type})>"


# =============================================================================
# Strategy Versioning - Config change history
# =============================================================================

class StrategyVersionDB(Base):
    """
    Strategy version snapshot.

    Automatically created when a strategy's config, symbols, or description
    is changed. Allows users to view change history and restore previous
    configurations.
    """
    __tablename__ = "strategy_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Version number (auto-incremented per strategy)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Snapshot of strategy state at this version
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    symbols: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Change description (auto-generated or user-provided)
    change_note: Mapped[str] = mapped_column(Text, default="")

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    strategy: Mapped["StrategyDB"] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<StrategyVersion {self.strategy_id} v{self.version}>"


# =============================================================================
# Strategy Subscriptions - Paid strategy access
# =============================================================================

class StrategySubscriptionDB(Base):
    """
    Subscription record for a paid strategy.

    Tracks which users have subscribed to (purchased access to) a paid
    strategy, along with their subscription status and expiry.
    """
    __tablename__ = "strategy_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Subscription status
    status: Mapped[str] = mapped_column(
        String(20),
        default="active"
    )  # "active", "expired", "cancelled"

    # Pricing at time of subscription
    price_paid: Mapped[float] = mapped_column(Float, default=0.0)
    pricing_model: Mapped[str] = mapped_column(String(20), default="free")

    # Subscription period
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<Subscription user={self.user_id} strategy={self.strategy_id}>"


# =============================================================================
# Agent Layer - Execution instance = Strategy + Model + Account/Mock
# =============================================================================

class AgentDB(Base):
    """
    Execution agent - a running instance of a strategy.

    Binds a Strategy to runtime resources:
    - AI model (for AI strategies only)
    - Exchange account (for live mode) or mock config (for simulation)
    - Capital allocation and execution settings

    One Strategy can have multiple Agents (different models, accounts, modes).
    """
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Strategy binding
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # AI model binding (required for AI strategies, null for quant)
    # Format: "provider:model_id" (e.g., "deepseek:deepseek-chat")
    ai_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default=None
    )

    # Execution mode
    execution_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="mock"
    )  # "live", "mock"

    # Live mode: exchange account binding
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exchange_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Mock mode: simulated initial balance
    mock_initial_balance: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )

    # Capital allocation (pick one mode: fixed amount or percentage)
    allocated_capital: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )
    allocated_capital_percent: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )

    # Execution configuration
    execution_interval_minutes: Mapped[int] = mapped_column(
        Integer, default=15
    )
    auto_execute: Mapped[bool] = mapped_column(Boolean, default=True)

    # Quant strategy runtime state (only for grid/dca/rsi)
    # Grid: {filled_grids, active_orders, ...}
    # DCA: {orders_placed, total_invested, avg_cost, ...}
    # RSI: {current_position, last_signal, ...}
    runtime_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        index=True
    )  # draft, active, paused, stopped, error, warning
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Performance metrics
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)

    # Execution tracking
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="agents")
    strategy: Mapped["StrategyDB"] = relationship(back_populates="agents")
    account: Mapped[Optional["ExchangeAccountDB"]] = relationship(back_populates="agents")
    decisions: Mapped[list["DecisionRecordDB"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    positions: Mapped[list["AgentPositionDB"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan"
    )

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    @property
    def strategy_type(self) -> Optional[str]:
        """Get strategy type from related strategy.

        Provides backward compatibility for legacy QuantStrategyDB code
        that expected a strategy_type field directly on this model.
        """
        return self.strategy.type if self.strategy else None

    @property
    def symbol(self) -> Optional[str]:
        """Get primary symbol from related strategy.

        Provides backward compatibility for legacy QuantStrategyDB code.
        For quant strategies, returns the first (typically only) symbol.
        """
        if self.strategy and self.strategy.symbols:
            return self.strategy.symbols[0]
        return None

    @property
    def config(self) -> dict:
        """Get config from related strategy.

        Provides backward compatibility for legacy QuantStrategyDB code
        that expected a config field directly on this model.
        """
        return self.strategy.config if self.strategy else {}

    def get_effective_capital(self, account_equity: float) -> Optional[float]:
        """Calculate effective allocated capital based on mode.

        Returns None if no allocation is configured.
        """
        if self.allocated_capital is not None:
            return self.allocated_capital
        if self.allocated_capital_percent is not None:
            return account_equity * self.allocated_capital_percent
        return None

    def __repr__(self) -> str:
        return f"<Agent {self.name} (status={self.status})>"


# =============================================================================
# Position Layer - Agent-level position isolation
# =============================================================================

class AgentPositionDB(Base):
    """
    Agent-level position tracking with isolation.

    Each agent has its own position ledger, isolated from other agents
    even when sharing the same exchange account. This prevents Agent A
    from accidentally closing Agent B's positions.

    Rules:
    - Only ONE open position per (agent_id, symbol) at any time
      (enforced by partial unique index).
    - A 'pending' record is created BEFORE the order is placed to
      reserve the symbol slot (crash-safe "claim-then-execute" pattern).
    - On successful fill the record transitions to 'open'.
    - On failure the record is deleted (rollback).

    Exchange-level reconciliation:
    - The actual exchange position = SUM of all agent positions on that
      account for that symbol.
    - Reconciliation task periodically verifies consistency.
    """
    __tablename__ = "agent_positions"

    # Partial unique index: only one open/pending position per agent+symbol
    __table_args__ = (
        Index(
            "ix_agent_positions_unique_open",
            "agent_id",
            "symbol",
            unique=True,
            postgresql_where=text("status IN ('open', 'pending')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Agent that owns this position
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Exchange account (kept for exchange-level aggregation and reconciliation).
    # Nullable for mock agents which have no exchange account.
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exchange_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Position details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # "long" | "short"
    size: Mapped[float] = mapped_column(Float, default=0.0)  # Contract size
    size_usd: Mapped[float] = mapped_column(Float, default=0.0)  # Notional USD
    entry_price: Mapped[float] = mapped_column(Float, default=0.0)
    leverage: Mapped[int] = mapped_column(Integer, default=1)

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(10),
        default="pending",
        index=True,
    )  # pending -> open -> closed

    # PnL tracking
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    close_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    agent: Mapped["AgentDB"] = relationship(back_populates="positions")
    account: Mapped["ExchangeAccountDB"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<AgentPosition {self.symbol} {self.side} "
            f"status={self.status} agent={self.agent_id}>"
        )


# =============================================================================
# AI Provider Configuration
# =============================================================================

class AIProviderConfigDB(Base):
    """
    AI Provider configuration for storing user's API credentials.

    SECURITY: API keys are encrypted using AES-256-GCM before storage
    via CryptoService.

    Supports multiple provider types:
    - anthropic: Anthropic (Claude)
    - openai: OpenAI
    - deepseek: DeepSeek
    - gemini: Google Gemini
    - zhipu: Zhipu GLM
    - qwen: Alibaba Qwen
    - kimi: Moonshot Kimi
    - minimax: MiniMax
    - custom: Custom OpenAI-compatible API
    """
    __tablename__ = "ai_provider_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Provider identification
    provider_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # anthropic, openai, deepseek, gemini, zhipu, qwen, kimi, minimax, custom

    # Display info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Encrypted credentials
    encrypted_api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # API configuration
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_format: Mapped[str] = mapped_column(
        String(50),
        default="openai"
    )  # anthropic, openai, custom

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Model list (JSON array of model configs)
    # Each item: {"id": "deepseek-chat", "name": "DeepSeek V3", "context_window": 64000, ...}
    models: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="ai_providers")

    def __repr__(self) -> str:
        return f"<AIProviderConfig {self.name} ({self.provider_type})>"


# =============================================================================
# Decision Records - Audit trail for AI decisions
# =============================================================================

class DecisionRecordDB(Base):
    """
    AI decision record for audit trail.

    Stores complete information about each decision cycle including
    prompts, AI response, chain of thought, and execution results.

    Linked to Agent (not Strategy) because decisions are made by
    specific agent instances with specific model/account bindings.
    """
    __tablename__ = "decision_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True
    )

    # Prompts (for debugging and audit)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # AI response
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    chain_of_thought: Mapped[str] = mapped_column(Text, default="")
    market_assessment: Mapped[str] = mapped_column(Text, default="")

    # Parsed decisions
    decisions: Mapped[list] = mapped_column(JSON, default=list)
    overall_confidence: Mapped[int] = mapped_column(Integer, default=0)

    # Execution
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    execution_results: Mapped[list] = mapped_column(JSON, default=list)

    # Metadata
    ai_model: Mapped[str] = mapped_column(String(100), default="")
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Market data snapshot at the time of decision (structured JSON)
    market_snapshot: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Account state snapshot at the time of decision (structured JSON)
    account_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Multi-model debate fields
    is_debate: Mapped[bool] = mapped_column(Boolean, default=False)
    debate_models: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    debate_responses: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    debate_consensus_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    debate_agreement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    agent: Mapped["AgentDB"] = relationship(back_populates="decisions")

    def __repr__(self) -> str:
        return f"<DecisionRecord {self.id} at {self.timestamp}>"


# =============================================================================
# Backtest Results - Persisted backtest records
# =============================================================================

class BacktestResultDB(Base):
    """
    Persisted backtest result for history and comparison.

    Stores complete backtest results including configuration snapshot,
    performance metrics, equity curve, and trade history. Allows users
    to review past backtests and compare strategy performance over time.
    """
    __tablename__ = "backtest_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    strategy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Configuration snapshot (at backtest time)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbols: Mapped[list] = mapped_column(JSON, default=list)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False, default="hyperliquid")
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), default="1h")
    use_ai: Mapped[bool] = mapped_column(Boolean, default=False)

    # Time range
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Core metrics
    final_balance: Mapped[float] = mapped_column(Float, nullable=False)
    total_return_percent: Mapped[float] = mapped_column(Float, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown_percent: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calmar_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_fees: Mapped[float] = mapped_column(Float, default=0.0)

    # Full result data (JSON for efficient storage)
    equity_curve: Mapped[list] = mapped_column(JSON, default=list)
    drawdown_curve: Mapped[list] = mapped_column(JSON, default=list)
    trades: Mapped[list] = mapped_column(JSON, default=list)
    monthly_returns: Mapped[list] = mapped_column(JSON, default=list)
    trade_statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    symbol_breakdown: Mapped[list] = mapped_column(JSON, default=list)
    analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True
    )

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="backtest_results")
    strategy: Mapped[Optional["StrategyDB"]] = relationship()

    def __repr__(self) -> str:
        return f"<BacktestResult {self.strategy_name} {self.total_return_percent:.2f}%>"


# =============================================================================
# Backward compatibility aliases (deprecated)
# =============================================================================

# QuantStrategyDB was removed during Strategy-Agent decoupling.
# Quant strategy runtime state now lives on AgentDB.
# This alias keeps legacy imports working during migration.
QuantStrategyDB = AgentDB
