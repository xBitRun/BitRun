"""Dashboard routes for aggregated statistics"""

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, field_serializer
from sqlalchemy import func, select

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.models import DailyAccountSnapshotDB, DailyAgentSnapshotDB
from ...db.repositories.account import AccountRepository
from ...db.repositories.decision import DecisionRepository
from ...db.repositories.strategy import StrategyRepository
from ...services.redis_service import get_redis_service
from ...services.decision_record_normalizer import normalize_decisions
from ...traders.ccxt_trader import CCXTTrader, EXCHANGE_ID_MAP
from ...traders.base import calculate_unrealized_pnl_percent

# Import shared utility from agents route
from .agents import _fetch_public_prices

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ==================== Response Models ====================


class PositionSummary(BaseModel):
    """Summary of a position (includes detail fields for frontend reuse)"""

    symbol: str
    side: str
    size: float = 0.0
    size_usd: float
    entry_price: float = 0.0
    mark_price: float = 0.0
    leverage: float = 1.0
    unrealized_pnl: float
    unrealized_pnl_percent: float = 0.0
    liquidation_price: Optional[float] = None
    account_name: str
    exchange: str
    account_id: Optional[str] = None
    # Agent fields (for positions from agent_positions table)
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    execution_mode: Optional[str] = None  # "mock" or "live"
    position_id: Optional[str] = None  # id from agent_positions
    opened_at: Optional[str] = None


class AccountBalanceSummary(BaseModel):
    """Summary of a single account's balance and status"""

    account_id: str
    account_name: str
    exchange: str
    status: str  # online / offline / error
    total_equity: float
    available_balance: float
    daily_pnl: float
    daily_pnl_percent: float = 0.0
    open_positions: int = 0


class DashboardStatsResponse(BaseModel):
    """Aggregated dashboard statistics"""

    # Account-level breakdown (new)
    accounts: list[AccountBalanceSummary] = []
    # Aggregated totals
    total_equity: float
    total_available: float  # renamed from available_balance for clarity
    available_balance: float  # kept for backward compatibility
    unrealized_pnl: float
    # Daily P/L
    daily_pnl: float
    daily_pnl_percent: float
    # Weekly P/L (new)
    weekly_pnl: float = 0.0
    weekly_pnl_percent: float = 0.0
    # Monthly P/L (new)
    monthly_pnl: float = 0.0
    monthly_pnl_percent: float = 0.0
    # Strategies
    active_strategies: int
    total_strategies: int
    # Positions
    open_positions: int
    positions: list[PositionSummary]
    # Today's decisions
    today_decisions: int
    today_executed_decisions: int
    # Account breakdown (legacy - kept for backward compatibility)
    accounts_connected: int
    accounts_total: int


class ActivityItem(BaseModel):
    """A single activity item"""

    id: str
    type: str  # decision, trade, strategy_status, system
    timestamp: datetime
    title: str
    description: str
    data: Optional[dict] = None
    status: Optional[str] = None  # success, error, info

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        return dt.isoformat() + ("Z" if dt.tzinfo is None else "")


class ActivityFeedResponse(BaseModel):
    """Activity feed response"""

    items: list[ActivityItem]
    total: int
    has_more: bool


