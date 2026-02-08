"""
AI Client Factory.

Creates and manages AI client instances for different providers.
Supports dynamic model registration for custom endpoints.
"""

import logging
from typing import Optional

from .base import (
    AIClientConfig,
    AIClientError,
    AIProvider,
    BaseAIClient,
    ModelInfo,
)

logger = logging.getLogger(__name__)

# Client class registry
_CLIENT_CLASSES: dict[AIProvider, type[BaseAIClient]] = {}

# Custom models registry (for user-defined models)
_CUSTOM_MODELS: dict[str, ModelInfo] = {}

# Client instance cache (for singleton patterns if needed)
_CLIENT_CACHE: dict[str, BaseAIClient] = {}


def _ensure_clients_registered():
    """Ensure all client classes are registered. Called lazily."""
    if _CLIENT_CLASSES:
        return

    # Import clients lazily to avoid circular imports and hard dependencies

    # DeepSeek
    try:
        from .deepseek_client import DeepSeekClient
        _CLIENT_CLASSES[AIProvider.DEEPSEEK] = DeepSeekClient
    except Exception:
        pass

    # Qwen (Alibaba)
    try:
        from .qwen_client import QwenClient
        _CLIENT_CLASSES[AIProvider.QWEN] = QwenClient
    except Exception:
        pass

    # Zhipu (GLM)
    try:
        from .zhipu_client import ZhipuClient
        _CLIENT_CLASSES[AIProvider.ZHIPU] = ZhipuClient
    except Exception:
        pass

    # MiniMax
    try:
        from .minimax_client import MiniMaxClient
        _CLIENT_CLASSES[AIProvider.MINIMAX] = MiniMaxClient
    except Exception:
        pass

    # Kimi (Moonshot)
    try:
        from .kimi_client import KimiClient
        _CLIENT_CLASSES[AIProvider.KIMI] = KimiClient
    except Exception:
        pass

    # OpenAI (GPT)
    try:
        from .openai_client import OpenAIClient
        _CLIENT_CLASSES[AIProvider.OPENAI] = OpenAIClient
    except Exception:
        pass

    # Google Gemini
    try:
        from .gemini_client import GeminiClient
        _CLIENT_CLASSES[AIProvider.GEMINI] = GeminiClient
    except Exception:
        pass

    # xAI Grok
    try:
        from .grok_client import GrokClient
        _CLIENT_CLASSES[AIProvider.GROK] = GrokClient
    except Exception:
        pass

    # Custom
    try:
        from .custom_client import CustomOpenAIClient
        _CLIENT_CLASSES[AIProvider.CUSTOM] = CustomOpenAIClient
    except Exception:
        pass


def register_custom_model(
    model_id: str,
    name: str,
    base_url: str,
    description: str = "",
    context_window: int = 32000,
    max_output_tokens: int = 4096,
    supports_json_mode: bool = False,
) -> ModelInfo:
    """
    Register a custom OpenAI-compatible model.

    Args:
        model_id: Model identifier (used in API calls)
        name: Display name
        base_url: API endpoint URL
        description: Model description
        context_window: Max context tokens
        max_output_tokens: Max output tokens
        supports_json_mode: Whether the endpoint supports JSON mode

    Returns:
        ModelInfo for the registered model
    """
    full_id = f"custom:{model_id}"

    model_info = ModelInfo(
        id=model_id,
        provider=AIProvider.CUSTOM,
        name=name,
        description=description,
        context_window=context_window,
        max_output_tokens=max_output_tokens,
        supports_json_mode=supports_json_mode,
    )

    # Store custom metadata
    model_info.base_url = base_url  # type: ignore

    _CUSTOM_MODELS[full_id] = model_info
    logger.info(f"Registered custom model: {full_id} at {base_url}")

    return model_info


def get_all_models() -> list[ModelInfo]:
    """Get all custom-registered models (legacy helper)."""
    return list(_CUSTOM_MODELS.values())


