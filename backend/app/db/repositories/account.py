"""Exchange account repository for database operations"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ExchangeAccountDB
from ...core.security import get_crypto_service

logger = logging.getLogger(__name__)


class AccountRepository:
    """Repository for ExchangeAccount CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.crypto = get_crypto_service()

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        exchange: str,
        is_testnet: bool = False,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        private_key: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> ExchangeAccountDB:
        """
        Create a new exchange account.

        All credentials are encrypted before storage.
        """
        account = ExchangeAccountDB(
            user_id=user_id,
            name=name,
            exchange=exchange.lower(),
            is_testnet=is_testnet,
            encrypted_api_key=self.crypto.encrypt(api_key) if api_key else None,
            encrypted_api_secret=(
                self.crypto.encrypt(api_secret) if api_secret else None
            ),
            encrypted_private_key=(
                self.crypto.encrypt(private_key) if private_key else None
            ),
            encrypted_passphrase=(
                self.crypto.encrypt(passphrase) if passphrase else None
            ),
        )
        self.session.add(account)
        await self.session.flush()
        await self.session.refresh(account)
        return account

    async def get_by_id(
        self, account_id: uuid.UUID, user_id: Optional[uuid.UUID] = None
    ) -> Optional[ExchangeAccountDB]:
        """
        Get account by ID.

        If user_id is provided, ensures the account belongs to that user.
        """
        query = select(ExchangeAccountDB).where(ExchangeAccountDB.id == account_id)
        if user_id:
            query = query.where(ExchangeAccountDB.user_id == user_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id: uuid.UUID, exchange: Optional[str] = None
    ) -> list[ExchangeAccountDB]:
        """
        Get all accounts for a user.

        Optionally filter by exchange type.
        """
        query = select(ExchangeAccountDB).where(ExchangeAccountDB.user_id == user_id)
        if exchange:
            query = query.where(ExchangeAccountDB.exchange == exchange.lower())

        query = query.order_by(ExchangeAccountDB.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self, account_id: uuid.UUID, user_id: uuid.UUID, **kwargs
    ) -> Optional[ExchangeAccountDB]:
        """
        Update account fields.

        Credentials will be encrypted if provided.
        """
        account = await self.get_by_id(account_id, user_id)
        if not account:
            return None

        # Handle credential updates (encrypt them)
        credential_fields = {"api_key", "api_secret", "private_key", "passphrase"}
        for field in credential_fields:
            if field in kwargs and kwargs[field]:
                encrypted_field = f"encrypted_{field}"
                setattr(account, encrypted_field, self.crypto.encrypt(kwargs[field]))
                del kwargs[field]

        # Handle regular field updates
        allowed_fields = {"name", "is_testnet", "is_connected", "connection_error"}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(account, key, value)

        await self.session.flush()
        await self.session.refresh(account)
        return account

    async def update_connection_status(
        self, account_id: uuid.UUID, is_connected: bool, error: Optional[str] = None
    ) -> Optional[ExchangeAccountDB]:
        """Update account connection status"""
        result = await self.session.execute(
            select(ExchangeAccountDB).where(ExchangeAccountDB.id == account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            return None

        account.is_connected = is_connected
        account.connection_error = error
        if is_connected:
            account.last_connected_at = datetime.now(UTC)

        await self.session.flush()
        return account

    async def get_decrypted_credentials(
        self, account_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[dict]:
        """
        Get decrypted credentials for an account.

        Returns dict with api_key, api_secret, private_key, passphrase
        (only non-null values are included).
        """
        account = await self.get_by_id(account_id, user_id)
        if not account:
            logger.debug(f"[DEBUG] Account not found: {account_id}")
            return None

        try:
            credentials = {}
            if account.encrypted_api_key:
                credentials["api_key"] = self.crypto.decrypt(account.encrypted_api_key)
            if account.encrypted_api_secret:
                credentials["api_secret"] = self.crypto.decrypt(
                    account.encrypted_api_secret
                )
            if account.encrypted_private_key:
                credentials["private_key"] = self.crypto.decrypt(
                    account.encrypted_private_key
                )
            if account.encrypted_passphrase:
                credentials["passphrase"] = self.crypto.decrypt(
                    account.encrypted_passphrase
                )

            # Debug logging: print decrypted values (masked)
            logger.debug(f"[DEBUG] Decrypted credentials for account {account_id}:")
            for key, value in credentials.items():
                masked = self._mask_credential(value)
                logger.debug(f"[DEBUG]   {key}: {masked}")

            return credentials
        except Exception as e:
            logger.error(
                f"Failed to decrypt credentials for account {account_id}: {e}. "
                "This may indicate data corruption or encryption key rotation."
            )
            return None

    @staticmethod
    def _mask_credential(value: str) -> str:
        """Mask credential for safe logging (show first 4 and last 4 chars)"""
        if not value:
            return "(empty)"
        if len(value) <= 8:
            return f"{value[:2]}***{value[-2:]}" if len(value) >= 4 else "***"
        return f"{value[:4]}...{value[-4:]}"

    async def delete(self, account_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete account"""
        account = await self.get_by_id(account_id, user_id)
        if not account:
            return False

        await self.session.delete(account)
        await self.session.flush()
        return True
