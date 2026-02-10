"""
Tests for the security module - encryption and JWT.
"""

import os

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from app.core.security import (
    CryptoService,
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_password,
    verify_password,
)
from jose import JWTError


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "my_secure_password123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are ~60 chars
        assert hashed.startswith("$2")  # bcrypt prefix
    
    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty(self):
        """Test verifying empty password."""
        password = "test"
        hashed = hash_password(password)
        
        assert verify_password("", hashed) is False
    
    def test_hash_long_password(self):
        """Test hashing a password longer than bcrypt's 72 byte limit."""
        # bcrypt truncates at 72 bytes, but our function handles this
        long_password = "a" * 100
        hashed = hash_password(long_password)
        
        # Should still work (truncated)
        assert verify_password(long_password[:72], hashed) is True


class TestJWT:
    """Tests for JWT token functions."""
    
    def test_create_access_token(self):
        """Test creating an access token."""
        user_id = "test-user-123"
        token = create_access_token(user_id)
        
        assert token is not None
        assert len(token) > 100  # JWT tokens are typically longer
        assert token.count(".") == 2  # JWT has 3 parts separated by dots
    
    def test_create_refresh_token(self):
        """Test creating a refresh token."""
        user_id = "test-user-123"
        token = create_refresh_token(user_id)
        
        assert token is not None
        assert len(token) > 100
    
    def test_verify_access_token(self):
        """Test verifying a valid access token."""
        user_id = "test-user-456"
        token = create_access_token(user_id)
        
        token_data = verify_token(token, token_type="access")
        
        assert token_data.sub == user_id
        assert token_data.type == "access"
        assert token_data.jti is not None
    
    def test_verify_refresh_token(self):
        """Test verifying a valid refresh token."""
        user_id = "test-user-789"
        token = create_refresh_token(user_id)
        
        token_data = verify_token(token, token_type="refresh")
        
        assert token_data.sub == user_id
        assert token_data.type == "refresh"
    
    def test_verify_wrong_token_type(self):
        """Test verifying token with wrong type raises error."""
        user_id = "test-user"
        access_token = create_access_token(user_id)
        
        with pytest.raises(JWTError) as exc_info:
            verify_token(access_token, token_type="refresh")
        
        assert "Invalid token type" in str(exc_info.value)
    
    def test_verify_invalid_token(self):
        """Test verifying invalid token raises error."""
        with pytest.raises(JWTError):
            verify_token("invalid.token.here", token_type="access")
    
    def test_verify_tampered_token(self):
        """Test verifying tampered token raises error."""
        user_id = "test-user"
        token = create_access_token(user_id)
        
        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "XXXXX"  # Modify payload
        tampered = ".".join(parts)
        
        with pytest.raises(JWTError):
            verify_token(tampered, token_type="access")
    
    def test_token_contains_jti(self):
        """Test that token contains unique JTI claim."""
        user_id = "test-user"
        token1 = create_access_token(user_id)
        token2 = create_access_token(user_id)
        
        data1 = verify_token(token1, token_type="access")
        data2 = verify_token(token2, token_type="access")
        
        # JTI should be unique per token
        assert data1.jti != data2.jti


class TestCryptoService:
    """Tests for CryptoService encryption/decryption."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Use a fixed 32-byte key for testing (256 bits)
        self.crypto = CryptoService(encryption_key="12345678901234567890123456789012")
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work correctly."""
        plaintext = "my_secret_api_key_12345"
        
        encrypted = self.crypto.encrypt(plaintext)
        decrypted = self.crypto.decrypt(encrypted)
        
        assert decrypted == plaintext
        assert encrypted != plaintext
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        encrypted = self.crypto.encrypt("")
        assert encrypted == ""
        
        decrypted = self.crypto.decrypt("")
        assert decrypted == ""
    
    def test_encrypt_produces_different_output(self):
        """Test that encrypting the same text produces different ciphertext (due to random nonce)."""
        plaintext = "same_text"
        
        encrypted1 = self.crypto.encrypt(plaintext)
        encrypted2 = self.crypto.encrypt(plaintext)
        
        # Each encryption should produce different ciphertext
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the same plaintext
        assert self.crypto.decrypt(encrypted1) == plaintext
        assert self.crypto.decrypt(encrypted2) == plaintext
    
    def test_decrypt_invalid_data(self):
        """Test decrypting invalid data raises error."""
        with pytest.raises(ValueError) as exc_info:
            self.crypto.decrypt("not_valid_encrypted_data")
        
        assert "Decryption failed" in str(exc_info.value)
    
    def test_is_encrypted(self):
        """Test checking if value is encrypted."""
        plaintext = "plain_text"
        encrypted = self.crypto.encrypt(plaintext)
        
        assert self.crypto.is_encrypted(encrypted) is True
        assert self.crypto.is_encrypted(plaintext) is False
        assert self.crypto.is_encrypted("") is False
    
    def test_encrypt_unicode(self):
        """Test encrypting unicode text."""
        plaintext = "こんにちは世界 🌍"
        
        encrypted = self.crypto.encrypt(plaintext)
        decrypted = self.crypto.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_long_text(self):
        """Test encrypting long text."""
        plaintext = "a" * 10000  # 10KB of data
        
        encrypted = self.crypto.encrypt(plaintext)
        decrypted = self.crypto.decrypt(encrypted)
        
        assert decrypted == plaintext


# ==================== Extended Security Tests ====================


