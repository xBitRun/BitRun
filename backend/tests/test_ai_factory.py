"""
Tests for AI Client Factory and Base Classes.

Covers: AIClientFactory, BaseAIClient, ModelInfo, AIClientConfig
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.ai.base import (
    AIClientConfig,
    AIClientError,
    AIProvider,
    AIResponse,
    BaseAIClient,
    ModelInfo,
    PRESET_PROVIDER_MODELS,
    get_preset_models,
    model_info_to_dict,
    preset_models_json,
)
from app.services.ai.factory import (
    AIClientFactory,
    get_ai_client,
    get_all_models,
    register_custom_model,
    clear_client_cache,
    _CUSTOM_MODELS,
    _CLIENT_CLASSES,
)


# ============================================================================
# ModelInfo Tests
# ============================================================================

class TestModelInfo:
    """Tests for ModelInfo dataclass"""

    def test_model_info_creation(self):
        """Test creating ModelInfo"""
        model = ModelInfo(
            id="test-model",
            provider=AIProvider.DEEPSEEK,
            name="Test Model",
            description="A test model",
            context_window=32000,
            max_output_tokens=4096,
        )
        
        assert model.id == "test-model"
        assert model.provider == AIProvider.DEEPSEEK
        assert model.name == "Test Model"
        assert model.context_window == 32000

    def test_model_info_full_id(self):
        """Test full_id property"""
        model = ModelInfo(
            id="deepseek-chat",
            provider=AIProvider.DEEPSEEK,
            name="DeepSeek V3",
        )
        
        assert model.full_id == "deepseek:deepseek-chat"

    def test_model_info_defaults(self):
        """Test default values"""
        model = ModelInfo(
            id="test",
            provider=AIProvider.OPENAI,
            name="Test",
        )
        
        assert model.description == ""
        assert model.context_window == 128000
        assert model.max_output_tokens == 8192
        assert model.supports_json_mode is False
        assert model.supports_vision is False
        assert model.cost_per_1k_input == 0.0


class TestAIClientConfig:
    """Tests for AIClientConfig dataclass"""

    def test_config_creation(self):
        """Test creating config"""
        config = AIClientConfig(
            api_key="test-key",
            model="gpt-4",
            max_tokens=2048,
            temperature=0.5,
        )
        
        assert config.api_key == "test-key"
        assert config.model == "gpt-4"
        assert config.max_tokens == 2048
        assert config.temperature == 0.5

    def test_config_defaults(self):
        """Test default values"""
        config = AIClientConfig(
            api_key="key",
            model="model",
        )
        
        assert config.base_url is None
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.timeout == 120
        assert config.extra_params == {}


# ============================================================================
# Preset Models Tests
# ============================================================================

class TestPresetModels:
    """Tests for preset model definitions"""

    def test_deepseek_presets(self):
        """Test DeepSeek preset models exist and have correct API model names"""
        models = get_preset_models("deepseek")
        assert len(models) >= 1
        model_ids = [m.id for m in models]
        assert "deepseek-chat" in model_ids

    def test_openai_presets(self):
        """Test OpenAI preset models exist"""
        models = get_preset_models("openai")
        assert len(models) >= 1
        model_ids = [m.id for m in models]
        assert "gpt-4o" in model_ids

    def test_gemini_presets(self):
        """Test Gemini preset models exist"""
        models = get_preset_models("gemini")
        assert len(models) >= 1
        assert all(m.provider == AIProvider.GEMINI for m in models)

    def test_qwen_presets(self):
        """Test Qwen preset models use correct API names"""
        models = get_preset_models("qwen")
        assert len(models) >= 1
        model_ids = [m.id for m in models]
        assert "qwen3-plus" in model_ids or "qwen3-max" in model_ids

    def test_unknown_provider_returns_empty(self):
        """Test unknown provider returns empty list"""
        models = get_preset_models("nonexistent")
        assert models == []

    def test_model_info_to_dict(self):
        """Test serializing ModelInfo to dict"""
        model = ModelInfo(
            id="test-model",
            provider=AIProvider.DEEPSEEK,
            name="Test",
            description="desc",
            context_window=64000,
            max_output_tokens=8192,
            supports_json_mode=True,
        )
        d = model_info_to_dict(model)
        assert d["id"] == "test-model"
        assert d["name"] == "Test"
        assert d["context_window"] == 64000
        assert d["supports_json_mode"] is True
        # Should not contain provider (stored at provider level)
        assert "provider" not in d

    def test_preset_models_json(self):
        """Test preset models JSON serialization"""
        import json
        j = preset_models_json("deepseek")
        data = json.loads(j)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == "deepseek-chat"

    def test_all_providers_have_presets(self):
        """Test that all standard providers have preset models"""
        for provider_type in ["deepseek", "qwen", "zhipu", "minimax", "kimi", "openai", "gemini", "grok"]:
            models = get_preset_models(provider_type)
            assert len(models) >= 1, f"No presets for {provider_type}"


# ============================================================================
# AIClientFactory Tests
# ============================================================================

class TestAIClientFactory:
    """Tests for AIClientFactory"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup before each test"""
        clear_client_cache()
        _CUSTOM_MODELS.clear()
        yield
        clear_client_cache()
        _CUSTOM_MODELS.clear()

    def test_create_invalid_format(self):
        """Test creating client with invalid model ID format"""
        with pytest.raises(AIClientError) as exc_info:
            AIClientFactory.create("invalid-format")
        
        assert "Invalid model ID format" in str(exc_info.value)

    def test_create_unknown_provider(self):
        """Test creating client with unknown provider"""
        with pytest.raises(AIClientError) as exc_info:
            AIClientFactory.create("unknown:model")
        
        assert "Unknown provider" in str(exc_info.value)

    def test_create_any_model_allowed(self):
        """Test that factory accepts any model_id (no AVAILABLE_MODELS check)"""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        with patch.dict(_CLIENT_CLASSES, {AIProvider.DEEPSEEK: mock_client_class}):
            client = AIClientFactory.create(
                "deepseek:any-model-name",
                api_key="test-key"
            )
            
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args[0][0]
            assert call_args.model == "any-model-name"

    @patch("app.services.ai.factory._CLIENT_CLASSES", {})
    def test_create_no_implementation(self):
        """Test creating client without implementation"""
        from app.services.ai import factory
        
        # Patch _ensure_clients_registered to no-op so clear actually sticks
        with patch.object(factory, '_ensure_clients_registered', lambda: None):
            saved = dict(factory._CLIENT_CLASSES)
            factory._CLIENT_CLASSES.clear()
            try:
                with pytest.raises(AIClientError) as exc_info:
                    AIClientFactory.create_with_config(
                        AIProvider.DEEPSEEK,
                        AIClientConfig(api_key="test", model="test")
                    )
                assert "No client implementation" in str(exc_info.value)
            finally:
                factory._CLIENT_CLASSES.update(saved)

    def test_create_with_api_key(self):
        """Test creating client with provided API key"""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        with patch.dict(_CLIENT_CLASSES, {AIProvider.DEEPSEEK: mock_client_class}):
            client = AIClientFactory.create(
                "deepseek:deepseek-chat",
                api_key="my-api-key"
            )
            
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args[0][0]
            assert call_args.api_key == "my-api-key"
            assert call_args.model == "deepseek-chat"

    def test_create_with_config(self):
        """Test creating client with explicit config"""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        with patch.dict(_CLIENT_CLASSES, {AIProvider.OPENAI: mock_client_class}):
            config = AIClientConfig(
                api_key="test-key",
                model="gpt-4o",
                temperature=0.5,
            )
            
            client = AIClientFactory.create_with_config(AIProvider.OPENAI, config)
            
            mock_client_class.assert_called_once_with(config)

    def test_get_api_key_raises_for_non_custom(self):
        """Test _get_api_key raises when no api_key (caller must pass from DB)"""
        with pytest.raises(AIClientError) as exc_info:
            AIClientFactory._get_api_key(AIProvider.DEEPSEEK)
        assert "No API key provided" in str(exc_info.value)
        assert "Configure the provider" in str(exc_info.value)

    def test_get_api_key_raises_for_openai(self):
        """Test _get_api_key raises for OpenAI when not passed in"""
        with pytest.raises(AIClientError) as exc_info:
            AIClientFactory._get_api_key(AIProvider.OPENAI)
        assert "No API key provided" in str(exc_info.value)

    def test_get_api_key_custom_provider(self):
        """Test custom provider doesn't require API key (returns empty string)"""
        key = AIClientFactory._get_api_key(AIProvider.CUSTOM)
        assert key == ""

    def test_get_supported_providers(self):
        """Test getting supported providers"""
        providers = AIClientFactory.get_supported_providers()
        
        assert isinstance(providers, list)
        # After lazy loading, should have registered providers


