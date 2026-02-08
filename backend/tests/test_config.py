"""
Tests for app.core.config module.

Covers Settings, get_settings, get_ccxt_proxy_config.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings, get_ccxt_proxy_config, get_settings


class TestSettings:
    """Test Settings model."""

    def test_defaults(self):
        s = Settings()
        assert s.app_name == "BITRUN"
        assert s.environment == "development"
        assert s.host == "0.0.0.0"
        assert s.port == 8000

    def test_is_debug_development(self):
        s = Settings(environment="development")
        assert s.is_debug is True

    def test_is_debug_staging(self):
        s = Settings(environment="staging")
        assert s.is_debug is True

    def test_is_debug_production(self):
        env = {
            "JWT_SECRET": "a" * 32,
            "DATA_ENCRYPTION_KEY": "b" * 32,
        }
        with patch.dict(os.environ, env):
            s = Settings(environment="production", jwt_secret="a" * 32)
            assert s.is_debug is False

    def test_get_cors_origins_single(self):
        s = Settings(cors_origins="http://localhost:3000")
        assert s.get_cors_origins() == ["http://localhost:3000"]

    def test_get_cors_origins_multiple(self):
        s = Settings(cors_origins="http://a.com, http://b.com ,http://c.com")
        assert s.get_cors_origins() == ["http://a.com", "http://b.com", "http://c.com"]

    def test_get_cors_origins_empty(self):
        s = Settings(cors_origins="")
        assert s.get_cors_origins() == []

    def test_production_requires_jwt_secret(self):
        with patch.dict(os.environ, {}, clear=False):
            # Remove JWT_SECRET from env
            env = os.environ.copy()
            env.pop("JWT_SECRET", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValueError, match="JWT_SECRET must be explicitly set"):
                    Settings(environment="production")

    def test_production_jwt_secret_too_short(self):
        env = {
            "JWT_SECRET": "short",
            "DATA_ENCRYPTION_KEY": "b" * 32,
        }
        with patch.dict(os.environ, env):
            with pytest.raises(ValueError, match="at least 32 characters"):
                Settings(environment="production", jwt_secret="short")

    def test_production_requires_data_encryption_key(self):
        env = {
            "JWT_SECRET": "a" * 32,
        }
        with patch.dict(os.environ, env):
            # Remove DATA_ENCRYPTION_KEY
            env_copy = os.environ.copy()
            env_copy.pop("DATA_ENCRYPTION_KEY", None)
            env_copy["JWT_SECRET"] = "a" * 32
            with patch.dict(os.environ, env_copy, clear=True):
                with pytest.raises(ValueError, match="DATA_ENCRYPTION_KEY"):
                    Settings(environment="production", jwt_secret="a" * 32)

    def test_production_valid(self):
        env = {
            "JWT_SECRET": "a" * 32,
            "DATA_ENCRYPTION_KEY": "b" * 32,
        }
        with patch.dict(os.environ, env):
            s = Settings(environment="production", jwt_secret="a" * 32)
            assert s.environment == "production"

    def test_db_pool_defaults(self):
        s = Settings()
        assert s.db_pool_size == 5
        assert s.db_pool_max_overflow == 10
        assert s.db_pool_timeout == 30
        assert s.db_pool_recycle == 1800

    def test_simulator_defaults(self):
        s = Settings()
        assert s.simulator_maker_fee == 0.0002
        assert s.simulator_taker_fee == 0.0005
        assert s.simulator_default_slippage == 0.001

    def test_worker_defaults(self):
        s = Settings()
        assert s.worker_enabled is True
        assert s.worker_distributed is False
        assert s.worker_max_concurrent_jobs == 10

    def test_notification_defaults(self):
        s = Settings()
        assert s.telegram_bot_token == ""
        assert s.discord_webhook_url == ""


class TestGetSettings:
    """Test get_settings function."""

    def test_returns_settings(self):
        get_settings.cache_clear()
        s = get_settings()
        assert isinstance(s, Settings)

    def test_caching(self):
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


class TestGetCcxtProxyConfig:
    """Test get_ccxt_proxy_config function."""

    def test_no_proxy(self):
        get_settings.cache_clear()
        mock = MagicMock()
        mock.proxy_url = ""
        with patch("app.core.config.get_settings", return_value=mock):
            result = get_ccxt_proxy_config()
            assert result == {}

    def test_with_proxy(self):
        get_settings.cache_clear()
        url = "http://host.docker.internal:6152"
        mock = MagicMock()
        mock.proxy_url = url
        with patch("app.core.config.get_settings", return_value=mock):
            result = get_ccxt_proxy_config()
            assert result["aiohttp_proxy"] == url
            assert result["proxies"]["http"] == url
            assert result["proxies"]["https"] == url
