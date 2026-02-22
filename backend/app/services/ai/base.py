"""
AI Client Base Classes and Model Configuration.

Defines the abstract interface for AI clients and model configuration system
that supports multiple providers (DeepSeek, Qwen, Zhipu, MiniMax, Kimi, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class AIProvider(str, Enum):
    """Supported AI providers"""

    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    ZHIPU = "zhipu"  # GLM models
    MINIMAX = "minimax"
    KIMI = "kimi"
    OPENAI = "openai"  # OpenAI GPT models
    GEMINI = "gemini"  # Google Gemini models
    GROK = "grok"  # xAI Grok models
    CUSTOM = "custom"  # OpenAI-compatible custom endpoints


@dataclass
class ModelInfo:
    """Information about a specific AI model"""

    id: str  # Model identifier (e.g., "claude-sonnet-4-5-20250514")
    provider: AIProvider
    name: str  # Display name (e.g., "Claude Sonnet 4.5")
    description: str = ""
    context_window: int = 128000  # Max context tokens
    max_output_tokens: int = 8192  # Max output tokens
    supports_json_mode: bool = False  # Native JSON mode support
    supports_vision: bool = False  # Image/vision support
    cost_per_1k_input: float = 0.0  # Cost per 1K input tokens (USD)
    cost_per_1k_output: float = 0.0  # Cost per 1K output tokens (USD)

    @property
    def full_id(self) -> str:
        """Full model identifier including provider"""
        return f"{self.provider.value}:{self.id}"


@dataclass
class AIClientConfig:
    """Configuration for an AI client instance"""

    api_key: str
    model: str
    base_url: Optional[str] = None  # For custom endpoints
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 120
    extra_params: dict = field(default_factory=dict)  # Provider-specific params


@dataclass
class AIResponse:
    """Standardized response from AI clients"""

    content: str
    model: str
    provider: AIProvider
    tokens_used: int
    input_tokens: int
    output_tokens: int
    stop_reason: str = ""
    latency_ms: int = 0
    raw_response: Optional[Any] = None  # Original response object


class AIClientError(Exception):
    """Base error for AI client operations"""

    def __init__(self, message: str, provider: Optional[AIProvider] = None):
        self.message = message
        self.provider = provider
        super().__init__(message)


class AIAuthenticationError(AIClientError):
    """Authentication failed with provider"""

    pass


class AIRateLimitError(AIClientError):
    """Rate limit exceeded"""

    pass


class AIConnectionError(AIClientError):
    """Connection to provider failed"""

    pass


class AIInvalidRequestError(AIClientError):
    """Invalid request to provider"""

    pass


class BaseAIClient(ABC):
    """
    Abstract base class for AI clients.

    All AI provider adapters must implement this interface to ensure
    consistent behavior across different providers.

    Usage:
        class MyClient(BaseAIClient):
            async def generate(self, ...) -> AIResponse: ...

        client = MyClient(config)
        response = await client.generate(system_prompt, user_prompt)
    """

    def __init__(self, config: AIClientConfig):
        """
        Initialize the AI client.

        Args:
            config: Client configuration including API key, model, etc.
        """
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration. Override for provider-specific validation."""
        if not self.config.api_key:
            raise AIClientError(f"API key is required for {self.provider.value}")

    @property
    @abstractmethod
    def provider(self) -> AIProvider:
        """Return the provider type for this client"""
        pass

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
    ) -> AIResponse:
        """
        Generate a response from the AI model.

        Args:
            system_prompt: System instructions for the model
            user_prompt: User message/query
            json_mode: If True, guide/force model to output JSON

        Returns:
            AIResponse with content and metadata

        Raises:
            AIClientError: On any error from the AI provider
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test the connection to the AI provider.

        Returns:
            True if connection is successful, False otherwise
        """
        pass

    async def generate_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
    ) -> AIResponse:
        """
        Generate with retry logic for parse errors.

        If the response doesn't contain valid JSON, retry with
        a more explicit instruction.
        """
        import asyncio

        last_error = None
        current_user_prompt = user_prompt

        for attempt in range(max_retries):
            try:
                response = await self.generate(system_prompt, current_user_prompt)
                content = response.content

                # Try to validate JSON in response
                if self._contains_valid_json(content):
                    return response

                # If no valid JSON, add explicit instruction
                if attempt < max_retries - 1:
                    current_user_prompt = f"""IMPORTANT: Your previous response did not contain valid JSON.
Please respond with ONLY a valid JSON object matching the required schema.
No additional text or explanation - just the JSON.

{user_prompt}"""

            except AIClientError as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff

        if last_error:
            raise last_error

        return response

    def _contains_valid_json(self, text: str) -> bool:
        """Check if text contains valid JSON"""
        import json
        import re

        # Try to find JSON object or array
        patterns = [
            r'\{[\s\S]*"chain_of_thought"[\s\S]*\}',
            r'\{[\s\S]*"decisions"[\s\S]*\}',
            r"```json\s*([\s\S]*?)\s*```",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    json_str = match.group(1) if "```" in pattern else match.group(0)
                    json.loads(json_str)
                    return True
                except (json.JSONDecodeError, IndexError):
                    continue

        return False


# ============================================================================
# Preset model lists per provider type.
# Used ONLY as defaults when a user creates a new provider config.
# The actual model list lives on each AIProviderConfigDB.models column.
# ============================================================================

PRESET_PROVIDER_MODELS: dict[str, list[ModelInfo]] = {
    "deepseek": [
        ModelInfo(
            id="deepseek-chat",
            provider=AIProvider.DEEPSEEK,
            name="DeepSeek V3.2",
            description="DeepSeek's latest and most capable model",
            context_window=128000,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.00028,
            cost_per_1k_output=0.00042,
        ),
        ModelInfo(
            id="deepseek-reasoner",
            provider=AIProvider.DEEPSEEK,
            name="DeepSeek R1",
            description="DeepSeek's reasoning model with thinking mode",
            context_window=128000,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.00055,
            cost_per_1k_output=0.00219,
        ),
    ],
    "qwen": [
        ModelInfo(
            id="qwen3-turbo",
            provider=AIProvider.QWEN,
            name="Qwen3 Turbo",
            description="Alibaba's high-speed cost-efficient model with 1M context",
            context_window=1000000,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.0003,
            cost_per_1k_output=0.0006,
        ),
        ModelInfo(
            id="qwen3-plus",
            provider=AIProvider.QWEN,
            name="Qwen3 Plus",
            description="Alibaba's balanced cost-performance model",
            context_window=262144,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.0008,
            cost_per_1k_output=0.002,
        ),
        ModelInfo(
            id="qwen3-max",
            provider=AIProvider.QWEN,
            name="Qwen3 Max",
            description="Alibaba's most capable flagship model",
            context_window=262144,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.0012,
            cost_per_1k_output=0.006,
        ),
    ],
    "zhipu": [
        ModelInfo(
            id="glm-4.6",
            provider=AIProvider.ZHIPU,
            name="GLM-4.6",
            description="Zhipu's advanced model with 256K context",
            context_window=256000,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.0012,
            cost_per_1k_output=0.0036,
        ),
        ModelInfo(
            id="glm-4.7",
            provider=AIProvider.ZHIPU,
            name="GLM-4.7",
            description="Zhipu's flagship reasoning model with interleaved thinking",
            context_window=200000,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.002,
            cost_per_1k_output=0.006,
        ),
    ],
    "minimax": [
        ModelInfo(
            id="MiniMax-M2.1",
            provider=AIProvider.MINIMAX,
            name="MiniMax M2.1",
            description="MiniMax's flagship model for complex tasks",
            context_window=196608,
            max_output_tokens=128000,
            supports_json_mode=True,
            cost_per_1k_input=0.0003,
            cost_per_1k_output=0.0012,
        ),
        ModelInfo(
            id="MiniMax-M2.1-lightning",
            provider=AIProvider.MINIMAX,
            name="MiniMax M2.1 Lightning",
            description="MiniMax's fast inference variant",
            context_window=196608,
            max_output_tokens=128000,
            supports_json_mode=True,
            cost_per_1k_input=0.0003,
            cost_per_1k_output=0.0024,
        ),
    ],
    "kimi": [
        ModelInfo(
            id="kimi-k2.5",
            provider=AIProvider.KIMI,
            name="Kimi K2.5",
            description="Moonshot's flagship multimodal model",
            context_window=128000,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.0006,
            cost_per_1k_output=0.003,
        ),
        ModelInfo(
            id="kimi-k2",
            provider=AIProvider.KIMI,
            name="Kimi K2",
            description="Moonshot's trillion-parameter MoE model",
            context_window=128000,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.00039,
            cost_per_1k_output=0.0019,
        ),
    ],
    "openai": [
        ModelInfo(
            id="gpt-4o",
            provider=AIProvider.OPENAI,
            name="GPT-4o",
            description="OpenAI's advanced multimodal model",
            context_window=128000,
            max_output_tokens=16384,
            supports_json_mode=True,
            supports_vision=True,
            cost_per_1k_input=0.0025,
            cost_per_1k_output=0.01,
        ),
        ModelInfo(
            id="gpt-4o-mini",
            provider=AIProvider.OPENAI,
            name="GPT-4o Mini",
            description="OpenAI's efficient and cost-effective model",
            context_window=128000,
            max_output_tokens=16384,
            supports_json_mode=True,
            supports_vision=True,
            cost_per_1k_input=0.00015,
            cost_per_1k_output=0.0006,
        ),
        ModelInfo(
            id="o4-mini",
            provider=AIProvider.OPENAI,
            name="o4 Mini",
            description="OpenAI's latest efficient reasoning model",
            context_window=128000,
            max_output_tokens=16384,
            supports_json_mode=True,
            supports_vision=True,
            cost_per_1k_input=0.004,
            cost_per_1k_output=0.016,
        ),
    ],
    "gemini": [
        ModelInfo(
            id="gemini-2.5-flash",
            provider=AIProvider.GEMINI,
            name="Gemini 2.5 Flash",
            description="Google's fastest and most efficient model",
            context_window=1000000,
            max_output_tokens=8192,
            supports_json_mode=True,
            supports_vision=True,
            cost_per_1k_input=0.0003,
            cost_per_1k_output=0.0025,
        ),
        ModelInfo(
            id="gemini-2.5-pro",
            provider=AIProvider.GEMINI,
            name="Gemini 2.5 Pro",
            description="Google's most advanced reasoning model",
            context_window=1000000,
            max_output_tokens=65535,
            supports_json_mode=True,
            supports_vision=True,
            cost_per_1k_input=0.00125,
            cost_per_1k_output=0.01,
        ),
    ],
    "grok": [
        ModelInfo(
            id="grok-4",
            provider=AIProvider.GROK,
            name="Grok 4",
            description="xAI's flagship reasoning model with vision",
            context_window=256000,
            max_output_tokens=8192,
            supports_json_mode=True,
            supports_vision=True,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
        ),
        ModelInfo(
            id="grok-3-mini-beta",
            provider=AIProvider.GROK,
            name="Grok 3 Mini",
            description="xAI's efficient and cost-effective model",
            context_window=131072,
            max_output_tokens=8192,
            supports_json_mode=True,
            cost_per_1k_input=0.0003,
            cost_per_1k_output=0.0005,
        ),
    ],
    "custom": [],
}


def get_preset_models(provider_type: str) -> list[ModelInfo]:
    """Get preset model list for a provider type (used as defaults)."""
    return PRESET_PROVIDER_MODELS.get(provider_type, [])


def model_info_to_dict(model: ModelInfo) -> dict:
    """Serialize a ModelInfo to a dict suitable for JSON storage."""
    return {
        "id": model.id,
        "name": model.name,
        "description": model.description,
        "context_window": model.context_window,
        "max_output_tokens": model.max_output_tokens,
        "supports_json_mode": model.supports_json_mode,
        "supports_vision": model.supports_vision,
        "cost_per_1k_input": model.cost_per_1k_input,
        "cost_per_1k_output": model.cost_per_1k_output,
    }


def preset_models_json(provider_type: str) -> str:
    """Get the preset models for a provider as a JSON string."""
    import json

    models = get_preset_models(provider_type)
    return json.dumps([model_info_to_dict(m) for m in models])
