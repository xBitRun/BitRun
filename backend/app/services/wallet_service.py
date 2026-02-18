"""Wallet service for balance management"""

import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.repositories import WalletRepository, RechargeRepository, ChannelRepository
from ..db.models import WalletDB, WalletTransactionDB, RechargeOrderDB


class InsufficientBalanceError(Exception):
    """Raised when user has insufficient balance"""
    pass


class WalletService:
    """
    Service for wallet balance management.

    Handles:
    - Balance queries
    - Recharge processing
    - Consumption with commission calculation
    - Transaction history
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.wallet_repo = WalletRepository(session)
        self.recharge_repo = RechargeRepository(session)
        self.channel_repo = ChannelRepository(session)

    # =========================================================================
    # Balance Operations
    # =========================================================================

    async def get_wallet(self, user_id: uuid.UUID) -> Optional[WalletDB]:
        """Get user wallet"""
        return await self.wallet_repo.get_or_create(user_id)

    async def get_balance(self, user_id: uuid.UUID) -> float:
        """Get user available balance"""
        wallet = await self.get_wallet(user_id)
        return wallet.balance if wallet else 0.0

    async def has_sufficient_balance(
        self,
        user_id: uuid.UUID,
        amount: float,
    ) -> bool:
        """Check if user has sufficient balance"""
        balance = await self.get_balance(user_id)
        return balance >= amount

    # =========================================================================
    # Recharge Operations
    # =========================================================================

    async def create_recharge_order(
        self,
        user_id: uuid.UUID,
        amount: float,
        bonus_amount: float = 0.0,
    ) -> RechargeOrderDB:
        """
        Create a new recharge order.

        Args:
            user_id: User ID
            amount: Recharge amount
            bonus_amount: Promotional bonus

        Returns:
            Created RechargeOrderDB
        """
        return await self.recharge_repo.create(
            user_id=user_id,
            amount=amount,
            bonus_amount=bonus_amount,
            payment_method="manual",
        )

    async def process_recharge(
        self,
        order_id: uuid.UUID,
        processed_by: uuid.UUID,
    ) -> Tuple[Optional[WalletDB], Optional[str]]:
        """
        Process a paid recharge order and credit balance.

        This should be called after payment is confirmed.

        Args:
            order_id: Recharge order ID
            processed_by: Admin user ID who confirmed the payment

        Returns:
            Tuple of (wallet, error_message)
        """
        # Get order
        order = await self.recharge_repo.get_by_id(order_id)
        if not order:
            return None, "Order not found"

        if order.status != "paid":
            return None, f"Order status is '{order.status}', expected 'paid'"

        # Get wallet
        wallet = await self.wallet_repo.get_or_create(order.user_id)
        balance_before = wallet.balance

        # Calculate total amount (base + bonus)
        total_amount = order.amount + order.bonus_amount

        # Update wallet balance
        wallet = await self.wallet_repo.update_balance(
            user_id=order.user_id,
            balance_delta=total_amount,
            recharged_delta=total_amount,
            expected_version=wallet.version,
        )

        if not wallet:
            return None, "Concurrent wallet update conflict, please retry"

        # Create transaction record
        await self.wallet_repo.create_transaction(
            wallet_id=wallet.id,
            user_id=order.user_id,
            type="recharge",
            amount=total_amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            reference_type="recharge_order",
            reference_id=order.id,
            description=f"Recharge order {order.order_no}" +
                       (f" (includes bonus: {order.bonus_amount})" if order.bonus_amount > 0 else ""),
        )

        # Mark order as completed
        await self.recharge_repo.mark_completed(order.id)

        return wallet, None

    # =========================================================================
    # Consumption Operations
    # =========================================================================

    async def consume(
        self,
        user_id: uuid.UUID,
        amount: float,
        reference_type: str,
        reference_id: uuid.UUID,
        description: Optional[str] = None,
    ) -> Tuple[Optional[WalletTransactionDB], Optional[str]]:
        """
        Consume balance from user wallet with commission calculation.

        This method:
        1. Checks and deducts balance
        2. Creates transaction record
        3. Calculates and records channel commission

        Args:
            user_id: User ID
            amount: Amount to consume
            reference_type: Type of consumption (strategy_subscription, etc.)
            reference_id: ID of referenced entity
            description: Transaction description

        Returns:
            Tuple of (transaction, error_message)

        Raises:
            InsufficientBalanceError: If user doesn't have enough balance
        """
        # Get wallet
        wallet = await self.wallet_repo.get_or_create(user_id)
        if wallet.balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance: {wallet.balance} < {amount}"
            )

        balance_before = wallet.balance

        # Deduct balance
        wallet = await self.wallet_repo.update_balance(
            user_id=user_id,
            balance_delta=-amount,
            consumed_delta=amount,
            expected_version=wallet.version,
        )

        if not wallet:
            return None, "Concurrent wallet update conflict, please retry"

        # Calculate commission info
        commission_info = await self._calculate_commission(user_id, amount)

        # Create transaction record
        transaction = await self.wallet_repo.create_transaction(
            wallet_id=wallet.id,
            user_id=user_id,
            type="consume",
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            reference_type=reference_type,
            reference_id=reference_id,
            commission_info=commission_info,
            description=description,
        )

        # Record channel commission if applicable
        if commission_info and commission_info.get("channel_id"):
            await self._record_channel_commission(
                channel_id=uuid.UUID(commission_info["channel_id"]),
                user_id=user_id,
                amount=commission_info["channel_amount"],
                reference_type=reference_type,
                reference_id=reference_id,
            )

        return transaction, None

    async def refund(
        self,
        user_id: uuid.UUID,
        amount: float,
        reference_type: str,
        reference_id: uuid.UUID,
        description: Optional[str] = None,
    ) -> Tuple[Optional[WalletTransactionDB], Optional[str]]:
        """
        Refund balance to user wallet.

        Args:
            user_id: User ID
            amount: Amount to refund
            reference_type: Type of refund
            reference_id: ID of referenced entity
            description: Refund description

        Returns:
            Tuple of (transaction, error_message)
        """
        # Get wallet
        wallet = await self.wallet_repo.get_or_create(user_id)
        balance_before = wallet.balance

        # Add balance
        wallet = await self.wallet_repo.update_balance(
            user_id=user_id,
            balance_delta=amount,
            consumed_delta=-amount,  # Reduce consumed count
            expected_version=wallet.version,
        )

        if not wallet:
            return None, "Concurrent wallet update conflict, please retry"

        # Create transaction record
        transaction = await self.wallet_repo.create_transaction(
            wallet_id=wallet.id,
            user_id=user_id,
            type="refund",
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description or "Refund",
        )

        return transaction, None

    # =========================================================================
    # Gift/Bonus Operations
    # =========================================================================

    async def gift_balance(
        self,
        user_id: uuid.UUID,
        amount: float,
        description: str = "System gift",
    ) -> Tuple[Optional[WalletTransactionDB], Optional[str]]:
        """
        Gift balance to user wallet (system bonus, promotion, etc.).

        Args:
            user_id: User ID
            amount: Gift amount
            description: Gift description

        Returns:
            Tuple of (transaction, error_message)
        """
        # Get wallet
        wallet = await self.wallet_repo.get_or_create(user_id)
        balance_before = wallet.balance

        # Add balance
        wallet = await self.wallet_repo.update_balance(
            user_id=user_id,
            balance_delta=amount,
            expected_version=wallet.version,
        )

        if not wallet:
            return None, "Concurrent wallet update conflict, please retry"

        # Create transaction record
        transaction = await self.wallet_repo.create_transaction(
            wallet_id=wallet.id,
            user_id=user_id,
            type="gift",
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            reference_type="system_gift",
            description=description,
        )

        return transaction, None

    # =========================================================================
    # Transaction History
    # =========================================================================

    async def get_transactions(
        self,
        user_id: uuid.UUID,
        types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WalletTransactionDB]:
        """Get transaction history for user"""
        return await self.wallet_repo.get_transactions(
            user_id=user_id,
            types=types,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

    async def get_transaction_summary(
        self,
        user_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """Get transaction summary by type"""
        return await self.wallet_repo.get_transaction_summary(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

    # =========================================================================
    # Private Helpers
    # =========================================================================

    async def _calculate_commission(
        self,
        user_id: uuid.UUID,
        amount: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate commission for a transaction.

        Returns dict with:
        - channel_id: Channel ID (if user belongs to a channel)
        - channel_amount: Commission amount for channel
        - platform_amount: Amount retained by platform
        """
        from sqlalchemy import select
        from ..db.models import UserDB

        # Get user's channel
        result = await self.session.execute(
            select(UserDB.channel_id).where(UserDB.id == user_id)
        )
        channel_id = result.scalar_one_or_none()

        if not channel_id:
            # No channel, all goes to platform
            return {
                "channel_id": None,
                "channel_amount": 0.0,
                "platform_amount": amount,
            }

        # Get channel commission rate
        channel = await self.channel_repo.get_by_id(channel_id)
        if not channel or channel.commission_rate <= 0:
            return {
                "channel_id": str(channel_id),
                "channel_amount": 0.0,
                "platform_amount": amount,
            }

        # Calculate commission
        channel_amount = amount * channel.commission_rate
        platform_amount = amount - channel_amount

        return {
            "channel_id": str(channel_id),
            "channel_amount": channel_amount,
            "platform_amount": platform_amount,
        }

    async def _record_channel_commission(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: float,
        reference_type: str,
        reference_id: uuid.UUID,
    ) -> None:
        """Record commission in channel wallet"""
        from ..db.models import ChannelWalletDB, ChannelTransactionDB

        # Get or create channel wallet
        wallet = await self.channel_repo.get_wallet(channel_id)
        if not wallet:
            wallet = await self.channel_repo.create_wallet(channel_id)

        balance_before = wallet.balance

        # Update wallet
        wallet = await self.channel_repo.update_wallet_balance(
            channel_id=channel_id,
            balance_delta=amount,
            total_commission_delta=amount,
        )

        if not wallet:
            return  # Skip on conflict

        # Create transaction record
        transaction = ChannelTransactionDB(
            wallet_id=wallet.id,
            channel_id=channel_id,
            source_user_id=user_id,
            type="commission",
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            reference_type=reference_type,
            reference_id=reference_id,
            description=f"Commission from user consumption",
        )
        self.session.add(transaction)

        # Update channel statistics
        await self.channel_repo.update_revenue(
            channel_id=channel_id,
            revenue=amount / (1 - (await self.channel_repo.get_by_id(channel_id)).commission_rate)
            if (await self.channel_repo.get_by_id(channel_id)).commission_rate < 1
            else amount,
            commission=amount,
        )