# ============================================================================
# Custom Model Registration Tests
# ============================================================================

class TestCustomModelRegistration:
    """Tests for custom model registration"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear custom models before each test"""
        _CUSTOM_MODELS.clear()
        yield
        _CUSTOM_MODELS.clear()

    def test_register_custom_model(self):
        """Test registering a custom model"""
        model = register_custom_model(
            model_id="my-model",
            name="My Custom Model",
            base_url="https://api.example.com/v1",
            description="A custom model",
            context_window=16000,
        )
        
        assert model.id == "my-model"
        assert model.name == "My Custom Model"
        assert model.provider == AIProvider.CUSTOM
        assert hasattr(model, "base_url")

    def test_registered_model_in_custom_models(self):
        """Test registered model is stored"""
        register_custom_model(
            model_id="test-model",
            name="Test",
            base_url="https://test.com",
        )
        
        assert "custom:test-model" in _CUSTOM_MODELS


# ============================================================================
# BaseAIClient Tests
# ============================================================================

class TestBaseAIClient:
    """Tests for BaseAIClient abstract class"""

    def test_cannot_instantiate_directly(self):
        """Test that BaseAIClient cannot be instantiated directly"""
        config = AIClientConfig(api_key="test", model="test")
        
        with pytest.raises(TypeError):
            BaseAIClient(config)

    def test_validate_config_requires_api_key(self):
        """Test that config validation requires API key"""
        class TestClient(BaseAIClient):
            @property
            def provider(self):
                return AIProvider.CUSTOM
            
            async def generate(self, system_prompt, user_prompt, json_mode=True):
                pass
            
            async def test_connection(self):
                return True
        
        config = AIClientConfig(api_key="", model="test")
        
        with pytest.raises(AIClientError) as exc_info:
            TestClient(config)
        
        assert "API key is required" in str(exc_info.value)

    def test_contains_valid_json_true(self):
        """Test JSON validation with valid JSON"""
        class TestClient(BaseAIClient):
            @property
            def provider(self):
                return AIProvider.CUSTOM
            
            async def generate(self, system_prompt, user_prompt, json_mode=True):
                pass
            
            async def test_connection(self):
                return True
        
        config = AIClientConfig(api_key="test", model="test")
        client = TestClient(config)
        
        text = '{"chain_of_thought": "analysis", "decisions": []}'
        assert client._contains_valid_json(text) is True

    def test_contains_valid_json_with_code_block(self):
        """Test JSON validation with markdown code block"""
        class TestClient(BaseAIClient):
            @property
            def provider(self):
                return AIProvider.CUSTOM
            
            async def generate(self, system_prompt, user_prompt, json_mode=True):
                pass
            
            async def test_connection(self):
                return True
        
        config = AIClientConfig(api_key="test", model="test")
        client = TestClient(config)
        
        text = '''Here's the response:
```json
{"chain_of_thought": "test", "decisions": []}
```'''
        assert client._contains_valid_json(text) is True

    def test_contains_valid_json_false(self):
        """Test JSON validation with invalid JSON"""
        class TestClient(BaseAIClient):
            @property
            def provider(self):
                return AIProvider.CUSTOM
            
            async def generate(self, system_prompt, user_prompt, json_mode=True):
                pass
            
            async def test_connection(self):
                return True
        
        config = AIClientConfig(api_key="test", model="test")
        client = TestClient(config)
        
        text = "This is just plain text without JSON"
        assert client._contains_valid_json(text) is False


