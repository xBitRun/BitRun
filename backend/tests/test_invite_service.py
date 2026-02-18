"""
Tests for InviteService.

Simplified model:
- Only channels have invite codes
- Users register using channel invite codes
- Users do NOT have their own invite codes
- No referral tracking
"""

import pytest
import uuid

from app.services.invite_service import InviteService
from app.db.models import UserDB, ChannelDB


@pytest.mark.unit
class TestInviteCodeValidation:
    """Tests for invite code validation."""

    async def test_validate_empty_code(
        self,
        db_session,
    ):
        """Test validation with empty code."""
        service = InviteService(db_session)
        is_valid, channel = await service.validate_invite_code("")

        assert is_valid is False
        assert channel is None

    async def test_validate_none_code(
        self,
        db_session,
    ):
        """Test validation with None code."""
        service = InviteService(db_session)
        is_valid, channel = await service.validate_invite_code(None)

        assert is_valid is False
        assert channel is None

    async def test_validate_channel_code(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test validation of channel code."""
        service = InviteService(db_session)
        is_valid, channel = await service.validate_invite_code(test_channel.code)

        assert is_valid is True
        assert channel is not None
        assert channel.id == test_channel.id

    async def test_validate_invalid_code(
        self,
        db_session,
    ):
        """Test validation of invalid code."""
        service = InviteService(db_session)
        is_valid, channel = await service.validate_invite_code("INVALID")

        assert is_valid is False
        assert channel is None

    async def test_validate_case_insensitive(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test that validation is case-insensitive."""
        service = InviteService(db_session)
        is_valid, channel = await service.validate_invite_code(test_channel.code.lower())

        assert is_valid is True
        assert channel is not None

    async def test_validate_user_invite_code_not_valid(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test that user's invite code is NOT valid (only channel codes work)."""
        test_user.invite_code = "USER123ABC"
        await db_session.commit()

        service = InviteService(db_session)
        is_valid, channel = await service.validate_invite_code("USER123ABC")

        # User codes are no longer valid
        assert is_valid is False
        assert channel is None


@pytest.mark.unit
class TestUserCreationWithInvite:
    """Tests for user creation with invitation."""

    async def test_create_user_with_channel_invite(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test creating user with channel code."""
        initial_user_count = test_channel.total_users

        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email="channeluser@example.com",
            password="password123",
            name="Channel User",
            invite_code=test_channel.code,
        )

        assert error is None
        assert user is not None
        assert user.email == "channeluser@example.com"
        assert user.name == "Channel User"
        assert user.channel_id == test_channel.id
        assert user.invite_code is None  # Users don't have invite codes
        assert user.referrer_id is None  # No referral tracking

        # Verify channel user count incremented
        await db_session.refresh(test_channel)
        assert test_channel.total_users == initial_user_count + 1

    async def test_create_user_with_invalid_invite(
        self,
        db_session,
    ):
        """Test creating user with invalid invite code."""
        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email="newuser@example.com",
            password="password123",
            name="New User",
            invite_code="INVALID",
        )

        assert user is None
        assert error == "Invalid invitation code"

    async def test_create_user_duplicate_email(
        self,
        db_session,
        test_channel: ChannelDB,
        test_user: UserDB,
    ):
        """Test creating user with existing email."""
        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email=test_user.email,
            password="password123",
            name="New User",
            invite_code=test_channel.code,
        )

        assert user is None
        assert error == "Email already registered"

    async def test_create_user_no_own_invite_code(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test that new user does NOT get their own invite code."""
        service = InviteService(db_session)
        new_user, error = await service.create_user_with_invite(
            email="newuser@example.com",
            password="password123",
            name="New User",
            invite_code=test_channel.code,
        )

        assert error is None
        assert new_user.invite_code is None  # No invite code for users

    async def test_create_user_email_lowercase(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test that email is converted to lowercase."""
        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email="NEWUSER@EXAMPLE.COM",
            password="password123",
            name="New User",
            invite_code=test_channel.code,
        )

        assert error is None
        assert user.email == "newuser@example.com"

    async def test_create_user_no_referrer(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test that new user has no referrer (no referral tracking)."""
        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email="newuser@example.com",
            password="password123",
            name="New User",
            invite_code=test_channel.code,
        )

        assert error is None
        assert user.referrer_id is None


@pytest.mark.unit
class TestGetUserInviteInfo:
    """Tests for getting user invite info."""

    async def test_get_invite_info_no_channel(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test getting info for user without channel."""
        test_user.channel_id = None
        test_user.invite_code = None
        await db_session.commit()

        service = InviteService(db_session)
        info = await service.get_user_invite_info(test_user.id)

        assert info is not None
        assert info["invite_code"] is None  # Users don't have codes
        assert info["referrer_id"] is None  # No referral tracking
        assert info["channel_id"] is None
        assert info["total_invited"] == 0  # Users can't invite
        assert info["channel_code"] is None  # No channel

    async def test_get_invite_info_nonexistent_user(
        self,
        db_session,
    ):
        """Test getting info for nonexistent user."""
        service = InviteService(db_session)
        info = await service.get_user_invite_info(uuid.uuid4())

        assert info is None

    async def test_get_invite_info_with_channel(
        self,
        db_session,
        test_channel_user: UserDB,
        test_channel: ChannelDB,
    ):
        """Test getting info for user with channel."""
        service = InviteService(db_session)
        info = await service.get_user_invite_info(test_channel_user.id)

        assert info is not None
        assert info["channel_id"] == test_channel.id
        assert info["channel_code"] == test_channel.code
        assert info["invite_code"] is None  # Users don't have codes
        assert info["total_invited"] == 0  # Users can't invite

    async def test_get_invite_info_returns_channel_code(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test that channel_code is returned for sharing."""
        from app.core.security import hash_password

        user = UserDB(
            email="channeluser@example.com",
            password_hash=hash_password("password123"),
            name="Channel User",
            channel_id=test_channel.id,
            role="user",
        )
        db_session.add(user)
        await db_session.commit()

        service = InviteService(db_session)
        info = await service.get_user_invite_info(user.id)

        assert info is not None
        assert info["channel_code"] == test_channel.code


@pytest.mark.unit
class TestInviteServiceEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_validate_very_long_code(
        self,
        db_session,
    ):
        """Test validation with very long code."""
        service = InviteService(db_session)
        is_valid, channel = await service.validate_invite_code("A" * 100)

        assert is_valid is False

    async def test_validate_special_characters(
        self,
        db_session,
    ):
        """Test validation with special characters."""
        service = InviteService(db_session)
        is_valid, channel = await service.validate_invite_code("TEST-123_ABC")

        assert is_valid is False

    async def test_create_user_minimal_data(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test creating user with minimal required data."""
        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email="minimal@example.com",
            password="pw",
            name="M",
            invite_code=test_channel.code,
        )

        assert error is None
        assert user is not None

    async def test_create_user_invite_code_already_used(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test that an invite code can only be used once."""
        service = InviteService(db_session)

        # First user should succeed
        user1, error1 = await service.create_user_with_invite(
            email="first@example.com",
            password="password123",
            name="First User",
            invite_code=test_channel.code,
        )
        assert error1 is None
        assert user1 is not None

        # Second user should fail - invite code already used
        user2, error2 = await service.create_user_with_invite(
            email="second@example.com",
            password="password123",
            name="Second User",
            invite_code=test_channel.code,
        )
        assert user2 is None
        assert error2 == "Invitation code has already been used"

    async def test_create_user_different_channels(
        self,
        db_session,
    ):
        """Test creating users with different channel codes."""
        from app.db.repositories import ChannelRepository

        # Create two channels
        channel_repo = ChannelRepository(db_session)
        channel1 = await channel_repo.create(name="Channel 1", code="CH001")
        channel2 = await channel_repo.create(name="Channel 2", code="CH002")

        service = InviteService(db_session)

        # User1 with channel1
        user1, error1 = await service.create_user_with_invite(
            email="user1@example.com",
            password="password123",
            name="User 1",
            invite_code=channel1.code,
        )
        assert error1 is None
        assert user1.channel_id == channel1.id

        # User2 with channel2 (should work, different channel)
        user2, error2 = await service.create_user_with_invite(
            email="user2@example.com",
            password="password123",
            name="User 2",
            invite_code=channel2.code,
        )
        assert error2 is None
        assert user2.channel_id == channel2.id
