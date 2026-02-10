"""Decision record routes"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.repositories.decision import DecisionRepository
from ...db.repositories.strategy import StrategyRepository

router = APIRouter(prefix="/decisions", tags=["Decisions"])


# ==================== Response Models ====================

class DecisionResponse(BaseModel):
    """Decision record response"""
    id: str
    strategy_id: str
    timestamp: str

    chain_of_thought: str
    market_assessment: str
    decisions: list
    overall_confidence: int

    executed: bool
    execution_results: list

    ai_model: str
    tokens_used: int
    latency_ms: int

    # Market data snapshot at the time of decision
    market_snapshot: Optional[list] = None

    # Account state snapshot at the time of decision
    account_snapshot: Optional[dict] = None

    # Multi-model debate fields
    is_debate: bool = False
    debate_models: Optional[list] = None
    debate_responses: Optional[list] = None
    debate_consensus_mode: Optional[str] = None
    debate_agreement_score: Optional[float] = None


class PaginatedDecisionResponse(BaseModel):
    """Paginated decision list response"""
    items: list[DecisionResponse]
    total: int
    limit: int
    offset: int


class DecisionStatsResponse(BaseModel):
    """Decision statistics response"""
    total_decisions: int
    executed_decisions: int
    average_confidence: float
    average_latency_ms: float
    total_tokens: int = 0
    action_counts: dict = {}


# ==================== Routes ====================

@router.get("/recent", response_model=list[DecisionResponse])
async def get_recent_decisions(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    limit: int = 20,
):
    """
    Get recent decisions across all user's strategies.

    Returns newest first.
    """
    repo = DecisionRepository(db)
    decisions = await repo.get_recent(uuid.UUID(user_id), limit=limit)

    return [_decision_to_response(d) for d in decisions]


@router.get("/strategy/{strategy_id}", response_model=PaginatedDecisionResponse)
async def get_strategy_decisions(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    limit: int = 10,
    offset: int = 0,
    execution_filter: str = "all",
    action: Optional[str] = None,
):
    """
    Get decisions for a specific strategy (paginated).

    Returns newest first.

    - execution_filter: "all" | "executed" | "skipped"
    - action: filter by action type (e.g. "open_long", "hold")
    """
    # Verify user owns the strategy
    strategy_repo = StrategyRepository(db)
    strategy = await strategy_repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    repo = DecisionRepository(db)
    sid = uuid.UUID(strategy_id)

    decisions = await repo.get_by_strategy(
        sid,
        limit=limit,
        offset=offset,
        execution_filter=execution_filter,
        action_filter=action,
    )
    total = await repo.count_by_strategy(sid, execution_filter=execution_filter, action_filter=action)

    return PaginatedDecisionResponse(
        items=[_decision_to_response(d) for d in decisions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/strategy/{strategy_id}/stats", response_model=DecisionStatsResponse)
async def get_strategy_decision_stats(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get decision statistics for a strategy"""
    # Verify user owns the strategy
    strategy_repo = StrategyRepository(db)
    strategy = await strategy_repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    repo = DecisionRepository(db)
    stats = await repo.get_stats(uuid.UUID(strategy_id))

    return DecisionStatsResponse(**stats)


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get a specific decision record"""
    repo = DecisionRepository(db)
    decision = await repo.get_by_id(uuid.UUID(decision_id), uuid.UUID(user_id))

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found"
        )

    # Verify user owns the strategy
    strategy_repo = StrategyRepository(db)
    strategy = await strategy_repo.get_by_id(decision.strategy_id, uuid.UUID(user_id))
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found"
        )

    return _decision_to_response(decision)


# ==================== Helper Functions ====================

def _decision_to_response(decision) -> DecisionResponse:
    """Convert decision DB model to response"""
    ts = decision.timestamp
    timestamp = ts.isoformat() + ("Z" if ts.tzinfo is None else "")
    return DecisionResponse(
        id=str(decision.id),
        strategy_id=str(decision.strategy_id),
        timestamp=timestamp,
        chain_of_thought=decision.chain_of_thought,
        market_assessment=decision.market_assessment,
        decisions=decision.decisions,
        overall_confidence=decision.overall_confidence,
        executed=decision.executed,
        execution_results=decision.execution_results,
        ai_model=decision.ai_model,
        tokens_used=decision.tokens_used,
        latency_ms=decision.latency_ms,
        market_snapshot=decision.market_snapshot,
        account_snapshot=decision.account_snapshot,
        is_debate=decision.is_debate,
        debate_models=decision.debate_models,
        debate_responses=decision.debate_responses,
        debate_consensus_mode=decision.debate_consensus_mode,
        debate_agreement_score=decision.debate_agreement_score,
    )