# ==================== Routes ====================


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    bypass_cache: bool = False,
    execution_mode: str = "all",
):
    """
    Get aggregated dashboard statistics.

    Fetches and combines data from:
    - All connected exchange accounts (equity, positions)
    - Strategies (active count, performance)
    - Decisions (today's activity)

    Results are cached for 10 seconds to reduce load while preserving freshness.
    Pass bypass_cache=true to force a fresh fetch.
    """
    mode = execution_mode if execution_mode in {"all", "live", "mock"} else "all"
    cache_user_key = user_id if mode == "all" else f"{user_id}:{mode}"

    # Try to get from cache first (unless bypass requested)
    if not bypass_cache:
        try:
            redis = await get_redis_service()
            cached = await redis.get_cached_dashboard_stats(cache_user_key)
            if cached:
                logger.debug(f"Returning cached dashboard stats for user {user_id}")
                return DashboardStatsResponse(**cached)
        except Exception as e:
            logger.warning(f"Cache lookup failed, fetching fresh data: {e}")

    account_repo = AccountRepository(db)
    strategy_repo = StrategyRepository(db)
    decision_repo = DecisionRepository(db)

    # Fetch user's accounts
    accounts = await account_repo.get_by_user(uuid.UUID(user_id))

    # Fetch user's strategies
    strategies = await strategy_repo.get_by_user(uuid.UUID(user_id))
    # StrategyDB doesn't have status; status is on AgentDB.
    # Optionally scope stats to a specific execution mode.
    if mode == "all":
        active_strategies_count = len(
            [s for s in strategies if any(a.status == "active" for a in s.agents)]
        )
        total_strategies_count = len(strategies)
    else:
        active_strategies_count = len(
            [
                s
                for s in strategies
                if any(
                    a.status == "active" and a.execution_mode == mode for a in s.agents
                )
            ]
        )
        total_strategies_count = len(
            [s for s in strategies if any(a.execution_mode == mode for a in s.agents)]
        )

    # Initialize aggregated values
    total_equity = 0.0
    available_balance = 0.0
    unrealized_pnl = 0.0
    all_positions: list[PositionSummary] = []
    accounts_connected = 0
    account_summaries: list[AccountBalanceSummary] = []

    # Fetch real-time data from all connected accounts in parallel
    connected_accounts = (
        [a for a in accounts if a.is_connected] if mode in {"all", "live"} else []
    )

    async def _fetch_single_account(account: Any) -> Optional[tuple]:
        """Fetch account state for a single account. Returns (account, state) or None.

        Optimisation: check per-account Redis balance cache before hitting the
        exchange API.  The ``/accounts/{id}/balance`` endpoint already populates
        this cache (10 s TTL), so we can often avoid an expensive exchange
        round-trip.
        """
        from ...traders.base import AccountState, Position as TraderPosition

        # --- Try per-account balance cache first ---
        try:
            redis = await get_redis_service()
            cached = await redis.get_cached_account_balance(str(account.id))
            if cached:
                positions = [
                    TraderPosition(
                        symbol=p.get("symbol", ""),
                        side=p.get("side", "long"),
                        size=p.get("size", 0),
                        size_usd=p.get("size_usd", 0),
                        entry_price=p.get("entry_price", 0),
                        mark_price=p.get("mark_price", 0),
                        leverage=int(p.get("leverage", 1)),
                        unrealized_pnl=p.get("unrealized_pnl", 0),
                        unrealized_pnl_percent=p.get("unrealized_pnl_percent", 0),
                        liquidation_price=p.get("liquidation_price"),
                    )
                    for p in cached.get("positions", [])
                ]
                state = AccountState(
                    equity=cached.get("equity", 0),
                    available_balance=cached.get("available_balance", 0),
                    total_margin_used=cached.get("total_margin_used", 0),
                    unrealized_pnl=cached.get("unrealized_pnl", 0),
                    positions=positions,
                )
                logger.debug(f"Dashboard using cached balance for account {account.id}")
                return (account, state)
        except Exception as e:
            logger.debug(f"Cache lookup failed for account {account.id}: {e}")

        # --- Cache miss: fetch from exchange ---
        try:
            credentials = await account_repo.get_decrypted_credentials(
                account.id, uuid.UUID(user_id)
            )
            if not credentials:
                return None

            trader = _create_trader(account.exchange, credentials, account.is_testnet)
            if not trader:
                return None

            try:
                await trader.initialize()
                state = await trader.get_account_state()

                # Write result to per-account cache so subsequent
                # requests (including /accounts/{id}/balance) benefit.
                try:
                    redis = await get_redis_service()
                    await redis.cache_account_balance(
                        str(account.id),
                        {
                            "account_id": str(account.id),
                            "equity": state.equity,
                            "available_balance": state.available_balance,
                            "total_margin_used": state.total_margin_used,
                            "unrealized_pnl": state.unrealized_pnl,
                            "positions": [
                                {
                                    "symbol": p.symbol,
                                    "side": p.side,
                                    "size": p.size,
                                    "size_usd": p.size_usd,
                                    "entry_price": p.entry_price,
                                    "mark_price": p.mark_price,
                                    "leverage": p.leverage,
                                    "unrealized_pnl": p.unrealized_pnl,
                                    "unrealized_pnl_percent": p.unrealized_pnl_percent,
                                    "liquidation_price": p.liquidation_price,
                                }
                                for p in state.positions
                            ],
                        },
                        ttl=10,
                    )
                except Exception:
                    pass  # Non-critical

                return (account, state)
            finally:
                await trader.close()
        except Exception as e:
            logger.warning(f"Failed to fetch account {account.id} state: {e}")
            return None

    results = await asyncio.gather(
        *[_fetch_single_account(a) for a in connected_accounts],
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Account fetch raised exception: {result}")
            continue
        if result is None:
            continue

        account, account_state = result
        total_equity += account_state.equity
        available_balance += account_state.available_balance
        unrealized_pnl += account_state.unrealized_pnl
        accounts_connected += 1

        # Build account summary
        # Calculate daily P/L for this account from Redis or use unrealized as fallback
        account_daily_pnl = 0.0
        account_daily_pnl_percent = 0.0
        try:
            redis = await get_redis_service()
            account_start_equity = await redis.get_today_start_equity(
                f"{user_id}_{account.id}"
            )
            if account_start_equity is not None and account_start_equity > 0:
                account_daily_pnl = account_state.equity - account_start_equity
                account_daily_pnl_percent = (
                    account_daily_pnl / account_start_equity
                ) * 100
            else:
                account_daily_pnl = account_state.unrealized_pnl
                account_daily_pnl_percent = (
                    (account_daily_pnl / account_state.equity * 100)
                    if account_state.equity > 0
                    else 0.0
                )
        except Exception:
            account_daily_pnl = account_state.unrealized_pnl
            account_daily_pnl_percent = (
                (account_daily_pnl / account_state.equity * 100)
                if account_state.equity > 0
                else 0.0
            )

        account_summaries.append(
            AccountBalanceSummary(
                account_id=str(account.id),
                account_name=account.name,
                exchange=account.exchange,
                status="online",
                total_equity=round(account_state.equity, 2),
                available_balance=round(account_state.available_balance, 2),
                daily_pnl=round(account_daily_pnl, 2),
                daily_pnl_percent=round(account_daily_pnl_percent, 2),
                open_positions=len(account_state.positions),
            )
        )

        for pos in account_state.positions:
            all_positions.append(
                PositionSummary(
                    symbol=pos.symbol,
                    side=pos.side,
                    size=pos.size,
                    size_usd=pos.size_usd,
                    entry_price=pos.entry_price,
                    mark_price=pos.mark_price,
                    leverage=float(pos.leverage),
                    unrealized_pnl=pos.unrealized_pnl,
                    unrealized_pnl_percent=pos.unrealized_pnl_percent,
                    liquidation_price=pos.liquidation_price,
                    account_name=account.name,
                    exchange=account.exchange,
                    account_id=str(account.id),
                )
            )

    # Add offline accounts to summaries
    if mode in {"all", "live"}:
        offline_accounts = [a for a in accounts if not a.is_connected]
        for account in offline_accounts:
            account_summaries.append(
                AccountBalanceSummary(
                    account_id=str(account.id),
                    account_name=account.name,
                    exchange=account.exchange,
                    status="offline",
                    total_equity=0.0,
                    available_balance=0.0,
                    daily_pnl=0.0,
                    daily_pnl_percent=0.0,
                    open_positions=0,
                )
            )

    # Calculate daily P/L using cached midnight equity
    daily_pnl = 0.0
    daily_pnl_percent = 0.0

    try:
        redis = await get_redis_service()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Get midnight equity for today
        start_equity = await redis.get_today_start_equity(user_id)

        if start_equity is not None and start_equity > 0:
            # Calculate actual daily P&L
            daily_pnl = total_equity - start_equity
            daily_pnl_percent = (daily_pnl / start_equity) * 100
        else:
            # No midnight snapshot yet - save current equity as baseline
            # This happens on first request of the day or for new users
            if total_equity > 0:
                await redis.set_daily_equity(user_id, today, total_equity)
            # Fall back to unrealized P&L as proxy
            daily_pnl = unrealized_pnl
            daily_pnl_percent = (
                (daily_pnl / total_equity * 100) if total_equity > 0 else 0.0
            )

    except Exception as e:
        # If Redis is unavailable, fall back to unrealized P&L
        logger.warning(f"Redis unavailable for daily P&L calculation: {e}")
        daily_pnl = unrealized_pnl
        daily_pnl_percent = (
            (daily_pnl / total_equity * 100) if total_equity > 0 else 0.0
        )

    # Calculate weekly and monthly P/L from daily snapshots
    weekly_pnl = 0.0
    weekly_pnl_percent = 0.0
    monthly_pnl = 0.0
    monthly_pnl_percent = 0.0

    try:
        today_date = date.today()

        # Get user's account IDs
        user_account_ids = [str(a.id) for a in connected_accounts]
        if user_account_ids:
            # Weekly P/L: from start of week (Monday)
            week_start = today_date - timedelta(days=today_date.weekday())

            # Query weekly snapshots
            weekly_stmt = (
                select(
                    DailyAccountSnapshotDB.account_id,
                    func.sum(DailyAccountSnapshotDB.daily_pnl).label("weekly_pnl"),
                    func.min(
                        DailyAccountSnapshotDB.equity - DailyAccountSnapshotDB.daily_pnl
                    ).label("week_start_equity"),
                )
                .where(
                    DailyAccountSnapshotDB.user_id == uuid.UUID(user_id),
                    DailyAccountSnapshotDB.snapshot_date >= week_start,
                    DailyAccountSnapshotDB.snapshot_date <= today_date,
                )
                .group_by(DailyAccountSnapshotDB.account_id)
            )

            weekly_result = await db.execute(weekly_stmt)
            weekly_rows = weekly_result.all()

            if weekly_rows:
                weekly_pnl = sum(row.weekly_pnl or 0 for row in weekly_rows)
                week_start_equity = sum(
                    row.week_start_equity or 0 for row in weekly_rows
                )
                if week_start_equity > 0:
                    weekly_pnl_percent = (weekly_pnl / week_start_equity) * 100

            # Monthly P/L: from start of month
            month_start = today_date.replace(day=1)

            monthly_stmt = (
                select(
                    DailyAccountSnapshotDB.account_id,
                    func.sum(DailyAccountSnapshotDB.daily_pnl).label("monthly_pnl"),
                    func.min(
                        DailyAccountSnapshotDB.equity - DailyAccountSnapshotDB.daily_pnl
                    ).label("month_start_equity"),
                )
                .where(
                    DailyAccountSnapshotDB.user_id == uuid.UUID(user_id),
                    DailyAccountSnapshotDB.snapshot_date >= month_start,
                    DailyAccountSnapshotDB.snapshot_date <= today_date,
                )
                .group_by(DailyAccountSnapshotDB.account_id)
            )

            monthly_result = await db.execute(monthly_stmt)
            monthly_rows = monthly_result.all()

            if monthly_rows:
                monthly_pnl = sum(row.monthly_pnl or 0 for row in monthly_rows)
                month_start_equity = sum(
                    row.month_start_equity or 0 for row in monthly_rows
                )
                if month_start_equity > 0:
                    monthly_pnl_percent = (monthly_pnl / month_start_equity) * 100

    except Exception as e:
        logger.debug(f"Failed to calculate weekly/monthly P/L: {e}")

    # Fetch Agent positions from agent_positions table
    from ...db.repositories.agent import AgentRepository
    from ...services.agent_position_service import AgentPositionService

    agent_repo = AgentRepository(db)
    user_agents = await agent_repo.get_by_user(uuid.UUID(user_id))
    ps = AgentPositionService(db=db)

    # Collect all open Agent positions
    agent_positions_symbols = set()
    agent_position_records = []  # (agent, position)

    for agent in user_agents:
        if mode != "all" and agent.execution_mode != mode:
            continue
        positions = await ps.get_agent_positions(agent.id, status_filter="open")
        for pos in positions:
            agent_positions_symbols.add(pos.symbol)
            agent_position_records.append((agent, pos))

    # Fetch current prices for Agent positions
    agent_prices: dict[str, float] = {}
    if agent_positions_symbols:
        try:
            agent_prices = await _fetch_public_prices(list(agent_positions_symbols))
        except Exception as e:
            logger.warning(f"Failed to fetch prices for agent positions: {e}")

    # Add Agent positions to all_positions
    mock_agent_unrealized: dict[str, float] = {}
    mock_agent_margin_used: dict[str, float] = {}
    for agent, pos in agent_position_records:
        mark_price = agent_prices.get(pos.symbol, 0.0)
        unrealized_pnl = 0.0
        unrealized_pnl_percent = 0.0

        if mark_price > 0 and pos.entry_price > 0 and pos.size > 0:
            if pos.side == "long":
                unrealized_pnl = (mark_price - pos.entry_price) * pos.size
            else:
                unrealized_pnl = (pos.entry_price - mark_price) * pos.size
            margin_used = pos.size_usd / max(pos.leverage, 1)
            unrealized_pnl_percent = calculate_unrealized_pnl_percent(
                unrealized_pnl,
                margin_used=margin_used,
                size_usd=pos.size_usd,
                leverage=pos.leverage,
            )

        if agent.execution_mode == "mock":
            aid = str(agent.id)
            mock_agent_unrealized[aid] = (
                mock_agent_unrealized.get(aid, 0.0) + unrealized_pnl
            )
            mock_agent_margin_used[aid] = mock_agent_margin_used.get(aid, 0.0) + (
                pos.size_usd / max(float(pos.leverage), 1.0)
            )

        # Determine exchange name for the agent
        exchange_name = (
            "mock"
            if agent.execution_mode == "mock"
            else (agent.account.exchange if agent.account else "unknown")
        )

        all_positions.append(
            PositionSummary(
                symbol=pos.symbol,
                side=pos.side,
                size=pos.size,
                size_usd=pos.size_usd,
                entry_price=pos.entry_price,
                mark_price=mark_price,
                leverage=float(pos.leverage),
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                liquidation_price=None,
                account_name=agent.account.name if agent.account else agent.name,
                exchange=exchange_name,
                account_id=str(agent.account_id) if agent.account_id else None,
                agent_id=str(agent.id),
                agent_name=agent.name,
                execution_mode=agent.execution_mode,
                position_id=str(pos.id),
                opened_at=pos.opened_at.isoformat() if pos.opened_at else None,
            )
        )

    # Mock mode: build dashboard aggregates from mock agents (overall paper view).
    if mode == "mock":
        mock_agents = [a for a in user_agents if a.execution_mode == "mock"]
        mock_agent_ids = [a.id for a in mock_agents]
        daily_by_agent: dict[str, float] = {}
        weekly_pnl = 0.0
        monthly_pnl = 0.0
        weekly_pnl_percent = 0.0
        monthly_pnl_percent = 0.0

        if mock_agent_ids:
            today_date = date.today()
            week_start = today_date - timedelta(days=today_date.weekday())
            month_start = today_date.replace(day=1)
            today_start_dt = datetime.combine(today_date, datetime.min.time()).replace(
                tzinfo=UTC
            )
            tomorrow_start_dt = today_start_dt + timedelta(days=1)

            try:
                today_stmt = select(
                    DailyAgentSnapshotDB.agent_id,
                    DailyAgentSnapshotDB.daily_pnl,
                ).where(
                    DailyAgentSnapshotDB.user_id == uuid.UUID(user_id),
                    DailyAgentSnapshotDB.agent_id.in_(mock_agent_ids),
                    DailyAgentSnapshotDB.snapshot_date >= today_start_dt,
                    DailyAgentSnapshotDB.snapshot_date < tomorrow_start_dt,
                )
                today_rows = (await db.execute(today_stmt)).all()
                daily_by_agent = {
                    str(row.agent_id): row.daily_pnl or 0.0 for row in today_rows
                }
            except Exception as e:
                logger.debug(f"Failed to fetch mock daily pnl snapshots: {e}")

            try:
                weekly_stmt = select(
                    func.sum(DailyAgentSnapshotDB.daily_pnl).label("weekly_pnl"),
                ).where(
                    DailyAgentSnapshotDB.user_id == uuid.UUID(user_id),
                    DailyAgentSnapshotDB.agent_id.in_(mock_agent_ids),
                    DailyAgentSnapshotDB.snapshot_date >= week_start,
                    DailyAgentSnapshotDB.snapshot_date <= today_date,
                )
                weekly_row = (await db.execute(weekly_stmt)).one_or_none()
                if weekly_row:
                    weekly_pnl = float(weekly_row.weekly_pnl or 0.0)

                monthly_stmt = select(
                    func.sum(DailyAgentSnapshotDB.daily_pnl).label("monthly_pnl"),
                ).where(
                    DailyAgentSnapshotDB.user_id == uuid.UUID(user_id),
                    DailyAgentSnapshotDB.agent_id.in_(mock_agent_ids),
                    DailyAgentSnapshotDB.snapshot_date >= month_start,
                    DailyAgentSnapshotDB.snapshot_date <= today_date,
                )
                monthly_row = (await db.execute(monthly_stmt)).one_or_none()
                if monthly_row:
                    monthly_pnl = float(monthly_row.monthly_pnl or 0.0)
            except Exception as e:
                logger.debug(f"Failed to calculate mock weekly/monthly pnl: {e}")

        total_equity = 0.0
        available_balance = 0.0
        unrealized_pnl = 0.0
        accounts_connected = len(mock_agents)
        account_summaries = []

        for agent in mock_agents:
            aid = str(agent.id)
            base_capital = float(agent.mock_initial_balance or 10000.0)
            agent_unrealized = mock_agent_unrealized.get(aid, 0.0)
            agent_margin = mock_agent_margin_used.get(aid, 0.0)
            agent_total_pnl = float(agent.total_pnl or 0.0)
            agent_equity = base_capital + agent_total_pnl + agent_unrealized
            agent_available = max(agent_equity - agent_margin, 0.0)
            agent_daily_pnl = float(daily_by_agent.get(aid, agent_total_pnl))
            agent_start_equity = agent_equity - agent_daily_pnl
            agent_daily_pnl_percent = (
                (agent_daily_pnl / agent_start_equity) * 100 if agent_start_equity > 0 else 0.0
            )

            total_equity += agent_equity
            available_balance += agent_available
            unrealized_pnl += agent_unrealized

            account_summaries.append(
                AccountBalanceSummary(
                    account_id=aid,
                    account_name=agent.name,
                    exchange="mock",
                    status="online" if agent.status == "active" else "offline",
                    total_equity=round(agent_equity, 2),
                    available_balance=round(agent_available, 2),
                    daily_pnl=round(agent_daily_pnl, 2),
                    daily_pnl_percent=round(agent_daily_pnl_percent, 2),
                    open_positions=sum(
                        1
                        for pos_agent, _ in agent_position_records
                        if pos_agent.id == agent.id
                    ),
                )
            )

        daily_pnl = sum(
            daily_by_agent.get(str(a.id), float(a.total_pnl or 0.0))
            for a in mock_agents
        )
        start_equity = total_equity - daily_pnl
        daily_pnl_percent = (daily_pnl / start_equity * 100) if start_equity > 0 else 0.0
        week_start_equity = total_equity - weekly_pnl
        if week_start_equity > 0:
            weekly_pnl_percent = (weekly_pnl / week_start_equity) * 100
        month_start_equity = total_equity - monthly_pnl
        if month_start_equity > 0:
            monthly_pnl_percent = (monthly_pnl / month_start_equity) * 100

    # Get today's decisions
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    recent_decisions = await decision_repo.get_recent(uuid.UUID(user_id), limit=100)
    allowed_agent_ids: set[str] | None = None
    if mode != "all":
        allowed_agent_ids = {
            str(a.id) for s in strategies for a in s.agents if a.execution_mode == mode
        }
    today_decisions = [
        d
        for d in recent_decisions
        if (
            d.timestamp is not None
            and _ensure_utc(d.timestamp) >= today_start
            and (allowed_agent_ids is None or str(d.agent_id) in allowed_agent_ids)
        )
    ]
    today_executed = [d for d in today_decisions if d.executed]

    # Build response
    response = DashboardStatsResponse(
        accounts=account_summaries,
        total_equity=round(total_equity, 2),
        total_available=round(available_balance, 2),
        available_balance=round(available_balance, 2),
        unrealized_pnl=round(unrealized_pnl, 2),
        daily_pnl=round(daily_pnl, 2),
        daily_pnl_percent=round(daily_pnl_percent, 2),
        weekly_pnl=round(weekly_pnl, 2),
        weekly_pnl_percent=round(weekly_pnl_percent, 2),
        monthly_pnl=round(monthly_pnl, 2),
        monthly_pnl_percent=round(monthly_pnl_percent, 2),
        active_strategies=active_strategies_count,
        total_strategies=total_strategies_count,
        open_positions=len(all_positions),
        positions=all_positions,
        today_decisions=len(today_decisions),
        today_executed_decisions=len(today_executed),
        accounts_connected=accounts_connected,
        accounts_total=len(accounts),
    )

    # Cache the response for future requests
    try:
        redis = await get_redis_service()
        await redis.cache_dashboard_stats(
            cache_user_key, response.model_dump(), ttl=10  # Cache for 10 seconds
        )
    except Exception as e:
        logger.debug(f"Failed to cache dashboard stats: {e}")

    return response


@router.get("/activity", response_model=ActivityFeedResponse)
async def get_activity_feed(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    limit: int = 20,
    offset: int = 0,
    execution_mode: str = "all",
):
    """
    Get recent activity feed for the dashboard.

    Combines activities from:
    - AI decisions (all, not just executed)
    - Strategy status changes
    - System notifications

    Returns items sorted by timestamp descending.
    """
    decision_repo = DecisionRepository(db)
    strategy_repo = StrategyRepository(db)

    activities: list[ActivityItem] = []
    mode = execution_mode if execution_mode in {"all", "live", "mock"} else "all"

    # Get recent decisions
    decisions = await decision_repo.get_recent(
        uuid.UUID(user_id), limit=limit + offset + 10
    )

    # Get user's strategies for names and agent execution modes
    # DecisionRecordDB has agent_id (not strategy_id), so we build agent_id -> strategy_name mapping
    strategies = await strategy_repo.get_by_user(uuid.UUID(user_id))
    agent_strategy_names: dict[str, str] = {}
    agent_execution_modes: dict[str, str] = {}
    for s in strategies:
        for a in s.agents:
            agent_strategy_names[str(a.id)] = s.name
            agent_execution_modes[str(a.id)] = a.execution_mode

    for decision in decisions:
        agent_mode = agent_execution_modes.get(str(decision.agent_id), "mock")
        if mode != "all" and agent_mode != mode:
            continue

        normalized_decisions = normalize_decisions(decision.decisions)
        strategy_name = agent_strategy_names.get(
            str(decision.agent_id), "Unknown Strategy"
        )

        # Determine title based on decisions
        main_action = "Analysis"
        if normalized_decisions:
            actions = [d.get("action", "hold") for d in normalized_decisions]
            if "open_long" in actions or "open_short" in actions:
                main_action = "Trade Signal"
            elif "close_long" in actions or "close_short" in actions:
                main_action = "Close Signal"
            elif "hold" in actions or "wait" in actions:
                main_action = "Hold Decision"

        # Build description
        if decision.executed:
            status = "success"
            desc_prefix = "Executed"
        else:
            status = "info"
            desc_prefix = "Analyzed"

        symbols = list(
            set(d.get("symbol", "") for d in normalized_decisions if d.get("symbol"))
        )
        symbol_str = ", ".join(symbols[:3]) if symbols else "Market"

        activities.append(
            ActivityItem(
                id=str(decision.id),
                type="decision",
                timestamp=_ensure_utc(decision.timestamp),
                title=f"{main_action}: {strategy_name}",
                description=f"{desc_prefix} {symbol_str} with {decision.overall_confidence}% confidence",
                data={
                    "agent_id": str(decision.agent_id),
                    "confidence": decision.overall_confidence,
                    "executed": decision.executed,
                    "decisions_count": len(normalized_decisions),
                    "execution_mode": agent_mode,
                },
                status=status,
            )
        )

    # Sort by timestamp descending
    activities.sort(key=lambda x: x.timestamp, reverse=True)

    # Apply pagination
    total = len(activities)
    activities = activities[offset : offset + limit]
    has_more = offset + limit < total

    return ActivityFeedResponse(
        items=activities,
        total=total,
        has_more=has_more,
    )


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (assume UTC if naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _create_trader(exchange: str, credentials: dict, is_testnet: bool):
    """Create a CCXTTrader instance based on exchange type"""
    ccxt_id = EXCHANGE_ID_MAP.get(exchange.lower())
    if not ccxt_id:
        return None
    try:
        return CCXTTrader(
            exchange_id=ccxt_id,
            credentials=credentials,
            testnet=is_testnet,
        )
    except Exception:
        return None
