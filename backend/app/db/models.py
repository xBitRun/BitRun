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

    # Invitation and channel fields
    invite_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
        index=True
    )
    referrer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    channel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
        index=True
    )  # user, channel_admin, platform_admin

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
    pnl_records: Mapped[list["PnlRecordDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    daily_account_snapshots: Mapped[list["DailyAccountSnapshotDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    daily_agent_snapshots: Mapped[list["DailyAgentSnapshotDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # Channel relationships
    channel: Mapped[Optional["ChannelDB"]] = relationship(
        back_populates="users",
        foreign_keys=[channel_id]
    )
    referrer: Mapped[Optional["UserDB"]] = relationship(
        remote_side=[id],
        foreign_keys=[referrer_id]
    )
    wallet: Mapped[Optional["WalletDB"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    recharge_orders: Mapped[list["RechargeOrderDB"]] = relationship(
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

    # Trade type configuration (crypto_perp, crypto_spot, forex, metals)
    trade_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="crypto_perp"
    )

    # Multi-model debate configuration (for AI strategies)
    debate_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    debate_models: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    debate_consensus_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    debate_min_participants: Mapped[int] = mapped_column(Integer, default=2)

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

    # Worker heartbeat tracking
    worker_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    worker_instance_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
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


# =============================================================================
# P&L Records - Trade-level profit/loss tracking
# =============================================================================

class PnlRecordDB(Base):
    """
    P&L record for tracking individual trade profit/loss.

    Records are created when positions are closed, enabling detailed
    trade history and performance analysis. Each record captures
    the complete trade context including entry/exit prices, duration,
    and realized P&L.
    """
    __tablename__ = "pnl_records"

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
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exchange_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    position_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_positions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Trade details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # 'long' | 'short'
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    fees: Mapped[float] = mapped_column(Float, default=0.0)

    # Price and size
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    size_usd: Mapped[float] = mapped_column(Float, nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, default=1)

    # Timing
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    closed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    exit_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="pnl_records")
    agent: Mapped["AgentDB"] = relationship()
    account: Mapped[Optional["ExchangeAccountDB"]] = relationship()

    def __repr__(self) -> str:
        return f"<PnlRecord {self.symbol} {self.side} pnl={self.realized_pnl}>"


# =============================================================================
# Daily Snapshots - Historical equity and performance tracking
# =============================================================================

class DailyAccountSnapshotDB(Base):
    """
    Daily snapshot of account equity and positions.

    Created once per day (UTC midnight) for each active account.
    Enables historical equity curve visualization and period-based
    P&L analysis. Used for calculating daily/weekly/monthly returns.
    """
    __tablename__ = "daily_account_snapshots"
    __table_args__ = (
        Index(
            "uq_daily_account_snapshots_account_date",
            "account_id",
            "snapshot_date",
            unique=True,
        ),
    )

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
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exchange_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    snapshot_date: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True
    )  # Date (UTC midnight)

    # Equity components
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    available_balance: Mapped[float] = mapped_column(Float, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    margin_used: Mapped[float] = mapped_column(Float, default=0.0)

    # Daily P&L (computed from previous snapshot)
    daily_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    daily_pnl_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Position summary at snapshot time
    open_positions: Mapped[int] = mapped_column(Integer, default=0)
    position_summary: Mapped[list] = mapped_column(JSON, default=list)

    # Metadata
    snapshot_source: Mapped[str] = mapped_column(
        String(20),
        default="scheduled"
    )  # 'scheduled', 'manual', 'trade'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="daily_account_snapshots")
    account: Mapped["ExchangeAccountDB"] = relationship()

    def __repr__(self) -> str:
        return f"<DailyAccountSnapshot account={self.account_id} date={self.snapshot_date}>"


class DailyAgentSnapshotDB(Base):
    """
    Daily snapshot of agent performance metrics.

    Created once per day (UTC midnight) for each active agent.
    Tracks cumulative and daily performance metrics enabling
    historical performance analysis and comparison.
    """
    __tablename__ = "daily_agent_snapshots"
    __table_args__ = (
        Index(
            "uq_daily_agent_snapshots_agent_date",
            "agent_id",
            "snapshot_date",
            unique=True,
        ),
    )

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
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exchange_accounts.id", ondelete="SET NULL"),
        nullable=True
    )
    snapshot_date: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True
    )  # Date (UTC midnight)

    # Cumulative metrics (at snapshot time)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)

    # Daily metrics (changes since last snapshot)
    daily_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    daily_trades: Mapped[int] = mapped_column(Integer, default=0)
    daily_winning: Mapped[int] = mapped_column(Integer, default=0)
    daily_losing: Mapped[int] = mapped_column(Integer, default=0)

    # Virtual equity (for mock agents)
    virtual_equity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="daily_agent_snapshots")
    agent: Mapped["AgentDB"] = relationship()
    account: Mapped[Optional["ExchangeAccountDB"]] = relationship()

    def __repr__(self) -> str:
        return f"<DailyAgentSnapshot agent={self.agent_id} date={self.snapshot_date}>"


# =============================================================================
# Channel Management - Invitation and billing system
# =============================================================================

class ChannelDB(Base):
    """
    Channel/Distributor model for multi-tenant distribution.

    Channels are distribution partners that can invite users and earn
    commissions on user spending. Each channel has:
    - A unique code used as invite code prefix
    - A commission rate (0.0-1.0)
    - An optional admin user (channel_admin role)
    - A channel wallet for commission tracking
    """
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )  # Unique code for invite prefix
    admin_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Commission settings
    commission_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0-1.0

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        index=True
    )  # active, suspended, closed

    # Contact info
    contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Statistics (denormalized for performance)
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    total_commission: Mapped[float] = mapped_column(Float, default=0.0)

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
    users: Mapped[list["UserDB"]] = relationship(
        back_populates="channel",
        foreign_keys="UserDB.channel_id"
    )
    admin_user: Mapped[Optional["UserDB"]] = relationship(
        foreign_keys=[admin_user_id]
    )
    wallet: Mapped[Optional["ChannelWalletDB"]] = relationship(
        back_populates="channel",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Channel {self.name} ({self.code})>"


class WalletDB(Base):
    """
    User wallet for balance management.

    Each user has one wallet that tracks:
    - Available balance for spending
    - Frozen balance (reserved for ongoing operations)
    - Total recharged and consumed amounts
    Uses optimistic locking (version) for concurrent updates.
    """
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Balance
    balance: Mapped[float] = mapped_column(Float, default=0.0)  # Available balance
    frozen_balance: Mapped[float] = mapped_column(Float, default=0.0)  # Reserved

    # Statistics
    total_recharged: Mapped[float] = mapped_column(Float, default=0.0)
    total_consumed: Mapped[float] = mapped_column(Float, default=0.0)

    # Optimistic locking
    version: Mapped[int] = mapped_column(Integer, default=1)

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
    user: Mapped["UserDB"] = relationship(back_populates="wallet")
    transactions: Mapped[list["WalletTransactionDB"]] = relationship(
        back_populates="wallet",
        cascade="all, delete-orphan"
    )

    @property
    def total_balance(self) -> float:
        """Total balance including frozen."""
        return self.balance + self.frozen_balance

    def __repr__(self) -> str:
        return f"<Wallet user={self.user_id} balance={self.balance}>"


class ChannelWalletDB(Base):
    """
    Channel wallet for commission tracking.

    Each channel has one wallet that tracks:
    - Available commission balance
    - Frozen balance
    - Pending commission (to be settled)
    - Total commission earned and withdrawn
    """
    __tablename__ = "channel_wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Balance
    balance: Mapped[float] = mapped_column(Float, default=0.0)  # Available
    frozen_balance: Mapped[float] = mapped_column(Float, default=0.0)  # Reserved
    pending_commission: Mapped[float] = mapped_column(Float, default=0.0)  # Not yet settled

    # Statistics
    total_commission: Mapped[float] = mapped_column(Float, default=0.0)
    total_withdrawn: Mapped[float] = mapped_column(Float, default=0.0)

    # Optimistic locking
    version: Mapped[int] = mapped_column(Integer, default=1)

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
    channel: Mapped["ChannelDB"] = relationship(back_populates="wallet")
    transactions: Mapped[list["ChannelTransactionDB"]] = relationship(
        back_populates="wallet",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChannelWallet channel={self.channel_id} balance={self.balance}>"


class WalletTransactionDB(Base):
    """
    User wallet transaction history.

    Records all balance changes including:
    - recharge: User topped up balance
    - consume: User spent on services
    - refund: Refund to balance
    - gift: System bonus/gift
    - adjustment: Manual adjustment by admin

    Each transaction records balance before and after for audit.
    """
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction type
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )  # recharge, consume, refund, gift, adjustment

    # Amount and balance snapshot
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    balance_before: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)

    # Reference info (what caused this transaction)
    reference_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )  # strategy_subscription, recharge_order, system_gift, etc.
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Commission info (if this transaction generated commission)
    # Format: {channel_id, channel_amount, platform_amount}
    commission_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True
    )

    # Relationships
    wallet: Mapped["WalletDB"] = relationship(back_populates="transactions")

    # Indexes for efficient querying
    __table_args__ = (
        Index(
            "ix_wallet_transactions_reference",
            "reference_type",
            "reference_id"
        ),
    )

    def __repr__(self) -> str:
        return f"<WalletTransaction {self.type} amount={self.amount}>"


