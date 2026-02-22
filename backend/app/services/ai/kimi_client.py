"""
Kimi (Moonshot) Client Adapter.

Implements the BaseAIClient interface for Moonshot's Kimi models.
Uses OpenAI-compatible API.
"""

import time

from .base import (
    AIClientConfig,
    AIClientError,
    AIAuthenticationError,
    AIRateLimitError,
    AIConnectionError,
    AIInvalidRequestError,
    AIProvider,
    AIResponse,
    BaseAIClient,
)

# Lazy import to avoid hard dependency
openai = None


def _get_openai():
    """Lazy load openai module."""
    global openai
    if openai is None:
        try:
            import openai as _openai

            openai = _openai
        except ImportError:
            raise AIClientError(
                "openai package not installed. Install with: pip install openai",
                AIProvider.KIMI,
            )
    return openai


# Kimi API base URL
KIMI_BASE_URL = "https://api.moonshot.cn/v1"


class KimiClient(BaseAIClient):
    """
    Kimi AI client (Moonshot).

    Uses OpenAI-compatible API with Moonshot's endpoint.
    Supports Kimi series models.

    Usage:
        config = AIClientConfig(api_key="...", model="moonshot-v1-auto")
        client = KimiClient(config)
        response = await client.generate(system_prompt, user_prompt)
    """

    def __init__(self, config: AIClientConfig):
        """Initialize Kimi client."""
        # Set Kimi base URL if not custom
        if not config.base_url:
            config.base_url = KIMI_BASE_URL

        super().__init__(config)

        _openai = _get_openai()

        # Initialize the async client
        self._client = _openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )

    @property
    def provider(self) -> AIProvider:
        return AIProvider.KIMI

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
    ) -> AIResponse:
        """
        Generate a response from Kimi.

        Args:
            system_prompt: System instructions
            user_prompt: User message with context
            json_mode: If True, use JSON mode (supported by Kimi)

        Returns:
            AIResponse with content and metadata
        """
        _openai = _get_openai()
        start_time = time.time()

        try:
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Build request kwargs
            request_kwargs = {
                "model": self.config.model,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            # Kimi supports JSON mode
            if json_mode:
                request_kwargs["response_format"] = {"type": "json_object"}

            # Call Kimi API
            response = await self._client.chat.completions.create(**request_kwargs)

            # Extract content
            content = response.choices[0].message.content or ""

            # Calculate tokens
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            latency_ms = int((time.time() - start_time) * 1000)

            return AIResponse(
                content=content,
                model=response.model,
                provider=self.provider,
                tokens_used=input_tokens + output_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                stop_reason=response.choices[0].finish_reason or "",
                latency_ms=latency_ms,
                raw_response=response,
            )

        except _openai.BadRequestError as e:
            raise AIInvalidRequestError(f"Bad request: {e}", self.provider)
        except _openai.AuthenticationError as e:
            raise AIAuthenticationError(f"Authentication failed: {e}", self.provider)
        except _openai.RateLimitError as e:
            raise AIRateLimitError(f"Rate limit exceeded: {e}", self.provider)
        except _openai.APIConnectionError as e:
            raise AIConnectionError(f"Connection failed: {e}", self.provider)
        except _openai.APIStatusError as e:
            raise AIClientError(f"API error: {e}", self.provider)
        except Exception as e:
            raise AIClientError(f"Unexpected error: {e}", self.provider)

    async def test_connection(self) -> bool:
        """Test API connection using a minimal request."""
        _openai = _get_openai()
        try:
            await self._client.chat.completions.create(
                model="moonshot-v1-8k",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except _openai.AuthenticationError as e:
            raise AIAuthenticationError(f"Authentication failed: {e}", self.provider)
        except _openai.RateLimitError as e:
            raise AIRateLimitError(f"Rate limit exceeded: {e}", self.provider)
        except _openai.APIConnectionError as e:
            raise AIConnectionError(f"Connection failed: {e}", self.provider)
        except _openai.APIStatusError as e:
            raise AIClientError(f"API error: {e}", self.provider)
        except Exception as e:
            raise AIClientError(f"Unexpected error: {e}", self.provider)
