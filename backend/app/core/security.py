"""
Security module - Encryption and Authentication

Security Architecture (based on NoFx + SlowMist audit recommendations):
1. Data at Rest: AES-256-GCM encryption for API keys and secrets
2. Data in Transit: Optional RSA-OAEP + AES-GCM hybrid encryption
3. Authentication: JWT with random secret per deployment
"""

import asyncio
import base64
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import get_settings


class TokenData(BaseModel):
    """JWT token payload"""

    sub: str  # user_id
    exp: datetime
    iat: datetime
    type: str = "access"  # access or refresh
    jti: Optional[str] = None  # unique token identifier


class CryptoService:
    """
    Encryption service for secure credential storage.

    Uses AES-256-GCM for data at rest encryption.
    Optionally supports RSA-OAEP + AES-GCM for transport encryption.

    Reference: NoFx crypto/service.go implementation
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize crypto service with encryption key.

        Args:
            encryption_key: Base64-encoded 32-byte key for AES-256.
                           If not provided, uses DATA_ENCRYPTION_KEY from settings.
        """
        settings = get_settings()
        key_str = encryption_key or settings.data_encryption_key

        # Decode or generate key
        try:
            # Try to decode as base64
            self._key = base64.urlsafe_b64decode(key_str + "==")[:32]
        except Exception:
            # If decoding fails, derive key from string
            self._key = key_str.encode()[:32].ljust(32, b"\0")

        self._aesgcm = AESGCM(self._key)

        # RSA key pair for transport encryption (generated per instance)
        self._rsa_private_key: Optional[rsa.RSAPrivateKey] = None
        self._rsa_public_key: Optional[rsa.RSAPublicKey] = None

        if settings.transport_encryption_enabled:
            self._generate_rsa_keypair()

    def _generate_rsa_keypair(self) -> None:
        """Generate RSA-2048 key pair for transport encryption"""
        self._rsa_private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        self._rsa_public_key = self._rsa_private_key.public_key()

    # ==================== Storage Encryption (AES-256-GCM) ====================

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt data for storage using AES-256-GCM.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string (format: nonce + ciphertext)
        """
        if not plaintext:
            return ""

        # Generate random 12-byte nonce (recommended for GCM)
        nonce = os.urandom(12)

        # Encrypt
        ciphertext = self._aesgcm.encrypt(
            nonce, plaintext.encode("utf-8"), None  # No additional authenticated data
        )

        # Return base64(nonce + ciphertext)
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt data from storage.

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted:
            return ""

        try:
            # Decode base64
            data = base64.b64decode(encrypted)

            # Extract nonce (first 12 bytes) and ciphertext
            nonce = data[:12]
            ciphertext = data[12:]

            # Decrypt
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}") from e

    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value appears to be encrypted.

        Used for backward compatibility when migrating plaintext data.
        """
        if not value:
            return False
        try:
            data = base64.b64decode(value)
            # Encrypted data should be at least nonce (12) + tag (16) = 28 bytes
            return len(data) >= 28
        except Exception:
            return False

    # ==================== Transport Encryption (RSA + AES) ====================

    def get_public_key_pem(self) -> str:
        """
        Get RSA public key in PEM format for transport encryption.

        This key should be sent to the frontend for encrypting sensitive data
        before transmission.
        """
        if not self._rsa_public_key:
            raise RuntimeError("Transport encryption not enabled")

        return self._rsa_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def decrypt_transport(self, encrypted_data: str) -> str:
        """
        Decrypt data encrypted by frontend using hybrid RSA+AES encryption.

        Expected format (base64 encoded):
        - First 256 bytes: RSA-OAEP encrypted AES key
        - Next 12 bytes: AES-GCM nonce
        - Remaining: AES-GCM ciphertext

        Args:
            encrypted_data: Base64-encoded encrypted payload

        Returns:
            Decrypted plaintext
        """
        if not self._rsa_private_key:
            raise RuntimeError("Transport encryption not enabled")

        try:
            data = base64.b64decode(encrypted_data)

            # Extract components
            encrypted_aes_key = data[:256]  # RSA-2048 output is 256 bytes
            nonce = data[256:268]  # 12 bytes
            ciphertext = data[268:]

            # Decrypt AES key using RSA
            aes_key = self._rsa_private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            # Decrypt data using AES-GCM
            aesgcm = AESGCM(aes_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Transport decryption failed: {e}") from e


# ==================== JWT Authentication ====================


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        user_id: User identifier to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "access",
        "jti": secrets.token_urlsafe(16),  # Unique token ID
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token with longer expiration"""
    settings = get_settings()

    expires_delta = timedelta(days=settings.jwt_refresh_token_expire_days)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        TokenData with decoded payload

    Raises:
        JWTError: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )

        # Verify token type
        if payload.get("type") != token_type:
            raise JWTError(f"Invalid token type: expected {token_type}")

        return TokenData(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            type=payload["type"],
            jti=payload.get("jti"),
        )
    except jwt.ExpiredSignatureError:
        raise JWTError("Token has expired")
    except jwt.JWTClaimsError as e:
        raise JWTError(f"Invalid token claims: {e}")
    except Exception as e:
        raise JWTError(f"Token verification failed: {e}")


# ==================== Password Hashing ====================


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # Encode password to bytes, truncate to 72 bytes (bcrypt limit)
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash (synchronous version)"""
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash in a thread pool.

    bcrypt is CPU-intensive (~200-500ms). Running it via ``asyncio.to_thread``
    prevents blocking the event loop so other requests can be served concurrently.
    """
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)


# ==================== Singleton Instance ====================

_crypto_service: Optional[CryptoService] = None


def get_crypto_service() -> CryptoService:
    """Get or create singleton CryptoService instance"""
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoService()
    return _crypto_service
