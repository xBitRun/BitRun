"""Dashboard routes for aggregated statistics"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_serializer

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.repositories.account import AccountRepository
from ...db.repositories.decision import DecisionRepository
from ...db.repositories.strategy import StrategyRepository
from ...services.redis_service import get_redis_service
from ...traders import TradeError
from ...traders.ccxt_trader import CCXTTrader, EXCHANGE_ID_MAP

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


class DashboardStatsResponse(BaseModel):
    """Aggregated dashboard statistics"""
    total_equity: float
    available_balance: float
    unrealized_pnl: float
    daily_pnl: float
    daily_pnl_percent: float
    active_strategies: int
    total_strategies: int
    open_positions: int
    positions: list[PositionSummary]
    today_decisions: int
    today_executed_decisions: int
    # Account breakdown
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
):
    """
    Get aggregated dashboard statistics.

    Fetches and combines data from:
    - All connected exchange accounts (equity, positions)
    - Strategies (active count, performance)
    - Decisions (today's activity)

    Results are cached for 30 seconds to reduce load.
    Pass bypass_cache=true to force a fresh fetch.
    """
    # Try to get from cache first (unless bypass requested)
    if not bypass_cache:
        try:
            redis = await get_redis_service()
            cached = await redis.get_cached_dashboard_stats(user_id)
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
    active_strategies = [s for s in strategies if s.status == "active"]

    # Initialize aggregated values
    total_equity = 0.0
    available_balance = 0.0
    unrealized_pnl = 0.0
    all_positions: list[PositionSummary] = []
    accounts_connected = 0

    # Fetch real-time data from all connected accounts in parallel
    connected_accounts = [a for a in accounts if a.is_connected]

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

        for pos in account_state.positions:
            all_positions.append(PositionSummary(
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
            ))

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
            daily_pnl_percent = (daily_pnl / total_equity * 100) if total_equity > 0 else 0.0

    except Exception as e:
        # If Redis is unavailable, fall back to unrealized P&L
        logger.warning(f"Redis unavailable for daily P&L calculation: {e}")
        daily_pnl = unrealized_pnl
        daily_pnl_percent = (daily_pnl / total_equity * 100) if total_equity > 0 else 0.0

    # Get today's decisions
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    recent_decisions = await decision_repo.get_recent(uuid.UUID(user_id), limit=100)
    today_decisions = [
        d for d in recent_decisions
        if d.timestamp is not None and _ensure_utc(d.timestamp) >= today_start
    ]
    today_executed = [d for d in today_decisions if d.executed]

    # Build response
    response = DashboardStatsResponse(
        total_equity=round(total_equity, 2),
        available_balance=round(available_balance, 2),
        unrealized_pnl=round(unrealized_pnl, 2),
        daily_pnl=round(daily_pnl, 2),
        daily_pnl_percent=round(daily_pnl_percent, 2),
        active_strategies=len(active_strategies),
        total_strategies=len(strategies),
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
            user_id,
            response.model_dump(),
            ttl=30  # Cache for 30 seconds
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

    # Get recent decisions
    decisions = await decision_repo.get_recent(uuid.UUID(user_id), limit=limit + offset + 10)

    # Get user's strategies for names
    strategies = await strategy_repo.get_by_user(uuid.UUID(user_id))
    strategy_names = {str(s.id): s.name for s in strategies}

    for decision in decisions:
        strategy_name = strategy_names.get(str(decision.strategy_id), "Unknown Strategy")

        # Determine title based on decisions
        main_action = "Analysis"
        if decision.decisions:
            actions = [d.get("action", "hold") for d in decision.decisions]
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

        symbols = list(set(d.get("symbol", "") for d in decision.decisions if d.get("symbol")))
        symbol_str = ", ".join(symbols[:3]) if symbols else "Market"

        activities.append(ActivityItem(
            id=str(decision.id),
            type="decision",
            timestamp=_ensure_utc(decision.timestamp),
            title=f"{main_action}: {strategy_name}",
            description=f"{desc_prefix} {symbol_str} with {decision.overall_confidence}% confidence",
            data={
                "strategy_id": str(decision.strategy_id),
                "confidence": decision.overall_confidence,
                "executed": decision.executed,
                "decisions_count": len(decision.decisions),
            },
            status=status,
        ))

    # Sort by timestamp descending
    activities.sort(key=lambda x: x.timestamp, reverse=True)

    # Apply pagination
    total = len(activities)
    activities = activities[offset:offset + limit]
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
