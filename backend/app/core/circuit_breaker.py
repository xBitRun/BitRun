"""
Circuit Breaker Pattern Implementation.

Provides fault tolerance for external service calls by:
- Detecting failures and preventing cascading failures
- Automatically recovering when services become healthy
- Providing fallback behavior during outages

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is down, requests fail fast
- HALF_OPEN: Testing if service has recovered

Usage:
    from app.core.circuit_breaker import circuit_breaker, CircuitBreakerOpen
    
    @circuit_breaker("ai_api")
    async def call_ai_api():
        ...
    
    # Or use the context manager
    async with get_circuit_breaker("exchange_api"):
        result = await some_api_call()
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union

import pybreaker

from .config import get_settings

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker state"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    
    def __init__(self, breaker_name: str, remaining_timeout: float = 0):
        self.breaker_name = breaker_name
        self.remaining_timeout = remaining_timeout
        super().__init__(
            f"Circuit breaker '{breaker_name}' is open. "
            f"Retry after {remaining_timeout:.1f}s"
        )


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker."""
    name: str
    state: CircuitState
    failure_count: int
    success_count: int
    total_calls: int
    failure_rate: float
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "failure_rate": round(self.failure_rate, 4),
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }


class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """
    Listener for circuit breaker state changes.
    
    Logs state transitions and can publish metrics.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.opened_at: Optional[datetime] = None
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
    
    def state_change(
        self,
        cb: pybreaker.CircuitBreaker,
        old_state: pybreaker.CircuitBreakerState,
        new_state: pybreaker.CircuitBreakerState,
    ) -> None:
        """Called when circuit breaker state changes."""
        old_name = old_state.name if hasattr(old_state, 'name') else str(old_state)
        new_name = new_state.name if hasattr(new_state, 'name') else str(new_state)
        
        logger.warning(
            f"Circuit breaker '{self.name}' state changed: {old_name} -> {new_name}"
        )
        
        if new_name == "open":
            self.opened_at = datetime.now(UTC)
            logger.error(
                f"Circuit breaker '{self.name}' OPENED - "
                f"failures={cb.fail_counter}, threshold={cb.fail_max}"
            )
        elif new_name == "closed" and old_name in ("open", "half-open"):
            recovery_time = None
            if self.opened_at:
                recovery_time = (datetime.now(UTC) - self.opened_at).total_seconds()
            logger.info(
                f"Circuit breaker '{self.name}' CLOSED - "
                f"service recovered (recovery_time={recovery_time:.1f}s)"
                if recovery_time else f"service recovered"
            )
            self.opened_at = None
    
    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception) -> None:
        """Called when a failure is recorded."""
        self.last_failure_time = datetime.now(UTC)
        logger.debug(
            f"Circuit breaker '{self.name}' recorded failure: {type(exc).__name__}"
        )
    
    def success(self, cb: pybreaker.CircuitBreaker) -> None:
        """Called when a success is recorded."""
        self.last_success_time = datetime.now(UTC)


class AsyncCircuitBreaker:
    """
    Async-friendly circuit breaker wrapper.
    
    Wraps pybreaker's CircuitBreaker for async operations with:
    - Custom exception handling
    - Statistics tracking
    - Prometheus metrics integration
    """
    
    # Default settings
    DEFAULT_FAIL_MAX = 5  # Open after 5 failures
    DEFAULT_RESET_TIMEOUT = 30  # 30 seconds before half-open
    DEFAULT_EXCLUDE_EXCEPTIONS = ()  # Exceptions that don't count as failures
    
    # Global registry of circuit breakers
    _breakers: dict[str, "AsyncCircuitBreaker"] = {}
    
    def __init__(
        self,
        name: str,
        fail_max: int = DEFAULT_FAIL_MAX,
        reset_timeout: float = DEFAULT_RESET_TIMEOUT,
        exclude: tuple[type[Exception], ...] = DEFAULT_EXCLUDE_EXCEPTIONS,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Unique name for this breaker
            fail_max: Number of failures before opening
            reset_timeout: Seconds before attempting recovery
            exclude: Exception types that don't count as failures
        """
        self.name = name
        self.listener = CircuitBreakerListener(name)
        
        self._breaker = pybreaker.CircuitBreaker(
            fail_max=fail_max,
            reset_timeout=reset_timeout,
            exclude=list(exclude),
            listeners=[self.listener],
            name=name,
        )
        
        # Track total calls for metrics
        self._total_calls = 0
        self._success_count = 0
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        state = self._breaker.current_state
        # Handle both string and object with .name attribute (pybreaker version compatibility)
        state_name = state.name if hasattr(state, 'name') else str(state)
        if state_name == "closed":
            return CircuitState.CLOSED
        elif state_name == "open":
            return CircuitState.OPEN
        else:
            return CircuitState.HALF_OPEN
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == CircuitState.OPEN
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._breaker.fail_counter
    
    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        total = self._total_calls
        failures = self._breaker.fail_counter
        successes = self._success_count
        
        failure_rate = failures / total if total > 0 else 0.0
        
        return CircuitBreakerStats(
            name=self.name,
            state=self.state,
            failure_count=failures,
            success_count=successes,
            total_calls=total,
            failure_rate=failure_rate,
            last_failure_time=self.listener.last_failure_time,
            last_success_time=self.listener.last_success_time,
            opened_at=self.listener.opened_at,
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: If function raises an exception
        """
        self._total_calls += 1
        
        # Check if circuit is open (handle both string and object with .name attribute)
        state = self._breaker.current_state
        state_name = state.name if hasattr(state, 'name') else str(state)
        if state_name == "open":
            # Calculate remaining timeout
            remaining = self._breaker.reset_timeout
            if hasattr(self._breaker, '_state_storage'):
                opened_at = getattr(self._breaker._state_storage, 'opened_at', None)
                if opened_at:
                    # Convert datetime to timestamp if needed
                    if isinstance(opened_at, datetime):
                        opened_at = opened_at.timestamp()
                    elapsed = time.time() - opened_at
                    remaining = max(0, self._breaker.reset_timeout - elapsed)
            
            raise CircuitBreakerOpen(self.name, remaining)
        
        try:
            # Execute the function directly instead of using pybreaker's
            # call_async, which has compatibility issues with Python >= 3.13.
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
        except Exception as e:
            # Record failure with pybreaker's state machine
            self._record_failure(e)
            raise
        
        # Record success with pybreaker's state machine
        self._success_count += 1
        self._record_success()
        return result
    
    def _record_success(self) -> None:
        """Record a successful call with pybreaker's state machine."""
        try:
            self._breaker.call(lambda: None)
        except Exception:
            pass
    
    def _record_failure(self, exc: Exception) -> None:
        """Record a failed call with pybreaker's state machine."""
        def raise_exc():
            raise exc
        try:
            self._breaker.call(raise_exc)
        except Exception:
            pass
    
    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._breaker.close()
        logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    @classmethod
    def get(
        cls,
        name: str,
        fail_max: int = DEFAULT_FAIL_MAX,
        reset_timeout: float = DEFAULT_RESET_TIMEOUT,
        exclude: tuple[type[Exception], ...] = DEFAULT_EXCLUDE_EXCEPTIONS,
    ) -> "AsyncCircuitBreaker":
        """
        Get or create a circuit breaker by name.
        
        Circuit breakers are cached by name, so multiple calls with
        the same name return the same instance.
        """
        if name not in cls._breakers:
            cls._breakers[name] = cls(name, fail_max, reset_timeout, exclude)
        return cls._breakers[name]
    
    @classmethod
    def get_all_stats(cls) -> list[CircuitBreakerStats]:
        """Get statistics for all circuit breakers."""
        return [breaker.stats for breaker in cls._breakers.values()]
    
    @classmethod
    def reset_all(cls) -> None:
        """Reset all circuit breakers."""
        for breaker in cls._breakers.values():
            breaker.reset()


# ==================== Decorators ====================

T = TypeVar("T")


def circuit_breaker(
    name: str,
    fail_max: int = AsyncCircuitBreaker.DEFAULT_FAIL_MAX,
    reset_timeout: float = AsyncCircuitBreaker.DEFAULT_RESET_TIMEOUT,
    exclude: tuple[type[Exception], ...] = (),
    fallback: Optional[Callable[..., T]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to wrap a function with circuit breaker protection.
    
    Args:
        name: Circuit breaker name
        fail_max: Failures before opening
        reset_timeout: Recovery timeout in seconds
        exclude: Exceptions that don't count as failures
        fallback: Optional fallback function to call when circuit is open
        
    Usage:
        @circuit_breaker("ai_api", fail_max=3, reset_timeout=60)
        async def call_ai():
            ...
        
        # With fallback
        @circuit_breaker("exchange_api", fallback=lambda: default_value)
        async def get_price():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker = AsyncCircuitBreaker.get(name, fail_max, reset_timeout, exclude)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            try:
                return await breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpen:
                if fallback is not None:
                    result = fallback(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            try:
                # For sync functions, we need to run the breaker call
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(breaker.call(func, *args, **kwargs))
            except CircuitBreakerOpen:
                if fallback is not None:
                    return fallback(*args, **kwargs)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ==================== Context Manager ====================

@asynccontextmanager
async def get_circuit_breaker(
    name: str,
    fail_max: int = AsyncCircuitBreaker.DEFAULT_FAIL_MAX,
    reset_timeout: float = AsyncCircuitBreaker.DEFAULT_RESET_TIMEOUT,
):
    """
    Async context manager for circuit breaker.
    
    Usage:
        async with get_circuit_breaker("api") as breaker:
            result = await some_api_call()
            
        # Errors in the block are tracked by the circuit breaker
    """
    breaker = AsyncCircuitBreaker.get(name, fail_max, reset_timeout)
    
    if breaker.is_open:
        raise CircuitBreakerOpen(name, breaker._breaker.reset_timeout)
    
    try:
        yield breaker
        # Success - record it using internal state machine
        breaker._breaker._state.on_success(breaker._breaker)
        breaker._success_count += 1
    except Exception as e:
        # Failure - record it using internal error handler
        breaker._breaker._inc_counter()
        breaker.listener.failure(breaker._breaker, e)
        raise


# ==================== Predefined Circuit Breakers ====================

# AI API circuit breaker (more tolerant - AI APIs can be slow)
def get_ai_circuit_breaker() -> AsyncCircuitBreaker:
    """Get circuit breaker for AI API calls."""
    return AsyncCircuitBreaker.get(
        name="ai_api",
        fail_max=5,
        reset_timeout=60,  # 1 minute recovery
        exclude=(asyncio.TimeoutError,),  # Timeouts don't trip the breaker
    )


# Exchange API circuit breaker (stricter - exchanges should be reliable)
def get_exchange_circuit_breaker(exchange: str) -> AsyncCircuitBreaker:
    """Get circuit breaker for exchange API calls."""
    return AsyncCircuitBreaker.get(
        name=f"exchange_{exchange}",
        fail_max=3,
        reset_timeout=30,  # 30 second recovery
    )


# Market data circuit breaker (tolerant - can use cached data)
def get_market_data_circuit_breaker() -> AsyncCircuitBreaker:
    """Get circuit breaker for market data calls."""
    return AsyncCircuitBreaker.get(
        name="market_data",
        fail_max=5,
        reset_timeout=15,  # 15 second recovery
    )


# ==================== Health Check ====================

def get_circuit_breaker_health() -> dict:
    """
    Get health status of all circuit breakers.
    
    Returns:
        Dict with circuit breaker health information
    """
    all_stats = AsyncCircuitBreaker.get_all_stats()
    
    open_breakers = [s for s in all_stats if s.state == CircuitState.OPEN]
    
    return {
        "healthy": len(open_breakers) == 0,
        "total_breakers": len(all_stats),
        "open_breakers": len(open_breakers),
        "breakers": [s.to_dict() for s in all_stats],
    }
