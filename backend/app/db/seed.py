"""
Database seed data for initial setup.

This module provides functions to initialize default data on application startup.
"""

import logging
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal
from .models import UserDB
from ..core.security import hash_password

logger = logging.getLogger(__name__)


async def seed_admin_user() -> Optional[UserDB]:
    """
    Seed the default platform admin user if not exists.

    Admin credentials MUST be configured via environment variables:
    - ADMIN_EMAIL: Admin email (required)
    - ADMIN_PASSWORD: Admin password (required)
    - ADMIN_NAME: Admin display name (optional, defaults to "Admin")

    Returns:
        UserDB if created or exists, None if failed or not configured
    """
    # Get credentials from environment (no defaults for sensitive data)
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_name = os.getenv("ADMIN_NAME", "Admin")

    # Skip if not configured
    if not admin_email or not admin_password:
        logger.info("Seed: Admin user not configured (set ADMIN_EMAIL and ADMIN_PASSWORD)")
        logger.debug(f"Current ADMIN_EMAIL value: {admin_email!r}")
        return None

    logger.info(f"Seed: Creating admin user {admin_email}...")

    async with AsyncSessionLocal() as session:
        try:
            # Check if admin already exists
            result = await session.execute(
                select(UserDB).where(UserDB.email == admin_email.lower())
            )
            existing_admin = result.scalar_one_or_none()

            if existing_admin:
                logger.info(f"Admin user already exists: {admin_email}")
                return existing_admin

            # Create admin user
            admin_user = UserDB(
                email=admin_email.lower(),
                password_hash=hash_password(admin_password),
                name=admin_name,
                role="platform_admin",
                is_active=True,
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)

            logger.info(f"Created default admin user: {admin_email}")
            return admin_user

        except Exception as e:
            logger.error(f"Failed to seed admin user: {e}")
            await session.rollback()
            return None


async def seed_all() -> dict:
    """
    Run all seed functions.

    Returns:
        Dictionary with seed results
    """
    results = {
        "admin_user": None,
    }

    # Seed admin user
    admin = await seed_admin_user()
    results["admin_user"] = "created" if admin else "skipped"

    return results
