"""
Tests for AI Client Implementations.

Covers: OpenAIClient generate/test_connection, error mapping,
BaseAIClient.generate_with_retry, and credential resolution.
Does NOT duplicate tests from test_ai_factory.py.
"""

import builtins
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.base import (
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
from app.services.ai.openai_client import OpenAIClient


# ============================================================================
# Helper: Concrete BaseAIClient for testing non-abstract methods
# ============================================================================

class ConcreteAIClient(BaseAIClient):
    """Concrete implementation for testing BaseAIClient methods."""

    @property
    def provider(self) -> AIProvider:
        return AIProvider.CUSTOM

    async def generate(self, system_prompt, user_prompt, json_mode=True):
        raise NotImplementedError("Override via mock in test")

    async def test_connection(self):
        return True


# ============================================================================
# Helper: Mock openai module builder
# ============================================================================

def _make_mock_openai():
    """Create a mock openai module with exception classes and AsyncOpenAI."""
    mock_openai = MagicMock()
    mock_async_client = AsyncMock()
    mock_openai.AsyncOpenAI.return_value = mock_async_client

    # Real exception classes so except clauses work
    mock_openai.BadRequestError = type("BadRequestError", (Exception,), {})
    mock_openai.AuthenticationError = type("AuthenticationError", (Exception,), {})
    mock_openai.RateLimitError = type("RateLimitError", (Exception,), {})
    mock_openai.APIConnectionError = type("APIConnectionError", (Exception,), {})
    mock_openai.APIStatusError = type("APIStatusError", (Exception,), {})

    return mock_openai, mock_async_client


def _make_mock_response(
    content="test response",
    model="gpt-4o",
    input_tokens=10,
    output_tokens=20,
    finish_reason="stop",
):
    """Create a mock OpenAI chat completion response."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.choices[0].finish_reason = finish_reason
    resp.model = model
    resp.usage = MagicMock()
    resp.usage.prompt_tokens = input_tokens
    resp.usage.completion_tokens = output_tokens
    return resp


# ============================================================================
# OpenAI Client Implementation Tests
# ============================================================================

class TestOpenAIClientImpl:
    """Tests for OpenAIClient with mocked HTTP layer."""

    def test_openai_client_init(self):
        """Test OpenAI client creates AsyncOpenAI with correct params."""
        mock_openai, _ = _make_mock_openai()

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            OpenAIClient(config)

            mock_openai.AsyncOpenAI.assert_called_once_with(
                api_key="sk-test",
                timeout=120,
            )

    def test_openai_client_provider_property(self):
        """Test provider property returns AIProvider.OPENAI."""
        mock_openai, _ = _make_mock_openai()

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)
            assert client.provider == AIProvider.OPENAI

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generate() returns proper AIResponse."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_resp = _make_mock_response(
            content='{"result": "ok"}',
            model="gpt-4o",
            input_tokens=15,
            output_tokens=25,
        )
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            response = await client.generate("system prompt", "user prompt")

            assert isinstance(response, AIResponse)
            assert response.content == '{"result": "ok"}'
            assert response.model == "gpt-4o"
            assert response.provider == AIProvider.OPENAI
            assert response.input_tokens == 15
            assert response.output_tokens == 25
            assert response.tokens_used == 40
            assert response.stop_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_json_mode_enabled(self):
        """Test generate() passes response_format when json_mode=True."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response()
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            await client.generate("sys", "usr", json_mode=True)

            call_kwargs = mock_async_client.chat.completions.create.call_args[1]
            assert call_kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_generate_json_mode_disabled(self):
        """Test generate() omits response_format when json_mode=False."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response()
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            await client.generate("sys", "usr", json_mode=False)

            call_kwargs = mock_async_client.chat.completions.create.call_args[1]
            assert "response_format" not in call_kwargs

    @pytest.mark.asyncio
    async def test_generate_auth_error(self):
        """Test generate() maps openai AuthenticationError → AIAuthenticationError."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=mock_openai.AuthenticationError("invalid key")
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="bad-key", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIAuthenticationError) as exc_info:
                await client.generate("sys", "usr")
            assert exc_info.value.provider == AIProvider.OPENAI

    @pytest.mark.asyncio
    async def test_generate_rate_limit_error(self):
        """Test generate() maps openai RateLimitError → AIRateLimitError."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=mock_openai.RateLimitError("too many requests")
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIRateLimitError):
                await client.generate("sys", "usr")

    @pytest.mark.asyncio
    async def test_generate_connection_error(self):
        """Test generate() maps openai APIConnectionError → AIConnectionError."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=mock_openai.APIConnectionError("network failure")
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIConnectionError):
                await client.generate("sys", "usr")

    @pytest.mark.asyncio
    async def test_generate_bad_request_error(self):
        """Test generate() maps openai BadRequestError → AIInvalidRequestError."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=mock_openai.BadRequestError("invalid model")
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIInvalidRequestError):
                await client.generate("sys", "usr")

    @pytest.mark.asyncio
    async def test_generate_unexpected_error(self):
        """Test generate() wraps unexpected errors in AIClientError."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("something broke")
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIClientError) as exc_info:
                await client.generate("sys", "usr")
            assert "Unexpected error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_no_usage_data(self):
        """Test generate() handles response with no usage field."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_resp = _make_mock_response()
        mock_resp.usage = None
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            response = await client.generate("sys", "usr")
            assert response.input_tokens == 0
            assert response.output_tokens == 0
            assert response.tokens_used == 0

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test test_connection() returns True on success."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            return_value=_make_mock_response()
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            result = await client.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_auth_failure(self):
        """Test test_connection() raises AIAuthenticationError on bad key."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=mock_openai.AuthenticationError("bad key")
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="bad-key", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIAuthenticationError):
                await client.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_rate_limit_error(self):
        """Test test_connection() raises AIRateLimitError on rate limit."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=mock_openai.RateLimitError("rate limit")
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIRateLimitError):
                await client.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_connection_error(self):
        """Test test_connection() raises AIConnectionError on network failure."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=mock_openai.APIConnectionError("network failure")
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIConnectionError):
                await client.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_api_status_error(self):
        """Test test_connection() raises AIClientError on APIStatusError."""
        mock_openai, mock_async_client = _make_mock_openai()
        # Create APIStatusError instance properly
        api_error = mock_openai.APIStatusError("API error")
        mock_async_client.chat.completions.create = AsyncMock(side_effect=api_error)

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIClientError) as exc_info:
                await client.test_connection()
            assert exc_info.value.provider == AIProvider.OPENAI

    @pytest.mark.asyncio
    async def test_test_connection_unexpected_error(self):
        """Test test_connection() wraps unexpected errors in AIClientError."""
        mock_openai, mock_async_client = _make_mock_openai()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("unexpected error")
        )

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIClientError) as exc_info:
                await client.test_connection()
            assert exc_info.value.provider == AIProvider.OPENAI

    def test_get_openai_import_error(self):
        """Test _get_openai() raises AIClientError when openai package not installed."""
        # Reset the module-level cache
        import app.services.ai.openai_client as openai_module
        from importlib import reload
        original_openai = openai_module.openai
        openai_module.openai = None
        
        original_import = builtins.__import__
        
        def selective_import(name, *args, **kwargs):
            if name == "openai" or name.startswith("openai."):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)
        
        try:
            with patch("builtins.__import__", side_effect=selective_import):
                # Reload the function to test import error handling
                reload(openai_module)
                from app.services.ai.openai_client import _get_openai
                
                with pytest.raises(AIClientError) as exc_info:
                    _get_openai()
                assert exc_info.value.provider == AIProvider.OPENAI
                assert "openai package not installed" in str(exc_info.value)
        finally:
            # Restore original state
            openai_module.openai = original_openai
            reload(openai_module)

    @pytest.mark.asyncio
    async def test_generate_api_status_error(self):
        """Test generate() maps openai APIStatusError → AIClientError."""
        mock_openai, mock_async_client = _make_mock_openai()
        # Create APIStatusError instance properly
        api_error = mock_openai.APIStatusError("API error")
        mock_async_client.chat.completions.create = AsyncMock(side_effect=api_error)

        with patch("app.services.ai.openai_client._get_openai", return_value=mock_openai):
            config = AIClientConfig(api_key="sk-test", model="gpt-4o")
            client = OpenAIClient(config)

            with pytest.raises(AIClientError) as exc_info:
                await client.generate("sys", "usr")
            assert exc_info.value.provider == AIProvider.OPENAI


