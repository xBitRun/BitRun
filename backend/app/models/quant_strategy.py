"""
Quant strategy models for traditional quantitative trading strategies.

Supports three strategy types:
- Grid: Grid trading with configurable price ranges
- DCA: Dollar-cost averaging with scheduled buys
- RSI: RSI indicator-based trading
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field, model_validator


class QuantStrategyType(str, Enum):
    """Type of quantitative strategy"""
    GRID = "grid"
    DCA = "dca"
    RSI = "rsi"


class QuantStrategyStatus(str, Enum):
    """Strategy lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    WARNING = "warning"


# ==================== Strategy-specific configs ====================

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


# Config model mapping for validation
QUANT_CONFIG_MODELS = {
    "grid": GridConfig,
    "dca": DCAConfig,
    "rsi": RSIConfig,
}


# ==================== Request/Response models ====================

class QuantStrategyCreate(BaseModel):
    """Request model for creating a quant strategy"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    strategy_type: QuantStrategyType
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol, e.g. BTC")
    account_id: Optional[str] = None
    config: dict = Field(..., description="Strategy-specific configuration")
    # Capital allocation (pick one)
    allocated_capital: Optional[float] = Field(default=None, ge=0)
    allocated_capital_percent: Optional[float] = Field(default=None, ge=0, le=1.0)

    @model_validator(mode="after")
    def validate_capital_allocation(self):
        if self.allocated_capital is not None and self.allocated_capital_percent is not None:
            raise ValueError(
                "Cannot set both allocated_capital and allocated_capital_percent. "
                "Choose one allocation mode."
            )
        return self


class QuantStrategyUpdate(BaseModel):
    """Request model for updating a quant strategy"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    config: Optional[dict] = None
    account_id: Optional[str] = None
    allocated_capital: Optional[float] = Field(default=None, ge=0)
    allocated_capital_percent: Optional[float] = Field(default=None, ge=0, le=1.0)

    @model_validator(mode="after")
    def validate_capital_allocation(self):
        if self.allocated_capital is not None and self.allocated_capital_percent is not None:
            raise ValueError(
                "Cannot set both allocated_capital and allocated_capital_percent. "
                "Choose one allocation mode."
            )
        return self


class QuantStrategyStatusUpdate(BaseModel):
    """Update quant strategy status"""
    status: str = Field(..., description="New status: active, paused, stopped")
    close_positions: bool = Field(
        default=False,
        description="If True, close all open positions when stopping"
    )


class QuantStrategyResponse(BaseModel):
    """Quant strategy response"""
    id: str
    name: str
    description: str
    strategy_type: str
    symbol: str
    config: dict
    runtime_state: dict
    status: str
    error_message: Optional[str] = None
    account_id: Optional[str] = None

    # Capital allocation
    allocated_capital: Optional[float] = None
    allocated_capital_percent: Optional[float] = None

    # Performance
    total_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float

    # Timestamps
    created_at: str
    updated_at: str
    last_run_at: Optional[str] = None
