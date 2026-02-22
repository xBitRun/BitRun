"""Channel service for channel management"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ..db.repositories import ChannelRepository, UserRepository, WalletRepository
from ..db.models import (
    ChannelDB,
    ChannelWalletDB,
    ChannelTransactionDB,
    UserDB,
    WalletTransactionDB,
    RechargeOrderDB,
    ExchangeAccountDB,
    AgentDB,
)


class ChannelService:
    """
    Service for channel management operations.

    Handles:
    - Channel CRUD
    - Channel wallet operations
    - Channel statistics
    - User management
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.channel_repo = ChannelRepository(session)
        self.user_repo = UserRepository(session)
        self.wallet_repo = WalletRepository(session)

    # =========================================================================
    # Channel CRUD
    # =========================================================================

    async def create_channel(
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
            code: Unique channel code (3-6 chars, uppercase)
            commission_rate: Commission rate (0.0-1.0)
            contact_name: Contact person name
            contact_email: Contact email
            contact_phone: Contact phone
            admin_user_id: User ID to set as channel admin

        Returns:
            Created ChannelDB
        """
        # Create channel
        channel = await self.channel_repo.create(
            name=name,
            code=code,
            commission_rate=commission_rate,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            admin_user_id=admin_user_id,
        )

        # Create channel wallet
        await self.channel_repo.create_wallet(channel.id)

        # If admin_user_id provided, update user role
        if admin_user_id:
            user = await self.user_repo.get_by_id(admin_user_id)
            if user:
                user.role = "channel_admin"
                user.channel_id = channel.id
                await self.session.flush()

        return channel

    async def get_channel(self, channel_id: uuid.UUID) -> Optional[ChannelDB]:
        """Get channel by ID"""
        return await self.channel_repo.get_by_id(channel_id)

    async def get_channel_by_code(self, code: str) -> Optional[ChannelDB]:
        """Get channel by code"""
        return await self.channel_repo.get_by_code(code)

    async def get_channel_by_admin(self, user_id: uuid.UUID) -> Optional[ChannelDB]:
        """Get channel by admin user ID"""
        return await self.channel_repo.get_by_admin_user(user_id)

    async def list_channels(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ChannelDB]:
        """List all channels with optional filtering"""
        return await self.channel_repo.list_all(
            status=status,
            limit=limit,
            offset=offset,
        )

    async def update_channel(
        self, channel_id: uuid.UUID, **kwargs
    ) -> Optional[ChannelDB]:
        """Update channel fields"""
        return await self.channel_repo.update(channel_id, **kwargs)

    async def update_channel_status(
        self,
        channel_id: uuid.UUID,
        status: str,
    ) -> Optional[ChannelDB]:
        """Update channel status (active, suspended, closed)"""
        return await self.channel_repo.update_status(channel_id, status)

    async def set_channel_admin(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[ChannelDB]:
        """Set channel admin user"""
        # Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        # Update channel
        channel = await self.channel_repo.update(
            channel_id,
            admin_user_id=user_id,
        )
        if not channel:
            return None

        # Update user
        user.role = "channel_admin"
        user.channel_id = channel_id
        await self.session.flush()

        return channel

    # =========================================================================
    # Channel Wallet Operations
    # =========================================================================

    async def get_channel_wallet(
        self,
        channel_id: uuid.UUID,
    ) -> Optional[ChannelWalletDB]:
        """Get channel wallet"""
        return await self.channel_repo.get_wallet(channel_id)

    async def get_channel_transactions(
        self,
        channel_id: uuid.UUID,
        types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ChannelTransactionDB]:
        """Get channel transaction history"""
        query = select(ChannelTransactionDB).where(
            ChannelTransactionDB.channel_id == channel_id
        )

        if types:
            query = query.where(ChannelTransactionDB.type.in_(types))
        if start_date:
            query = query.where(ChannelTransactionDB.created_at >= start_date)
        if end_date:
            query = query.where(ChannelTransactionDB.created_at <= end_date)

        query = query.order_by(ChannelTransactionDB.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def withdraw_commission(
        self,
        channel_id: uuid.UUID,
        amount: float,
        note: Optional[str] = None,
    ) -> Tuple[Optional[ChannelTransactionDB], Optional[str]]:
        """
        Withdraw commission from channel wallet.

        Args:
            channel_id: Channel ID
            amount: Amount to withdraw
            note: Withdrawal note

        Returns:
            Tuple of (transaction, error_message)
        """
        wallet = await self.channel_repo.get_wallet(channel_id)
        if not wallet:
            return None, "Channel wallet not found"

        if wallet.balance < amount:
            return None, f"Insufficient balance: {wallet.balance} < {amount}"

        balance_before = wallet.balance

        # Update wallet
        wallet = await self.channel_repo.update_wallet_balance(
            channel_id=channel_id,
            balance_delta=-amount,
            total_withdrawn_delta=amount,
        )

        if not wallet:
            return None, "Concurrent update conflict, please retry"

        # Create transaction
        transaction = ChannelTransactionDB(
            wallet_id=wallet.id,
            channel_id=channel_id,
            type="withdraw",
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=note or "Commission withdrawal",
        )
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(transaction)

        return transaction, None

    # =========================================================================
    # Channel Users
    # =========================================================================

    async def get_channel_users(
        self,
        channel_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserDB]:
        """Get users belonging to a channel"""
        return await self.channel_repo.get_channel_users(
            channel_id=channel_id,
            limit=limit,
            offset=offset,
        )

    async def count_channel_users(self, channel_id: uuid.UUID) -> int:
        """Count users in a channel"""
        return await self.channel_repo.count_channel_users(channel_id)

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_channel_statistics(
        self,
        channel_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive channel statistics.

        Returns:
            - total_users: Total channel users
            - active_users: Users with activity in period
            - total_revenue: Total revenue from users
            - total_commission: Total commission earned
            - pending_commission: Pending commission
            - available_balance: Available for withdrawal
        """
        channel = await self.channel_repo.get_by_id(channel_id)
        if not channel:
            return {}

        wallet = await self.channel_repo.get_wallet(channel_id)

        # Count active users (with transactions in period)
        active_users_query = (
            select(func.count(func.distinct(WalletTransactionDB.user_id)))
            .select_from(WalletTransactionDB)
            .join(UserDB, UserDB.id == WalletTransactionDB.user_id)
            .where(UserDB.channel_id == channel_id)
        )

        if start_date:
            active_users_query = active_users_query.where(
                WalletTransactionDB.created_at >= start_date
            )
        if end_date:
            active_users_query = active_users_query.where(
                WalletTransactionDB.created_at <= end_date
            )

        result = await self.session.execute(active_users_query)
        active_users = result.scalar() or 0

        # Get commission for period
        commission_query = select(func.sum(ChannelTransactionDB.amount)).where(
            and_(
                ChannelTransactionDB.channel_id == channel_id,
                ChannelTransactionDB.type == "commission",
            )
        )
        if start_date:
            commission_query = commission_query.where(
                ChannelTransactionDB.created_at >= start_date
            )
        if end_date:
            commission_query = commission_query.where(
                ChannelTransactionDB.created_at <= end_date
            )

        result = await self.session.execute(commission_query)
        period_commission = result.scalar() or 0.0

        return {
            "total_users": channel.total_users,
            "active_users": active_users,
            "total_revenue": channel.total_revenue,
            "total_commission": channel.total_commission,
            "period_commission": period_commission,
            "pending_commission": wallet.pending_commission if wallet else 0.0,
            "available_balance": wallet.balance if wallet else 0.0,
            "frozen_balance": wallet.frozen_balance if wallet else 0.0,
        }

    async def get_platform_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get platform-wide statistics.

        Returns:
            - total_channels: Total channels
            - active_channels: Active channels
            - total_users: Total users
            - total_revenue: Total revenue (from completed recharge orders)
            - total_commission: Total commission paid to channels
            - platform_revenue: Revenue after commission
        """
        # Count channels
        total_channels = await self.channel_repo.count()
        active_channels = await self.channel_repo.count(status="active")

        # Count users
        users_result = await self.session.execute(select(func.count(UserDB.id)))
        total_users = users_result.scalar() or 0

        # Get total revenue from completed recharge orders
        # This includes all recharge income, regardless of channel
        revenue_query = select(
            func.sum(RechargeOrderDB.amount).label("total_revenue")
        ).where(RechargeOrderDB.status == "completed")

        if start_date:
            revenue_query = revenue_query.where(
                RechargeOrderDB.completed_at >= start_date
            )
        if end_date:
            revenue_query = revenue_query.where(
                RechargeOrderDB.completed_at <= end_date
            )

        revenue_result = await self.session.execute(revenue_query)
        total_revenue = revenue_result.scalar() or 0.0

        # Get total commission paid to channels
        commission_result = await self.session.execute(
            select(func.sum(ChannelDB.total_commission).label("total_commission"))
        )
        total_commission = commission_result.scalar() or 0.0

        return {
            "total_channels": total_channels,
            "active_channels": active_channels,
            "total_users": total_users,
            "total_revenue": total_revenue,
            "total_commission": total_commission,
            "platform_revenue": total_revenue - total_commission,
        }

    async def get_channel_extended_stats(
        self,
        channel_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get extended statistics for a channel (accounts, agents).

        Returns:
            - total_accounts: Total exchange accounts for channel users
            - total_agents: Total agents for channel users
        """
        # Get channel users IDs
        users_query = select(UserDB.id).where(UserDB.channel_id == channel_id)
        result = await self.session.execute(users_query)
        user_ids = [row[0] for row in result.fetchall()]

        if not user_ids:
            return {
                "total_accounts": 0,
                "total_agents": 0,
            }

        # Count exchange accounts
        accounts_query = select(func.count(ExchangeAccountDB.id)).where(
            ExchangeAccountDB.user_id.in_(user_ids)
        )
        accounts_result = await self.session.execute(accounts_query)
        total_accounts = accounts_result.scalar() or 0

        # Count agents
        agents_query = select(func.count(AgentDB.id)).where(
            AgentDB.user_id.in_(user_ids)
        )
        agents_result = await self.session.execute(agents_query)
        total_agents = agents_result.scalar() or 0

        return {
            "total_accounts": total_accounts,
            "total_agents": total_agents,
        }
