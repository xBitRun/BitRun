"""
Resolve AI provider credentials from database.

Used by strategy execution, debate, backtest, and model test flows.
API keys are stored per user in AIProviderConfigDB (encrypted).
"""

import uuid
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.security import CryptoService
from ...db.models import AIProviderConfigDB


async def resolve_provider_credentials(
    db: AsyncSession,
    crypto: CryptoService,
    user_id: uuid.UUID,
    model_id: str,
) -> Tuple[str | None, str | None]:
    """
    Resolve API key and optional base_url for a model from the user's provider config.

    Args:
        db: Database session
        crypto: Crypto service for decrypting stored API key
        user_id: Current user ID
        model_id: Full model ID (e.g. "deepseek:deepseek-chat"); provider_type is taken from the prefix

    Returns:
        (api_key, base_url). (None, None) if no enabled config with API key found.
    """
    if ":" not in model_id:
        return (None, None)
    provider_type = model_id.split(":", 1)[0].strip().lower()
    if not provider_type:
        return (None, None)

    result = await db.execute(
        select(AIProviderConfigDB)
        .where(
            AIProviderConfigDB.user_id == user_id,
            AIProviderConfigDB.provider_type == provider_type,
            AIProviderConfigDB.is_enabled.is_(True),
        )
        .order_by(AIProviderConfigDB.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row or not row.encrypted_api_key:
        return (None, None)

    api_key = crypto.decrypt(row.encrypted_api_key)
    base_url = (row.base_url or "").strip() or None
    if base_url:
        base_url = base_url.rstrip("/")
    return (api_key, base_url)
