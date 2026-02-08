"""AI Provider configuration routes"""

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from ...core.dependencies import CryptoDep, CurrentUserDep, DbSessionDep, RateLimitApiDep
from ...db.models import AIProviderConfigDB
from ...services.ai import AIClientFactory, AIProvider, preset_models_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["AI Providers"])


# ==================== Constants ====================

# Predefined providers with their default configurations
PRESET_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "api_format": "openai",
        "website_url": "https://platform.deepseek.com/",
    },
    "qwen": {
        "name": "Alibaba Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_format": "openai",
        "website_url": "https://dashscope.console.aliyun.com/",
    },
    "zhipu": {
        "name": "Zhipu GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_format": "openai",
        "website_url": "https://open.bigmodel.cn/",
    },
    "minimax": {
        "name": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "api_format": "openai",
        "website_url": "https://platform.minimaxi.com/",
    },
    "kimi": {
        "name": "Moonshot Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "api_format": "openai",
        "website_url": "https://platform.moonshot.cn/",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "",
        "api_format": "openai",
        "website_url": "https://platform.openai.com/",
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "",
        "api_format": "openai",
        "website_url": "https://aistudio.google.com/",
    },
    "grok": {
        "name": "xAI Grok",
        "base_url": "https://api.x.ai/v1",
        "api_format": "openai",
        "website_url": "https://console.x.ai/",
    },
    "custom": {
        "name": "Custom Provider",
        "base_url": "",
        "api_format": "openai",
        "website_url": "",
    },
}

# API format options
API_FORMATS = ["openai", "custom"]


# ==================== Request/Response Models ====================

class ProviderCreate(BaseModel):
    """Create provider configuration request"""
    provider_type: str = Field(..., description="Provider type: deepseek, qwen, zhipu, minimax, kimi, etc.")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    note: Optional[str] = Field(None, max_length=500, description="Notes")
    website_url: Optional[str] = Field(None, max_length=500, description="Website URL")
    api_key: str = Field(..., min_length=1, description="API key")
    base_url: Optional[str] = Field(None, max_length=500, description="API base URL")
    api_format: str = Field(default="openai", description="API format: openai, custom")


