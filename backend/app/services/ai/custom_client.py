"""
Custom OpenAI-Compatible Client Adapter.

Implements the BaseAIClient interface for any OpenAI-compatible API endpoint.
This allows users to connect to local deployments (like vLLM, Ollama) or
other providers that implement the OpenAI API format.
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
                AIProvider.CUSTOM,
            )
    return openai


class CustomOpenAIClient(BaseAIClient):
    """
    Custom OpenAI-compatible API client.

    Connects to any endpoint that implements the OpenAI Chat Completions API.
    Useful for:
    - Local deployments (vLLM, Ollama, LMStudio)
    - Self-hosted models
    - Other providers with OpenAI-compatible APIs

    Usage:
        config = AIClientConfig(
            api_key="...",  # Or "dummy" for local endpoints without auth
            model="llama-3.1-70b",
            base_url="http://localhost:8000/v1",
        )
        client = CustomOpenAIClient(config)
        response = await client.generate(system_prompt, user_prompt)
    """

    def __init__(self, config: AIClientConfig):
        """Initialize custom OpenAI-compatible client."""
        # Custom endpoints require base_url
        if not config.base_url:
            raise AIClientError(
                "base_url is required for custom OpenAI-compatible endpoints",
                AIProvider.CUSTOM,
            )

        # For custom endpoints, API key might not be required
        # Override validation
        self.config = config

        _openai = _get_openai()

        # Initialize the async client
        client_kwargs = {
            "base_url": config.base_url,
            "timeout": config.timeout,
        }

        # Only add API key if provided
        if config.api_key:
            client_kwargs["api_key"] = config.api_key
        else:
            # Use a dummy key for endpoints that don't require auth
            client_kwargs["api_key"] = "not-needed"

        self._client = _openai.AsyncOpenAI(**client_kwargs)

    def _validate_config(self) -> None:
        """Custom endpoints may not require API key."""
        # Override base validation - base_url is validated in __init__
        pass

    @property
    def provider(self) -> AIProvider:
        return AIProvider.CUSTOM

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
    ) -> AIResponse:
        """
        Generate a response from custom endpoint.

        Args:
            system_prompt: System instructions
            user_prompt: User message with context
            json_mode: If True, request JSON output (may not be supported)

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
            }

            # Only add optional params if the endpoint supports them
            # Some endpoints may not support all parameters
            if self.config.max_tokens:
                request_kwargs["max_tokens"] = self.config.max_tokens

            if self.config.temperature is not None:
                request_kwargs["temperature"] = self.config.temperature

            # JSON mode - try to add but handle gracefully
            # Not all custom endpoints support this
            if json_mode and self.config.extra_params.get("supports_json_mode", True):
                try:
                    request_kwargs["response_format"] = {"type": "json_object"}
                except Exception:
                    pass  # Endpoint doesn't support it

            # Call the API
            response = await self._client.chat.completions.create(**request_kwargs)

            # Extract content
            content = response.choices[0].message.content or ""

            # Calculate tokens (may not be available from all endpoints)
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage") and response.usage:
                input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
                output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

            latency_ms = int((time.time() - start_time) * 1000)

            return AIResponse(
                content=content,
                model=getattr(response, "model", self.config.model),
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