class TestCryptoServiceKeyDerivation:
    """Tests for CryptoService key derivation and transport encryption."""

    def test_key_derivation_from_non_base64(self):
        """When base64 decode fails, key is derived from raw string."""
        from app.core.security import CryptoService
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.data_encryption_key = "not-base64-at-all!!!"
            mock_settings.return_value.transport_encryption_enabled = False
            crypto = CryptoService(encryption_key="not-base64-at-all!!!")
            # Should still work for encrypt/decrypt
            encrypted = crypto.encrypt("hello")
            assert crypto.decrypt(encrypted) == "hello"

    def test_transport_encryption_enabled(self):
        """RSA keypair is generated when transport encryption enabled."""
        from app.core.security import CryptoService
        import base64
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.data_encryption_key = key
            mock_settings.return_value.transport_encryption_enabled = True
            crypto = CryptoService(encryption_key=key)
            assert crypto._rsa_private_key is not None
            assert crypto._rsa_public_key is not None

    def test_get_public_key_pem(self):
        """get_public_key_pem returns PEM string."""
        from app.core.security import CryptoService
        import base64
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.data_encryption_key = key
            mock_settings.return_value.transport_encryption_enabled = True
            crypto = CryptoService(encryption_key=key)
            pem = crypto.get_public_key_pem()
            assert "BEGIN PUBLIC KEY" in pem

    def test_get_public_key_pem_not_enabled(self):
        """get_public_key_pem raises when transport encryption disabled."""
        from app.core.security import CryptoService
        import base64
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.data_encryption_key = key
            mock_settings.return_value.transport_encryption_enabled = False
            crypto = CryptoService(encryption_key=key)
            with pytest.raises(RuntimeError, match="not enabled"):
                crypto.get_public_key_pem()

    def test_decrypt_transport_round_trip(self):
        """Full RSA+AES hybrid encryption round trip."""
        from app.core.security import CryptoService
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()

        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.data_encryption_key = key
            mock_settings.return_value.transport_encryption_enabled = True
            crypto = CryptoService(encryption_key=key)

            # Simulate frontend encryption
            plaintext = "sensitive data"
            aes_key = os.urandom(32)
            nonce = os.urandom(12)

            # Encrypt AES key with RSA public key
            encrypted_aes_key = crypto._rsa_public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            # Encrypt data with AES-GCM
            aesgcm = AESGCM(aes_key)
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

            # Combine: encrypted_aes_key (256) + nonce (12) + ciphertext
            payload = base64.b64encode(encrypted_aes_key + nonce + ciphertext).decode()

            # Decrypt
            result = crypto.decrypt_transport(payload)
            assert result == plaintext

    def test_decrypt_transport_not_enabled(self):
        """decrypt_transport raises when transport disabled."""
        from app.core.security import CryptoService
        import base64
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.data_encryption_key = key
            mock_settings.return_value.transport_encryption_enabled = False
            crypto = CryptoService(encryption_key=key)
            with pytest.raises(RuntimeError, match="not enabled"):
                crypto.decrypt_transport("invalid")

    def test_decrypt_transport_invalid_data(self):
        """decrypt_transport raises ValueError on corrupt data."""
        from app.core.security import CryptoService
        import base64
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.data_encryption_key = key
            mock_settings.return_value.transport_encryption_enabled = True
            crypto = CryptoService(encryption_key=key)
            with pytest.raises(ValueError, match="Transport decryption failed"):
                crypto.decrypt_transport(base64.b64encode(b"invalid" * 50).decode())


class TestTokenEdgeCases:
    """Tests for JWT token edge cases."""

    def test_verify_expired_token(self):
        """Expired token raises JWTError."""
        from app.core.security import create_access_token, verify_token
        from jose import JWTError
        from datetime import timedelta
        token = create_access_token("user_1", expires_delta=timedelta(seconds=-1))
        with pytest.raises(JWTError):
            verify_token(token)

    def test_verify_token_wrong_type(self):
        """Wrong token type raises JWTError."""
        from app.core.security import create_access_token, verify_token
        from jose import JWTError
        token = create_access_token("user_1")
        with pytest.raises(JWTError):
            verify_token(token, token_type="refresh")


class TestPasswordAsync:
    """Tests for verify_password_async."""

    @pytest.mark.asyncio
    async def test_verify_password_async_correct(self):
        from app.core.security import hash_password, verify_password_async
        hashed = hash_password("my_password")
        result = await verify_password_async("my_password", hashed)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_password_async_wrong(self):
        from app.core.security import hash_password, verify_password_async
        hashed = hash_password("my_password")
        result = await verify_password_async("wrong", hashed)
        assert result is False


class TestCryptoSingleton:
    def test_get_crypto_service_singleton(self):
        from app.core.security import get_crypto_service, CryptoService
        import app.core.security as mod
        import base64

        old = mod._crypto_service
        mod._crypto_service = None
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value.data_encryption_key = key
            mock_settings.return_value.transport_encryption_enabled = False
            mock_settings.return_value.jwt_secret = "test"
            mock_settings.return_value.jwt_algorithm = "HS256"
            mock_settings.return_value.jwt_access_token_expire_minutes = 30
            mock_settings.return_value.jwt_refresh_token_expire_days = 7

            svc = get_crypto_service()
            assert svc is not None
            svc2 = get_crypto_service()
            assert svc is svc2
        mod._crypto_service = old