class ChannelTransactionDB(Base):
    """
    Channel wallet transaction history.

    Records all channel balance changes including:
    - commission: Commission earned from user spending
    - withdraw: Channel admin withdrew funds
    - adjustment: Manual adjustment
    - refund: Refund deducted from commission

    source_user_id indicates which user's activity generated this transaction.
    """
    __tablename__ = "channel_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )  # User whose activity generated this transaction

    # Transaction type
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )  # commission, withdraw, adjustment, refund

    # Amount and balance snapshot
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    balance_before: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)

    # Reference info
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True
    )

    # Relationships
    wallet: Mapped["ChannelWalletDB"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<ChannelTransaction {self.type} amount={self.amount}>"


class RechargeOrderDB(Base):
    """
    Recharge order for user balance top-up.

    Tracks the full lifecycle of a recharge:
    1. User creates order (status=pending)
    2. User makes payment (offline transfer)
    3. Platform admin confirms payment (status=paid)
    4. System processes and credits balance (status=completed)

    Supports bonus amounts for promotional campaigns.
    """
    __tablename__ = "recharge_orders"

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

    # Order info
    order_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    bonus_amount: Mapped[float] = mapped_column(Float, default=0.0)  # Promotional bonus

    # Payment
    payment_method: Mapped[str] = mapped_column(
        String(30),
        default="manual"
    )  # manual, stripe, crypto, etc.
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        index=True
    )  # pending, paid, completed, failed, refunded

    # Timestamps
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False
    )

    # Note (admin can add notes)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["UserDB"] = relationship(back_populates="recharge_orders")

    @property
    def total_amount(self) -> float:
        """Total amount including bonus."""
        return self.amount + self.bonus_amount

    def __repr__(self) -> str:
        return f"<RechargeOrder {self.order_no} amount={self.amount} status={self.status}>"
