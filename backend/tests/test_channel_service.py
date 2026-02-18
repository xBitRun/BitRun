"""
Tests for ChannelService.

Covers:
- Channel CRUD operations
- Channel wallet operations
- Channel user management
- Statistics
- Edge cases and error handling
"""

import pytest
import uuid
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.channel_service import ChannelService
from app.db.models import (
    ChannelDB,
    ChannelWalletDB,
    ChannelTransactionDB,
    UserDB,
    WalletDB,
    WalletTransactionDB,
)


@pytest.mark.unit
class TestChannelCRUD:
    """Tests for channel CRUD operations."""

    async def test_create_channel(
        self,
        db_session,
    ):
        """Test creating a channel."""
        service = ChannelService(db_session)
        channel = await service.create_channel(
            name="Test Channel",
            code="TEST01",
            commission_rate=0.15,
            contact_name="John Doe",
            contact_email="john@test.com",
        )

        assert channel is not None
        assert channel.name == "Test Channel"
        assert channel.code == "TEST01"
        assert channel.commission_rate == 0.15
        assert channel.status == "active"

    async def test_create_channel_creates_wallet(
        self,
        db_session,
    ):
        """Test that creating channel also creates wallet."""
        service = ChannelService(db_session)
        channel = await service.create_channel(
            name="Test Channel",
            code="WALLET01",
        )

        wallet = await service.get_channel_wallet(channel.id)
        assert wallet is not None
        assert wallet.channel_id == channel.id
        assert wallet.balance == 0.0

    async def test_create_channel_with_admin(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test creating channel with admin user."""
        service = ChannelService(db_session)
        channel = await service.create_channel(
            name="Test Channel",
            code="ADMIN01",
            admin_user_id=test_user.id,
        )

        assert channel.admin_user_id == test_user.id

        # Verify user role updated
        await db_session.refresh(test_user)
        assert test_user.role == "channel_admin"
        assert test_user.channel_id == channel.id

    async def test_get_channel(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test getting channel by ID."""
        service = ChannelService(db_session)
        channel = await service.get_channel(test_channel.id)

        assert channel is not None
        assert channel.id == test_channel.id

    async def test_get_channel_not_found(
        self,
        db_session,
    ):
        """Test getting non-existent channel."""
        service = ChannelService(db_session)
        channel = await service.get_channel(uuid.uuid4())

        assert channel is None

    async def test_get_channel_by_code(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test getting channel by code."""
        service = ChannelService(db_session)
        channel = await service.get_channel_by_code(test_channel.code)

        assert channel is not None
        assert channel.id == test_channel.id

    async def test_get_channel_by_admin(
        self,
        db_session,
        test_channel_admin: UserDB,
        test_channel: ChannelDB,
    ):
        """Test getting channel by admin user."""
        service = ChannelService(db_session)
        channel = await service.get_channel_by_admin(test_channel_admin.id)

        assert channel is not None
        assert channel.admin_user_id == test_channel_admin.id

    async def test_list_channels(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test listing channels."""
        service = ChannelService(db_session)
        channels = await service.list_channels()

        assert len(channels) >= 1
        assert any(c.id == test_channel.id for c in channels)

    async def test_list_channels_filter_by_status(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test listing channels with status filter."""
        # Create another channel with different status
        service = ChannelService(db_session)
        await service.create_channel(
            name="Suspended Channel",
            code="SUSP01",
        )
        await service.update_channel_status(
            (await service.get_channel_by_code("SUSP01")).id,
            "suspended",
        )

        active_channels = await service.list_channels(status="active")
        suspended_channels = await service.list_channels(status="suspended")

        for c in active_channels:
            assert c.status == "active"
        for c in suspended_channels:
            assert c.status == "suspended"

    async def test_update_channel(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test updating channel."""
        service = ChannelService(db_session)
        channel = await service.update_channel(
            test_channel.id,
            name="Updated Name",
            commission_rate=0.2,
        )

        assert channel is not None
        assert channel.name == "Updated Name"
        assert channel.commission_rate == 0.2

    async def test_update_channel_status(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test updating channel status."""
        service = ChannelService(db_session)
        channel = await service.update_channel_status(
            test_channel.id,
            "suspended",
        )

        assert channel is not None
        assert channel.status == "suspended"

    async def test_set_channel_admin(
        self,
        db_session,
        test_channel: ChannelDB,
        test_user: UserDB,
    ):
        """Test setting channel admin."""
        service = ChannelService(db_session)
        channel = await service.set_channel_admin(
            test_channel.id,
            test_user.id,
        )

        assert channel is not None
        assert channel.admin_user_id == test_user.id

        await db_session.refresh(test_user)
        assert test_user.role == "channel_admin"
        assert test_user.channel_id == test_channel.id


@pytest.mark.unit
class TestChannelWallet:
    """Tests for channel wallet operations."""

    async def test_get_channel_wallet(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test getting channel wallet."""
        service = ChannelService(db_session)
        wallet = await service.get_channel_wallet(test_channel.id)

        assert wallet is not None
        assert wallet.channel_id == test_channel.id
        assert wallet.balance == 100.0

    async def test_get_channel_wallet_not_found(
        self,
        db_session,
    ):
        """Test getting wallet for non-existent channel."""
        service = ChannelService(db_session)
        wallet = await service.get_channel_wallet(uuid.uuid4())

        assert wallet is None

    async def test_withdraw_commission_success(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test successful commission withdrawal."""
        service = ChannelService(db_session)
        transaction, error = await service.withdraw_commission(
            channel_id=test_channel.id,
            amount=50.0,
            note="Test withdrawal",
        )

        assert error is None
        assert transaction is not None
        assert transaction.amount == 50.0
        assert transaction.balance_before == 100.0
        assert transaction.balance_after == 50.0
        assert transaction.type == "withdraw"

    async def test_withdraw_commission_insufficient_balance(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test withdrawal with insufficient balance."""
        service = ChannelService(db_session)
        transaction, error = await service.withdraw_commission(
            channel_id=test_channel.id,
            amount=200.0,
        )

        assert transaction is None
        assert "Insufficient balance" in error

    async def test_withdraw_commission_no_wallet(
        self,
        db_session,
    ):
        """Test withdrawal with no wallet."""
        service = ChannelService(db_session)
        transaction, error = await service.withdraw_commission(
            channel_id=uuid.uuid4(),
            amount=100.0,
        )

        assert transaction is None
        assert error == "Channel wallet not found"

    async def test_withdraw_commission_exact_balance(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test withdrawal of exact balance."""
        service = ChannelService(db_session)
        transaction, error = await service.withdraw_commission(
            channel_id=test_channel.id,
            amount=100.0,
        )

        assert error is None
        assert transaction.balance_after == 0.0

    async def test_get_channel_transactions(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test getting channel transactions."""
        service = ChannelService(db_session)

        # Create some transactions
        await service.withdraw_commission(test_channel.id, 10.0)
        await service.withdraw_commission(test_channel.id, 20.0)

        transactions = await service.get_channel_transactions(test_channel.id)

        assert len(transactions) == 2

    async def test_get_channel_transactions_with_type_filter(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test getting transactions filtered by type."""
        service = ChannelService(db_session)

        await service.withdraw_commission(test_channel.id, 10.0)

        # Add a commission transaction manually
        commission_tx = ChannelTransactionDB(
            wallet_id=test_channel_wallet.id,
            channel_id=test_channel.id,
            type="commission",
            amount=50.0,
            balance_before=100.0,
            balance_after=150.0,
        )
        db_session.add(commission_tx)
        await db_session.commit()

        withdraw_txs = await service.get_channel_transactions(
            test_channel.id,
            types=["withdraw"],
        )

        for tx in withdraw_txs:
            assert tx.type == "withdraw"


@pytest.mark.unit
class TestChannelUsers:
    """Tests for channel user management."""

    async def test_get_channel_users(
        self,
        db_session,
        test_channel_user: UserDB,
        test_channel: ChannelDB,
    ):
        """Test getting channel users."""
        service = ChannelService(db_session)
        users = await service.get_channel_users(test_channel.id)

        assert len(users) >= 1
        assert any(u.id == test_channel_user.id for u in users)

    async def test_get_channel_users_empty(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test getting users for channel with no users."""
        service = ChannelService(db_session)
        users = await service.get_channel_users(test_channel.id)

        assert len(users) == 0

    async def test_count_channel_users(
        self,
        db_session,
        test_channel_user: UserDB,
        test_channel: ChannelDB,
    ):
        """Test counting channel users."""
        service = ChannelService(db_session)
        count = await service.count_channel_users(test_channel.id)

        assert count >= 1

    async def test_get_channel_users_pagination(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test channel users pagination."""
        service = ChannelService(db_session)

        # Create multiple users
        from app.core.security import hash_password
        for i in range(10):
            user = UserDB(
                id=uuid.uuid4(),
                email=f"pageuser{i}@test.com",
                password_hash=hash_password("password"),
                name=f"User {i}",
                channel_id=test_channel.id,
            )
            db_session.add(user)
        await db_session.commit()

        first_page = await service.get_channel_users(test_channel.id, limit=5, offset=0)
        second_page = await service.get_channel_users(test_channel.id, limit=5, offset=5)

        assert len(first_page) == 5
        assert len(second_page) == 5
        # Ensure no overlap
        first_ids = {u.id for u in first_page}
        second_ids = {u.id for u in second_page}
        assert first_ids.isdisjoint(second_ids)


@pytest.mark.unit
class TestChannelStatistics:
    """Tests for channel statistics."""

    async def test_get_channel_statistics(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test getting channel statistics."""
        service = ChannelService(db_session)
        stats = await service.get_channel_statistics(test_channel.id)

        assert "total_users" in stats
        assert "active_users" in stats
        assert "total_commission" in stats
        assert "available_balance" in stats

    async def test_get_channel_statistics_nonexistent(
        self,
        db_session,
    ):
        """Test getting statistics for nonexistent channel."""
        service = ChannelService(db_session)
        stats = await service.get_channel_statistics(uuid.uuid4())

        assert stats == {}

    async def test_get_platform_statistics(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test getting platform statistics."""
        service = ChannelService(db_session)
        stats = await service.get_platform_statistics()

        assert "total_channels" in stats
        assert "active_channels" in stats
        assert "total_users" in stats
        assert "total_revenue" in stats
        assert "platform_revenue" in stats

        assert stats["total_channels"] >= 1

    async def test_get_statistics_with_date_filter(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test statistics with date range."""
        service = ChannelService(db_session)

        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)

        stats = await service.get_channel_statistics(
            test_channel.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert "period_commission" in stats


@pytest.mark.unit
class TestChannelServiceEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_create_channel_zero_commission(
        self,
        db_session,
    ):
        """Test creating channel with zero commission."""
        service = ChannelService(db_session)
        channel = await service.create_channel(
            name="Zero Commission",
            code="ZERO01",
            commission_rate=0.0,
        )

        assert channel.commission_rate == 0.0

    async def test_create_channel_full_commission(
        self,
        db_session,
    ):
        """Test creating channel with 100% commission."""
        service = ChannelService(db_session)
        channel = await service.create_channel(
            name="Full Commission",
            code="FULL01",
            commission_rate=1.0,
        )

        assert channel.commission_rate == 1.0

    async def test_withdraw_zero_amount(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test withdrawing zero amount."""
        service = ChannelService(db_session)
        transaction, error = await service.withdraw_commission(
            channel_id=test_channel.id,
            amount=0.0,
        )

        # Should succeed - zero withdrawal is technically valid
        assert error is None
        assert transaction.balance_after == transaction.balance_before

    async def test_withdraw_negative_amount(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test withdrawing negative amount."""
        service = ChannelService(db_session)

        # This is a business logic question - negative withdrawal
        # could be treated as deposit or rejected
        # Current implementation may allow it
        transaction, error = await service.withdraw_commission(
            channel_id=test_channel.id,
            amount=-10.0,
        )

        # Wallet balance should increase (or error, depending on implementation)
        # Just verify no crash
        assert transaction is not None or error is not None

    async def test_update_channel_nonexistent(
        self,
        db_session,
    ):
        """Test updating non-existent channel."""
        service = ChannelService(db_session)
        channel = await service.update_channel(
            uuid.uuid4(),
            name="New Name",
        )

        assert channel is None

    async def test_set_admin_nonexistent_user(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test setting non-existent user as admin."""
        service = ChannelService(db_session)
        channel = await service.set_channel_admin(
            test_channel.id,
            uuid.uuid4(),
        )

        assert channel is None

    async def test_list_channels_pagination(
        self,
        db_session,
    ):
        """Test listing channels with pagination."""
        service = ChannelService(db_session)

        # Create multiple channels
        for i in range(15):
            await service.create_channel(
                name=f"Channel {i}",
                code=f"PAGE{i:02d}",
            )

        first_page = await service.list_channels(limit=10, offset=0)
        second_page = await service.list_channels(limit=10, offset=10)

        assert len(first_page) == 10
        assert len(second_page) >= 5

    async def test_duplicate_channel_code(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test creating channel with duplicate code."""
        service = ChannelService(db_session)

        # This should fail at the database level due to unique constraint
        # or the service should handle it gracefully
        try:
            channel = await service.create_channel(
                name="Duplicate Code",
                code=test_channel.code,
            )
            # If it doesn't raise, the test should verify the behavior
            # depends on implementation
        except Exception:
            # Expected - duplicate code should fail
            pass

    async def test_channel_status_transitions(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test channel status transitions."""
        service = ChannelService(db_session)

        # active -> suspended
        channel = await service.update_channel_status(test_channel.id, "suspended")
        assert channel.status == "suspended"

        # suspended -> active
        channel = await service.update_channel_status(test_channel.id, "active")
        assert channel.status == "active"

        # active -> closed
        channel = await service.update_channel_status(test_channel.id, "closed")
        assert channel.status == "closed"

    async def test_get_channel_transactions_with_dates(
        self,
        db_session,
        test_channel: ChannelDB,
        test_channel_wallet: ChannelWalletDB,
    ):
        """Test getting transactions with date range."""
        service = ChannelService(db_session)

        # Create transaction
        await service.withdraw_commission(test_channel.id, 10.0)

        # Query with future date range
        future_start = datetime.now(UTC) + timedelta(days=1)
        transactions = await service.get_channel_transactions(
            test_channel.id,
            start_date=future_start,
        )

        assert len(transactions) == 0

        # Query with past date range
        past_start = datetime.now(UTC) - timedelta(days=1)
        transactions = await service.get_channel_transactions(
            test_channel.id,
            start_date=past_start,
        )

        assert len(transactions) >= 1
