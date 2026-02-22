"""
Sentry APM Integration.

Provides error tracking and performance monitoring via Sentry.

Features:
- Automatic error capture with context
- Performance tracing for requests
- Profiling for hot paths
- Custom tags and context

Usage:
    # Initialize in app startup
    from app.monitoring.sentry import init_sentry, capture_exception, capture_message

    init_sentry()

    # Capture custom errors
    try:
        risky_operation()
    except Exception as e:
        capture_exception(e, tags={"component": "trading"})
"""

import logging
from typing import Any, Callable, Optional

from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Sentry SDK import (optional)
try:
    import sentry_sdk
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    sentry_sdk = None
    logger.warning("Sentry SDK not installed. Error tracking disabled.")


def init_sentry() -> bool:
    """
    Initialize Sentry SDK.

    Returns:
        True if Sentry was initialized successfully, False otherwise.
    """
    if not SENTRY_AVAILABLE:
        logger.info("Sentry SDK not available, skipping initialization")
        return False

    settings = get_settings()

    if not settings.sentry_dsn:
        logger.info("Sentry DSN not configured, skipping initialization")
        return False

    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            release=f"bitrun@{settings.app_version}",
            # Performance monitoring
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            # Enable tracing for specific operations
            enable_tracing=True,
            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                AsyncioIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
            ],
            # Data scrubbing
            send_default_pii=False,
            # Before send hook for filtering
            before_send=_before_send,
            # Attach stack locals
            attach_stacktrace=True,
            # Request bodies
            request_bodies="medium",
            # Max breadcrumbs
            max_breadcrumbs=50,
        )

        # Set common tags
        sentry_sdk.set_tag("app", settings.app_name)
        sentry_sdk.set_tag("environment", settings.environment)

        logger.info(
            f"Sentry initialized: environment={settings.environment}, "
            f"traces_sample_rate={settings.sentry_traces_sample_rate}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def _before_send(event: dict, hint: dict) -> Optional[dict]:
    """
    Filter events before sending to Sentry.

    Use this to:
    - Remove sensitive data
    - Filter out noisy errors
    - Add custom context
    """
    # Get exception info if available
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Filter out common non-errors
        if exc_type.__name__ in (
            "ConnectionResetError",
            "BrokenPipeError",
            "asyncio.CancelledError",
        ):
            return None

        # Filter out 404s and other expected errors
        if hasattr(exc_value, "status_code"):
            if exc_value.status_code in (401, 403, 404):
                return None

    # Remove potentially sensitive data from request
    if "request" in event:
        request = event["request"]

        # Remove auth headers
        if "headers" in request:
            headers = request["headers"]
            for sensitive in ("authorization", "cookie", "x-api-key"):
                if sensitive in headers:
                    headers[sensitive] = "[Filtered]"

        # Remove sensitive body fields
        if "data" in request and isinstance(request["data"], dict):
            for sensitive in ("password", "api_key", "api_secret", "private_key"):
                if sensitive in request["data"]:
                    request["data"][sensitive] = "[Filtered]"

    return event


def capture_exception(
    error: Exception,
    tags: Optional[dict] = None,
    extra: Optional[dict] = None,
    user: Optional[dict] = None,
) -> Optional[str]:
    """
    Capture an exception and send to Sentry.

    Args:
        error: The exception to capture
        tags: Additional tags (key-value pairs)
        extra: Additional context data
        user: User information (id, email, etc.)

    Returns:
        Event ID if captured, None otherwise
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        logger.error(f"Exception (Sentry disabled): {error}")
        return None

    with sentry_sdk.push_scope() as scope:
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        if user:
            scope.set_user(user)

        event_id = sentry_sdk.capture_exception(error)
        logger.debug(f"Captured exception to Sentry: {event_id}")
        return event_id


def capture_message(
    message: str,
    level: str = "info",
    tags: Optional[dict] = None,
    extra: Optional[dict] = None,
) -> Optional[str]:
    """
    Capture a message and send to Sentry.

    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        tags: Additional tags
        extra: Additional context data

    Returns:
        Event ID if captured, None otherwise
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        logger.info(f"Message (Sentry disabled): {message}")
        return None

    with sentry_sdk.push_scope() as scope:
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        event_id = sentry_sdk.capture_message(message, level=level)
        return event_id


def set_user(
    user_id: str, email: Optional[str] = None, name: Optional[str] = None
) -> None:
    """
    Set the current user context for Sentry events.

    Args:
        user_id: User ID
        email: User email (optional)
        name: User name (optional)
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return

    user_data = {"id": user_id}
    if email:
        user_data["email"] = email
    if name:
        user_data["username"] = name

    sentry_sdk.set_user(user_data)


def clear_user() -> None:
    """Clear the current user context."""
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return

    sentry_sdk.set_user(None)


def add_breadcrumb(
    message: str,
    category: str = "info",
    level: str = "info",
    data: Optional[dict] = None,
) -> None:
    """
    Add a breadcrumb for debugging.

    Breadcrumbs are a trail of events that happened before an error.

    Args:
        message: Breadcrumb message
        category: Category (e.g., "http", "query", "user")
        level: Level (debug, info, warning, error)
        data: Additional data
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        return

    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data,
    )


def start_transaction(
    name: str,
    op: str = "task",
    description: Optional[str] = None,
) -> Any:
    """
    Start a performance transaction.

    Use this for monitoring custom operations.

    Args:
        name: Transaction name
        op: Operation type (e.g., "task", "queue", "cron")
        description: Optional description

    Returns:
        Transaction object (use as context manager)

    Usage:
        with start_transaction("process_strategy", op="task") as transaction:
            # ... do work ...
            transaction.set_tag("strategy_id", "123")
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        # Return a no-op context manager
        from contextlib import nullcontext

        return nullcontext()

    return sentry_sdk.start_transaction(
        name=name,
        op=op,
        description=description,
    )


def start_span(
    op: str,
    description: Optional[str] = None,
) -> Any:
    """
    Start a performance span within a transaction.

    Use this for monitoring sub-operations.

    Args:
        op: Operation type
        description: Optional description

    Returns:
        Span object (use as context manager)

    Usage:
        with start_span("db.query", "SELECT users") as span:
            result = await db.execute(query)
            span.set_data("rows", len(result))
    """
    if not SENTRY_AVAILABLE or not sentry_sdk:
        from contextlib import nullcontext

        return nullcontext()

    return sentry_sdk.start_span(op=op, description=description)


# Decorator for automatic error capture
def sentry_trace(name: Optional[str] = None, op: str = "function"):
    """
    Decorator to trace function execution.

    Usage:
        @sentry_trace("process_order", op="task")
        async def process_order(order_id: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        import functools
        import asyncio

        transaction_name = name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with start_transaction(transaction_name, op=op):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with start_transaction(transaction_name, op=op):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
