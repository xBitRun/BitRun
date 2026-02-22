"""
DEPRECATED: Quant strategy models.

Quant strategies (Grid, DCA, RSI) have been unified into the Strategy model
with a `type` discriminator. Config models are now in strategy.py.

This file re-exports for backward compatibility during migration.
"""

import warnings
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator
from .strategy import (
    DCAConfig,
    GridConfig,
    RSIConfig,
)

warnings.warn(
    "quant_strategy.py is deprecated. Use strategy.py with StrategyType instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export config models for backward compatibility
QUANT_CONFIG_MODELS = {
    "grid": GridConfig,
    "dca": DCAConfig,
    "rsi": RSIConfig,
}


class QuantStrategyType(str, Enum):
    """DEPRECATED: Use StrategyType instead"""

    GRID = "grid"
    DCA = "dca"
    RSI = "rsi"


class QuantStrategyStatus(str, Enum):
    """DEPRECATED: Use AgentStatus instead"""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    WARNING = "warning"


class QuantStrategyCreate(BaseModel):
    """DEPRECATED: Use StrategyCreate + AgentCreate instead"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    strategy_type: QuantStrategyType
    symbol: str = Field(..., min_length=1, max_length=20)
    account_id: Optional[str] = None
    config: dict = Field(...)
    allocated_capital: Optional[float] = Field(default=None, ge=0)
    allocated_capital_percent: Optional[float] = Field(default=None, ge=0, le=1.0)

    @model_validator(mode="after")
    def validate_capital_allocation(self):
        if (
            self.allocated_capital is not None
            and self.allocated_capital_percent is not None
        ):
            raise ValueError(
                "Cannot set both allocated_capital and allocated_capital_percent."
            )
        return self


class QuantStrategyUpdate(BaseModel):
    """DEPRECATED: Use StrategyUpdate + AgentUpdate instead"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    config: Optional[dict] = None
    account_id: Optional[str] = None
    allocated_capital: Optional[float] = Field(default=None, ge=0)
    allocated_capital_percent: Optional[float] = Field(default=None, ge=0, le=1.0)

    @model_validator(mode="after")
    def validate_capital_allocation(self):
        if (
            self.allocated_capital is not None
            and self.allocated_capital_percent is not None
        ):
            raise ValueError(
                "Cannot set both allocated_capital and allocated_capital_percent."
            )
        return self


class QuantStrategyStatusUpdate(BaseModel):
    """DEPRECATED: Use AgentStatusUpdate instead"""

    status: str = Field(...)
    close_positions: bool = Field(default=False)


class QuantStrategyResponse(BaseModel):
    """DEPRECATED: Use Agent response instead"""

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
    allocated_capital: Optional[float] = None
    allocated_capital_percent: Optional[float] = None
    total_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    created_at: str
    updated_at: str
    last_run_at: Optional[str] = None