# ============================================================================
# BaseAIClient.generate_with_retry Tests
# ============================================================================

class TestGenerateWithRetry:
    """Tests for BaseAIClient.generate_with_retry (retry + JSON validation)."""

    def _make_response(self, content: str) -> AIResponse:
        return AIResponse(
            content=content,
            model="test-model",
            provider=AIProvider.CUSTOM,
            tokens_used=10,
            input_tokens=5,
            output_tokens=5,
        )

    @pytest.mark.asyncio
    async def test_returns_immediately_on_valid_json(self):
        """Test returns on first try when response contains valid JSON."""
        config = AIClientConfig(api_key="test", model="test")
        client = ConcreteAIClient(config)

        valid = self._make_response('{"chain_of_thought": "ok", "decisions": []}')
        client.generate = AsyncMock(return_value=valid)

        result = await client.generate_with_retry("sys", "usr")
        assert result is valid
        assert client.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_invalid_json_then_succeeds(self):
        """Test retries with explicit JSON instruction when first response lacks JSON."""
        config = AIClientConfig(api_key="test", model="test")
        client = ConcreteAIClient(config)

        invalid = self._make_response("The market looks bullish overall.")
        valid = self._make_response('{"chain_of_thought": "analysis", "decisions": []}')
        client.generate = AsyncMock(side_effect=[invalid, valid])

        result = await client.generate_with_retry("sys", "usr", max_retries=3)
        assert result is valid
        assert client.generate.call_count == 2
        # Second call should include the explicit JSON instruction
        second_prompt = client.generate.call_args_list[1][0][1]
        assert "IMPORTANT" in second_prompt

    @pytest.mark.asyncio
    async def test_retries_on_error_with_backoff(self):
        """Test retries with exponential backoff on AIClientError."""
        config = AIClientConfig(api_key="test", model="test")
        client = ConcreteAIClient(config)

        valid = self._make_response('{"chain_of_thought": "ok", "decisions": []}')
        client.generate = AsyncMock(side_effect=[
            AIConnectionError("timeout"),
            valid,
        ])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client.generate_with_retry("sys", "usr", max_retries=3)

        assert result is valid
        mock_sleep.assert_called_once_with(1)  # 2**0 = 1

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self):
        """Test raises final error when all retries fail."""
        config = AIClientConfig(api_key="test", model="test")
        client = ConcreteAIClient(config)

        client.generate = AsyncMock(side_effect=AIConnectionError("timeout"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(AIConnectionError):
                await client.generate_with_retry("sys", "usr", max_retries=2)


# ============================================================================
# Credential Resolution Tests
# ============================================================================

class TestCredentialResolution:
    """Tests for resolve_provider_credentials from credentials.py."""

    @pytest.mark.asyncio
    async def test_resolve_success_with_base_url(self):
        """Test successful resolution returns decrypted key and trimmed base_url."""
        mock_db = AsyncMock()
        mock_crypto = MagicMock()
        mock_crypto.decrypt.return_value = "decrypted-api-key"

        mock_row = MagicMock()
        mock_row.encrypted_api_key = "encrypted-key"
        mock_row.base_url = "https://custom-api.com/v1/"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.services.ai.credentials import resolve_provider_credentials

        api_key, base_url = await resolve_provider_credentials(
            db=mock_db,
            crypto=mock_crypto,
            user_id=uuid.uuid4(),
            model_id="deepseek:deepseek-chat",
        )

        assert api_key == "decrypted-api-key"
        assert base_url == "https://custom-api.com/v1"  # trailing slash stripped

    @pytest.mark.asyncio
    async def test_resolve_no_colon_returns_none(self):
        """Test returns (None, None) when model_id has no colon separator."""
        mock_db = AsyncMock()
        mock_crypto = MagicMock()

        from app.services.ai.credentials import resolve_provider_credentials

        api_key, base_url = await resolve_provider_credentials(
            db=mock_db,
            crypto=mock_crypto,
            user_id=uuid.uuid4(),
            model_id="invalid-model-id",
        )

        assert api_key is None
        assert base_url is None

    @pytest.mark.asyncio
    async def test_resolve_empty_provider_returns_none(self):
        """Test returns (None, None) when provider part is empty."""
        mock_db = AsyncMock()
        mock_crypto = MagicMock()

        from app.services.ai.credentials import resolve_provider_credentials

        api_key, base_url = await resolve_provider_credentials(
            db=mock_db,
            crypto=mock_crypto,
            user_id=uuid.uuid4(),
            model_id=":some-model",
        )

        assert api_key is None
        assert base_url is None

    @pytest.mark.asyncio
    async def test_resolve_no_config_in_db(self):
        """Test returns (None, None) when no config found in database."""
        mock_db = AsyncMock()
        mock_crypto = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.services.ai.credentials import resolve_provider_credentials

        api_key, base_url = await resolve_provider_credentials(
            db=mock_db,
            crypto=mock_crypto,
            user_id=uuid.uuid4(),
            model_id="openai:gpt-4o",
        )

        assert api_key is None
        assert base_url is None

    @pytest.mark.asyncio
    async def test_resolve_no_base_url_configured(self):
        """Test returns None base_url when config has empty base_url."""
        mock_db = AsyncMock()
        mock_crypto = MagicMock()
        mock_crypto.decrypt.return_value = "my-api-key"

        mock_row = MagicMock()
        mock_row.encrypted_api_key = "encrypted"
        mock_row.base_url = ""

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_db.execute = AsyncMock(return_value=mock_result)

        from app.services.ai.credentials import resolve_provider_credentials

        api_key, base_url = await resolve_provider_credentials(
            db=mock_db,
            crypto=mock_crypto,
            user_id=uuid.uuid4(),
            model_id="openai:gpt-4o",
        )

        assert api_key == "my-api-key"
        assert base_url is None
