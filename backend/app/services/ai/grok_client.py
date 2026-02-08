"""
xAI Grok Client Adapter.

Implements the BaseAIClient interface for xAI's Grok models.
Grok uses OpenAI-compatible API, so this follows the same pattern as DeepSeek.
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
                AIProvider.GROK,
            )
    return openai


# xAI Grok API base URL
GROK_BASE_URL = "https://api.x.ai/v1"


class GrokClient(BaseAIClient):
    """
    xAI Grok client.

    Uses OpenAI-compatible API with xAI's endpoint.
    Supports Grok-2 and Grok-2 Vision models.

    Usage:
        config = AIClientConfig(api_key="...", model="grok-2")
        client = GrokClient(config)
        response = await client.generate(system_prompt, user_prompt)
    """

    def __init__(self, config: AIClientConfig):
        """Initialize Grok client."""
        # Set Grok base URL if not custom
        if not config.base_url:
            config.base_url = GROK_BASE_URL

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
        return AIProvider.GROK

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
    ) -> AIResponse:
        """
        Generate a response from Grok.

        Args:
            system_prompt: System instructions
            user_prompt: User message with context
            json_mode: If True, use JSON mode (supported by Grok)

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

            # Grok supports JSON mode via OpenAI-compatible API
            if json_mode:
                request_kwargs["response_format"] = {"type": "json_object"}

            # Call Grok API
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
                model=self.config.model,
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