class AIClientFactory:
    """
    Factory for creating AI client instances.

    Supports:
    - Creating clients by model full ID (provider:model_id)
    - Creating clients by provider with custom config
    - Automatic API key resolution from settings
    - Custom model registration

    Usage:
        # Create client by model ID
        client = AIClientFactory.create("deepseek:deepseek-chat")

        # Create with custom config
        client = AIClientFactory.create_with_config(
            AIProvider.QWEN,
            AIClientConfig(api_key="...", model="qwen-plus")
        )
    """

    @staticmethod
    def create(
        model_full_id: str,
        api_key: Optional[str] = None,
        **kwargs,
    ) -> BaseAIClient:
        """
        Create an AI client by model full ID.

        Args:
            model_full_id: Full model ID in format "provider:model_id"
                          e.g., "deepseek:deepseek-chat"
            api_key: Optional API key (uses settings if not provided)
            **kwargs: Additional config options (temperature, max_tokens, etc.)

        Returns:
            Configured AI client instance

        Raises:
            AIClientError: If model not found or client creation fails
        """
        _ensure_clients_registered()

        # Parse model ID
        if ":" not in model_full_id:
            raise AIClientError(f"Invalid model ID format: {model_full_id}. Expected 'provider:model_id'")

        provider_str, model_id = model_full_id.split(":", 1)

        try:
            provider = AIProvider(provider_str)
        except ValueError:
            raise AIClientError(f"Unknown provider: {provider_str}")

        # Check custom models registry (for legacy register_custom_model usage)
        custom_model_info = _CUSTOM_MODELS.get(model_full_id)

        # Resolve API key
        resolved_api_key = api_key or AIClientFactory._get_api_key(provider)

        # Build config -- model_id is passed directly to the provider API
        config = AIClientConfig(
            api_key=resolved_api_key,
            model=model_id,
            max_tokens=kwargs.get("max_tokens", custom_model_info.max_output_tokens if custom_model_info else 4096),
            temperature=kwargs.get("temperature", 0.7),
            timeout=kwargs.get("timeout", 120),
        )

        # Handle custom base_url
        if custom_model_info and hasattr(custom_model_info, 'base_url'):
            config.base_url = custom_model_info.base_url  # type: ignore
        elif kwargs.get("base_url"):
            config.base_url = kwargs["base_url"]

        return AIClientFactory.create_with_config(provider, config)

    @staticmethod
    def create_with_config(
        provider: AIProvider,
        config: AIClientConfig,
    ) -> BaseAIClient:
        """
        Create an AI client with explicit configuration.

        Args:
            provider: AI provider type
            config: Client configuration

        Returns:
            Configured AI client instance
        """
        _ensure_clients_registered()

        if provider not in _CLIENT_CLASSES:
            raise AIClientError(
                f"No client implementation for provider: {provider.value}. "
                f"Available providers: {[p.value for p in _CLIENT_CLASSES.keys()]}"
            )

        client_class = _CLIENT_CLASSES[provider]
        return client_class(config)

    @staticmethod
    def _get_api_key(provider: AIProvider) -> str:
        """
        Get API key for a provider. No longer reads from env/settings.
        Callers must pass api_key (e.g. from resolve_provider_credentials).
        CUSTOM may use empty key for local endpoints.
        """
        if provider == AIProvider.CUSTOM:
            return ""
        raise AIClientError(
            f"No API key provided for {provider.value}. "
            "Configure the provider in the app (Models / Providers) and ensure API key is set, "
            "or pass api_key when creating the client."
        )

    @staticmethod
    def get_supported_providers() -> list[AIProvider]:
        """Get list of providers with registered client implementations."""
        _ensure_clients_registered()
        return list(_CLIENT_CLASSES.keys())


# Convenience function
def get_ai_client(
    model_full_id: str,
    api_key: Optional[str] = None,
    **kwargs,
) -> BaseAIClient:
    """
    Convenience function to get an AI client.

    Args:
        model_full_id: Full model ID (e.g., "deepseek:deepseek-chat")
        api_key: Optional API key
        **kwargs: Additional config options

    Returns:
        Configured AI client instance
    """
    return AIClientFactory.create(model_full_id, api_key, **kwargs)


def clear_client_cache():
    """Clear the client cache. Useful for testing or reconfiguration."""
    _CLIENT_CACHE.clear()
