"""Recharge order repository for database operations"""

import uuid
from datetime import datetime, UTC
from typing import Optional, List
import time

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import (
    RechargeOrderDB,
)


def generate_order_no() -> str:
    """Generate a unique order number: RCH{timestamp}{random}"""
    timestamp = int(time.time() * 1000) % 1000000000  # Last 9 digits of timestamp
    random_suffix = uuid.uuid4().hex[:6].upper()
    return f"RCH{timestamp}{random_suffix}"


class RechargeRepository:
    """Repository for Recharge Order operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Order CRUD
    # =========================================================================

    async def create(
        self,
        user_id: uuid.UUID,
        amount: float,
        bonus_amount: float = 0.0,
        payment_method: str = "manual",
        order_no: Optional[str] = None,
    ) -> RechargeOrderDB:
        """
        Create a new recharge order.

        Args:
            user_id: User ID
            amount: Recharge amount
            bonus_amount: Promotional bonus amount
            payment_method: Payment method (manual, stripe, etc.)
            order_no: Custom order number (auto-generated if not provided)

        Returns:
            Created RechargeOrderDB instance
        """
        order = RechargeOrderDB(
            user_id=user_id,
            order_no=order_no or generate_order_no(),
            amount=amount,
            bonus_amount=bonus_amount,
            payment_method=payment_method,
            status="pending",
        )
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)
        return order

    async def get_by_id(self, order_id: uuid.UUID) -> Optional[RechargeOrderDB]:
        """Get order by ID"""
        result = await self.session.execute(
            select(RechargeOrderDB)
            .options(selectinload(RechargeOrderDB.user))
            .where(RechargeOrderDB.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_no(self, order_no: str) -> Optional[RechargeOrderDB]:
        """Get order by order number"""
        result = await self.session.execute(
            select(RechargeOrderDB)
            .options(selectinload(RechargeOrderDB.user))
            .where(RechargeOrderDB.order_no == order_no)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RechargeOrderDB]:
        """
        Get orders for a user.

        Args:
            user_id: User ID
            status: Filter by status
            limit: Max results
            offset: Pagination offset

        Returns:
            List of RechargeOrderDB instances
        """
        query = select(RechargeOrderDB).where(RechargeOrderDB.user_id == user_id)

        if status:
            query = query.where(RechargeOrderDB.status == status)

        query = query.order_by(desc(RechargeOrderDB.created_at))
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_all(
        self,
        status: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RechargeOrderDB]:
        """
        List all orders with filters.

        Args:
            status: Filter by status
            user_id: Filter by user
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Max results
            offset: Pagination offset

        Returns:
            List of RechargeOrderDB instances
        """
        query = select(RechargeOrderDB).options(selectinload(RechargeOrderDB.user))

        if status:
            query = query.where(RechargeOrderDB.status == status)
        if user_id:
            query = query.where(RechargeOrderDB.user_id == user_id)
        if start_date:
            query = query.where(RechargeOrderDB.created_at >= start_date)
        if end_date:
            query = query.where(RechargeOrderDB.created_at <= end_date)

        query = query.order_by(desc(RechargeOrderDB.created_at))
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        status: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Count orders with filters"""
        query = select(func.count(RechargeOrderDB.id))

        if status:
            query = query.where(RechargeOrderDB.status == status)
        if user_id:
            query = query.where(RechargeOrderDB.user_id == user_id)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update_status(
        self,
        order_id: uuid.UUID,
        status: str,
        note: Optional[str] = None,
    ) -> Optional[RechargeOrderDB]:
        """
        Update order status.

        Args:
            order_id: Order ID
            status: New status (pending, paid, completed, failed, refunded)
            note: Optional note

        Returns:
            Updated RechargeOrderDB or None
        """
        order = await self.get_by_id(order_id)
        if not order:
            return None

        order.status = status

        # Update timestamps based on status
        now = datetime.now(UTC)
        if status == "paid":
            order.paid_at = now
        elif status == "completed":
            order.completed_at = now

        if note:
            order.note = note

        await self.session.flush()
        await self.session.refresh(order)
        return order

    async def mark_paid(
        self,
        order_id: uuid.UUID,
        note: Optional[str] = None,
    ) -> Optional[RechargeOrderDB]:
        """Mark order as paid"""
        return await self.update_status(order_id, "paid", note)

    async def mark_completed(
        self,
        order_id: uuid.UUID,
        note: Optional[str] = None,
    ) -> Optional[RechargeOrderDB]:
        """Mark order as completed"""
        return await self.update_status(order_id, "completed", note)

    async def mark_failed(
        self,
        order_id: uuid.UUID,
        note: Optional[str] = None,
    ) -> Optional[RechargeOrderDB]:
        """Mark order as failed"""
        return await self.update_status(order_id, "failed", note)

    async def mark_refunded(
        self,
        order_id: uuid.UUID,
        note: Optional[str] = None,
    ) -> Optional[RechargeOrderDB]:
        """Mark order as refunded"""
        return await self.update_status(order_id, "refunded", note)

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_total_amount(
        self,
        status: str = "completed",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """Get total recharge amount with filters"""
        query = select(func.sum(RechargeOrderDB.amount)).where(
            RechargeOrderDB.status == status
        )

        if start_date:
            query = query.where(RechargeOrderDB.completed_at >= start_date)
        if end_date:
            query = query.where(RechargeOrderDB.completed_at <= end_date)

        result = await self.session.execute(query)
        return result.scalar() or 0.0

    async def get_user_total(
        self,
        user_id: uuid.UUID,
        status: str = "completed",
    ) -> float:
        """Get total recharge amount for a user"""
        result = await self.session.execute(
            select(func.sum(RechargeOrderDB.amount)).where(
                and_(
                    RechargeOrderDB.user_id == user_id,
                    RechargeOrderDB.status == status,
                )
            )
        )
        return result.scalar() or 0.0
