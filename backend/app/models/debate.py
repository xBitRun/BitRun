"""
Debate models for multi-model AI decision making.

Supports multiple AI models participating in a debate to reach
consensus on trading decisions.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .decision import TradingDecision, DecisionResponse, ActionType


class ConsensusMode(str, Enum):
    """Consensus modes for multi-model debate"""
    MAJORITY_VOTE = "majority_vote"  # Most common action wins
    HIGHEST_CONFIDENCE = "highest_confidence"  # Highest confidence model wins
    WEIGHTED_AVERAGE = "weighted_average"  # Weight by confidence
    UNANIMOUS = "unanimous"  # All must agree, else hold


class DebateParticipant(BaseModel):
    """
    Response from a single AI model in the debate.
    """
    model_id: str = Field(..., description="Full model ID (provider:model)")
    raw_response: str = Field(default="", description="Raw AI response text")
    chain_of_thought: str = Field(default="", description="Model's reasoning")
    market_assessment: str = Field(default="", description="Market assessment")
    decisions: list[TradingDecision] = Field(default_factory=list)
    overall_confidence: int = Field(default=0, ge=0, le=100)
    latency_ms: int = Field(default=0, ge=0)
    tokens_used: int = Field(default=0, ge=0)
    error: Optional[str] = Field(default=None, description="Error if model failed")

    @property
    def succeeded(self) -> bool:
        """Check if this participant responded successfully"""
        return self.error is None and len(self.decisions) > 0


class DebateVote(BaseModel):
    """
    Vote summary for a specific symbol and action.
    """
    symbol: str
    action: ActionType
    vote_count: int
    total_confidence: int
    average_confidence: float
    voters: list[str] = Field(default_factory=list)  # Model IDs that voted for this


class DebateResult(BaseModel):
    """
    Complete result of a multi-model debate.
    """
    # Participants
    participants: list[DebateParticipant] = Field(default_factory=list)
    successful_participants: int = Field(default=0)
    failed_participants: int = Field(default=0)

    # Consensus configuration
    consensus_mode: ConsensusMode = Field(default=ConsensusMode.MAJORITY_VOTE)
    min_participants: int = Field(default=2)

    # Voting results
    votes: list[DebateVote] = Field(default_factory=list)
    agreement_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="0-1 score of model agreement"
    )

    # Final consensus
    final_decisions: list[TradingDecision] = Field(default_factory=list)
    final_confidence: int = Field(default=0, ge=0, le=100)
    consensus_reasoning: str = Field(
        default="",
        description="Explanation of how consensus was reached"
    )

    # Aggregated market assessment
    combined_market_assessment: str = Field(default="")
    combined_chain_of_thought: str = Field(default="")

    # Timing
    total_latency_ms: int = Field(default=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_decision_response(self) -> DecisionResponse:
        """Convert debate result to standard DecisionResponse"""
        return DecisionResponse(
            chain_of_thought=self.combined_chain_of_thought,
            market_assessment=self.combined_market_assessment,
            decisions=self.final_decisions,
            overall_confidence=self.final_confidence,
            next_review_minutes=60,
        )

    @property
    def is_valid(self) -> bool:
        """Check if debate had enough successful participants"""
        return self.successful_participants >= self.min_participants


class DebateConfig(BaseModel):
    """
    Configuration for a debate session.
    """
    enabled: bool = Field(default=False, description="Enable debate mode")
    model_ids: list[str] = Field(
        default_factory=list,
        description="List of model IDs to participate"
    )
    consensus_mode: ConsensusMode = Field(
        default=ConsensusMode.MAJORITY_VOTE,
        description="How to reach consensus"
    )
    min_participants: int = Field(
        default=2,
        ge=2,
        le=5,
        description="Minimum successful responses required"
    )
    timeout_seconds: int = Field(
        default=120,
        ge=30,
        le=300,
        description="Timeout for each model"
    )

    def validate_config(self) -> tuple[bool, str]:
        """Validate debate configuration"""
        if not self.enabled:
            return True, "Debate disabled"

        if len(self.model_ids) < 2:
            return False, "At least 2 models required for debate"

        if len(self.model_ids) > 5:
            return False, "Maximum 5 models allowed in debate"

        if self.min_participants > len(self.model_ids):
            return False, "min_participants cannot exceed number of models"

        return True, "Valid configuration"
