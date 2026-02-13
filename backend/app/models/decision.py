"""
Decision models for AI trading decisions.

Based on NoFx decision structure with enhancements:
- Confidence Score (信心指数)
- Risk Controls (硬性风控约束)
- Chain of Thought logging
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    """Trading action types"""
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    HOLD = "hold"
    WAIT = "wait"


class RiskControls(BaseModel):
    """
    Risk control parameters - enforced by code, not just AI suggestions.
    
    These are hard limits that the execution engine will enforce regardless
    of what the AI suggests.
    """
    max_leverage: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum allowed leverage multiplier"
    )
    max_position_ratio: float = Field(
        default=0.2,
        ge=0.01,
        le=1.0,
        description="Max margin per position as ratio of total equity"
    )
    max_total_exposure: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="Max total exposure as ratio of equity"
    )
    min_risk_reward_ratio: float = Field(
        default=2.0,
        ge=1.0,
        description="Minimum risk/reward ratio for trades"
    )
    max_drawdown_percent: float = Field(
        default=0.1,
        ge=0.01,
        le=0.5,
        description="Max allowed drawdown before strategy pause"
    )
    min_confidence: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Minimum confidence score to execute trades"
    )
    # --- Stop Loss / Take Profit defaults ---
    default_sl_atr_multiplier: float = Field(
        default=1.5,
        ge=0.5,
        le=5.0,
        description="Default stop loss distance as ATR multiplier (e.g. 1.5 = 1.5 × ATR)"
    )
    default_tp_atr_multiplier: float = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="Default take profit distance as ATR multiplier (e.g. 3.0 = 3.0 × ATR)"
    )
    max_sl_percent: float = Field(
        default=0.10,
        ge=0.01,
        le=0.30,
        description="Maximum stop loss as percentage of entry price (hard cap, e.g. 0.10 = 10%)"
    )


class TradingDecision(BaseModel):
    """
    Single trading decision from AI.
    
    This represents one action the AI wants to take on a specific symbol.
    """
    symbol: str = Field(
        ...,
        description="Trading symbol, e.g., 'BTC', 'ETH'"
    )
    action: ActionType = Field(
        ...,
        description="Trading action to take"
    )
    leverage: int = Field(
        default=1,
        ge=1,
        le=50,
        description="Leverage multiplier"
    )
    position_size_usd: float = Field(
        default=0,
        ge=0,
        description="Notional position value in USD (= margin × leverage)"
    )
    entry_price: Optional[float] = Field(
        None,
        description="Entry price for limit orders"
    )
    stop_loss: Optional[float] = Field(
        None,
        description="Stop loss price"
    )
    take_profit: Optional[float] = Field(
        None,
        description="Take profit price"
    )
    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score 0-100"
    )
    risk_usd: float = Field(
        default=0,
        ge=0,
        description="Estimated maximum risk in USD"
    )
    reasoning: str = Field(
        ...,
        min_length=10,
        description="Reasoning for this decision"
    )
    
    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        """Normalize symbol to uppercase"""
        return v.upper().strip()
    
    def should_execute(self, min_confidence: int = 60) -> bool:
        """Check if decision meets minimum confidence threshold"""
        if self.action in (ActionType.HOLD, ActionType.WAIT):
            return False
        return self.confidence >= min_confidence


class DecisionResponse(BaseModel):
    """
    Complete AI decision response.
    
    Contains the AI's chain of thought, market assessment, and trading decisions.
    This is the structured output format we expect from Claude.
    """
    chain_of_thought: str = Field(
        ...,
        description="AI's reasoning process"
    )
    market_assessment: str = Field(
        ...,
        description="Overall market condition assessment"
    )
    decisions: list[TradingDecision] = Field(
        default_factory=list,
        description="List of trading decisions"
    )
    risk_controls: RiskControls = Field(
        default_factory=RiskControls,
        description="Risk control parameters for this cycle"
    )
    overall_confidence: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Overall confidence in market conditions"
    )
    next_review_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="Suggested time until next review"
    )


class DecisionRecord(BaseModel):
    """
    Stored decision record for audit trail.
    
    Includes all information about a decision cycle for later analysis.
    Linked to Agent (not Strategy) because decisions are made by
    specific agent instances with specific model/account bindings.
    """
    id: str
    agent_id: str
    timestamp: datetime
    
    # AI outputs
    system_prompt: str = Field(description="System prompt used")
    user_prompt: str = Field(description="User prompt with market data")
    raw_response: str = Field(description="Raw AI response")
    
    # Parsed decision
    chain_of_thought: str
    market_assessment: str
    decisions: list[TradingDecision]
    overall_confidence: int
    
    # Execution
    executed: bool = False
    execution_results: list[dict] = Field(default_factory=list)
    
    # Metadata
    ai_model: str
    tokens_used: int = 0
    latency_ms: int = 0


# JSON Schema for AI output (used in system prompt)
_DECISION_JSON_SCHEMA_EN = """{
  "chain_of_thought": "string - Your detailed reasoning process",
  "market_assessment": "string - Overall market condition summary",
  "decisions": [
    {
      "symbol": "string - Trading pair symbol (e.g., 'BTC')",
      "action": "string - One of: open_long, open_short, close_long, close_short, hold, wait",
      "leverage": "integer - Leverage multiplier (1-50)",
      "position_size_usd": "number - Notional position value in USD (= margin × leverage). E.g. to use $40 margin at 20x leverage, set this to 800.",
      "entry_price": "number | null - Entry price for limit orders",
      "stop_loss": "number - Stop loss price (REQUIRED for open_long/open_short)",
      "take_profit": "number - Take profit price (REQUIRED for open_long/open_short)",
      "confidence": "integer - Confidence score 0-100",
      "risk_usd": "number - Estimated max risk in USD",
      "reasoning": "string - Reasoning for this specific decision"
    }
  ],
  "overall_confidence": "integer - Overall market confidence 0-100",
  "next_review_minutes": "integer - Suggested time until next review (5-1440)"
}"""

_DECISION_JSON_SCHEMA_ZH = """{
  "chain_of_thought": "string - 你的详细推理分析过程（必须使用中文）",
  "market_assessment": "string - 整体市场状况评估总结（必须使用中文）",
  "decisions": [
    {
      "symbol": "string - 交易对符号（如 'BTC'）",
      "action": "string - 以下之一: open_long, open_short, close_long, close_short, hold, wait",
      "leverage": "integer - 杠杆倍数 (1-50)",
      "position_size_usd": "number - 仓位名义价值（美元）（= 保证金 × 杠杆）。例如使用 $40 保证金、20x 杠杆时，设为 800。",
      "entry_price": "number | null - 限价单入场价格",
      "stop_loss": "number - 止损价格（open_long/open_short 时必填）",
      "take_profit": "number - 止盈价格（open_long/open_short 时必填）",
      "confidence": "integer - 置信度评分 0-100",
      "risk_usd": "number - 预估最大风险（美元）",
      "reasoning": "string - 该决策的具体推理依据（必须使用中文）"
    }
  ],
  "overall_confidence": "integer - 整体市场置信度 0-100",
  "next_review_minutes": "integer - 建议下次复查时间（5-1440 分钟）"
}"""

# Keep backward-compatible alias (English version)
DECISION_JSON_SCHEMA = _DECISION_JSON_SCHEMA_EN


def get_decision_json_schema(language: str = "en") -> str:
    """Get the decision JSON schema in the specified language."""
    if language == "zh":
        return _DECISION_JSON_SCHEMA_ZH
    return _DECISION_JSON_SCHEMA_EN
