"""Application configuration using Pydantic Settings"""

import os
import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Marker to detect if JWT_SECRET was auto-generated vs explicitly set
_JWT_SECRET_AUTO_GENERATED = secrets.token_urlsafe(32)


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "BITRUN"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"

    # Brand Configuration (for backend notifications/emails)
    # Full branding (logo, theme, links) is handled by frontend env vars
    brand_name: str = "BITRUN"
    brand_tagline: str = "AI-Powered Trading Agent"
    brand_description: str = "Prompt-driven automated trading with AI decision making"

    @property
    def is_debug(self) -> bool:
        """Debug mode is derived from environment (non-production = debug)."""
        return self.environment != "production"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database
    # In production, DATABASE_URL must be set via environment variable.
    # The default uses 'bitrun' user for local development (avoid hardcoding 'postgres:postgres').
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://bitrun:bitrun_dev@localhost:5432/bitrun"
    )
    # Database pool settings
    db_pool_size: int = 5
    db_pool_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800  # 30 minutes

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    # Security - Data Encryption
    # 32-byte key for AES-256, base64 encoded
    # Generate with: python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
    data_encryption_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32)
    )

    # Security - JWT
    # Random secret generated at startup if not provided (recommended for dev only)
    # In production, JWT_SECRET MUST be explicitly set via environment variable
    jwt_secret: str = Field(default=_JWT_SECRET_AUTO_GENERATED)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """
        Validate critical security settings in production environment.

        Ensures JWT_SECRET is explicitly configured and not auto-generated.
        """
        if self.environment == "production":
            # Check if JWT_SECRET was explicitly set via environment variable
            jwt_secret_from_env = os.environ.get("JWT_SECRET")

            if not jwt_secret_from_env:
                raise ValueError(
                    "JWT_SECRET must be explicitly set in production environment. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )

            if len(jwt_secret_from_env) < 32:
                raise ValueError(
                    "JWT_SECRET must be at least 32 characters long for security. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )

            # Check data encryption key in production
            data_key_from_env = os.environ.get("DATA_ENCRYPTION_KEY")
            if not data_key_from_env:
                raise ValueError(
                    "DATA_ENCRYPTION_KEY must be explicitly set in production environment. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )

        return self

    # Security - Transport Encryption (RSA)
    transport_encryption_enabled: bool = False

    # CORS (stored as string, parsed to list)
    cors_origins: str = Field(default="http://localhost:3000")

    # Trading defaults
    default_max_positions: int = 3

    # Backtest settings
    backtest_equity_curve_limit: int = 1000
    backtest_trades_limit: int = 1000  # Limit number of trades returned in response

    # Execution worker settings
    worker_enabled: bool = True  # Enable/disable automatic strategy execution
    worker_distributed: bool = False  # Use distributed task queue (ARQ) instead of in-process workers
    worker_max_concurrent_jobs: int = 10  # Max concurrent jobs per worker (distributed mode)
    worker_job_timeout: int = 300  # Job timeout in seconds (distributed mode)
    worker_max_consecutive_errors: int = 5

    # Simulator settings (for backtesting)
    simulator_maker_fee: float = 0.0002  # 0.02%
    simulator_taker_fee: float = 0.0005  # 0.05%
    simulator_default_slippage: float = 0.001  # 0.1%

    # Notification settings
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""
    resend_api_key: str = ""
    resend_from: str = ""  # Sender email (must be verified domain in Resend)
    
    # Proxy (for geo-restricted exchange APIs)
    proxy_url: str = ""  # e.g. http://host.docker.internal:6152

    # Sentry APM settings
    sentry_dsn: str = ""  # Sentry DSN for error tracking
    sentry_traces_sample_rate: float = 0.1  # 10% of transactions
    sentry_profiles_sample_rate: float = 0.1  # 10% of profiled transactions

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def get_ccxt_proxy_config() -> dict:
    """Return CCXT proxy kwargs if PROXY_URL is configured, else empty dict."""
    url = get_settings().proxy_url
    if not url:
        return {}
    return {
        "aiohttp_proxy": url,
        "proxies": {
            "http": url,
            "https": url,
        },
    }
