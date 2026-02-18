"""Recharge order management routes"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.repositories import UserRepository
from ...services.wallet_service import WalletService

router = APIRouter(prefix="/recharge", tags=["Recharge"])


# ==================== Request/Response Models ====================

class RechargeOrderCreate(BaseModel):
    """Recharge order creation request"""
    amount: float = Field(..., gt=0, description="Recharge amount")
    bonus_amount: float = Field(0.0, ge=0, description="Promotional bonus amount")


class RechargeOrderConfirm(BaseModel):
    """Recharge order confirmation request (admin)"""
    note: Optional[str] = Field(None, max_length=500, description="Admin note")


class RechargeOrderResponse(BaseModel):
    """Recharge order response"""
    id: str
    user_id: str
    order_no: str
    amount: float
    bonus_amount: float
    total_amount: float
    payment_method: str
    status: str
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RechargeOrderListResponse(BaseModel):
    """Recharge order list response with user info"""
    id: str
    user_id: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    order_no: str
    amount: float
    bonus_amount: float
    total_amount: float
    payment_method: str
    status: str
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ==================== User Routes ====================

@router.post("/orders", response_model=RechargeOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_recharge_order(
    request: RechargeOrderCreate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Create a recharge order.

    After creating, user should make payment via the specified method.
    For manual payment, contact admin to confirm.
    """
    service = WalletService(db)
    order = await service.create_recharge_order(
        user_id=uuid.UUID(user_id),
        amount=request.amount,
        bonus_amount=request.bonus_amount,
    )

    await db.commit()

    return RechargeOrderResponse(
        id=str(order.id),
        user_id=str(order.user_id),
        order_no=order.order_no,
        amount=order.amount,
        bonus_amount=order.bonus_amount,
        total_amount=order.total_amount,
        payment_method=order.payment_method,
        status=order.status,
        paid_at=order.paid_at,
        completed_at=order.completed_at,
        note=order.note,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("/orders", response_model=List[RechargeOrderResponse])
async def list_my_orders(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get current user's recharge orders."""
    from ...db.repositories import RechargeRepository

    repo = RechargeRepository(db)
    orders = await repo.get_by_user(
        user_id=uuid.UUID(user_id),
        status=status,
        limit=limit,
        offset=offset,
    )

    return [
        RechargeOrderResponse(
            id=str(o.id),
            user_id=str(o.user_id),
            order_no=o.order_no,
            amount=o.amount,
            bonus_amount=o.bonus_amount,
            total_amount=o.total_amount,
            payment_method=o.payment_method,
            status=o.status,
            paid_at=o.paid_at,
            completed_at=o.completed_at,
            note=o.note,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in orders
    ]


@router.get("/orders/{order_id}", response_model=RechargeOrderResponse)
async def get_my_order(
    order_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get a specific recharge order."""
    from ...db.repositories import RechargeRepository

    repo = RechargeRepository(db)
    order = await repo.get_by_id(uuid.UUID(order_id))

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Ensure user owns this order
    if str(order.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this order"
        )

    return RechargeOrderResponse(
        id=str(order.id),
        user_id=str(order.user_id),
        order_no=order.order_no,
        amount=order.amount,
        bonus_amount=order.bonus_amount,
        total_amount=order.total_amount,
        payment_method=order.payment_method,
        status=order.status,
        paid_at=order.paid_at,
        completed_at=order.completed_at,
        note=order.note,
        created_at=order.created_at,
        updated_at=order.updated_at,
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


PlatformAdminDep = Depends(require_platform_admin)


@router.get("/admin/orders", response_model=List[RechargeOrderListResponse])
async def admin_list_orders(
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all recharge orders (platform admin only)."""
    from ...db.repositories import RechargeRepository

    repo = RechargeRepository(db)

    uid = uuid.UUID(user_id) if user_id else None
    orders = await repo.list_all(
        status=status,
        user_id=uid,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return [
        RechargeOrderListResponse(
            id=str(o.id),
            user_id=str(o.user_id),
            user_email=o.user.email if o.user else None,
            user_name=o.user.name if o.user else None,
            order_no=o.order_no,
            amount=o.amount,
            bonus_amount=o.bonus_amount,
            total_amount=o.total_amount,
            payment_method=o.payment_method,
            status=o.status,
            paid_at=o.paid_at,
            completed_at=o.completed_at,
            note=o.note,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in orders
    ]


@router.post("/admin/orders/{order_id}/mark-paid", response_model=RechargeOrderResponse)
async def admin_mark_order_paid(
    order_id: str,
    request: RechargeOrderConfirm,
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
):
    """Mark order as paid (platform admin only)."""
    from ...db.repositories import RechargeRepository

    repo = RechargeRepository(db)
    order = await repo.mark_paid(uuid.UUID(order_id), request.note)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    await db.commit()

    return RechargeOrderResponse(
        id=str(order.id),
        user_id=str(order.user_id),
        order_no=order.order_no,
        amount=order.amount,
        bonus_amount=order.bonus_amount,
        total_amount=order.total_amount,
        payment_method=order.payment_method,
        status=order.status,
        paid_at=order.paid_at,
        completed_at=order.completed_at,
        note=order.note,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("/admin/orders/{order_id}/confirm", response_model=RechargeOrderResponse)
async def admin_confirm_order(
    order_id: str,
    request: RechargeOrderConfirm,
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
):
    """
    Confirm recharge order and credit balance (platform admin only).

    This will:
    1. Mark order as paid
    2. Credit user wallet with amount + bonus
    3. Mark order as completed
    """
    from ...db.repositories import RechargeRepository

    repo = RechargeRepository(db)
    service = WalletService(db)

    # First mark as paid
    order = await repo.mark_paid(uuid.UUID(order_id), request.note)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Process recharge (credit balance)
    wallet, error = await service.process_recharge(order.id, admin_user.id)
    if error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    await db.commit()

    # Refresh order
    order = await repo.get_by_id(uuid.UUID(order_id))

    return RechargeOrderResponse(
        id=str(order.id),
        user_id=str(order.user_id),
        order_no=order.order_no,
        amount=order.amount,
        bonus_amount=order.bonus_amount,
        total_amount=order.total_amount,
        payment_method=order.payment_method,
        status=order.status,
        paid_at=order.paid_at,
        completed_at=order.completed_at,
        note=order.note,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("/admin/orders/{order_id}/cancel")
async def admin_cancel_order(
    order_id: str,
    request: RechargeOrderConfirm,
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
):
    """Cancel a pending order (platform admin only)."""
    from ...db.repositories import RechargeRepository

    repo = RechargeRepository(db)
    order = await repo.get_by_id(uuid.UUID(order_id))

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status not in ("pending", "paid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status '{order.status}'"
        )

    order = await repo.mark_failed(uuid.UUID(order_id), request.note or "Cancelled by admin")

    await db.commit()

    return {"message": "Order cancelled", "order_id": str(order.id)}