# ============================================================================
# AIResponse Tests
# ============================================================================

class TestAIResponse:
    """Tests for AIResponse dataclass"""

    def test_response_creation(self):
        """Test creating AIResponse"""
        response = AIResponse(
            content='{"result": "test"}',
            model="gpt-4",
            provider=AIProvider.OPENAI,
            tokens_used=100,
            input_tokens=50,
            output_tokens=50,
            stop_reason="stop",
            latency_ms=500,
        )
        
        assert response.content == '{"result": "test"}'
        assert response.model == "gpt-4"
        assert response.provider == AIProvider.OPENAI
        assert response.tokens_used == 100

    def test_response_defaults(self):
        """Test default values"""
        response = AIResponse(
            content="test",
            model="model",
            provider=AIProvider.DEEPSEEK,
            tokens_used=10,
            input_tokens=5,
            output_tokens=5,
        )
        
        assert response.stop_reason == ""
        assert response.latency_ms == 0
        assert response.raw_response is None


# ============================================================================
# Error Classes Tests
# ============================================================================

class TestAIErrors:
    """Tests for AI error classes"""

    def test_ai_client_error(self):
        """Test AIClientError"""
        error = AIClientError("Test error", AIProvider.OPENAI)
        
        assert str(error) == "Test error"
        assert error.provider == AIProvider.OPENAI

    def test_ai_client_error_without_provider(self):
        """Test AIClientError without provider"""
        error = AIClientError("Test error")
        
        assert str(error) == "Test error"
        assert error.provider is None

    def test_error_subclasses(self):
        """Test error subclasses"""
        from app.services.ai.base import (
            AIAuthenticationError,
            AIRateLimitError,
            AIConnectionError,
            AIInvalidRequestError,
        )
        
        auth_error = AIAuthenticationError("Auth failed")
        rate_error = AIRateLimitError("Rate limited")
        conn_error = AIConnectionError("Connection failed")
        invalid_error = AIInvalidRequestError("Invalid request")
        
        assert isinstance(auth_error, AIClientError)
        assert isinstance(rate_error, AIClientError)
        assert isinstance(conn_error, AIClientError)
        assert isinstance(invalid_error, AIClientError)


