"""
Tests for Circuit Breaker pattern implementation.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.circuit_breaker import (
    AsyncCircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
    circuit_breaker,
    get_circuit_breaker_health,
)


class TestAsyncCircuitBreaker:
    """Tests for AsyncCircuitBreaker class."""

    def setup_method(self):
        """Reset circuit breakers before each test."""
        AsyncCircuitBreaker._breakers.clear()

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self):
        """Circuit breaker should start in closed state."""
        breaker = AsyncCircuitBreaker("test_initial", fail_max=3)
        assert breaker.state == CircuitState.CLOSED
        assert not breaker.is_open
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_successful_calls_keep_circuit_closed(self):
        """Successful calls should not affect circuit state."""
        breaker = AsyncCircuitBreaker("test_success", fail_max=3)
        
        async def success_func():
            return "success"
        
        for _ in range(10):
            result = await breaker.call(success_func)
            assert result == "success"
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failures_trip_circuit(self):
        """Circuit should open after fail_max failures."""
        breaker = AsyncCircuitBreaker("test_failures", fail_max=3, reset_timeout=10)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # First 2 failures should keep circuit closed
        for i in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.CLOSED
        
        # Third failure should open the circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open

    @pytest.mark.asyncio
    async def test_open_circuit_raises_exception(self):
        """Open circuit should raise CircuitBreakerOpen immediately."""
        breaker = AsyncCircuitBreaker("test_open", fail_max=1, reset_timeout=10)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        assert breaker.is_open
        
        # Next call should raise CircuitBreakerOpen
        async def another_func():
            return "should not reach"
        
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await breaker.call(another_func)
        
        assert exc_info.value.breaker_name == "test_open"

    @pytest.mark.asyncio
    async def test_excluded_exceptions_dont_trip_circuit(self):
        """Excluded exceptions should not count as failures."""
        breaker = AsyncCircuitBreaker(
            "test_exclude",
            fail_max=1,
            exclude=(asyncio.TimeoutError,),
        )
        
        async def timeout_func():
            raise asyncio.TimeoutError("Timeout")
        
        # TimeoutError should not trip the circuit
        for _ in range(5):
            with pytest.raises(asyncio.TimeoutError):
                await breaker.call(timeout_func)
        
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        """Manual reset should close the circuit."""
        breaker = AsyncCircuitBreaker("test_reset", fail_max=1, reset_timeout=100)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        assert breaker.is_open
        
        # Manual reset
        breaker.reset()
        
        assert breaker.state == CircuitState.CLOSED
        assert not breaker.is_open

    @pytest.mark.asyncio
    async def test_get_creates_singleton(self):
        """get() should return the same instance for the same name."""
        breaker1 = AsyncCircuitBreaker.get("singleton_test")
        breaker2 = AsyncCircuitBreaker.get("singleton_test")
        
        assert breaker1 is breaker2

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Statistics should be tracked correctly."""
        breaker = AsyncCircuitBreaker("test_stats", fail_max=5)
        
        async def success_func():
            return "ok"
        
        async def fail_func():
            raise ValueError("error")
        
        # 3 successes
        for _ in range(3):
            await breaker.call(success_func)
        
        # 2 failures
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(fail_func)
        
        stats = breaker.stats
        assert stats.name == "test_stats"
        assert stats.state == CircuitState.CLOSED
        assert stats.total_calls == 5
        assert stats.success_count == 3
        assert stats.failure_count == 2
        assert stats.failure_rate == 0.4


class TestCircuitBreakerDecorator:
    """Tests for @circuit_breaker decorator."""

    def setup_method(self):
        """Reset circuit breakers before each test."""
        AsyncCircuitBreaker._breakers.clear()

    @pytest.mark.asyncio
    async def test_decorator_protects_function(self):
        """Decorator should protect async function."""
        call_count = 0
        
        @circuit_breaker("decorator_test", fail_max=2)
        async def protected_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("error")
        
        # First two calls should raise ValueError
        for _ in range(2):
            with pytest.raises(ValueError):
                await protected_func()
        
        assert call_count == 2
        
        # Third call should raise CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen):
            await protected_func()
        
        # Function should not be called when circuit is open
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_with_fallback(self):
        """Decorator with fallback should return fallback value when open."""
        @circuit_breaker(
            "fallback_test",
            fail_max=1,
            fallback=lambda: "fallback_value",
        )
        async def failing_func():
            raise ValueError("error")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            await failing_func()
        
        # Should return fallback
        result = await failing_func()
        assert result == "fallback_value"

    @pytest.mark.asyncio
    async def test_decorator_with_async_fallback(self):
        """Decorator should support async fallback functions."""
        async def async_fallback():
            return "async_fallback"
        
        @circuit_breaker(
            "async_fallback_test",
            fail_max=1,
            fallback=async_fallback,
        )
        async def failing_func():
            raise ValueError("error")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            await failing_func()
        
        # Should return async fallback
        result = await failing_func()
        assert result == "async_fallback"


class TestCircuitBreakerHealth:
    """Tests for circuit breaker health reporting."""

    def setup_method(self):
        """Reset circuit breakers before each test."""
        AsyncCircuitBreaker._breakers.clear()

    @pytest.mark.asyncio
    async def test_health_with_no_breakers(self):
        """Health should report healthy when no breakers exist."""
        health = get_circuit_breaker_health()
        
        assert health["healthy"] is True
        assert health["total_breakers"] == 0
        assert health["open_breakers"] == 0

    @pytest.mark.asyncio
    async def test_health_with_closed_breakers(self):
        """Health should report healthy when all breakers are closed."""
        AsyncCircuitBreaker.get("health_test_1")
        AsyncCircuitBreaker.get("health_test_2")
        
        health = get_circuit_breaker_health()
        
        assert health["healthy"] is True
        assert health["total_breakers"] == 2
        assert health["open_breakers"] == 0

    @pytest.mark.asyncio
    async def test_health_with_open_breaker(self):
        """Health should report unhealthy when any breaker is open."""
        breaker = AsyncCircuitBreaker.get("health_open_test", fail_max=1)
        
        async def failing_func():
            raise ValueError("error")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        
        health = get_circuit_breaker_health()
        
        assert health["healthy"] is False
        assert health["total_breakers"] == 1
        assert health["open_breakers"] == 1

    @pytest.mark.asyncio
    async def test_reset_all_breakers(self):
        """reset_all() should reset all circuit breakers."""
        breaker1 = AsyncCircuitBreaker.get("reset_all_1", fail_max=1)
        breaker2 = AsyncCircuitBreaker.get("reset_all_2", fail_max=1)
        
        async def failing_func():
            raise ValueError("error")
        
        # Trip both circuits
        with pytest.raises(ValueError):
            await breaker1.call(failing_func)
        with pytest.raises(ValueError):
            await breaker2.call(failing_func)
        
        assert breaker1.is_open
        assert breaker2.is_open
        
        # Reset all
        AsyncCircuitBreaker.reset_all()
        
        assert not breaker1.is_open
        assert not breaker2.is_open
