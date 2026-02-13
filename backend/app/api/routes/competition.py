"""Competition routes for agent leaderboard and strategy ranking.

Two views:
1. User's own agent leaderboard (/competition/leaderboard)
   - Ranks user's agents by performance metrics
2. Strategy marketplace ranking (/competition/strategy-ranking)
   - Aggregates performance across all agents of each public strategy
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.models import AgentDB, StrategyDB
from ...db.repositories.agent import AgentRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/competition", tags=["Competition"])


# ==================== Response Models ====================


class LeaderboardEntry(BaseModel):
    """A single entry in the user's agent leaderboard."""

    agent_id: str
    agent_name: str
    strategy_id: str
    strategy_name: str
    strategy_type: str
    status: str
    execution_mode: str
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

    total_agents: int
    active_agents: int
    best_performer: Optional[str] = None
    best_pnl: float = 0.0
    worst_pnl: float = 0.0
    avg_win_rate: float = 0.0
    total_trades: int = 0


class LeaderboardResponse(BaseModel):
    """Full leaderboard response."""

    leaderboard: list[LeaderboardEntry]
    stats: CompetitionStatsResponse


class StrategyRankingEntry(BaseModel):
    """Aggregated ranking entry for a public strategy."""

    strategy_id: str
    strategy_name: str
    strategy_type: str
    author_name: Optional[str] = None
    description: str = ""
    symbols: list[str] = []
    fork_count: int = 0
    agent_count: int = 0
    avg_pnl: float = 0.0
    total_pnl: float = 0.0
    avg_win_rate: float = 0.0
    best_pnl: float = 0.0
    total_trades: int = 0
    rank: int = 0


class StrategyRankingResponse(BaseModel):
    """Strategy marketplace ranking response."""

    rankings: list[StrategyRankingEntry]
    total: int


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
    Get leaderboard for the user's own agents.

    Returns ranked agents sorted by the specified performance metric.
    Performance data (total_pnl, win_rate, etc.) lives on AgentDB.
    """
    repo = AgentRepository(db)
    agents = await repo.get_by_user(user.id)

    entries: list[LeaderboardEntry] = []
    for a in agents:
        total_pnl = a.total_pnl or 0.0
        win_rate_val = a.win_rate
        total_trades = a.total_trades or 0
        max_drawdown = a.max_drawdown or 0.0

        # Calculate PnL percent based on allocated capital or mock balance
        allocated = a.allocated_capital or a.mock_initial_balance or 0.0
        total_pnl_percent = (
            (total_pnl / allocated * 100) if allocated > 0 else 0.0
        )

        # Get strategy info (eagerly loaded)
        strategy_name = a.strategy.name if a.strategy else "Unknown"
        strategy_type = a.strategy.type if a.strategy else "ai"

        entries.append(
            LeaderboardEntry(
                agent_id=str(a.id),
                agent_name=a.name,
                strategy_id=str(a.strategy_id),
                strategy_name=strategy_name,
                strategy_type=strategy_type,
                status=a.status or "draft",
                execution_mode=a.execution_mode,
                ai_model=a.ai_model,
                total_pnl=total_pnl,
                total_pnl_percent=total_pnl_percent,
                win_rate=win_rate_val,
                total_trades=total_trades,
                max_drawdown=max_drawdown,
                rank=0,
                created_at=a.created_at,
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
        total_agents=len(entries),
        active_agents=active_count,
        best_performer=best.agent_name if best else None,
        best_pnl=best.total_pnl if best else 0.0,
        worst_pnl=worst.total_pnl if worst else 0.0,
        avg_win_rate=avg_win,
        total_trades=total_trades_sum,
    )

    return LeaderboardResponse(leaderboard=entries, stats=stats)


@router.get("/strategy-ranking", response_model=StrategyRankingResponse)
async def get_strategy_ranking(
    user: CurrentUserDep,
    db: DbSessionDep,
    sort_by: str = Query(
        default="avg_pnl",
        description="Sort field: avg_pnl, total_pnl, avg_win_rate, agent_count, fork_count",
    ),
    type_filter: Optional[str] = Query(
        default=None,
        description="Filter by strategy type: ai, grid, dca, rsi",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    Get aggregated performance ranking for public strategies.

    For each public strategy, aggregates performance across all agents
    that have ever been created from it (own + forks).
    """
    # Fetch public strategies with user (author) info
    query = (
        select(StrategyDB)
        .where(StrategyDB.visibility == "public")
        .options(selectinload(StrategyDB.user))
    )
    if type_filter:
        query = query.where(StrategyDB.type == type_filter)

    result = await db.execute(query)
    public_strategies = list(result.scalars().all())

    if not public_strategies:
        return StrategyRankingResponse(rankings=[], total=0)

    # Fetch all agents that reference these strategies
    strategy_ids = [s.id for s in public_strategies]
    agents_query = (
        select(AgentDB)
        .where(AgentDB.strategy_id.in_(strategy_ids))
    )
    agents_result = await db.execute(agents_query)
    all_agents = list(agents_result.scalars().all())

    # Group agents by strategy
    agents_by_strategy: dict[str, list[AgentDB]] = defaultdict(list)
    for a in all_agents:
        agents_by_strategy[str(a.strategy_id)].append(a)

    # Build ranking entries
    rankings: list[StrategyRankingEntry] = []
    for s in public_strategies:
        sid = str(s.id)
        agents = agents_by_strategy.get(sid, [])
        agent_count = len(agents)

        # Aggregate performance
        total_pnl = sum(a.total_pnl or 0 for a in agents)
        avg_pnl = total_pnl / agent_count if agent_count > 0 else 0.0
        avg_win_rate = (
            sum(a.win_rate for a in agents) / agent_count
            if agent_count > 0
            else 0.0
        )
        best_pnl = max((a.total_pnl or 0 for a in agents), default=0.0)
        total_trades = sum(a.total_trades or 0 for a in agents)

        author_name = None
        try:
            if s.user:
                author_name = s.user.name
        except Exception:
            pass

        rankings.append(
            StrategyRankingEntry(
                strategy_id=sid,
                strategy_name=s.name,
                strategy_type=s.type,
                author_name=author_name,
                description=s.description or "",
                symbols=s.symbols or [],
                fork_count=s.fork_count or 0,
                agent_count=agent_count,
                avg_pnl=round(avg_pnl, 2),
                total_pnl=round(total_pnl, 2),
                avg_win_rate=round(avg_win_rate, 2),
                best_pnl=round(best_pnl, 2),
                total_trades=total_trades,
            )
        )

    # Sort
    sort_key_map = {
        "avg_pnl": lambda e: e.avg_pnl,
        "total_pnl": lambda e: e.total_pnl,
        "avg_win_rate": lambda e: e.avg_win_rate,
        "agent_count": lambda e: e.agent_count,
        "fork_count": lambda e: e.fork_count,
    }
    key_fn = sort_key_map.get(sort_by, lambda e: e.avg_pnl)
    rankings.sort(key=key_fn, reverse=True)

    total = len(rankings)

    # Paginate
    page = rankings[offset : offset + limit]

    # Assign ranks
    for i, entry in enumerate(page):
        entry.rank = offset + i + 1

    return StrategyRankingResponse(rankings=page, total=total)