# ============================================================================
# Get AI Client Tests
# ============================================================================

class TestGetAIClient:
    """Tests for get_ai_client convenience function"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear cache before each test"""
        clear_client_cache()
        yield
        clear_client_cache()

    def test_get_ai_client(self):
        """Test get_ai_client function"""
        mock_client_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        with patch.dict(_CLIENT_CLASSES, {AIProvider.DEEPSEEK: mock_client_class}):
            client = get_ai_client(
                "deepseek:deepseek-chat",
                api_key="test-key"
            )
            
            mock_client_class.assert_called_once()


# ============================================================================
# Provider Enum Tests
# ============================================================================

class TestAIProvider:
    """Tests for AIProvider enum"""

    def test_all_providers(self):
        """Test all providers are defined"""
        providers = [
            AIProvider.DEEPSEEK,
            AIProvider.QWEN,
            AIProvider.ZHIPU,
            AIProvider.MINIMAX,
            AIProvider.KIMI,
            AIProvider.OPENAI,
            AIProvider.GEMINI,
            AIProvider.GROK,
            AIProvider.CUSTOM,
        ]
        
        assert len(providers) == 9

    def test_provider_values(self):
        """Test provider string values"""
        assert AIProvider.DEEPSEEK.value == "deepseek"
        assert AIProvider.OPENAI.value == "openai"
        assert AIProvider.CUSTOM.value == "custom"

    def test_provider_from_string(self):
        """Test creating provider from string"""
        provider = AIProvider("deepseek")
        assert provider == AIProvider.DEEPSEEK

    def test_provider_invalid_string(self):
        """Test invalid provider string"""
        with pytest.raises(ValueError):
            AIProvider("invalid")
