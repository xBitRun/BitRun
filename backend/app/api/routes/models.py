"""AI Model routes - models are read from user's provider configurations."""

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from ...core.dependencies import (
    CryptoDep,
    CurrentUserDep,
    DbSessionDep,
    RateLimitApiDep,
)
from ...db.models import AIProviderConfigDB
from ...services.ai import (
    AIProvider,
    AIClientError,
    AIClientFactory,
    AIAuthenticationError,
    AIConnectionError,
    AIRateLimitError,
)

router = APIRouter(prefix="/models", tags=["AI Models"])
logger = logging.getLogger(__name__)


# ==================== Request/Response Models ====================


class ModelInfoResponse(BaseModel):
    """AI model information"""

    id: str  # Full ID (provider:model_id)
    provider: str
    name: str
    description: str = ""
    context_window: int = 128000
    max_output_tokens: int = 4096
    supports_json_mode: bool = False
    supports_vision: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


class ProviderResponse(BaseModel):
    """AI provider information"""

    id: str
    name: str
    configured: bool  # Whether API key is configured


class TestModelRequest(BaseModel):
    """Request to test a model connection"""

    model_id: str = Field(..., description="Full model ID (provider:model_id)")
    api_key: Optional[str] = Field(
        default=None, description="Optional API key override"
    )


# ==================== Helpers ====================

_PROVIDER_DISPLAY_NAMES = {
    AIProvider.DEEPSEEK: "DeepSeek",
    AIProvider.QWEN: "Alibaba Qwen",
    AIProvider.ZHIPU: "Zhipu GLM",
    AIProvider.MINIMAX: "MiniMax",
    AIProvider.KIMI: "Moonshot Kimi",
    AIProvider.OPENAI: "OpenAI",
    AIProvider.GEMINI: "Google Gemini",
    AIProvider.GROK: "xAI Grok",
    AIProvider.CUSTOM: "Custom (OpenAI-compatible)",
}


def _parse_provider_models(provider: AIProviderConfigDB) -> list[ModelInfoResponse]:
    """Parse models JSON from a provider config row into response objects."""
    if not provider.models:
        return []
    try:
        raw = json.loads(provider.models)
    except (json.JSONDecodeError, TypeError):
        return []
    results = []
    for m in raw:
        model_id = m.get("id", "")
        if not model_id:
            continue
        full_id = f"{provider.provider_type}:{model_id}"
        results.append(
            ModelInfoResponse(
                id=full_id,
                provider=provider.provider_type,
                name=m.get("name", model_id),
                description=m.get("description", ""),
                context_window=m.get("context_window", 128000),
                max_output_tokens=m.get("max_output_tokens", 4096),
                supports_json_mode=m.get("supports_json_mode", False),
                supports_vision=m.get("supports_vision", False),
                cost_per_1k_input=m.get("cost_per_1k_input", 0.0),
                cost_per_1k_output=m.get("cost_per_1k_output", 0.0),
            )
        )
    return results


# ==================== Routes ====================


@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers(
    user_id: CurrentUserDep,
    db: DbSessionDep,
):
    """
    List all supported AI providers.

    Returns whether each provider has API key configured (from DB for current user).
    """
    subq = (
        select(AIProviderConfigDB.provider_type)
        .where(
            AIProviderConfigDB.user_id == uuid.UUID(user_id),
            AIProviderConfigDB.is_enabled.is_(True),
            AIProviderConfigDB.encrypted_api_key.isnot(None),
        )
        .distinct()
    )
    rows = await db.execute(subq)
    configured_types = {r.lower() for r in rows.scalars().all()}

    result = []
    for provider in AIProvider:
        name = _PROVIDER_DISPLAY_NAMES.get(provider, provider.value)
        configured = (provider.value.lower() in configured_types) or (
            provider == AIProvider.CUSTOM
        )
        result.append(
            ProviderResponse(
                id=provider.value,
                name=name,
                configured=configured,
            )
        )

    return result


