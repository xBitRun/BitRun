"""
Centralized error handling and sanitization.

Provides:
- Standard error types for the application
- Error sanitization for production environments
- Consistent error response formatting
"""

import logging
from enum import Enum
from typing import Any, Optional

from fastapi import HTTPException, status

from .config import get_settings

logger = logging.getLogger(__name__)

# Import TradeError for type checking (avoid circular import)
try:
    from ..traders.base import TradeError
except ImportError:
    TradeError = None  # type: ignore


class ErrorCode(str, Enum):
    """Standard error codes for the application"""

    # Authentication
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_REVOKED = "AUTH_TOKEN_REVOKED"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_ACCOUNT_LOCKED = "AUTH_ACCOUNT_LOCKED"
    AUTH_RATE_LIMITED = "AUTH_RATE_LIMITED"
    AUTH_EMAIL_EXISTS = "AUTH_EMAIL_EXISTS"

    # Authorization
    AUTHZ_FORBIDDEN = "AUTHZ_FORBIDDEN"
    AUTHZ_RESOURCE_NOT_FOUND = "AUTHZ_RESOURCE_NOT_FOUND"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"

    # External services
    EXCHANGE_ERROR = "EXCHANGE_ERROR"
    EXCHANGE_CONNECTION_FAILED = "EXCHANGE_CONNECTION_FAILED"
    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"
    REDIS_UNAVAILABLE = "REDIS_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"

    # Business logic
    BACKTEST_FAILED = "BACKTEST_FAILED"
    STRATEGY_ERROR = "STRATEGY_ERROR"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class AppError(Exception):
    """
    Base application error with structured information.

    Supports automatic sanitization for production environments.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[dict[str, Any]] = None,
        internal_message: Optional[str] = None,
    ):
        """
        Create an application error.

        Args:
            code: Error code enum for machine-readable identification
            message: User-friendly error message (safe to expose)
            status_code: HTTP status code
            details: Additional details (sanitized in production)
            internal_message: Detailed message for logging only (never exposed)
        """
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.internal_message = internal_message
        super().__init__(message)


def sanitize_error_message(
    error: Exception,
    user_message: str = "An unexpected error occurred",
    include_type: bool = False,
) -> str:
    """
    Sanitize an error message for client response.

    In production: Returns generic user message
    In development: Returns detailed error information

    Args:
        error: The exception to sanitize
        user_message: User-friendly message to show in production
        include_type: Whether to include error type in dev message

    Returns:
        Sanitized error message string
    """
    settings = get_settings()

    if settings.environment == "production":
        return user_message

    # In development/staging, include details
    error_str = str(error)
    if include_type:
        return f"{type(error).__name__}: {error_str}"
    return error_str


def log_and_raise_http_error(
    error: Exception,
    code: ErrorCode,
    user_message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    log_level: str = "error",
) -> None:
    """
    Log an error and raise an HTTPException with sanitized message.

    Args:
        error: The original exception
        code: Error code for identification
        user_message: User-friendly message (shown in production)
        status_code: HTTP status code
        log_level: Logging level (error, warning, info)
    """
    settings = get_settings()

    # Log the full error with traceback
    log_func = getattr(logger, log_level, logger.error)
    log_func(
        f"[{code.value}] {user_message}: {error}",
        exc_info=True if log_level == "error" else False,
    )

    # Build response detail
    if settings.environment == "production":
        detail = user_message
    else:
        detail = f"{user_message}: {error}"

    raise HTTPException(
        status_code=status_code,
        detail=detail,
    )


def create_http_exception(
    code: ErrorCode,
    user_message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    internal_error: Optional[Exception] = None,
    log_error: bool = True,
) -> HTTPException:
    """
    Create an HTTPException with sanitized message.

    Args:
        code: Error code for identification
        user_message: User-friendly message (shown in production)
        status_code: HTTP status code
        internal_error: Optional internal exception for logging
        log_error: Whether to log the error

    Returns:
        HTTPException ready to raise
    """
    settings = get_settings()

    # Log if requested
    if log_error and internal_error:
        logger.error(
            f"[{code.value}] {user_message}: {internal_error}",
            exc_info=True,
        )
    elif log_error:
        logger.error(f"[{code.value}] {user_message}")

    # Build response detail
    if settings.environment == "production":
        detail = user_message
    else:
        if internal_error:
            detail = f"{user_message}: {internal_error}"
        else:
            detail = user_message

    return HTTPException(
        status_code=status_code,
        detail=detail,
    )


# ==================== Pre-built HTTP Exceptions ====================


def backtest_failed_error(error: Exception) -> HTTPException:
    """Create standardized backtest failed error"""
    return create_http_exception(
        code=ErrorCode.BACKTEST_FAILED,
        user_message="Backtest execution failed. Please check your parameters and try again.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        internal_error=error,
    )


def exchange_connection_error(error: Exception, exchange: str = "") -> HTTPException:
    """Create standardized exchange connection error"""
    exchange_info = f" ({exchange})" if exchange else ""
    return create_http_exception(
        code=ErrorCode.EXCHANGE_CONNECTION_FAILED,
        user_message=f"Failed to connect to exchange{exchange_info}. Please verify your credentials.",
        status_code=status.HTTP_502_BAD_GATEWAY,
        internal_error=error,
    )


def exchange_api_error(error: Exception, operation: str = "") -> HTTPException:
    """Create standardized exchange API error"""
    op_info = f" during {operation}" if operation else ""
    settings = get_settings()

    # Check if it's a TradeError with specific error code
    if TradeError and isinstance(error, TradeError):
        error_code = getattr(error, "code", None)
        error_message = getattr(error, "message", str(error))

        if error_code == "AUTH_ERROR":
            # Authentication error - provide clear guidance
            user_message = f"认证失败{op_info}。请检查 API Key 和 Secret Key 是否正确，并确保已启用必要的权限。"
            if settings.environment != "production":
                user_message = f"{user_message} 详细错误: {error_message}"
        elif error_code == "EXCHANGE_ERROR":
            # Exchange-specific error - use the detailed message from TradeError
            user_message = f"交易所 API 错误{op_info}。"
            if settings.environment != "production":
                user_message = f"{user_message} {error_message}"
            else:
                # In production, provide generic message but log the details
                user_message = f"{user_message} 请稍后重试。"
        else:
            # Other TradeError - use generic message with details in dev
            user_message = f"交易所 API 错误{op_info}。"
            if settings.environment != "production":
                user_message = f"{user_message} {error_message}"
            else:
                user_message = f"{user_message} 请稍后重试。"

        return create_http_exception(
            code=ErrorCode.EXCHANGE_ERROR,
            user_message=user_message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            internal_error=error,
        )

    # Generic error handling
    return create_http_exception(
        code=ErrorCode.EXCHANGE_ERROR,
        user_message=f"Exchange API error{op_info}. Please try again later.",
        status_code=status.HTTP_502_BAD_GATEWAY,
        internal_error=error,
    )


def ai_service_error(error: Exception) -> HTTPException:
    """Create standardized AI service error"""
    return create_http_exception(
        code=ErrorCode.AI_SERVICE_ERROR,
        user_message="AI service temporarily unavailable. Please try again later.",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        internal_error=error,
    )


def internal_error(error: Exception, context: str = "") -> HTTPException:
    """Create standardized internal error"""
    ctx = f" ({context})" if context else ""
    return create_http_exception(
        code=ErrorCode.INTERNAL_ERROR,
        user_message=f"An internal error occurred{ctx}. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        internal_error=error,
    )


# ==================== Auth Error Helpers ====================


def auth_error(
    code: ErrorCode,
    status_code: int = status.HTTP_401_UNAUTHORIZED,
    headers: Optional[dict[str, str]] = None,
    **extra_data: Any,
) -> HTTPException:
    """
    Create an auth error with structured detail for frontend i18n.

    The detail is a dict containing:
    - code: Error code for frontend to look up translation
    - Any additional data (e.g., remaining_attempts, remaining_minutes)

    Args:
        code: Error code enum
        status_code: HTTP status code
        headers: Optional response headers
        **extra_data: Additional data to include in detail (e.g., remaining_attempts=3)

    Returns:
        HTTPException with structured detail
    """
    detail = {"code": code.value, **extra_data}
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers=headers,
    )
