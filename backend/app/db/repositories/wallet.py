"""Wallet repository for database operations"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    WalletDB,
    WalletTransactionDB,
)


class WalletRepository:
    """Repository for User Wallet operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Wallet CRUD
    # =========================================================================

    async def create(self, user_id: uuid.UUID) -> WalletDB:
        """
        Create a wallet for a user.

        Args:
            user_id: User ID

        Returns:
            Created WalletDB instance
        """
        wallet = WalletDB(user_id=user_id)
        self.session.add(wallet)
        await self.session.flush()
        await self.session.refresh(wallet)
        return wallet

    async def get_by_id(self, wallet_id: uuid.UUID) -> Optional[WalletDB]:
        """Get wallet by ID"""
        result = await self.session.execute(
            select(WalletDB).where(WalletDB.id == wallet_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: uuid.UUID) -> Optional[WalletDB]:
        """Get wallet by user ID"""
        result = await self.session.execute(
            select(WalletDB).where(WalletDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: uuid.UUID) -> WalletDB:
        """Get existing wallet or create new one"""
        wallet = await self.get_by_user(user_id)
        if not wallet:
            wallet = await self.create(user_id)
        return wallet

    async def update_balance(
        self,
        user_id: uuid.UUID,
        balance_delta: float = 0.0,
        frozen_delta: float = 0.0,
        recharged_delta: float = 0.0,
        consumed_delta: float = 0.0,
        expected_version: Optional[int] = None,
    ) -> Optional[WalletDB]:
        """
        Update wallet balance with optimistic locking.

        Args:
            user_id: User ID
            balance_delta: Change to available balance
            frozen_delta: Change to frozen balance
            recharged_delta: Change to total_recharged
            consumed_delta: Change to total_consumed
            expected_version: Expected version for optimistic lock

        Returns:
            Updated WalletDB or None if version mismatch
        """
        wallet = await self.get_by_user(user_id)
        if not wallet:
            return None

        # Check version for optimistic locking
        if expected_version is not None and wallet.version != expected_version:
            return None

        # Apply deltas
        if balance_delta != 0:
            wallet.balance += balance_delta
        if frozen_delta != 0:
            wallet.frozen_balance += frozen_delta
        if recharged_delta != 0:
            wallet.total_recharged += recharged_delta
        if consumed_delta != 0:
            wallet.total_consumed += consumed_delta

        # Increment version
        wallet.version += 1

        await self.session.flush()
        await self.session.refresh(wallet)
        return wallet

    # =========================================================================
    # Transaction Operations
    # =========================================================================

    async def create_transaction(
        self,
        wallet_id: uuid.UUID,
        user_id: uuid.UUID,
        type: str,
        amount: float,
        balance_before: float,
        balance_after: float,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
        commission_info: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> WalletTransactionDB:
        """
        Create a wallet transaction record.

        Args:
            wallet_id: Wallet ID
            user_id: User ID
            type: Transaction type (recharge, consume, refund, gift, adjustment)
            amount: Transaction amount
            balance_before: Balance before transaction
            balance_after: Balance after transaction
            reference_type: Type of reference (strategy_subscription, recharge_order, etc.)
            reference_id: ID of referenced entity
            commission_info: Commission details if applicable
            description: Transaction description

        Returns:
            Created WalletTransactionDB instance
        """
        transaction = WalletTransactionDB(
            wallet_id=wallet_id,
            user_id=user_id,
            type=type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=reference_id,
            commission_info=commission_info,
            description=description,
        )
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(transaction)
        return transaction

    async def get_transactions(
        self,
        user_id: uuid.UUID,
        types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WalletTransactionDB]:
        """
        Get transaction history for a user.

        Args:
            user_id: User ID
            types: Filter by transaction types
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Max results
            offset: Pagination offset

        Returns:
            List of WalletTransactionDB instances
        """
        query = select(WalletTransactionDB).where(
            WalletTransactionDB.user_id == user_id
        )

        if types:
            query = query.where(WalletTransactionDB.type.in_(types))
        if start_date:
            query = query.where(WalletTransactionDB.created_at >= start_date)
        if end_date:
            query = query.where(WalletTransactionDB.created_at <= end_date)

        query = query.order_by(desc(WalletTransactionDB.created_at))
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_transactions(
        self,
        user_id: uuid.UUID,
        types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Count transactions with filters"""
        query = select(func.count(WalletTransactionDB.id)).where(
            WalletTransactionDB.user_id == user_id
        )

        if types:
            query = query.where(WalletTransactionDB.type.in_(types))
        if start_date:
            query = query.where(WalletTransactionDB.created_at >= start_date)
        if end_date:
            query = query.where(WalletTransactionDB.created_at <= end_date)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_transaction_by_reference(
        self,
        reference_type: str,
        reference_id: uuid.UUID,
    ) -> Optional[WalletTransactionDB]:
        """Get transaction by reference"""
        result = await self.session.execute(
            select(WalletTransactionDB).where(
                and_(
                    WalletTransactionDB.reference_type == reference_type,
                    WalletTransactionDB.reference_id == reference_id,
                )
            )
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_transaction_summary(
        self,
        user_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """
        Get transaction summary by type.

        Returns dict with total amounts per transaction type.
        """
        query = select(
            WalletTransactionDB.type,
            func.sum(WalletTransactionDB.amount).label("total"),
        ).where(WalletTransactionDB.user_id == user_id)

        if start_date:
            query = query.where(WalletTransactionDB.created_at >= start_date)
        if end_date:
            query = query.where(WalletTransactionDB.created_at <= end_date)

        query = query.group_by(WalletTransactionDB.type)

        result = await self.session.execute(query)
        return {row.type: row.total for row in result.all()}
