"""Invite service for invitation code management"""

import uuid
import secrets
import string
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.repositories import UserRepository, ChannelRepository
from ..db.models import UserDB, ChannelDB
from ..core.security import hash_password


class InviteService:
    """
    Service for invitation code generation and validation.

    Invitation Code Format:
    - Channel code prefix (3-6 chars) + random suffix (6 chars)
    - Example: ABC123XYZ (ABC = channel code, 123XYZ = random)

    For users without a channel (direct platform users):
    - PLT prefix + random suffix
    """

    # Prefix for platform-direct users (no channel)
    PLATFORM_PREFIX = "PLT"

    # Length of random suffix
    SUFFIX_LENGTH = 6

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.channel_repo = ChannelRepository(session)

    def _generate_random_suffix(self) -> str:
        """Generate a random alphanumeric suffix"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(self.SUFFIX_LENGTH))

    async def generate_invite_code(
        self,
        channel_code: Optional[str] = None,
    ) -> str:
        """
        Generate a unique invitation code.

        Args:
            channel_code: Optional channel code prefix

        Returns:
            Unique invitation code
        """
        prefix = (channel_code or self.PLATFORM_PREFIX).upper()

        # Generate unique code (retry if collision)
        max_attempts = 10
        for _ in range(max_attempts):
            suffix = self._generate_random_suffix()
            code = f"{prefix}{suffix}"

            # Check if code already exists
            existing = await self.user_repo.get_by_invite_code(code)
            if not existing:
                return code

        # Fallback with timestamp if too many collisions
        import time
        timestamp = int(time.time()) % 100000
        return f"{prefix}{timestamp}{self._generate_random_suffix()[:3]}"

    async def validate_invite_code(
        self,
        invite_code: str,
    ) -> Tuple[bool, Optional[UserDB], Optional[ChannelDB]]:
        """
        Validate an invitation code.

        Args:
            invite_code: The invitation code to validate

        Returns:
            Tuple of (is_valid, referrer_user, channel)
            - is_valid: True if code is valid
            - referrer_user: The user who owns this invite code (if user invite)
            - channel: The channel this code belongs to (if channel code)
        """
        if not invite_code:
            return False, None, None

        code = invite_code.upper()

        # First, try to find a user with this invite code
        referrer = await self.user_repo.get_by_invite_code(code)
        if referrer:
            # Get the channel from referrer
            channel = None
            if referrer.channel_id:
                channel = await self.channel_repo.get_by_id(referrer.channel_id)
            return True, referrer, channel

        # If no user found, check if it's a channel code directly
        # Extract potential channel code prefix (first 3-6 characters)
        for prefix_len in range(6, 2, -1):
            potential_prefix = code[:prefix_len]
            channel = await self.channel_repo.get_by_code(potential_prefix)
            if channel:
                # This is a direct channel invite
                return True, None, channel

        return False, None, None

    async def create_user_with_invite(
        self,
        email: str,
        password: str,
        name: str,
        invite_code: str,
    ) -> Tuple[Optional[UserDB], Optional[str]]:
        """
        Create a new user with invitation code binding.

        Args:
            email: User email
            password: User password
            name: User display name
            invite_code: Invitation code (required)

        Returns:
            Tuple of (user, error_message)
            - user: Created user or None on failure
            - error_message: Error description or None on success
        """
        # Validate invite code
        is_valid, referrer, channel = await self.validate_invite_code(invite_code)
        if not is_valid:
            return None, "Invalid invitation code"

        # Check if email already exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            return None, "Email already registered"

        # Generate user's own invite code
        channel_code = channel.code if channel else None
        user_invite_code = await self.generate_invite_code(channel_code)

        # Create user
        user = UserDB(
            email=email.lower(),
            password_hash=hash_password(password),
            name=name,
            invite_code=user_invite_code,
            referrer_id=referrer.id if referrer else None,
            channel_id=channel.id if channel else None,
            role="user",
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        # Update channel user count
        if channel:
            await self.channel_repo.increment_users(channel.id)

        return user, None

    async def get_user_invite_info(
        self,
        user_id: uuid.UUID,
    ) -> Optional[dict]:
        """
        Get invitation information for a user.

        Returns dict with:
        - invite_code: User's invite code
        - referrer: Referrer user info (if any)
        - channel: Channel info (if any)
        - total_invited: Count of users invited by this user
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        # Count invited users
        from sqlalchemy import select, func
        from ..db.models import UserDB as UserModel
        result = await self.session.execute(
            select(func.count(UserModel.id)).where(UserModel.referrer_id == user_id)
        )
        total_invited = result.scalar() or 0

        return {
            "invite_code": user.invite_code,
            "referrer_id": user.referrer_id,
            "channel_id": user.channel_id,
            "total_invited": total_invited,
        }