@router.get("", response_model=list[ModelInfoResponse])
async def list_models(
    user_id: CurrentUserDep,
    db: DbSessionDep,
    provider: Optional[str] = None,
):
    """
    List all available AI models from user's provider configurations.

    Optionally filter by provider type.
    """
    query = select(AIProviderConfigDB).where(
        AIProviderConfigDB.user_id == uuid.UUID(user_id),
        AIProviderConfigDB.is_enabled.is_(True),
    )
    if provider:
        query = query.where(AIProviderConfigDB.provider_type == provider)

    result = await db.execute(query.order_by(AIProviderConfigDB.created_at.desc()))
    providers = result.scalars().all()

    models: list[ModelInfoResponse] = []
    for p in providers:
        models.extend(_parse_provider_models(p))
    return models


@router.get("/{model_id:path}", response_model=ModelInfoResponse)
async def get_model(
    model_id: str,
    user_id: CurrentUserDep,
    db: DbSessionDep,
):
    """
    Get information about a specific model.

    Model ID format: provider:model_id (e.g., deepseek:deepseek-chat)
    """
    if ":" not in model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model ID format: {model_id}. Expected 'provider:model_id'",
        )

    provider_type = model_id.split(":", 1)[0]

    result = await db.execute(
        select(AIProviderConfigDB).where(
            AIProviderConfigDB.user_id == uuid.UUID(user_id),
            AIProviderConfigDB.provider_type == provider_type,
            AIProviderConfigDB.is_enabled.is_(True),
        )
    )
    providers = result.scalars().all()

    for p in providers:
        for m in _parse_provider_models(p):
            if m.id == model_id:
                return m

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Model not found: {model_id}"
    )


def _model_test_error_code(e: Exception) -> str:
    """Map exception to a stable error_code for i18n on the frontend."""
    if isinstance(e, AIAuthenticationError):
        return "auth_error"
    if isinstance(e, AIConnectionError):
        return "connection_error"
    if isinstance(e, AIRateLimitError):
        return "rate_limit"
    if isinstance(e, AIClientError):
        msg = (e.message if hasattr(e, "message") else str(e)).lower()
        if "no api key" in msg or "api key" in msg and "configure" in msg:
            return "no_api_key"
        if "base_url" in msg and "required" in msg:
            return "no_base_url"
        if "model" in msg and (
            "not found" in msg or "404" in msg or "invalid" in msg or "not exist" in msg
        ):
            return "model_not_found"
        return "api_error"
    return "unknown"


@router.post("/test")
async def test_model_connection(
    data: TestModelRequest,
    user_id: CurrentUserDep,
    db: DbSessionDep,
    crypto: CryptoDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Test connection to an AI model.

    Uses the current user's saved API key for the model's provider (if any).
    Optionally provide an API key in the request to override.

    On failure, returns error_code for frontend i18n.
    """
    api_key = data.api_key
    base_url = None

    if not api_key and ":" in data.model_id:
        provider_type = data.model_id.split(":", 1)[0]
        result = await db.execute(
            select(AIProviderConfigDB)
            .where(
                AIProviderConfigDB.user_id == uuid.UUID(user_id),
                AIProviderConfigDB.provider_type == provider_type,
                AIProviderConfigDB.is_enabled.is_(True),
            )
            .order_by(AIProviderConfigDB.created_at.desc())
            .limit(1)
        )
        provider = result.scalar_one_or_none()
        if provider and provider.encrypted_api_key:
            api_key = crypto.decrypt(provider.encrypted_api_key)
            if provider.base_url:
                base_url = provider.base_url.rstrip("/")

    try:
        create_kwargs = {
            "model_full_id": data.model_id,
            "api_key": api_key,
        }
        if base_url is not None:
            create_kwargs["base_url"] = base_url
        client = AIClientFactory.create(**create_kwargs)

        success = await client.test_connection()

        return {
            "model_id": data.model_id,
            "success": success,
            "message": "Connection successful" if success else "Connection failed",
        }
    except Exception as e:
        error_code = _model_test_error_code(e)
        return {
            "model_id": data.model_id,
            "success": False,
            "message": str(e),
            "error_code": error_code,
        }
