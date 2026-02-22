"""
Google Gemini Client Adapter.

Implements the BaseAIClient interface for Google's Gemini models.
"""

import asyncio
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
genai = None


def _get_genai():
    """Lazy load google-generativeai module."""
    global genai
    if genai is None:
        try:
            import google.generativeai as _genai

            genai = _genai
        except ImportError:
            raise AIClientError(
                "google-generativeai package not installed. Install with: pip install google-generativeai",
                AIProvider.GEMINI,
            )
    return genai


class GeminiClient(BaseAIClient):
    """
    Google Gemini client.

    Supports Gemini 2.0 Flash, Gemini 1.5 Pro, and other Gemini models.

    Usage:
        config = AIClientConfig(api_key="...", model="gemini-2.0-flash-exp")
        client = GeminiClient(config)
        response = await client.generate(system_prompt, user_prompt)
    """

    def __init__(self, config: AIClientConfig):
        """Initialize Gemini client."""
        super().__init__(config)

        _genai = _get_genai()

        # Configure the API key
        _genai.configure(api_key=config.api_key)

        # Initialize the model
        self._model = _genai.GenerativeModel(
            model_name=config.model,
            generation_config={
                "max_output_tokens": config.max_tokens,
                "temperature": config.temperature,
            },
        )

    @property
    def provider(self) -> AIProvider:
        return AIProvider.GEMINI

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
    ) -> AIResponse:
        """
        Generate a response from Gemini.

        Args:
            system_prompt: System instructions
            user_prompt: User message with context
            json_mode: If True, request JSON output

        Returns:
            AIResponse with content and metadata
        """
        _genai = _get_genai()
        start_time = time.time()

        try:
            # Gemini uses a different format - combine system and user into contents
            # System instructions can be set as system_instruction or prepended to content

            # Create a new model instance with system instruction
            model = _genai.GenerativeModel(
                model_name=self.config.model,
                generation_config={
                    "max_output_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "response_mime_type": (
                        "application/json" if json_mode else "text/plain"
                    ),
                },
                system_instruction=system_prompt,
            )

            # Generate content asynchronously
            # Note: google-generativeai uses synchronous API, so we run in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: model.generate_content(user_prompt)
            )

            # Extract content
            content = response.text if response.text else ""

            # Calculate tokens (Gemini provides usage metadata)
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
                output_tokens = getattr(
                    response.usage_metadata, "candidates_token_count", 0
                )

            latency_ms = int((time.time() - start_time) * 1000)

            # Determine stop reason
            stop_reason = ""
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, "finish_reason"):
                    stop_reason = str(candidate.finish_reason)

            return AIResponse(
                content=content,
                model=self.config.model,
                provider=self.provider,
                tokens_used=input_tokens + output_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                stop_reason=stop_reason,
                latency_ms=latency_ms,
                raw_response=response,
            )

        except Exception as e:
            error_str = str(e).lower()

            if (
                "api_key" in error_str
                or "authentication" in error_str
                or "invalid" in error_str
            ):
                raise AIAuthenticationError(
                    f"Authentication failed: {e}", self.provider
                )
            elif "quota" in error_str or "rate" in error_str or "limit" in error_str:
                raise AIRateLimitError(f"Rate limit exceeded: {e}", self.provider)
            elif "connection" in error_str or "network" in error_str:
                raise AIConnectionError(f"Connection failed: {e}", self.provider)
            elif "bad request" in error_str or "invalid" in error_str:
                raise AIInvalidRequestError(f"Bad request: {e}", self.provider)
            else:
                raise AIClientError(f"Gemini error: {e}", self.provider)

    async def test_connection(self) -> bool:
        """Test API connection using a minimal request."""
        try:
            _genai = _get_genai()
            model = _genai.GenerativeModel(model_name=self.config.model)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: model.generate_content("Hi")
            )
            return response.text is not None
        except Exception as e:
            error_str = str(e).lower()
            if (
                "api_key" in error_str
                or "authentication" in error_str
                or "invalid" in error_str
            ):
                raise AIAuthenticationError(
                    f"Authentication failed: {e}", self.provider
                )
            if "quota" in error_str or "rate" in error_str or "limit" in error_str:
                raise AIRateLimitError(f"Rate limit exceeded: {e}", self.provider)
            if "connection" in error_str or "network" in error_str:
                raise AIConnectionError(f"Connection failed: {e}", self.provider)
            raise AIClientError(f"Gemini error: {e}", self.provider)
