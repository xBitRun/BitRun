"""Wallet management routes"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.repositories import UserRepository
from ...services.wallet_service import WalletService

router = APIRouter(prefix="/wallets", tags=["Wallets"])


# ==================== Request/Response Models ====================

class WalletResponse(BaseModel):
    """Wallet response"""
    user_id: str
    balance: float
    frozen_balance: float
    total_balance: float
    total_recharged: float
    total_consumed: float


class TransactionResponse(BaseModel):
    """Transaction response"""
    id: str
    type: str
    amount: float
    balance_before: float
    balance_after: float
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    commission_info: Optional[dict] = None
    description: Optional[str] = None
    created_at: datetime


class TransactionSummaryResponse(BaseModel):
    """Transaction summary response"""
    recharge: float = 0.0
    consume: float = 0.0
    refund: float = 0.0
    gift: float = 0.0
    adjustment: float = 0.0


class InviteInfoResponse(BaseModel):
    """Invite info response"""
    invite_code: Optional[str] = None
    referrer_id: Optional[str] = None
    channel_id: Optional[str] = None
    total_invited: int = 0


# ==================== User Wallet Routes ====================

@router.get("/me", response_model=WalletResponse)
async def get_my_wallet(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get current user's wallet."""
    service = WalletService(db)
    wallet = await service.get_wallet(uuid.UUID(user_id))

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )

    return WalletResponse(
        user_id=str(wallet.user_id),
        balance=wallet.balance,
        frozen_balance=wallet.frozen_balance,
        total_balance=wallet.total_balance,
        total_recharged=wallet.total_recharged,
        total_consumed=wallet.total_consumed,
    )


@router.get("/me/transactions", response_model=List[TransactionResponse])
async def get_my_transactions(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    types: Optional[str] = Query(None, description="Comma-separated transaction types"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get current user's transaction history."""
    service = WalletService(db)

    type_list = None
    if types:
        type_list = [t.strip() for t in types.split(",") if t.strip()]

    transactions = await service.get_transactions(
        user_id=uuid.UUID(user_id),
        types=type_list,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return [
        TransactionResponse(
            id=str(t.id),
            type=t.type,
            amount=t.amount,
            balance_before=t.balance_before,
            balance_after=t.balance_after,
            reference_type=t.reference_type,
            reference_id=str(t.reference_id) if t.reference_id else None,
            commission_info=t.commission_info,
            description=t.description,
            created_at=t.created_at,
        )
        for t in transactions
    ]


@router.get("/me/summary", response_model=TransactionSummaryResponse)
async def get_my_transaction_summary(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Get current user's transaction summary by type."""
    service = WalletService(db)
    summary = await service.get_transaction_summary(
        user_id=uuid.UUID(user_id),
        start_date=start_date,
        end_date=end_date,
    )

    return TransactionSummaryResponse(
        recharge=summary.get("recharge", 0.0),
        consume=summary.get("consume", 0.0),
        refund=summary.get("refund", 0.0),
        gift=summary.get("gift", 0.0),
        adjustment=summary.get("adjustment", 0.0),
    )


# ==================== Invite Info ====================

@router.get("/me/invite", response_model=InviteInfoResponse)
async def get_my_invite_info(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get current user's invitation information."""
    from ...services.invite_service import InviteService

    service = InviteService(db)
    info = await service.get_user_invite_info(uuid.UUID(user_id))

    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return InviteInfoResponse(
        invite_code=info.get("invite_code"),
        referrer_id=str(info["referrer_id"]) if info.get("referrer_id") else None,
        channel_id=str(info["channel_id"]) if info.get("channel_id") else None,
        total_invited=info.get("total_invited", 0),
    )


# ==================== Admin Routes ====================

async def require_platform_admin(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Dependency that requires platform admin role"""
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user or user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required"
        )
    return user


class GiftBalanceRequest(BaseModel):
    """Gift balance request"""
    user_id: str = Field(..., description="User ID to gift balance to")
    amount: float = Field(..., gt=0, description="Amount to gift")
    description: str = Field("System gift", max_length=500)


class AdjustBalanceRequest(BaseModel):
    """Adjust balance request"""
    user_id: str = Field(..., description="User ID to adjust")
    amount: float = Field(..., description="Amount to adjust (positive or negative)")
    description: str = Field(..., min_length=1, max_length=500)


@router.post("/gift", response_model=TransactionResponse)
async def gift_balance(
    request: GiftBalanceRequest,
    db: DbSessionDep,
    admin_user = Depends(require_platform_admin),
):
    """Gift balance to user (platform admin only)."""
    service = WalletService(db)
    transaction, error = await service.gift_balance(
        user_id=uuid.UUID(request.user_id),
        amount=request.amount,
        description=request.description,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    await db.commit()

    return TransactionResponse(
        id=str(transaction.id),
        type=transaction.type,
        amount=transaction.amount,
        balance_before=transaction.balance_before,
        balance_after=transaction.balance_after,
        reference_type=transaction.reference_type,
        reference_id=str(transaction.reference_id) if transaction.reference_id else None,
        commission_info=transaction.commission_info,
        description=transaction.description,
        created_at=transaction.created_at,
    )


@router.post("/adjust", response_model=TransactionResponse)
async def adjust_balance(
    request: AdjustBalanceRequest,
    db: DbSessionDep,
    admin_user = Depends(require_platform_admin),
):
    """Adjust user balance (platform admin only)."""
    service = WalletService(db)

    # For negative adjustments, check balance
    if request.amount < 0:
        balance = await service.get_balance(uuid.UUID(request.user_id))
        if balance < abs(request.amount):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance for adjustment. Current: {balance}"
            )

    # Use gift_balance for positive, refund for negative
    if request.amount >= 0:
        transaction, error = await service.gift_balance(
            user_id=uuid.UUID(request.user_id),
            amount=request.amount,
            description=request.description,
        )
    else:
        transaction, error = await service.refund(
            user_id=uuid.UUID(request.user_id),
            amount=abs(request.amount),
            reference_type="admin_adjustment",
            reference_id=uuid.uuid4(),
            description=request.description,
        )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    await db.commit()

    return TransactionResponse(
        id=str(transaction.id),
        type=transaction.type,
        amount=transaction.amount,
        balance_before=transaction.balance_before,
        balance_after=transaction.balance_after,
        reference_type=transaction.reference_type,
        reference_id=str(transaction.reference_id) if transaction.reference_id else None,
        commission_info=transaction.commission_info,
        description=transaction.description,
        created_at=transaction.created_at,
    )
