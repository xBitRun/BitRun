"""Analytics routes for P&L and performance analysis."""

import logging
import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.repositories.account import AccountRepository
from ...services.pnl_service import PnLService
from ...traders.base import TradeError
from ...traders import create_trader_from_account
from ...utils.error_handling import exchange_api_error, exchange_connection_error, sanitize_error_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ==================== Response Models ====================

class TradeRecord(BaseModel):
    """A single trade record with P&L"""
    id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    size: float
    size_usd: float
    leverage: int
    realized_pnl: float
    fees: float
    opened_at: str
    closed_at: str
    duration_minutes: int
    exit_reason: Optional[str]


class AgentPnLSummary(BaseModel):
    """P&L summary for an agent"""
    total_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_fees: float


class AgentPnLResponse(BaseModel):
    """Agent P&L detail response"""
    agent_id: str
    agent_name: str
    summary: AgentPnLSummary
    trades: list[TradeRecord]
    total: int
    limit: int
    offset: int


class AgentPerformance(BaseModel):
    """Performance metrics for an agent"""
    agent_id: str
    agent_name: str
    strategy_name: str
    strategy_type: str
    status: str
    total_pnl: float
    daily_pnl: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    max_drawdown: float
    open_positions: int


class AccountAgentsResponse(BaseModel):
    """Agents performance for an account"""
    account_id: str
    agents: list[AgentPerformance]
    total: int


class AccountPnLSummary(BaseModel):
    """P&L summary for an account"""
    account_id: str
    account_name: str
    exchange: str
    current_equity: float
    total_pnl: float
    total_pnl_percent: float
    daily_pnl: float
    daily_pnl_percent: float
    weekly_pnl: float
    weekly_pnl_percent: float
    monthly_pnl: float
    monthly_pnl_percent: float
    win_rate: float
    total_trades: int
    profit_factor: float
    max_drawdown_percent: Optional[float]
    sharpe_ratio: Optional[float]


class EquityDataPoint(BaseModel):
    """Single data point in equity curve"""
    date: str
    equity: float
    daily_pnl: float
    daily_pnl_percent: float
    cumulative_pnl: float
    cumulative_pnl_percent: float


class EquityCurveResponse(BaseModel):
    """Equity curve response"""
    account_id: str
    start_date: str
    end_date: str
    granularity: str
    data_points: list[EquityDataPoint]


# ==================== Routes ====================

