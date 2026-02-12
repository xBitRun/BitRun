"""Competition routes for AI strategy leaderboard and comparison."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.repositories.strategy import StrategyRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/competition", tags=["Competition"])


# ==================== Response Models ====================


class LeaderboardEntry(BaseModel):
    """A single entry in the competition leaderboard."""

    strategy_id: str
    name: str
    status: str
    trading_mode: str
    ai_model: Optional[str] = None
    total_pnl: float
    total_pnl_percent: float
    win_rate: float
    total_trades: int
    max_drawdown: float
    rank: int
    created_at: Optional[datetime] = None


class CompetitionStatsResponse(BaseModel):
    """Competition overview statistics."""

    total_strategies: int
    active_strategies: int
    best_performer: Optional[str] = None
    best_pnl: float = 0.0
    worst_pnl: float = 0.0
    avg_win_rate: float = 0.0
    total_trades: int = 0


class LeaderboardResponse(BaseModel):
    """Full leaderboard response."""

    leaderboard: list[LeaderboardEntry]
    stats: CompetitionStatsResponse


# ==================== Routes ====================


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    user: CurrentUserDep,
    db: DbSessionDep,
    sort_by: str = Query(
        default="total_pnl",
        description="Sort field: total_pnl, win_rate, total_trades, max_drawdown",
    ),
    order: str = Query(default="desc", description="Sort order: asc or desc"),
):
    """
    Get competition leaderboard for all user strategies.

    Returns ranked strategies sorted by the specified metric.
    """
    repo = StrategyRepository(db)

    # Fetch all strategies for this user (both AI agent and any with performance data)
    strategies = await repo.list_by_user(user.id)

    entries: list[LeaderboardEntry] = []
    for s in strategies:
        total_pnl = s.total_pnl or 0.0
        win_rate = s.win_rate or 0.0
        total_trades = s.total_trades or 0
        max_drawdown = s.max_drawdown or 0.0

        # Calculate PnL percent based on allocated capital
        allocated = s.allocated_capital or 0.0
        total_pnl_percent = (
            (total_pnl / allocated * 100) if allocated > 0 else 0.0
        )

        entries.append(
            LeaderboardEntry(
                strategy_id=str(s.id),
                name=s.name,
                status=s.status or "draft",
                trading_mode=s.trading_mode or "balanced",
                ai_model=s.ai_model,
                total_pnl=total_pnl,
                total_pnl_percent=total_pnl_percent,
                win_rate=win_rate,
                total_trades=total_trades,
                max_drawdown=max_drawdown,
                rank=0,  # Will be set after sorting
                created_at=s.created_at,
            )
        )

    # Sort
    reverse = order == "desc"
    sort_key_map = {
        "total_pnl": lambda e: e.total_pnl,
        "win_rate": lambda e: e.win_rate,
        "total_trades": lambda e: e.total_trades,
        "max_drawdown": lambda e: e.max_drawdown,
    }
    key_fn = sort_key_map.get(sort_by, lambda e: e.total_pnl)
    entries.sort(key=key_fn, reverse=reverse)

    # Assign ranks
    for i, entry in enumerate(entries):
        entry.rank = i + 1

    # Build stats
    active_count = sum(1 for e in entries if e.status == "active")
    total_trades_sum = sum(e.total_trades for e in entries)
    avg_win = (
        sum(e.win_rate for e in entries) / len(entries) if entries else 0.0
    )

    best = max(entries, key=lambda e: e.total_pnl) if entries else None
    worst = min(entries, key=lambda e: e.total_pnl) if entries else None

    stats = CompetitionStatsResponse(
        total_strategies=len(entries),
        active_strategies=active_count,
        best_performer=best.name if best else None,
        best_pnl=best.total_pnl if best else 0.0,
        worst_pnl=worst.total_pnl if worst else 0.0,
        avg_win_rate=avg_win,
        total_trades=total_trades_sum,
    )

    return LeaderboardResponse(leaderboard=entries, stats=stats)