class ProviderUpdate(BaseModel):
    """Update provider configuration request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    note: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, min_length=1)
    base_url: Optional[str] = Field(None, max_length=500)
    api_format: Optional[str] = Field(None)
    is_enabled: Optional[bool] = Field(None)


class ProviderResponse(BaseModel):
    """Provider configuration response (no API key)"""
    id: str
    provider_type: str
    name: str
    note: Optional[str] = None
    website_url: Optional[str] = None
    base_url: Optional[str] = None
    api_format: str
    is_enabled: bool
    has_api_key: bool
    created_at: str
    updated_at: str


class PresetProviderInfo(BaseModel):
    """Preset provider information"""
    id: str
    name: str
    base_url: str
    api_format: str
    website_url: str


class TestConnectionRequest(BaseModel):
    """Test connection request"""
    api_key: Optional[str] = Field(None, description="Optional API key to test with (uses saved key if not provided)")


class TestConnectionResponse(BaseModel):
    """Test connection response"""
    success: bool
    message: str


class ProviderModelItem(BaseModel):
    """A single model configuration within a provider"""
    id: str = Field(..., description="Model ID sent to the API (e.g. deepseek-chat)")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="Short description")
    context_window: int = Field(default=128000)
    max_output_tokens: int = Field(default=4096)
    supports_json_mode: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    cost_per_1k_input: float = Field(default=0.0)
    cost_per_1k_output: float = Field(default=0.0)


class UpdateProviderModelsRequest(BaseModel):
    """Replace the whole model list for a provider"""
    models: list[ProviderModelItem]


class AddProviderModelRequest(BaseModel):
    """Add a single model to a provider"""
    id: str = Field(..., description="Model ID sent to the API")
    name: str = Field(..., description="Display name")
    description: str = Field(default="")
    context_window: int = Field(default=128000)
    max_output_tokens: int = Field(default=4096)
    supports_json_mode: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    cost_per_1k_input: float = Field(default=0.0)
    cost_per_1k_output: float = Field(default=0.0)


# ==================== Helpers ====================

def _provider_to_response(p: AIProviderConfigDB) -> ProviderResponse:
    """Convert a provider DB row to response model."""
    return ProviderResponse(
        id=str(p.id),
        provider_type=p.provider_type,
        name=p.name,
        note=p.note,
        website_url=p.website_url,
        base_url=p.base_url,
        api_format=p.api_format,
        is_enabled=p.is_enabled,
        has_api_key=p.encrypted_api_key is not None,
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
    )


def _get_models_list(provider: AIProviderConfigDB) -> list[dict]:
    """Parse models JSON from provider row. Returns list of dicts."""
    if not provider.models:
        return []
    try:
        return json.loads(provider.models)
    except (json.JSONDecodeError, TypeError):
        return []


def _set_models_list(provider: AIProviderConfigDB, models: list[dict]) -> None:
    """Serialize models list to JSON and store on provider row."""
    provider.models = json.dumps(models, ensure_ascii=False)


# ==================== Routes ====================

@router.get("/presets", response_model=list[PresetProviderInfo])
async def list_preset_providers(
    user_id: CurrentUserDep,
):
    """
    List all preset provider configurations.

    These are predefined providers with their default configurations.
    """
    return [
        PresetProviderInfo(
            id=provider_id,
            name=info["name"],
            base_url=info["base_url"],
            api_format=info["api_format"],
            website_url=info["website_url"],
        )
        for provider_id, info in PRESET_PROVIDERS.items()
    ]


@router.get("/formats")
async def list_api_formats(
    user_id: CurrentUserDep,
):
    """List supported API formats."""
    return {
        "formats": [
            {"id": "openai", "name": "OpenAI Chat Completions"},
            {"id": "custom", "name": "Custom"},
        ]
    }


@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    List all provider configurations for the current user.
    """
    result = await db.execute(
        select(AIProviderConfigDB)
        .where(AIProviderConfigDB.user_id == uuid.UUID(user_id))
        .order_by(AIProviderConfigDB.created_at.desc())
    )
    providers = result.scalars().all()

    return [_provider_to_response(p) for p in providers]


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    data: ProviderCreate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    crypto: CryptoDep,
):
    """
    Create a new provider configuration.

    Models are pre-populated from preset defaults for the given provider type.
    """
    # Validate provider type
    if data.provider_type not in PRESET_PROVIDERS and data.provider_type != "custom":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider type: {data.provider_type}"
        )

    # Validate API format
    if data.api_format not in API_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown API format: {data.api_format}"
        )

    # Get default base_url from preset if not provided
    base_url = data.base_url
    if not base_url and data.provider_type in PRESET_PROVIDERS:
        base_url = PRESET_PROVIDERS[data.provider_type]["base_url"]

    # Encrypt API key
    encrypted_api_key = crypto.encrypt(data.api_key)

    # Pre-populate models from presets
    models_json = preset_models_json(data.provider_type)

    # Create provider config
    provider = AIProviderConfigDB(
        user_id=uuid.UUID(user_id),
        provider_type=data.provider_type,
        name=data.name,
        note=data.note,
        website_url=data.website_url,
        encrypted_api_key=encrypted_api_key,
        base_url=base_url,
        api_format=data.api_format,
        is_enabled=True,
        models=models_json,
    )

    db.add(provider)
    await db.commit()
    await db.refresh(provider)

    logger.info(f"Created provider config: {provider.name} ({provider.provider_type}) for user {user_id}")

    return _provider_to_response(provider)


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Get a specific provider configuration.
    """
    result = await db.execute(
        select(AIProviderConfigDB)
        .where(
            AIProviderConfigDB.id == uuid.UUID(provider_id),
            AIProviderConfigDB.user_id == uuid.UUID(user_id)
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    return _provider_to_response(provider)


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    data: ProviderUpdate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    crypto: CryptoDep,
):
    """
    Update a provider configuration.
    """
    result = await db.execute(
        select(AIProviderConfigDB)
        .where(
            AIProviderConfigDB.id == uuid.UUID(provider_id),
            AIProviderConfigDB.user_id == uuid.UUID(user_id)
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    # Update fields
    if data.name is not None:
        provider.name = data.name
    if data.note is not None:
        provider.note = data.note
    if data.website_url is not None:
        provider.website_url = data.website_url
    if data.base_url is not None:
        provider.base_url = data.base_url
    if data.api_format is not None:
        if data.api_format not in API_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown API format: {data.api_format}"
            )
        provider.api_format = data.api_format
    if data.is_enabled is not None:
        provider.is_enabled = data.is_enabled
    if data.api_key is not None:
        provider.encrypted_api_key = crypto.encrypt(data.api_key)

    await db.commit()
    await db.refresh(provider)

    logger.info(f"Updated provider config: {provider.name} ({provider.id})")

    return _provider_to_response(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Delete a provider configuration.
    """
    result = await db.execute(
        select(AIProviderConfigDB)
        .where(
            AIProviderConfigDB.id == uuid.UUID(provider_id),
            AIProviderConfigDB.user_id == uuid.UUID(user_id)
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    await db.delete(provider)
    await db.commit()

    logger.info(f"Deleted provider config: {provider.name} ({provider.id})")


@router.post("/{provider_id}/test", response_model=TestConnectionResponse)
async def test_provider_connection(
    provider_id: str,
    data: TestConnectionRequest,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    crypto: CryptoDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Test connection to a provider.

    Optionally provide an API key to test with (uses saved key if not provided).
    """
    result = await db.execute(
        select(AIProviderConfigDB)
        .where(
            AIProviderConfigDB.id == uuid.UUID(provider_id),
            AIProviderConfigDB.user_id == uuid.UUID(user_id)
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    # Get API key
    api_key = data.api_key
    if not api_key:
        if not provider.encrypted_api_key:
            return TestConnectionResponse(
                success=False,
                message="No API key configured"
            )
        api_key = crypto.decrypt(provider.encrypted_api_key)

    # Test connection based on provider type
    try:
        # Test OpenAI-compatible API (all supported providers use this format)
        import httpx
        async with httpx.AsyncClient() as http_client:
            base_url = provider.base_url or "https://api.deepseek.com"
            response = await http_client.get(
                f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
            success = response.status_code == 200

        if success:
            return TestConnectionResponse(
                success=True,
                message="Connection successful"
            )
        else:
            return TestConnectionResponse(
                success=False,
                message="Connection failed - invalid response"
            )
    except Exception as e:
        logger.error(f"Connection test failed for provider {provider.id}: {e}")
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


# ==================== Provider Model CRUD ====================

@router.get("/{provider_id}/models", response_model=list[ProviderModelItem])
async def list_provider_models(
    provider_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    List all models configured for a specific provider.
    """
    result = await db.execute(
        select(AIProviderConfigDB)
        .where(
            AIProviderConfigDB.id == uuid.UUID(provider_id),
            AIProviderConfigDB.user_id == uuid.UUID(user_id)
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    return [ProviderModelItem(**m) for m in _get_models_list(provider)]


@router.put("/{provider_id}/models", response_model=list[ProviderModelItem])
async def replace_provider_models(
    provider_id: str,
    data: UpdateProviderModelsRequest,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Replace the entire model list for a provider.
    """
    result = await db.execute(
        select(AIProviderConfigDB)
        .where(
            AIProviderConfigDB.id == uuid.UUID(provider_id),
            AIProviderConfigDB.user_id == uuid.UUID(user_id)
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    models = [m.model_dump() for m in data.models]
    _set_models_list(provider, models)

    await db.commit()
    await db.refresh(provider)

    logger.info(f"Replaced model list for provider {provider.id} ({len(models)} models)")

    return [ProviderModelItem(**m) for m in _get_models_list(provider)]


@router.post("/{provider_id}/models", response_model=ProviderModelItem, status_code=status.HTTP_201_CREATED)
async def add_provider_model(
    provider_id: str,
    data: AddProviderModelRequest,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Add a single model to a provider's model list.
    """
    result = await db.execute(
        select(AIProviderConfigDB)
        .where(
            AIProviderConfigDB.id == uuid.UUID(provider_id),
            AIProviderConfigDB.user_id == uuid.UUID(user_id)
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    models = _get_models_list(provider)

    # Check for duplicate
    if any(m.get("id") == data.id for m in models):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model '{data.id}' already exists in this provider"
        )

    new_model = data.model_dump()
    models.append(new_model)
    _set_models_list(provider, models)

    await db.commit()
    await db.refresh(provider)

    logger.info(f"Added model '{data.id}' to provider {provider.id}")

    return ProviderModelItem(**new_model)


@router.delete("/{provider_id}/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_model(
    provider_id: str,
    model_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Delete a single model from a provider's model list.
    """
    result = await db.execute(
        select(AIProviderConfigDB)
        .where(
            AIProviderConfigDB.id == uuid.UUID(provider_id),
            AIProviderConfigDB.user_id == uuid.UUID(user_id)
        )
    )
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider configuration not found"
        )

    models = _get_models_list(provider)
    original_len = len(models)
    models = [m for m in models if m.get("id") != model_id]

    if len(models) == original_len:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found in this provider"
        )

    _set_models_list(provider, models)

    await db.commit()

    logger.info(f"Deleted model '{model_id}' from provider {provider.id}")