@router.get("/agents/{agent_id}/pnl", response_model=AgentPnLResponse)
async def get_agent_pnl(
    agent_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    limit: int = Query(20, ge=1, le=100, description="Number of trades"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    Get P&L details for a specific agent.

    Returns summary metrics and trade history.
    """
    pnl_service = PnLService(db)
    agent_uuid = uuid.UUID(agent_id)

    # Get summary
    summary = await pnl_service.get_agent_pnl_summary(
        agent_id=agent_uuid,
        start_date=start_date,
        end_date=end_date,
    )

    # Get trade history
    trades, total = await pnl_service.get_agent_trade_history(
        agent_id=agent_uuid,
        limit=limit,
        offset=offset,
    )

    # Get agent name
    from sqlalchemy import select
    from ...db.models import AgentDB
    stmt = select(AgentDB).where(AgentDB.id == agent_uuid)
    result = await db.execute(stmt)
    agent = result.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Transform trades to response format
    trade_records = [
        TradeRecord(
            id=str(t.id),
            symbol=t.symbol,
            side=t.side,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            size=t.size,
            size_usd=t.size_usd,
            leverage=t.leverage,
            realized_pnl=t.realized_pnl,
            fees=t.fees,
            opened_at=t.opened_at.isoformat() if t.opened_at else "",
            closed_at=t.closed_at.isoformat() if t.closed_at else "",
            duration_minutes=t.duration_minutes,
            exit_reason=t.exit_reason,
        )
        for t in trades
    ]

    return AgentPnLResponse(
        agent_id=agent_id,
        agent_name=agent.name,
        summary=AgentPnLSummary(**summary),
        trades=trade_records,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/accounts/{account_id}/agents", response_model=AccountAgentsResponse)
async def get_account_agents_performance(
    account_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Get performance metrics for all agents on an account.
    """
    pnl_service = PnLService(db)
    account_uuid = uuid.UUID(account_id)

    performances = await pnl_service.get_account_agents_performance(account_uuid)

    return AccountAgentsResponse(
        account_id=account_id,
        agents=[AgentPerformance(**p) for p in performances],
        total=len(performances),
    )


@router.get("/accounts/{account_id}/equity-curve", response_model=EquityCurveResponse)
async def get_account_equity_curve(
    account_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    granularity: str = Query("day", regex="^(day|week|month)$", description="Data granularity"),
):
    """
    Get equity curve data for an account.

    Supports daily, weekly, or monthly granularity.
    """
    pnl_service = PnLService(db)
    account_uuid = uuid.UUID(account_id)

    # Default to last 30 days if not specified
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    data_points = await pnl_service.get_account_equity_curve(
        account_id=account_uuid,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )

    return EquityCurveResponse(
        account_id=account_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        granularity=granularity,
        data_points=[EquityDataPoint(**dp) for dp in data_points],
    )


@router.get("/accounts/{account_id}/pnl", response_model=AccountPnLSummary)
async def get_account_pnl(
    account_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Get P&L summary for an account.

    Returns overall P&L metrics and period-based returns.
    """
    from sqlalchemy import select
    from ...db.models import ExchangeAccountDB

    pnl_service = PnLService(db)
    account_uuid = uuid.UUID(account_id)

    # Get account info
    stmt = select(ExchangeAccountDB).where(ExchangeAccountDB.id == account_uuid)
    result = await db.execute(stmt)
    account = result.scalars().first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )

    # Get P&L for different periods
    all_pnl = await pnl_service.get_account_pnl_summary(account_uuid, "all")
    daily_pnl = await pnl_service.get_account_pnl_summary(account_uuid, "day")
    weekly_pnl = await pnl_service.get_account_pnl_summary(account_uuid, "week")
    monthly_pnl = await pnl_service.get_account_pnl_summary(account_uuid, "month")

    # Calculate percentages (would need initial equity for accurate calculation)
    # For now, use placeholder values
    current_equity = 0.0  # Would need to fetch from exchange

    return AccountPnLSummary(
        account_id=account_id,
        account_name=account.name,
        exchange=account.exchange,
        current_equity=current_equity,
        total_pnl=all_pnl["total_pnl"],
        total_pnl_percent=0.0,  # Would need initial equity
        daily_pnl=daily_pnl["total_pnl"],
        daily_pnl_percent=0.0,
        weekly_pnl=weekly_pnl["total_pnl"],
        weekly_pnl_percent=0.0,
        monthly_pnl=monthly_pnl["total_pnl"],
        monthly_pnl_percent=0.0,
        win_rate=all_pnl["win_rate"],
        total_trades=all_pnl["total_trades"],
        profit_factor=all_pnl["profit_factor"],
        max_drawdown_percent=None,
        sharpe_ratio=None,
    )


class SyncSnapshotResponse(BaseModel):
    """Response for sync snapshot operation"""
    success: bool
    message: str
    equity: Optional[float] = None
    daily_pnl: Optional[float] = None


@router.post("/accounts/{account_id}/sync", response_model=SyncSnapshotResponse)
async def sync_account_snapshot(
    account_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Sync account snapshot with real-time data from exchange.

    Fetches current balance from the exchange and creates/updates
    today's snapshot for immediate P&L visibility.
    """
    account_uuid = uuid.UUID(account_id)
    user_uuid = uuid.UUID(user_id)

    repo = AccountRepository(db)

    # Get account info
    account = await repo.get_by_id(account_uuid, user_uuid)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found"
        )

    if not account.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is not connected. Please test connection first."
        )

    # Get decrypted credentials
    credentials = await repo.get_decrypted_credentials(account_uuid, user_uuid)
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt account credentials"
        )

    trader = None
    try:
        # Create trader instance
        trader = create_trader_from_account(account, credentials)
        await trader.initialize()

        # Get real-time account state
        account_state = await trader.get_account_state()

        # Build position summary for snapshot
        position_summary = [
            {
                "symbol": pos.symbol,
                "side": pos.side,
                "size": pos.size,
                "unrealized_pnl": pos.unrealized_pnl,
            }
            for pos in account_state.positions
        ]

        # Create snapshot
        pnl_service = PnLService(db)
        snapshot = await pnl_service.create_account_snapshot(
            account_id=account_uuid,
            equity=account_state.equity,
            available_balance=account_state.available_balance,
            unrealized_pnl=account_state.unrealized_pnl,
            margin_used=account_state.total_margin_used,
            open_positions=len(account_state.positions),
            position_summary=position_summary,
            source="manual",
        )

        await db.commit()

        return SyncSnapshotResponse(
            success=True,
            message=f"Snapshot synced successfully for {account.exchange}",
            equity=account_state.equity,
            daily_pnl=snapshot.daily_pnl,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except TradeError as e:
        logger.warning(f"Exchange error syncing snapshot for account {account_id}: {e.message}")
        raise exchange_api_error(e, operation="sync snapshot")

    except Exception as e:
        logger.error(f"Unexpected error syncing snapshot for account {account_id}: {e}", exc_info=True)
        raise exchange_connection_error(e, exchange=account.exchange)

    finally:
        if trader:
            try:
                await trader.close()
            except Exception:
                pass
