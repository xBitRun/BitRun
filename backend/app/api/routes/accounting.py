"""Accounting and statistics routes"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ...core.dependencies import CurrentUserDep, DbSessionDep, PlatformAdminDep, ChannelAdminDep
from ...services.channel_service import ChannelService
from ...services.wallet_service import WalletService

router = APIRouter(prefix="/accounting", tags=["Accounting"])


# ==================== Response Models ====================

class UserAccountingOverview(BaseModel):
    """User accounting overview"""
    balance: float
    frozen_balance: float
    total_balance: float
    total_recharged: float
    total_consumed: float
    period_recharged: float = 0.0
    period_consumed: float = 0.0


class ChannelAccountingOverview(BaseModel):
    """Channel accounting overview"""
    channel_id: str
    channel_name: str
    channel_code: str
    commission_rate: float
    total_users: int
    total_revenue: float
    total_commission: float
    available_balance: float
    pending_commission: float
    period_commission: float = 0.0
    active_users: int = 0


class PlatformAccountingOverview(BaseModel):
    """Platform accounting overview"""
    total_channels: int
    active_channels: int
    total_users: int
    total_revenue: float
    total_commission: float
    platform_revenue: float


# ==================== User Accounting ====================

@router.get("/overview", response_model=UserAccountingOverview)
async def get_user_accounting_overview(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Get current user's accounting overview.

    Includes balance, totals, and period-specific metrics.
    """
    service = WalletService(db)
    wallet = await service.get_wallet(uuid.UUID(user_id))

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    # Get period summary
    summary = await service.get_transaction_summary(
        user_id=uuid.UUID(user_id),
        start_date=start_date,
        end_date=end_date,
    )

    return UserAccountingOverview(
        balance=wallet.balance,
        frozen_balance=wallet.frozen_balance,
        total_balance=wallet.total_balance,
        total_recharged=wallet.total_recharged,
        total_consumed=wallet.total_consumed,
        period_recharged=summary.get("recharge", 0.0),
        period_consumed=summary.get("consume", 0.0),
    )


# ==================== Channel Accounting ====================


@router.get("/channels/{channel_id}/overview", response_model=ChannelAccountingOverview)
async def get_channel_accounting_overview(
    channel_id: str,
    db: DbSessionDep,
    admin_user = ChannelAdminDep,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Get channel accounting overview.

    Includes users, revenue, commission, and period metrics.
    """
    service = ChannelService(db)
    channel = await service.get_channel(uuid.UUID(channel_id))

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    stats = await service.get_channel_statistics(
        channel.id,
        start_date=start_date,
        end_date=end_date,
    )

    wallet = await service.get_channel_wallet(channel.id)

    return ChannelAccountingOverview(
        channel_id=str(channel.id),
        channel_name=channel.name,
        channel_code=channel.code,
        commission_rate=channel.commission_rate,
        total_users=stats.get("total_users", 0),
        total_revenue=channel.total_revenue,
        total_commission=channel.total_commission,
        available_balance=wallet.balance if wallet else 0.0,
        pending_commission=stats.get("pending_commission", 0.0),
        period_commission=stats.get("period_commission", 0.0),
        active_users=stats.get("active_users", 0),
    )


@router.get("/channels/me/overview", response_model=ChannelAccountingOverview)
async def get_my_channel_accounting_overview(
    db: DbSessionDep,
    user = ChannelAdminDep,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Get current channel admin's channel accounting overview.
    """
    service = ChannelService(db)
    channel = await service.get_channel_by_admin(user.id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not an admin of any channel"
        )

    stats = await service.get_channel_statistics(
        channel.id,
        start_date=start_date,
        end_date=end_date,
    )

    wallet = await service.get_channel_wallet(channel.id)

    return ChannelAccountingOverview(
        channel_id=str(channel.id),
        channel_name=channel.name,
        channel_code=channel.code,
        commission_rate=channel.commission_rate,
        total_users=stats.get("total_users", 0),
        total_revenue=channel.total_revenue,
        total_commission=channel.total_commission,
        available_balance=wallet.balance if wallet else 0.0,
        pending_commission=stats.get("pending_commission", 0.0),
        period_commission=stats.get("period_commission", 0.0),
        active_users=stats.get("active_users", 0),
    )


# ==================== Platform Accounting ====================


@router.get("/platform/overview", response_model=PlatformAccountingOverview)
async def get_platform_accounting_overview(
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
):
    """
    Get platform-wide accounting overview (platform admin only).

    Includes total channels, users, revenue, and commission.
    """
    service = ChannelService(db)
    stats = await service.get_platform_statistics()

    return PlatformAccountingOverview(
        total_channels=stats.get("total_channels", 0),
        active_channels=stats.get("active_channels", 0),
        total_users=stats.get("total_users", 0),
        total_revenue=stats.get("total_revenue", 0.0),
        total_commission=stats.get("total_commission", 0.0),
        platform_revenue=stats.get("platform_revenue", 0.0),
    )


@router.get("/platform/daily", response_model=list)
async def get_platform_daily_stats(
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
    days: int = Query(30, ge=1, le=90, description="Number of days to include"),
):
    """
    Get platform daily statistics (platform admin only).

    Returns daily breakdown of recharges, consumption, and commission.
    """
    from sqlalchemy import select, func, and_, case
    from ...db.models import WalletTransactionDB, ChannelTransactionDB

    end_date = datetime.now(UTC).replace(hour=23, minute=59, second=59)
    start_date = (end_date - timedelta(days=days)).replace(hour=0, minute=0, second=0)

    # Daily user recharges
    recharge_query = select(
        func.date(WalletTransactionDB.created_at).label("date"),
        func.sum(WalletTransactionDB.amount).label("recharge_amount"),
    ).where(
        and_(
            WalletTransactionDB.type == "recharge",
            WalletTransactionDB.created_at >= start_date,
        )
    ).group_by(func.date(WalletTransactionDB.created_at))

    result = await db.execute(recharge_query)
    recharges = {str(r.date): r.recharge_amount for r in result.all()}

    # Daily consumption
    consume_query = select(
        func.date(WalletTransactionDB.created_at).label("date"),
        func.sum(WalletTransactionDB.amount).label("consume_amount"),
    ).where(
        and_(
            WalletTransactionDB.type == "consume",
            WalletTransactionDB.created_at >= start_date,
        )
    ).group_by(func.date(WalletTransactionDB.created_at))

    result = await db.execute(consume_query)
    consumes = {str(r.date): r.consume_amount for r in result.all()}

    # Daily commission
    commission_query = select(
        func.date(ChannelTransactionDB.created_at).label("date"),
        func.sum(ChannelTransactionDB.amount).label("commission_amount"),
    ).where(
        and_(
            ChannelTransactionDB.type == "commission",
            ChannelTransactionDB.created_at >= start_date,
        )
    ).group_by(func.date(ChannelTransactionDB.created_at))

    result = await db.execute(commission_query)
    commissions = {str(r.date): r.commission_amount for r in result.all()}

    # Combine all dates
    all_dates = set(recharges.keys()) | set(consumes.keys()) | set(commissions.keys())

    daily_stats = []
    for date in sorted(all_dates):
        daily_stats.append({
            "date": date,
            "recharge_amount": recharges.get(date, 0.0),
            "consume_amount": consumes.get(date, 0.0),
            "commission_amount": commissions.get(date, 0.0),
        })

    return daily_stats
