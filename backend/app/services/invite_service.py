"""Invite service for invitation code management"""

import uuid
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.repositories import UserRepository, ChannelRepository
from ..db.models import UserDB, ChannelDB
from ..core.security import hash_password


class InviteService:
    """
    Service for invitation code validation.

    Simplified model:
    - Only channels have invite codes
    - Users register using channel invite codes
    - Users do NOT have their own invite codes
    - Users cannot invite other users (no referral rewards)
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.channel_repo = ChannelRepository(session)

    async def validate_invite_code(
        self,
        invite_code: str,
    ) -> Tuple[bool, Optional[ChannelDB]]:
        """
        Validate an invitation code.

        Only validates channel invite codes (no user invite codes).

        Args:
            invite_code: The invitation code to validate

        Returns:
            Tuple of (is_valid, channel)
            - is_valid: True if code is a valid channel code
            - channel: The channel this code belongs to
        """
        if not invite_code:
            return False, None

        code = invite_code.upper()

        # Check if it's a channel code directly
        # Channel codes are 3-6 characters
        for prefix_len in range(6, 2, -1):
            potential_prefix = code[:prefix_len]
            channel = await self.channel_repo.get_by_code(potential_prefix)
            if channel:
                return True, channel

        return False, None

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
            invite_code: Channel invitation code (required)

        Returns:
            Tuple of (user, error_message)
            - user: Created user or None on failure
            - error_message: Error description or None on success
        """
        # Validate invite code (only channel codes)
        is_valid, channel = await self.validate_invite_code(invite_code)
        if not is_valid:
            return None, "Invalid invitation code"

        # Check if invite code has already been used (one code per user)
        existing_user_count = await self.channel_repo.count_channel_users(channel.id)
        if existing_user_count > 0:
            return None, "Invitation code has already been used"

        # Check if email already exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            return None, "Email already registered"

        # Create user (no invite_code, no referrer_id)
        user = UserDB(
            email=email.lower(),
            password_hash=hash_password(password),
            name=name,
            invite_code=None,  # Users don't have invite codes
            referrer_id=None,  # No referral tracking
            channel_id=channel.id,
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
        - invite_code: Always None (users don't have invite codes)
        - referrer_id: Always None (no referral tracking)
        - channel_id: Channel the user belongs to (if any)
        - total_invited: Always 0 (users can't invite)
        - channel_code: Channel's invite code (for sharing)
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        # Get channel info if user belongs to one
        channel_code = None
        if user.channel_id:
            channel = await self.channel_repo.get_by_id(user.channel_id)
            channel_code = channel.code if channel else None

        return {
            "invite_code": None,  # Users don't have invite codes
            "referrer_id": None,  # No referral tracking
            "channel_id": user.channel_id,
            "total_invited": 0,  # Users can't invite
            "channel_code": channel_code,  # Channel code for sharing
        }
