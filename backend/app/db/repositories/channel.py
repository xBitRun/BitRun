"""Channel repository for database operations"""

import uuid
from datetime import datetime, UTC
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import (
    ChannelDB,
    ChannelWalletDB,
    UserDB,
)


class ChannelRepository:
    """Repository for Channel CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Channel CRUD
    # =========================================================================

    async def create(
        self,
        name: str,
        code: str,
        commission_rate: float = 0.0,
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> ChannelDB:
        """
        Create a new channel.

        Args:
            name: Channel display name
            code: Unique channel code (used for invite codes)
            commission_rate: Commission rate (0.0-1.0)
            contact_name: Contact person name
            contact_email: Contact email
            contact_phone: Contact phone
            admin_user_id: User ID of channel admin

        Returns:
            Created ChannelDB instance
        """
        channel = ChannelDB(
            name=name,
            code=code.upper(),
            commission_rate=commission_rate,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            admin_user_id=admin_user_id,
        )
        self.session.add(channel)
        await self.session.flush()
        await self.session.refresh(channel)
        return channel

    async def get_by_id(self, channel_id: uuid.UUID) -> Optional[ChannelDB]:
        """Get channel by ID"""
        result = await self.session.execute(
            select(ChannelDB)
            .options(selectinload(ChannelDB.wallet))
            .where(ChannelDB.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[ChannelDB]:
        """Get channel by code (case-insensitive)"""
        result = await self.session.execute(
            select(ChannelDB)
            .options(selectinload(ChannelDB.wallet))
            .where(func.upper(ChannelDB.code) == code.upper())
        )
        return result.scalar_one_or_none()

    async def get_by_admin_user(self, user_id: uuid.UUID) -> Optional[ChannelDB]:
        """Get channel by admin user ID"""
        result = await self.session.execute(
            select(ChannelDB)
            .options(selectinload(ChannelDB.wallet))
            .where(ChannelDB.admin_user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ChannelDB]:
        """
        List all channels with optional filtering.

        Args:
            status: Filter by status (active, suspended, closed)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of ChannelDB instances
        """
        query = select(ChannelDB).options(selectinload(ChannelDB.wallet))

        if status:
            query = query.where(ChannelDB.status == status)

        query = query.order_by(ChannelDB.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, status: Optional[str] = None) -> int:
        """Count channels with optional status filter"""
        query = select(func.count(ChannelDB.id))
        if status:
            query = query.where(ChannelDB.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update(
        self,
        channel_id: uuid.UUID,
        **kwargs
    ) -> Optional[ChannelDB]:
        """
        Update channel fields.

        Supported fields: name, commission_rate, status, contact_name,
                          contact_email, contact_phone, admin_user_id
        """
        channel = await self.get_by_id(channel_id)
        if not channel:
            return None

        allowed_fields = {
            "name", "commission_rate", "status",
            "contact_name", "contact_email", "contact_phone",
            "admin_user_id"
        }
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(channel, key, value)

        await self.session.flush()
        await self.session.refresh(channel)
        return channel

    async def update_status(
        self,
        channel_id: uuid.UUID,
        status: str
    ) -> Optional[ChannelDB]:
        """Update channel status (active, suspended, closed)"""
        return await self.update(channel_id, status=status)

    async def increment_users(self, channel_id: uuid.UUID, count: int = 1) -> bool:
        """Increment total_users counter"""
        channel = await self.get_by_id(channel_id)
        if not channel:
            return False
        channel.total_users += count
        await self.session.flush()
        return True

    async def update_revenue(
        self,
        channel_id: uuid.UUID,
        revenue: float,
        commission: float,
    ) -> bool:
        """
        Update revenue and commission statistics.

        Args:
            channel_id: Channel ID
            revenue: Revenue amount to add
            commission: Commission amount to add
        """
        channel = await self.get_by_id(channel_id)
        if not channel:
            return False
        channel.total_revenue += revenue
        channel.total_commission += commission
        await self.session.flush()
        return True

    async def delete(self, channel_id: uuid.UUID) -> bool:
        """Delete channel (and cascade to wallet)"""
        channel = await self.get_by_id(channel_id)
        if not channel:
            return False

        await self.session.delete(channel)
        await self.session.flush()
        return True

    # =========================================================================
    # Channel Wallet Operations
    # =========================================================================

    async def create_wallet(self, channel_id: uuid.UUID) -> ChannelWalletDB:
        """Create a wallet for a channel"""
        wallet = ChannelWalletDB(channel_id=channel_id)
        self.session.add(wallet)
        await self.session.flush()
        await self.session.refresh(wallet)
        return wallet

    async def get_wallet(self, channel_id: uuid.UUID) -> Optional[ChannelWalletDB]:
        """Get channel wallet"""
        result = await self.session.execute(
            select(ChannelWalletDB).where(ChannelWalletDB.channel_id == channel_id)
        )
        return result.scalar_one_or_none()

    async def update_wallet_balance(
        self,
        channel_id: uuid.UUID,
        balance_delta: float = 0.0,
        pending_delta: float = 0.0,
        total_commission_delta: float = 0.0,
        total_withdrawn_delta: float = 0.0,
    ) -> Optional[ChannelWalletDB]:
        """
        Update channel wallet balance with optimistic locking.

        Returns None if version mismatch (concurrent update).
        """
        wallet = await self.get_wallet(channel_id)
        if not wallet:
            return None

        # Apply deltas
        if balance_delta != 0:
            wallet.balance += balance_delta
        if pending_delta != 0:
            wallet.pending_commission += pending_delta
        if total_commission_delta != 0:
            wallet.total_commission += total_commission_delta
        if total_withdrawn_delta != 0:
            wallet.total_withdrawn += total_withdrawn_delta

        # Increment version for optimistic locking
        wallet.version += 1

        await self.session.flush()
        await self.session.refresh(wallet)
        return wallet

    # =========================================================================
    # Channel User Operations
    # =========================================================================

    async def get_channel_users(
        self,
        channel_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserDB]:
        """Get users belonging to a channel"""
        result = await self.session.execute(
            select(UserDB)
            .where(UserDB.channel_id == channel_id)
            .order_by(UserDB.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_channel_users(self, channel_id: uuid.UUID) -> int:
        """Count users in a channel"""
        result = await self.session.execute(
            select(func.count(UserDB.id)).where(UserDB.channel_id == channel_id)
        )
        return result.scalar() or 0
