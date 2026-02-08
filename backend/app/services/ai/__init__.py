"""
AI Client Module.

Provides a unified interface for multiple AI providers:
- DeepSeek
- Qwen (Alibaba)
- Zhipu GLM
- MiniMax
- Kimi (Moonshot)
- OpenAI
- Google Gemini
- xAI Grok
- Custom OpenAI-compatible endpoints

Usage:
    from app.services.ai import get_ai_client, AIProvider

    # Get client for a specific model
    client = get_ai_client("deepseek:deepseek-chat", api_key="...")
    response = await client.generate(system_prompt, user_prompt)

    # Or use the factory directly
    from app.services.ai import AIClientFactory
    client = AIClientFactory.create("qwen:qwen-plus", api_key="...")
"""

from .base import (
    AIProvider,
    AIClientConfig,
    AIClientError,
    AIAuthenticationError,
    AIRateLimitError,
    AIConnectionError,
    AIInvalidRequestError,
    AIResponse,
    BaseAIClient,
    ModelInfo,
    PRESET_PROVIDER_MODELS,
    get_preset_models,
    model_info_to_dict,
    preset_models_json,
)
from .credentials import resolve_provider_credentials
from .factory import AIClientFactory, get_ai_client, register_custom_model

__all__ = [
    "resolve_provider_credentials",
    # Base classes and types
    "AIProvider",
    "AIClientConfig",
    "AIClientError",
    "AIAuthenticationError",
    "AIRateLimitError",
    "AIConnectionError",
    "AIInvalidRequestError",
    "AIResponse",
    "BaseAIClient",
    "ModelInfo",

    # Preset model registry (for populating new provider configs)
    "PRESET_PROVIDER_MODELS",
    "get_preset_models",
    "model_info_to_dict",
    "preset_models_json",

    # Factory
    "AIClientFactory",
    "get_ai_client",
    "register_custom_model",
]
