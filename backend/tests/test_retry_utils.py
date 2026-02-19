"""
Unit tests for retry utilities.

Tests cover:
- Error classification (transient vs permanent)
- Error window tracking
- Exponential backoff calculation
- Retry with backoff
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
import time

from app.core.retry_utils import (
    ErrorType,
    ErrorWindow,
    classify_error,
    calculate_backoff_delay,
    retry_with_backoff,
)


class TestClassifyError:
    """Tests for error classification."""

    def test_transient_network_errors(self):
        """Network errors should be classified as transient."""
        # Connection errors
        assert classify_error(ConnectionError("connection refused")) == ErrorType.TRANSIENT
        assert classify_error(ConnectionResetError("connection reset")) == ErrorType.TRANSIENT
        assert classify_error(TimeoutError("request timed out")) == ErrorType.TRANSIENT

        # String-based errors
        assert classify_error(Exception("connection timeout")) == ErrorType.TRANSIENT
        assert classify_error(Exception("socket error")) == ErrorType.TRANSIENT
        assert classify_error(Exception("network unreachable")) == ErrorType.TRANSIENT
        assert classify_error(Exception("dns resolution failed")) == ErrorType.TRANSIENT

    def test_transient_rate_limiting(self):
        """Rate limiting errors should be classified as transient."""
        assert classify_error(Exception("rate limit exceeded")) == ErrorType.TRANSIENT
        assert classify_error(Exception("too many requests")) == ErrorType.TRANSIENT
        assert classify_error(Exception("API throttled")) == ErrorType.TRANSIENT
        assert classify_error(Exception("HTTP 429 error")) == ErrorType.TRANSIENT

    def test_transient_service_unavailable(self):
        """Service unavailability should be classified as transient."""
        assert classify_error(Exception("service unavailable (503)")) == ErrorType.TRANSIENT
        assert classify_error(Exception("bad gateway 502")) == ErrorType.TRANSIENT
        assert classify_error(Exception("gateway timeout 504")) == ErrorType.TRANSIENT

    def test_transient_database_errors(self):
        """Transient database errors should be classified correctly."""
        assert classify_error(Exception("deadlock detected")) == ErrorType.TRANSIENT
        assert classify_error(Exception("lock wait timeout exceeded")) == ErrorType.TRANSIENT
        assert classify_error(Exception("connection pool exhausted")) == ErrorType.TRANSIENT
        assert classify_error(Exception("too many connections")) == ErrorType.TRANSIENT

    def test_permanent_auth_errors(self):
        """Authentication errors should be classified as permanent."""
        assert classify_error(Exception("unauthorized access")) == ErrorType.PERMANENT
        assert classify_error(Exception("forbidden - access denied")) == ErrorType.PERMANENT
        assert classify_error(Exception("invalid api key")) == ErrorType.PERMANENT
        assert classify_error(Exception("authentication failed")) == ErrorType.PERMANENT
        assert classify_error(Exception("HTTP 401 unauthorized")) == ErrorType.PERMANENT
        assert classify_error(Exception("HTTP 403 forbidden")) == ErrorType.PERMANENT

    def test_permanent_not_found_errors(self):
        """Not found errors should be classified as permanent."""
        assert classify_error(Exception("resource not found")) == ErrorType.PERMANENT
        assert classify_error(Exception("account does not exist")) == ErrorType.PERMANENT
        assert classify_error(Exception("invalid parameter")) == ErrorType.PERMANENT
        assert classify_error(Exception("HTTP 404 not found")) == ErrorType.PERMANENT

    def test_permanent_config_errors(self):
        """Configuration errors should be classified as permanent."""
        assert classify_error(Exception("config error: missing value")) == ErrorType.PERMANENT
        assert classify_error(Exception("missing required field")) == ErrorType.PERMANENT
        assert classify_error(Exception("validation error")) == ErrorType.PERMANENT

    def test_permanent_business_errors(self):
        """Business logic errors should be classified as permanent."""
        assert classify_error(Exception("insufficient balance")) == ErrorType.PERMANENT
        assert classify_error(Exception("insufficient funds")) == ErrorType.PERMANENT
        assert classify_error(Exception("position not found")) == ErrorType.PERMANENT

    def test_unknown_errors_default_to_transient(self):
        """Unknown errors should default to transient for safety."""
        assert classify_error(Exception("some random error")) == ErrorType.UNKNOWN
        assert classify_error(ValueError("unexpected value")) == ErrorType.UNKNOWN
        assert classify_error(RuntimeError("runtime issue")) == ErrorType.UNKNOWN


class TestErrorWindow:
    """Tests for error window tracking."""

    def test_initial_state(self):
        """Error window should start empty."""
        window = ErrorWindow(window_seconds=60, max_errors=3)
        assert window.error_count == 0
        assert not window.should_stop
        assert window.oldest_error_age is None

    def test_record_error_increments_count(self):
        """Recording errors should increment count."""
        window = ErrorWindow(window_seconds=60, max_errors=3)
        window.record_error()
        assert window.error_count == 1
        window.record_error()
        assert window.error_count == 2

    def test_should_stop_when_threshold_reached(self):
        """should_stop should be True when max_errors reached."""
        window = ErrorWindow(window_seconds=60, max_errors=3)

        window.record_error()
        assert not window.should_stop

        window.record_error()
        assert not window.should_stop

        window.record_error()
        assert window.should_stop

    def test_reset_clears_all_errors(self):
        """Reset should clear all recorded errors."""
        window = ErrorWindow(window_seconds=60, max_errors=3)
        window.record_error()
        window.record_error()
        window.record_error()

        assert window.should_stop

        window.reset()

        assert window.error_count == 0
        assert not window.should_stop
        assert window.oldest_error_age is None

    def test_old_errors_pruned(self):
        """Errors outside the window should be pruned."""
        window = ErrorWindow(window_seconds=0.1, max_errors=3)  # 100ms window

        window.record_error()
        assert window.error_count == 1

        # Wait for window to expire
        time.sleep(0.15)

        # Old error should be pruned on next access
        assert window.error_count == 0
        assert not window.should_stop

    def test_oldest_error_age(self):
        """oldest_error_age should return age of oldest error."""
        window = ErrorWindow(window_seconds=60, max_errors=3)

        window.record_error()
        time.sleep(0.05)
        window.record_error()

        age = window.oldest_error_age
        assert age is not None
        assert age >= 0.05

    def test_window_boundary(self):
        """Errors exactly at boundary should be included."""
        window = ErrorWindow(window_seconds=1, max_errors=2)

        window.record_error()
        time.sleep(0.6)
        window.record_error()

        # Both should still be in window
        assert window.error_count == 2


class TestCalculateBackoffDelay:
    """Tests for exponential backoff calculation."""

    def test_exponential_growth(self):
        """Delay should grow exponentially with attempts."""
        delays = [
            calculate_backoff_delay(attempt=i, jitter=False)
            for i in range(6)
        ]

        # base_delay * 2^attempt
        assert delays[0] == 2.0   # 2 * 2^0
        assert delays[1] == 4.0   # 2 * 2^1
        assert delays[2] == 8.0   # 2 * 2^2
        assert delays[3] == 16.0  # 2 * 2^3
        assert delays[4] == 32.0  # 2 * 2^4
        assert delays[5] == 60.0  # capped at max_delay

    def test_max_delay_cap(self):
        """Delay should be capped at max_delay."""
        # Even with high attempt number
        delay = calculate_backoff_delay(attempt=100, base_delay=2.0, max_delay=30.0, jitter=False)
        assert delay == 30.0

    def test_custom_base_delay(self):
        """Custom base delay should be respected."""
        delay = calculate_backoff_delay(attempt=0, base_delay=5.0, jitter=False)
        assert delay == 5.0

    def test_jitter_adds_randomization(self):
        """Jitter should randomize delay between 0 and calculated delay."""
        # With jitter, delays should vary (high probability)
        delays = [
            calculate_backoff_delay(attempt=2, jitter=True)
            for _ in range(100)
        ]

        # Should have some variation (not all same value)
        unique_delays = set(delays)
        assert len(unique_delays) > 50  # Most should be unique

        # All should be within bounds
        for delay in delays:
            assert 0 <= delay <= 8.0  # 2.0 * 2^2

    def test_no_jitter_returns_exact_delay(self):
        """Without jitter, should return exact calculated delay."""
        delays = [
            calculate_backoff_delay(attempt=3, jitter=False)
            for _ in range(10)
        ]

        # All should be exactly the same
        assert len(set(delays)) == 1
        assert delays[0] == 16.0


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Should succeed immediately if function succeeds."""
        func = AsyncMock(return_value="success")

        success, error = await retry_with_backoff(
            func, max_attempts=3, base_delay=0.1
        )

        assert success is True
        assert error is None
        assert func.call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Should succeed after some retries."""
        func = AsyncMock()
        func.side_effect = [
            Exception("temporary error"),
            Exception("temporary error"),
            "success",
        ]

        success, error = await retry_with_backoff(
            func, max_attempts=3, base_delay=0.01
        )

        assert success is True
        assert error is None
        assert func.call_count == 3

    @pytest.mark.asyncio
    async def test_failure_after_max_attempts(self):
        """Should fail after exhausting all attempts."""
        func = AsyncMock(side_effect=Exception("persistent error"))

        success, error = await retry_with_backoff(
            func, max_attempts=3, base_delay=0.01
        )

        assert success is False
        assert isinstance(error, Exception)
        assert str(error) == "persistent error"
        assert func.call_count == 3

    @pytest.mark.asyncio
    async def test_permanent_error_no_retry(self):
        """Permanent errors should not trigger retries."""
        func = AsyncMock(side_effect=Exception("unauthorized access"))

        success, error = await retry_with_backoff(
            func, max_attempts=3, base_delay=0.01
        )

        assert success is False
        assert isinstance(error, Exception)
        assert "unauthorized" in str(error).lower()
        assert func.call_count == 1  # No retries for permanent error

    @pytest.mark.asyncio
    async def test_custom_retry_on_exception_types(self):
        """Should only retry on specified exception types."""
        class CustomError(Exception):
            pass

        func = AsyncMock(side_effect=ValueError("not retryable"))

        # Non-retryable exception should propagate up
        with pytest.raises(ValueError, match="not retryable"):
            await retry_with_backoff(
                func,
                max_attempts=3,
                base_delay=0.01,
                retry_on=(CustomError,),  # Only retry on CustomError
            )

        assert func.call_count == 1  # No retry for ValueError

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        """Should pass arguments to the function."""
        func = AsyncMock(return_value="result")

        await retry_with_backoff(
            func,
            "arg1", "arg2",
            kwarg1="value1",
            max_attempts=1,
        )

        func.assert_called_once_with("arg1", "arg2", kwarg1="value1")


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_error_window_with_backoff_scenario(self):
        """Simulate a typical error handling scenario."""
        window = ErrorWindow(window_seconds=60, max_errors=3)
        attempt = 0

        # Simulate 3 transient errors
        for _ in range(3):
            error = Exception("connection timeout")
            error_type = classify_error(error)

            assert error_type == ErrorType.TRANSIENT

            window.record_error()
            delay = calculate_backoff_delay(
                attempt=attempt,
                base_delay=2.0,
                jitter=False,
            )
            attempt += 1

        # Should now be at threshold
        assert window.should_stop
        assert window.error_count == 3

        # Reset on success
        window.reset()
        assert not window.should_stop

    @pytest.mark.asyncio
    async def test_full_retry_flow(self):
        """Test a complete retry flow with transient errors."""
        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("network timeout")
            return "success"

        success, error = await retry_with_backoff(
            flaky_operation,
            max_attempts=5,
            base_delay=0.01,
            max_delay=0.1,
        )

        assert success is True
        assert error is None
        assert call_count == 3
