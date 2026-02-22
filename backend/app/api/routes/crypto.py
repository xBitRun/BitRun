"""Crypto routes - Encryption key management for transport security"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.config import get_settings
from ...core.dependencies import CryptoDep

router = APIRouter(prefix="/crypto", tags=["Security"])


class PublicKeyResponse(BaseModel):
    """RSA public key response"""

    public_key: str
    algorithm: str = "RSA-OAEP"
    key_size: int = 2048


class DecryptRequest(BaseModel):
    """Request to decrypt transport-encrypted data"""

    encrypted_data: str


class DecryptResponse(BaseModel):
    """Decrypted data response"""

    decrypted: str


@router.get("/public-key", response_model=PublicKeyResponse)
async def get_public_key(crypto: CryptoDep):
    """
    Get RSA public key for transport encryption.

    The frontend should use this key to encrypt sensitive data
    (like API keys) before sending to the server.

    Only available when TRANSPORT_ENCRYPTION_ENABLED=true.
    """
    settings = get_settings()

    if not settings.transport_encryption_enabled:
        raise HTTPException(
            status_code=400, detail="Transport encryption is not enabled"
        )

    try:
        public_key = crypto.get_public_key_pem()
        return PublicKeyResponse(public_key=public_key)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decrypt", response_model=DecryptResponse)
async def decrypt_data(request: DecryptRequest, crypto: CryptoDep):
    """
    Decrypt transport-encrypted data.

    This endpoint is used internally by the server to decrypt
    data that was encrypted by the frontend.

    Expected encryption format:
    - RSA-OAEP encrypted AES key (256 bytes)
    - AES-GCM nonce (12 bytes)
    - AES-GCM ciphertext
    """
    settings = get_settings()

    if not settings.transport_encryption_enabled:
        raise HTTPException(
            status_code=400, detail="Transport encryption is not enabled"
        )

    try:
        decrypted = crypto.decrypt_transport(request.encrypted_data)
        return DecryptResponse(decrypted=decrypted)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
