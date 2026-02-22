"""
Retry Utilities for Worker Error Handling

Provides error classification, error window tracking, and exponential backoff
utilities for robust worker error handling.

Key Components:
- ErrorType: Classifies errors as transient or permanent
- ErrorWindow: Tracks error frequency within a time window
- classify_error: Determines error type from exception
- calculate_backoff_delay: Computes exponential backoff with jitter
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types for retry decisions."""

    TRANSIENT = "transient"  # Temporary errors - should retry
    PERMANENT = "permanent"  # Permanent errors - should stop immediately
    UNKNOWN = "unknown"  # Unknown errors - treat as transient


# Patterns for error classification
_TRANSIENT_PATTERNS = (
    # Network errors
    "connection",
    "timeout",
    "timed out",
    "network",
    "socket",
    "dns",
    "refused",
    "reset",
    "unreachable",
    # Rate limiting
    "rate limit",
    "too many requests",
    "throttl",
    "429",
    # Temporary service issues
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "503",
    "502",
    "504",
    # Database transient errors
    "deadlock",
    "lock wait timeout",
    "connection pool",
    "too many connections",
    # Redis transient errors
    "redis",
    "i/o error",
)

_PERMANENT_PATTERNS = (
    # Authentication/Authorization
    "unauthorized",
    "forbidden",
    "auth",
    "invalid api key",
    "invalid credentials",
    "access denied",
    "401",
    "403",
    # Not found / Invalid
    "not found",
    "does not exist",
    "invalid",
    "malformed",
    "404",
    "400",
    # Configuration errors
    "config",
    "missing required",
    "validation error",
    # Business logic errors
    "insufficient balance",
    "insufficient funds",
    "position not found",
)


def classify_error(error: Exception) -> ErrorType:
    """
    Classify an exception as transient or permanent.

    Transient errors are temporary failures that may succeed on retry:
    - Network issues (connection reset, timeout)
    - Rate limiting
    - Service temporarily unavailable

    Permanent errors will never succeed regardless of retries:
    - Authentication failures
    - Invalid configuration
    - Resource not found

    Args:
        error: The exception to classify

    Returns:
        ErrorType indicating whether to retry or stop
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Check for permanent error patterns first
    for pattern in _PERMANENT_PATTERNS:
        if pattern in error_str or pattern in error_type:
            return ErrorType.PERMANENT

    # Check for transient error patterns
    for pattern in _TRANSIENT_PATTERNS:
        if pattern in error_str or pattern in error_type:
            return ErrorType.TRANSIENT

    # Default to transient (safer to retry unknown errors)
    return ErrorType.UNKNOWN


@dataclass
class ErrorWindow:
    """
    Tracks error frequency within a sliding time window.

    Used to implement circuit breaker-like behavior: if too many errors
    occur within the window, the worker should stop and report an error.

    Attributes:
        window_seconds: Duration of the tracking window
        max_errors: Maximum errors allowed before should_stop becomes True
    """

    window_seconds: int = 600  # 10 minutes default
    max_errors: int = 5

    _error_times: list[float] = field(default_factory=list, repr=False)

    def record_error(self) -> None:
        """
        Record an error occurrence.

        Automatically prunes errors outside the current window.
        """
        now = time.time()
        self._error_times.append(now)
        self._prune_old_errors(now)
        logger.debug(
            f"Error recorded, count in window: {self.error_count}/{self.max_errors}"
        )

    def _prune_old_errors(self, now: float) -> None:
        """Remove errors outside the current window."""
        cutoff = now - self.window_seconds
        self._error_times = [t for t in self._error_times if t > cutoff]

    @property
    def error_count(self) -> int:
        """Current number of errors within the window."""
        self._prune_old_errors(time.time())
        return len(self._error_times)

    @property
    def should_stop(self) -> bool:
        """
        Check if error threshold has been reached.

        Returns:
            True if max_errors exceeded within the window
        """
        return self.error_count >= self.max_errors

    @property
    def oldest_error_age(self) -> Optional[float]:
        """
        Age of the oldest error in the window, in seconds.

        Returns None if no errors in window.
        """
        self._prune_old_errors(time.time())
        if not self._error_times:
            return None
        return time.time() - self._error_times[0]

    def reset(self) -> None:
        """Clear all recorded errors (call after successful operation)."""
        self._error_times.clear()
        logger.debug("Error window reset")

    def __str__(self) -> str:
        return (
            f"ErrorWindow(errors={self.error_count}/{self.max_errors}, "
            f"window={self.window_seconds}s)"
        )


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Uses full jitter strategy: delay = random(0, min(max, base * 2^attempt))

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap in seconds
        jitter: Whether to add randomization

    Returns:
        Delay in seconds before next retry
    """
    # Exponential backoff: base * 2^attempt
    delay = base_delay * (2**attempt)

    # Cap at max delay
    delay = min(delay, max_delay)

    # Add jitter to prevent thundering herd
    if jitter:
        # Full jitter: random between 0 and delay
        delay = random.uniform(0, delay)

    return delay


async def retry_with_backoff(
    func,
    *args,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retry_on: tuple = (Exception,),
    **kwargs,
) -> tuple[bool, Optional[Exception]]:
    """
    Execute a function with exponential backoff retry.

    Args:
        func: Async function to execute
        max_attempts: Maximum number of attempts
        base_delay: Base delay for exponential backoff
        max_delay: Maximum delay cap
        jitter: Whether to add randomization
        retry_on: Tuple of exception types to retry on

    Returns:
        Tuple of (success: bool, last_error: Optional[Exception])
    """
    last_error = None

    for attempt in range(max_attempts):
        try:
            await func(*args, **kwargs)
            return True, None
        except retry_on as e:
            last_error = e
            error_type = classify_error(e)

            if error_type == ErrorType.PERMANENT:
                logger.warning(f"Permanent error, not retrying: {e}")
                return False, e

            if attempt < max_attempts - 1:
                delay = calculate_backoff_delay(attempt, base_delay, max_delay, jitter)
                logger.info(
                    f"Retry attempt {attempt + 1}/{max_attempts} "
                    f"after {delay:.1f}s: {e}"
                )
                await asyncio.sleep(delay)

    return False, last_error
