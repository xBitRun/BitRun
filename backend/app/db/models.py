"""
SQLAlchemy ORM Models

Database schema for BITRUN trading agent platform.
All sensitive credentials are encrypted using CryptoService before storage.
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
    ai_providers: Mapped[list["AIProviderConfigDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    quant_strategies: Mapped[list["QuantStrategyDB"]] = relationship(
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
    strategies: Mapped[list["StrategyDB"]] = relationship(back_populates="account")

    def __repr__(self) -> str:
        return f"<ExchangeAccount {self.name} ({self.exchange})>"


class StrategyDB(Base):
    """
    Trading strategy model.

    Stores the user's natural language prompt, trading configuration,
    and performance metrics.
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
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exchange_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Strategy info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # AI Model configuration
    # Format: "provider:model_id" (e.g., "anthropic:claude-sonnet-4-5-20250514")
    ai_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default=None
    )  # If None, uses global default from settings

    # Configuration
    trading_mode: Mapped[str] = mapped_column(
        String(20),
        default="conservative"
    )  # aggressive, balanced, conservative
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Capital allocation (pick one mode: fixed amount or percentage)
    # Fixed amount in USD (e.g. 5000.0 = $5,000)
    allocated_capital: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )
    # Percentage of account equity (e.g. 0.3 = 30%)
    allocated_capital_percent: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )

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
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    account: Mapped[Optional["ExchangeAccountDB"]] = relationship(back_populates="strategies")
    decisions: Mapped[list["DecisionRecordDB"]] = relationship(
        back_populates="strategy",
        cascade="all, delete-orphan"
    )

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

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
        return f"<Strategy {self.name} ({self.status})>"


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


class QuantStrategyDB(Base):
    """
    Traditional quantitative strategy model.

    Stores rule-based trading strategies such as Grid, DCA, and RSI.
    Unlike AI strategies (StrategyDB), these execute deterministic
    trading rules without AI involvement.
    """
    __tablename__ = "quant_strategies"

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
        ForeignKey("exchange_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Strategy info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    # Strategy type: grid, dca, rsi
    strategy_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    # Trading pair (single symbol, e.g. "BTC")
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)

    # Type-specific configuration (JSON)
    # Grid: {upper_price, lower_price, grid_count, total_investment, leverage}
    # DCA: {order_amount, interval_minutes, take_profit_percent, total_budget, max_orders}
    # RSI: {rsi_period, overbought_threshold, oversold_threshold, order_amount, timeframe, leverage}
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Runtime state (JSON) - tracks execution state between cycles
    # Grid: {filled_grids, active_orders, ...}
    # DCA: {orders_placed, total_invested, avg_cost, ...}
    # RSI: {current_position, last_signal, ...}
    runtime_state: Mapped[dict] = mapped_column(JSON, default=dict)

    # Capital allocation (pick one mode: fixed amount or percentage)
    allocated_capital: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )
    allocated_capital_percent: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )

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
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    user: Mapped["UserDB"] = relationship(back_populates="quant_strategies")
    account: Mapped[Optional["ExchangeAccountDB"]] = relationship()

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def get_effective_capital(self, account_equity: float) -> Optional[float]:
        """Calculate effective allocated capital based on mode."""
        if self.allocated_capital is not None:
            return self.allocated_capital
        if self.allocated_capital_percent is not None:
            return account_equity * self.allocated_capital_percent
        return None

    def __repr__(self) -> str:
        return f"<QuantStrategy {self.name} ({self.strategy_type}/{self.status})>"


class StrategyPositionDB(Base):
    """
    Strategy-level position tracking.

    Records which strategy owns which position on which account.
    This is the application-level bookkeeping layer that sits above
    the exchange's account-level positions.

    Rules:
    - Only ONE open position per (account_id, symbol) at any time
      (enforced by partial unique index).
    - A 'pending' record is created BEFORE the order is placed to
      reserve the symbol slot (crash-safe "claim-then-execute" pattern).
    - On successful fill the record transitions to 'open'.
    - On failure the record is deleted (rollback).
    """
    __tablename__ = "strategy_positions"

    # Partial unique index: only one open/pending position per account+symbol
    __table_args__ = (
        Index(
            "ix_strategy_positions_unique_open",
            "account_id",
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
    # Generic strategy reference (works for both AI and quant strategies)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    strategy_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )  # "ai" | "quant"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exchange_accounts.id", ondelete="CASCADE"),
        nullable=False,
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
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    account: Mapped["ExchangeAccountDB"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<StrategyPosition {self.symbol} {self.side} "
            f"status={self.status} strategy={self.strategy_id}>"
        )


class DecisionRecordDB(Base):
    """
    AI decision record for audit trail.

    Stores complete information about each decision cycle including
    prompts, AI response, chain of thought, and execution results.
    """
    __tablename__ = "decision_records"

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
    strategy: Mapped["StrategyDB"] = relationship(back_populates="decisions")

    def __repr__(self) -> str:
        return f"<DecisionRecord {self.id} at {self.timestamp}>"
