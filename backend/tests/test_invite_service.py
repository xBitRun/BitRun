"""
Tests for InviteService.

Covers:
- Invite code generation
- Invite code validation
- User creation with invite
- Invite info retrieval
- Edge cases and error handling
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.invite_service import InviteService
from app.db.models import UserDB, ChannelDB


@pytest.mark.unit
class TestInviteCodeGeneration:
    """Tests for invite code generation."""

    async def test_generate_invite_code_platform_prefix(
        self,
        db_session,
    ):
        """Test generating code with platform prefix."""
        service = InviteService(db_session)
        code = await service.generate_invite_code()

        assert code is not None
        assert code.startswith(InviteService.PLATFORM_PREFIX)
        assert len(code) == len(InviteService.PLATFORM_PREFIX) + InviteService.SUFFIX_LENGTH

    async def test_generate_invite_code_channel_prefix(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test generating code with channel prefix."""
        service = InviteService(db_session)
        code = await service.generate_invite_code(channel_code=test_channel.code)

        assert code is not None
        assert code.startswith(test_channel.code)

    async def test_generate_invite_code_lowercase_converted(
        self,
        db_session,
    ):
        """Test that lowercase prefix is converted to uppercase."""
        service = InviteService(db_session)
        code = await service.generate_invite_code(channel_code="abc")

        assert code.startswith("ABC")

    async def test_generate_invite_code_uniqueness(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test that generated codes are unique."""
        service = InviteService(db_session)

        codes = set()
        for _ in range(100):
            code = await service.generate_invite_code()
            assert code not in codes
            codes.add(code)

    async def test_generate_invite_code_collision_handling(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test that collision is handled by regenerating."""
        service = InviteService(db_session)

        # First code should work
        code1 = await service.generate_invite_code()
        assert code1 is not None

        # Second code should also be different
        code2 = await service.generate_invite_code()
        assert code2 is not None
        assert code1 != code2

    async def test_suffix_format(
        self,
        db_session,
    ):
        """Test that suffix contains only alphanumeric chars."""
        service = InviteService(db_session)

        for _ in range(10):
            code = await service.generate_invite_code()
            suffix = code[len(InviteService.PLATFORM_PREFIX):]

            assert suffix.isalnum()
            assert suffix.isupper() or suffix.isdigit() or any(c.isupper() for c in suffix)


@pytest.mark.unit
class TestInviteCodeValidation:
    """Tests for invite code validation."""

    async def test_validate_empty_code(
        self,
        db_session,
    ):
        """Test validation with empty code."""
        service = InviteService(db_session)
        is_valid, referrer, channel = await service.validate_invite_code("")

        assert is_valid is False
        assert referrer is None
        assert channel is None

    async def test_validate_none_code(
        self,
        db_session,
    ):
        """Test validation with None code."""
        service = InviteService(db_session)
        is_valid, referrer, channel = await service.validate_invite_code(None)

        assert is_valid is False
        assert referrer is None
        assert channel is None

    async def test_validate_user_invite_code(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test validation of user's invite code."""
        test_user.invite_code = "USER123ABC"
        await db_session.commit()

        service = InviteService(db_session)
        is_valid, referrer, channel = await service.validate_invite_code("USER123ABC")

        assert is_valid is True
        assert referrer is not None
        assert referrer.id == test_user.id

    async def test_validate_channel_code(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test validation of channel code directly."""
        service = InviteService(db_session)
        is_valid, referrer, channel = await service.validate_invite_code(test_channel.code)

        assert is_valid is True
        assert referrer is None
        assert channel is not None
        assert channel.id == test_channel.id

    async def test_validate_invalid_code(
        self,
        db_session,
    ):
        """Test validation of invalid code."""
        service = InviteService(db_session)
        is_valid, referrer, channel = await service.validate_invite_code("INVALID")

        assert is_valid is False
        assert referrer is None
        assert channel is None

    async def test_validate_case_insensitive(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test that validation is case-insensitive."""
        test_user.invite_code = "USER123ABC"
        await db_session.commit()

        service = InviteService(db_session)
        is_valid, referrer, channel = await service.validate_invite_code("user123abc")

        assert is_valid is True
        assert referrer is not None

    async def test_validate_user_with_channel(
        self,
        db_session,
        test_channel_user: UserDB,
        test_channel: ChannelDB,
    ):
        """Test validation of user code returns channel info."""
        service = InviteService(db_session)
        is_valid, referrer, channel = await service.validate_invite_code(
            test_channel_user.invite_code
        )

        assert is_valid is True
        assert referrer is not None
        assert channel is not None
        assert channel.id == test_channel.id


@pytest.mark.unit
class TestUserCreationWithInvite:
    """Tests for user creation with invitation."""

    async def test_create_user_with_valid_invite(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test creating user with valid invite code."""
        test_user.invite_code = "VALIDCODE"
        await db_session.commit()

        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email="newuser@example.com",
            password="password123",
            name="New User",
            invite_code="VALIDCODE",
        )

        assert error is None
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.referrer_id == test_user.id
        assert user.invite_code is not None

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
        test_user: UserDB,
    ):
        """Test creating user with existing email."""
        test_user.invite_code = "VALIDCODE"
        await db_session.commit()

        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email=test_user.email,
            password="password123",
            name="New User",
            invite_code="VALIDCODE",
        )

        assert user is None
        assert error == "Email already registered"

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
        assert user.channel_id == test_channel.id
        assert user.invite_code.startswith(test_channel.code)

        # Verify channel user count incremented
        await db_session.refresh(test_channel)
        assert test_channel.total_users == initial_user_count + 1

    async def test_create_user_assigns_own_invite_code(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test that new user gets their own invite code."""
        test_user.invite_code = "VALIDCODE"
        await db_session.commit()

        service = InviteService(db_session)
        new_user, error = await service.create_user_with_invite(
            email="newuser@example.com",
            password="password123",
            name="New User",
            invite_code="VALIDCODE",
        )

        assert error is None
        assert new_user.invite_code is not None
        assert new_user.invite_code != "VALIDCODE"

    async def test_create_user_email_lowercase(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test that email is converted to lowercase."""
        test_user.invite_code = "VALIDCODE"
        await db_session.commit()

        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email="NEWUSER@EXAMPLE.COM",
            password="password123",
            name="New User",
            invite_code="VALIDCODE",
        )

        assert error is None
        assert user.email == "newuser@example.com"


@pytest.mark.unit
class TestGetUserInviteInfo:
    """Tests for getting user invite info."""

    async def test_get_invite_info(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test getting user invite info."""
        test_user.invite_code = "USER123ABC"
        await db_session.commit()

        service = InviteService(db_session)
        info = await service.get_user_invite_info(test_user.id)

        assert info is not None
        assert info["invite_code"] == "USER123ABC"
        assert info["total_invited"] == 0

    async def test_get_invite_info_nonexistent_user(
        self,
        db_session,
    ):
        """Test getting info for nonexistent user."""
        service = InviteService(db_session)
        info = await service.get_user_invite_info(uuid.uuid4())

        assert info is None

    async def test_get_invite_info_with_referrer(
        self,
        db_session,
        test_user: UserDB,
        test_channel_admin: UserDB,
    ):
        """Test getting info for user with referrer."""
        test_user.referrer_id = test_channel_admin.id
        await db_session.commit()

        service = InviteService(db_session)
        info = await service.get_user_invite_info(test_user.id)

        assert info is not None
        assert info["referrer_id"] == test_channel_admin.id

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

    async def test_get_invite_info_counts_invited(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test that total_invited counts correctly."""
        test_user.invite_code = "REFERRER"
        await db_session.commit()

        service = InviteService(db_session)

        # Create invited users
        for i in range(3):
            await service.create_user_with_invite(
                email=f"invited{i}@example.com",
                password="password123",
                name=f"Invited {i}",
                invite_code="REFERRER",
            )

        info = await service.get_user_invite_info(test_user.id)

        assert info["total_invited"] == 3


@pytest.mark.unit
class TestInviteServiceEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_validate_very_long_code(
        self,
        db_session,
    ):
        """Test validation with very long code."""
        service = InviteService(db_session)
        is_valid, referrer, channel = await service.validate_invite_code("A" * 100)

        assert is_valid is False

    async def test_validate_special_characters(
        self,
        db_session,
    ):
        """Test validation with special characters."""
        service = InviteService(db_session)
        is_valid, referrer, channel = await service.validate_invite_code("TEST-123_ABC")

        assert is_valid is False

    async def test_create_user_minimal_data(
        self,
        db_session,
        test_user: UserDB,
    ):
        """Test creating user with minimal required data."""
        test_user.invite_code = "VALID"
        await db_session.commit()

        service = InviteService(db_session)
        user, error = await service.create_user_with_invite(
            email="minimal@example.com",
            password="pw",
            name="M",
            invite_code="VALID",
        )

        assert error is None
        assert user is not None

    async def test_create_multiple_users_same_channel(
        self,
        db_session,
        test_channel: ChannelDB,
    ):
        """Test creating multiple users with same channel code."""
        service = InviteService(db_session)

        users = []
        for i in range(5):
            user, error = await service.create_user_with_invite(
                email=f"multi{i}@example.com",
                password="password123",
                name=f"User {i}",
                invite_code=test_channel.code,
            )
            assert error is None
            users.append(user)

        # All users should have channel
        for user in users:
            assert user.channel_id == test_channel.id

        # Channel count should be updated
        await db_session.refresh(test_channel)
        assert test_channel.total_users == 5
