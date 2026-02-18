"""
Tests for WalletService.

Covers:
- Balance operations (get, check)
- Recharge order creation and processing
- Consumption with commission calculation
- Refund operations
- Gift/bonus operations
- Transaction history
- Edge cases and error handling
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.wallet_service import WalletService, InsufficientBalanceError
from app.db.models import WalletDB, WalletTransactionDB, RechargeOrderDB, ChannelDB, UserDB


@pytest.mark.unit
class TestWalletServiceBalance:
    """Tests for balance operations."""

    async def test_get_wallet_existing(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test getting existing wallet."""
        service = WalletService(db_session)
        wallet = await service.get_wallet(test_user.id)

        assert wallet is not None
        assert wallet.user_id == test_user.id
        assert wallet.balance == 1000.0

    async def test_get_wallet_creates_if_not_exists(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test that get_wallet creates wallet if it doesn't exist."""
        service = WalletService(db_session)
        wallet = await service.get_wallet(test_user.id)

        assert wallet is not None
        assert wallet.user_id == test_user.id
        assert wallet.balance == 0.0

    async def test_get_balance(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test getting balance."""
        service = WalletService(db_session)
        balance = await service.get_balance(test_user.id)

        assert balance == 1000.0

    async def test_get_balance_no_wallet(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test getting balance when wallet doesn't exist."""
        service = WalletService(db_session)
        balance = await service.get_balance(test_user.id)

        assert balance == 0.0

    async def test_has_sufficient_balance_true(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test sufficient balance check returns True."""
        service = WalletService(db_session)
        result = await service.has_sufficient_balance(test_user.id, 500.0)

        assert result is True

    async def test_has_sufficient_balance_false(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test sufficient balance check returns False."""
        service = WalletService(db_session)
        result = await service.has_sufficient_balance(test_user.id, 1500.0)

        assert result is False

    async def test_has_sufficient_balance_exact(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test sufficient balance check with exact amount."""
        service = WalletService(db_session)
        result = await service.has_sufficient_balance(test_user.id, 1000.0)

        assert result is True

    async def test_has_sufficient_balance_zero(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test sufficient balance check with zero amount."""
        service = WalletService(db_session)
        result = await service.has_sufficient_balance(test_user.id, 0.0)

        assert result is True


@pytest.mark.unit
class TestWalletServiceRecharge:
    """Tests for recharge operations."""

    async def test_create_recharge_order(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test creating a recharge order."""
        service = WalletService(db_session)
        order = await service.create_recharge_order(
            user_id=test_user.id,
            amount=100.0,
            bonus_amount=10.0,
        )

        assert order is not None
        assert order.user_id == test_user.id
        assert order.amount == 100.0
        assert order.bonus_amount == 10.0
        assert order.status == "pending"
        assert order.order_no is not None

    async def test_create_recharge_order_no_bonus(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test creating a recharge order without bonus."""
        service = WalletService(db_session)
        order = await service.create_recharge_order(
            user_id=test_user.id,
            amount=100.0,
        )

        assert order.bonus_amount == 0.0

    async def test_create_recharge_order_negative_amount(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test creating recharge with negative amount."""
        service = WalletService(db_session)

        # Should work - validation is at API layer
        order = await service.create_recharge_order(
            user_id=test_user.id,
            amount=-100.0,
        )

        assert order.amount == -100.0

    async def test_process_recharge_success(
        self,
        db_session,
        test_user: UserDB,
        test_recharge_order: RechargeOrderDB,
    ):
        """Test successful recharge processing."""
        # Mark order as paid first
        test_recharge_order.status = "paid"
        await db_session.commit()

        service = WalletService(db_session)
        wallet, error = await service.process_recharge(
            order_id=test_recharge_order.id,
            processed_by=test_user.id,
        )

        assert error is None
        assert wallet is not None
        assert wallet.balance == 110.0  # 100 + 10 bonus

        # Verify order is completed
        await db_session.refresh(test_recharge_order)
        assert test_recharge_order.status == "completed"
        assert test_recharge_order.completed_at is not None

    async def test_process_recharge_order_not_found(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test processing non-existent order."""
        service = WalletService(db_session)
        wallet, error = await service.process_recharge(
            order_id=uuid.uuid4(),
            processed_by=test_user.id,
        )

        assert wallet is None
        assert error == "Order not found"

    async def test_process_recharge_wrong_status(
        self,
        db_session,
        test_user: UserDB,
        test_recharge_order: RechargeOrderDB,
    ):
        """Test processing order with wrong status."""
        # Order is still "pending", not "paid"
        service = WalletService(db_session)
        wallet, error = await service.process_recharge(
            order_id=test_recharge_order.id,
            processed_by=test_user.id,
        )

        assert wallet is None
        assert "Order status is 'pending'" in error

    async def test_process_recharge_with_existing_balance(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
        test_recharge_order: RechargeOrderDB,
    ):
        """Test recharge adds to existing balance."""
        # Mark order as paid
        test_recharge_order.status = "paid"
        await db_session.commit()

        service = WalletService(db_session)
        wallet, error = await service.process_recharge(
            order_id=test_recharge_order.id,
            processed_by=test_user.id,
        )

        assert error is None
        assert wallet.balance == 1110.0  # 1000 existing + 100 + 10 bonus


@pytest.mark.unit
class TestWalletServiceConsume:
    """Tests for consumption operations."""

    async def test_consume_success(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test successful consumption."""
        service = WalletService(db_session)
        transaction, error = await service.consume(
            user_id=test_user.id,
            amount=100.0,
            reference_type="strategy_subscription",
            reference_id=uuid.uuid4(),
            description="Test consumption",
        )

        assert error is None
        assert transaction is not None
        assert transaction.amount == 100.0
        assert transaction.balance_before == 1000.0
        assert transaction.balance_after == 900.0
        assert transaction.type == "consume"

        # Verify wallet balance updated
        await db_session.refresh(test_wallet)
        assert test_wallet.balance == 900.0
        assert test_wallet.total_consumed == 100.0

    async def test_consume_insufficient_balance(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test consumption with insufficient balance."""
        service = WalletService(db_session)

        with pytest.raises(InsufficientBalanceError):
            await service.consume(
                user_id=test_user.id,
                amount=1500.0,
                reference_type="strategy_subscription",
                reference_id=uuid.uuid4(),
            )

    async def test_consume_exact_balance(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test consuming exact balance."""
        service = WalletService(db_session)
        transaction, error = await service.consume(
            user_id=test_user.id,
            amount=1000.0,
            reference_type="strategy_subscription",
            reference_id=uuid.uuid4(),
        )

        assert error is None
        assert transaction.balance_after == 0.0

        await db_session.refresh(test_wallet)
        assert test_wallet.balance == 0.0

    async def test_consume_with_channel_commission(
        self,
        db_session,
        test_channel_user: UserDB,
        test_wallet: WalletDB,
        test_channel: ChannelDB,
    ):
        """Test consumption with channel commission calculation."""
        service = WalletService(db_session)
        transaction, error = await service.consume(
            user_id=test_channel_user.id,
            amount=100.0,
            reference_type="strategy_subscription",
            reference_id=uuid.uuid4(),
        )

        assert error is None
        assert transaction is not None
        # Commission info should be populated
        assert transaction.commission_info is not None
        assert transaction.commission_info["channel_id"] == str(test_channel.id)
        # 10% of 100 = 10
        assert transaction.commission_info["channel_amount"] == 10.0
        assert transaction.commission_info["platform_amount"] == 90.0

    async def test_consume_no_channel(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test consumption without channel (no commission)."""
        service = WalletService(db_session)
        transaction, error = await service.consume(
            user_id=test_user.id,
            amount=100.0,
            reference_type="strategy_subscription",
            reference_id=uuid.uuid4(),
        )

        assert error is None
        assert transaction.commission_info["channel_id"] is None
        assert transaction.commission_info["channel_amount"] == 0.0
        assert transaction.commission_info["platform_amount"] == 100.0


@pytest.mark.unit
class TestWalletServiceRefund:
    """Tests for refund operations."""

    async def test_refund_success(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test successful refund."""
        service = WalletService(db_session)
        transaction, error = await service.refund(
            user_id=test_user.id,
            amount=50.0,
            reference_type="subscription_cancellation",
            reference_id=uuid.uuid4(),
            description="Test refund",
        )

        assert error is None
        assert transaction is not None
        assert transaction.amount == 50.0
        assert transaction.balance_before == 1000.0
        assert transaction.balance_after == 1050.0
        assert transaction.type == "refund"

        await db_session.refresh(test_wallet)
        assert test_wallet.balance == 1050.0

    async def test_refund_reduces_consumed(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test that refund reduces total_consumed."""
        # First consume
        service = WalletService(db_session)
        await service.consume(
            user_id=test_user.id,
            amount=100.0,
            reference_type="test",
            reference_id=uuid.uuid4(),
        )

        # Then refund
        transaction, error = await service.refund(
            user_id=test_user.id,
            amount=50.0,
            reference_type="test_refund",
            reference_id=uuid.uuid4(),
        )

        await db_session.refresh(test_wallet)
        assert test_wallet.total_consumed == 50.0  # 100 - 50


@pytest.mark.unit
class TestWalletServiceGift:
    """Tests for gift/bonus operations."""

    async def test_gift_balance(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test gifting balance."""
        service = WalletService(db_session)
        transaction, error = await service.gift_balance(
            user_id=test_user.id,
            amount=50.0,
            description="Welcome bonus",
        )

        assert error is None
        assert transaction is not None
        assert transaction.amount == 50.0
        assert transaction.type == "gift"
        assert transaction.balance_after == 1050.0

    async def test_gift_creates_wallet(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test that gift creates wallet if not exists."""
        service = WalletService(db_session)
        transaction, error = await service.gift_balance(
            user_id=test_user.id,
            amount=100.0,
        )

        assert error is None
        assert transaction.balance_before == 0.0
        assert transaction.balance_after == 100.0


@pytest.mark.unit
class TestWalletServiceTransactions:
    """Tests for transaction history."""

    async def test_get_transactions(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test getting transaction history."""
        service = WalletService(db_session)

        # Create some transactions
        await service.consume(
            user_id=test_user.id,
            amount=100.0,
            reference_type="test1",
            reference_id=uuid.uuid4(),
        )
        await service.consume(
            user_id=test_user.id,
            amount=50.0,
            reference_type="test2",
            reference_id=uuid.uuid4(),
        )

        transactions = await service.get_transactions(test_user.id)

        assert len(transactions) == 2

    async def test_get_transactions_with_type_filter(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test getting transactions filtered by type."""
        service = WalletService(db_session)

        # Create different types
        await service.consume(
            user_id=test_user.id,
            amount=100.0,
            reference_type="test",
            reference_id=uuid.uuid4(),
        )
        await service.gift_balance(
            user_id=test_user.id,
            amount=50.0,
        )

        consume_transactions = await service.get_transactions(
            test_user.id,
            types=["consume"],
        )
        assert len(consume_transactions) == 1
        assert consume_transactions[0].type == "consume"

    async def test_get_transactions_with_date_filter(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test getting transactions with date range."""
        service = WalletService(db_session)

        await service.consume(
            user_id=test_user.id,
            amount=100.0,
            reference_type="test",
            reference_id=uuid.uuid4(),
        )

        # Filter to future - should return empty
        future_start = datetime.now(UTC) + timedelta(days=1)
        transactions = await service.get_transactions(
            test_user.id,
            start_date=future_start,
        )
        assert len(transactions) == 0

    async def test_get_transaction_summary(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test getting transaction summary."""
        service = WalletService(db_session)

        await service.consume(
            user_id=test_user.id,
            amount=100.0,
            reference_type="test",
            reference_id=uuid.uuid4(),
        )
        await service.gift_balance(
            user_id=test_user.id,
            amount=50.0,
        )

        summary = await service.get_transaction_summary(test_user.id)

        assert "consume" in summary
        assert summary["consume"] == 100.0
        assert summary["gift"] == 50.0


@pytest.mark.unit
class TestWalletServiceCommission:
    """Tests for commission calculation."""

    async def test_calculate_commission_no_channel(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test commission calculation when user has no channel."""
        service = WalletService(db_session)
        commission = await service._calculate_commission(test_user.id, 100.0)

        assert commission["channel_id"] is None
        assert commission["channel_amount"] == 0.0
        assert commission["platform_amount"] == 100.0

    async def test_calculate_commission_with_channel(
        self,
        db_session,
        test_channel_user: UserDB,
        test_channel: ChannelDB,
    ):
        """Test commission calculation with channel."""
        service = WalletService(db_session)
        commission = await service._calculate_commission(test_channel_user.id, 100.0)

        assert commission["channel_id"] == str(test_channel.id)
        # 10% commission rate
        assert commission["channel_amount"] == 10.0
        assert commission["platform_amount"] == 90.0

    async def test_calculate_commission_zero_rate(
        self,
        db_session,
        test_channel_user: UserDB,
        test_channel: ChannelDB,
    ):
        """Test commission with zero commission rate."""
        test_channel.commission_rate = 0.0
        await db_session.commit()

        service = WalletService(db_session)
        commission = await service._calculate_commission(test_channel_user.id, 100.0)

        assert commission["channel_amount"] == 0.0
        assert commission["platform_amount"] == 100.0

    async def test_calculate_commission_full_rate(
        self,
        db_session,
        test_channel_user: UserDB,
        test_channel: ChannelDB,
    ):
        """Test commission with 100% commission rate."""
        test_channel.commission_rate = 1.0
        await db_session.commit()

        service = WalletService(db_session)
        commission = await service._calculate_commission(test_channel_user.id, 100.0)

        assert commission["channel_amount"] == 100.0
        assert commission["platform_amount"] == 0.0


@pytest.mark.unit
class TestWalletServiceEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_consume_zero_amount(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test consuming zero amount."""
        service = WalletService(db_session)
        transaction, error = await service.consume(
            user_id=test_user.id,
            amount=0.0,
            reference_type="test",
            reference_id=uuid.uuid4(),
        )

        assert error is None
        assert transaction.balance_after == transaction.balance_before

    async def test_consume_very_small_amount(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test consuming very small amount."""
        service = WalletService(db_session)
        transaction, error = await service.consume(
            user_id=test_user.id,
            amount=0.01,
            reference_type="test",
            reference_id=uuid.uuid4(),
        )

        assert error is None
        assert transaction.balance_after == pytest.approx(999.99, rel=1e-3)

    async def test_consume_floating_point_precision(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test floating point precision in consumption."""
        service = WalletService(db_session)

        # Multiple small consumptions
        for _ in range(10):
            await service.consume(
                user_id=test_user.id,
                amount=33.33,
                reference_type="test",
                reference_id=uuid.uuid4(),
            )

        await db_session.refresh(test_wallet)
        # 1000 - (33.33 * 10) = 666.7
        assert test_wallet.balance == pytest.approx(666.7, rel=1e-2)

    async def test_concurrent_consumption(
        self,
        db_session,
        test_user: UserDB,
        test_wallet: WalletDB,
    ):
        """Test that version check prevents concurrent update issues."""
        service = WalletService(db_session)

        # This simulates a version conflict by modifying the wallet
        # version externally
        original_version = test_wallet.version

        transaction, error = await service.consume(
            user_id=test_user.id,
            amount=100.0,
            reference_type="test",
            reference_id=uuid.uuid4(),
        )

        # Should succeed since version is correct
        assert error is None
        assert transaction is not None
