"""
Redis service for caching and JWT blacklist.

Provides:
- JWT token blacklist for logout functionality
- Strategy status caching
- General key-value caching
- Daily equity tracking for P&L calculations
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

from ..core.config import get_settings


class RedisService:
    """
    Redis service for caching and token management.

    Usage:
        redis_service = await get_redis_service()
        await redis_service.set("key", "value", ttl=3600)
        value = await redis_service.get("key")
    """

    # Key prefixes for organization
    PREFIX_JWT_BLACKLIST = "jwt:blacklist:"
    PREFIX_STRATEGY_STATUS = "strategy:status:"
    PREFIX_USER_SESSION = "user:session:"
    PREFIX_RATE_LIMIT = "rate_limit:"
    PREFIX_LOGIN_FAILURES = "login:failures:"
    PREFIX_CACHE = "cache:"
    PREFIX_DAILY_EQUITY = "equity:daily:"

    # Login lockout settings
    LOGIN_FAILURE_THRESHOLD = 5  # Lock after 5 failures
    LOGIN_FAILURE_WINDOW = 900   # 15 minutes window

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    # ==================== JWT Blacklist ====================

    async def blacklist_token(
        self,
        token_jti: str,
        expires_in: int = 3600
    ) -> bool:
        """
        Add a JWT token to the blacklist.

        Args:
            token_jti: The unique token identifier (jti claim)
            expires_in: Seconds until the blacklist entry expires
                       (should match token expiration)

        Returns:
            True if successfully blacklisted
        """
        key = f"{self.PREFIX_JWT_BLACKLIST}{token_jti}"
        await self.redis.setex(key, expires_in, "1")
        return True

    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """
        Check if a JWT token is blacklisted.

        Args:
            token_jti: The unique token identifier

        Returns:
            True if token is blacklisted
        """
        key = f"{self.PREFIX_JWT_BLACKLIST}{token_jti}"
        return await self.redis.exists(key) > 0

    # ==================== Strategy Status Cache ====================

    async def set_strategy_status(
        self,
        strategy_id: str,
        status: str,
        ttl: int = 300
    ) -> bool:
        """
        Cache strategy status for quick lookup.

        Args:
            strategy_id: Strategy UUID
            status: Current status (active, paused, etc.)
            ttl: Time-to-live in seconds (default 5 minutes)
        """
        key = f"{self.PREFIX_STRATEGY_STATUS}{strategy_id}"
        await self.redis.setex(key, ttl, status)
        return True

    async def get_strategy_status(self, strategy_id: str) -> Optional[str]:
        """Get cached strategy status"""
        key = f"{self.PREFIX_STRATEGY_STATUS}{strategy_id}"
        result = await self.redis.get(key)
        return result.decode() if result else None

    async def delete_strategy_status(self, strategy_id: str) -> bool:
        """Remove strategy status from cache"""
        key = f"{self.PREFIX_STRATEGY_STATUS}{strategy_id}"
        return await self.redis.delete(key) > 0

    # ==================== User Session ====================

    async def set_user_session(
        self,
        user_id: str,
        session_data: dict,
        ttl: int = 86400
    ) -> bool:
        """
        Store user session data.

        Args:
            user_id: User UUID
            session_data: Dict with session information
            ttl: Time-to-live (default 24 hours)
        """
        key = f"{self.PREFIX_USER_SESSION}{user_id}"
        await self.redis.setex(key, ttl, json.dumps(session_data))
        return True

    async def get_user_session(self, user_id: str) -> Optional[dict]:
        """Get user session data"""
        key = f"{self.PREFIX_USER_SESSION}{user_id}"
        result = await self.redis.get(key)
        if result:
            return json.loads(result.decode())
        return None

    async def delete_user_session(self, user_id: str) -> bool:
        """Delete user session"""
        key = f"{self.PREFIX_USER_SESSION}{user_id}"
        return await self.redis.delete(key) > 0

    # ==================== Login Failure Tracking ====================

    async def track_login_failure(self, email: str) -> int:
        """
        Track a failed login attempt.

        Args:
            email: User email (case-insensitive)

        Returns:
            Current failure count after increment
        """
        key = f"{self.PREFIX_LOGIN_FAILURES}{email.lower()}"
        count = await self.redis.incr(key)
        if count == 1:
            # Set expiry only on first failure
            await self.redis.expire(key, self.LOGIN_FAILURE_WINDOW)
        return count

    async def is_account_locked(self, email: str) -> bool:
        """
        Check if an account is temporarily locked due to failed login attempts.

        Args:
            email: User email (case-insensitive)

        Returns:
            True if account has exceeded failure threshold
        """
        key = f"{self.PREFIX_LOGIN_FAILURES}{email.lower()}"
        count = await self.redis.get(key)
        return int(count or 0) >= self.LOGIN_FAILURE_THRESHOLD

    async def get_login_failure_count(self, email: str) -> int:
        """
        Get current login failure count.

        Args:
            email: User email (case-insensitive)

        Returns:
            Number of failed login attempts in the current window
        """
        key = f"{self.PREFIX_LOGIN_FAILURES}{email.lower()}"
        count = await self.redis.get(key)
        return int(count) if count else 0

    async def clear_login_failures(self, email: str) -> bool:
        """
        Clear login failure counter on successful login.

        Args:
            email: User email (case-insensitive)

        Returns:
            True if failures were cleared
        """
        key = f"{self.PREFIX_LOGIN_FAILURES}{email.lower()}"
        return await self.redis.delete(key) > 0

    async def get_lockout_remaining_time(self, email: str) -> int:
        """
        Get remaining lockout time in seconds.

        Args:
            email: User email (case-insensitive)

        Returns:
            Seconds until lockout expires, or 0 if not locked
        """
        key = f"{self.PREFIX_LOGIN_FAILURES}{email.lower()}"
        ttl = await self.redis.ttl(key)
        if ttl > 0 and await self.is_account_locked(email):
            return ttl
        return 0

    async def check_account_lockout(self, email: str) -> tuple[bool, int]:
        """Check lockout status in a single Redis pipeline (GET + TTL).

        Returns:
            (is_locked, remaining_seconds) tuple.
        """
        key = f"{self.PREFIX_LOGIN_FAILURES}{email.lower()}"
        pipe = self.redis.pipeline(transaction=False)
        pipe.get(key)
        pipe.ttl(key)
        count_raw, ttl = await pipe.execute()

        is_locked = int(count_raw or 0) >= self.LOGIN_FAILURE_THRESHOLD
        remaining = ttl if (is_locked and ttl > 0) else 0
        return is_locked, remaining

    # ==================== Rate Limiting ====================

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check and update rate limit.

        Args:
            identifier: Unique identifier (e.g., user_id, ip_address)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        key = f"{self.PREFIX_RATE_LIMIT}{identifier}"

        # Get current count
        current = await self.redis.get(key)
        count = int(current) if current else 0

        if count >= max_requests:
            return False, 0

        # Increment and set expiry
        pipe = self.redis.pipeline()
        pipe.incr(key)
        if count == 0:
            pipe.expire(key, window_seconds)
        await pipe.execute()

        return True, max_requests - count - 1

    # ==================== General Cache ====================

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a cache value.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not string)
            ttl: Time-to-live in seconds (optional)
        """
        cache_key = f"{self.PREFIX_CACHE}{key}"

        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        elif not isinstance(value, str):
            value = str(value)

        if ttl:
            await self.redis.setex(cache_key, ttl, value)
        else:
            await self.redis.set(cache_key, value)

        return True

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a cached value.

        Attempts to parse as JSON, returns string if fails.
        """
        cache_key = f"{self.PREFIX_CACHE}{key}"
        result = await self.redis.get(cache_key)

        if result is None:
            return None

        value = result.decode()

        # Try to parse as JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def delete(self, key: str) -> bool:
        """Delete a cached value"""
        cache_key = f"{self.PREFIX_CACHE}{key}"
        return await self.redis.delete(cache_key) > 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists"""
        cache_key = f"{self.PREFIX_CACHE}{key}"
        return await self.redis.exists(cache_key) > 0

    # ==================== Dashboard Cache ====================

    async def cache_dashboard_stats(
        self,
        user_id: str,
        stats: dict,
        ttl: int = 30  # 30 seconds default
    ) -> bool:
        """
        Cache dashboard statistics for quick retrieval.

        Args:
            user_id: User UUID
            stats: Dashboard stats dictionary
            ttl: Time-to-live in seconds (default 30s)

        Returns:
            True if successfully cached
        """
        key = f"dashboard:{user_id}:stats"
        await self.redis.setex(key, ttl, json.dumps(stats))
        return True

    async def get_cached_dashboard_stats(
        self,
        user_id: str
    ) -> Optional[dict]:
        """
        Get cached dashboard statistics.

        Returns:
            Cached stats dict or None if not cached/expired
        """
        key = f"dashboard:{user_id}:stats"
        result = await self.redis.get(key)
        if result:
            return json.loads(result.decode())
        return None

    async def invalidate_dashboard_cache(self, user_id: str) -> bool:
        """Invalidate dashboard cache for a user."""
        key = f"dashboard:{user_id}:stats"
        return await self.redis.delete(key) > 0

    # ==================== Market Data Cache ====================

    async def cache_market_price(
        self,
        symbol: str,
        exchange: str,
        price: float,
        ttl: int = 10  # 10 seconds default
    ) -> bool:
        """
        Cache market price for quick lookup.

        Args:
            symbol: Trading symbol (e.g., "BTC")
            exchange: Exchange name
            price: Current price
            ttl: Time-to-live in seconds
        """
        key = f"market:{exchange}:{symbol}:price"
        await self.redis.setex(key, ttl, str(price))
        return True

    async def get_cached_market_price(
        self,
        symbol: str,
        exchange: str
    ) -> Optional[float]:
        """Get cached market price."""
        key = f"market:{exchange}:{symbol}:price"
        result = await self.redis.get(key)
        if result:
            return float(result.decode())
        return None

    async def cache_market_data(
        self,
        symbol: str,
        exchange: str,
        data: dict,
        ttl: int = 15  # 15 seconds default
    ) -> bool:
        """Cache full market data."""
        key = f"market:{exchange}:{symbol}:data"
        await self.redis.setex(key, ttl, json.dumps(data))
        return True

    async def get_cached_market_data(
        self,
        symbol: str,
        exchange: str
    ) -> Optional[dict]:
        """Get cached market data."""
        key = f"market:{exchange}:{symbol}:data"
        result = await self.redis.get(key)
        if result:
            return json.loads(result.decode())
        return None

    # ==================== Account Balance Cache ====================

    PREFIX_ACCOUNT_BALANCE = "account:balance:"

    async def cache_account_balance(
        self,
        account_id: str,
        balance_data: dict,
        ttl: int = 10  # 10 seconds default
    ) -> bool:
        """
        Cache account balance + positions for short-term reuse.

        Args:
            account_id: Account UUID
            balance_data: Serialised AccountBalanceResponse dict
            ttl: Time-to-live in seconds (default 10s)

        Returns:
            True if successfully cached
        """
        key = f"{self.PREFIX_ACCOUNT_BALANCE}{account_id}"
        await self.redis.setex(key, ttl, json.dumps(balance_data))
        return True

    async def get_cached_account_balance(
        self,
        account_id: str,
    ) -> Optional[dict]:
        """
        Get cached account balance data.

        Returns:
            Cached balance dict or None if not cached / expired
        """
        key = f"{self.PREFIX_ACCOUNT_BALANCE}{account_id}"
        result = await self.redis.get(key)
        if result:
            return json.loads(result.decode())
        return None

    async def invalidate_account_balance(self, account_id: str) -> bool:
        """Invalidate cached balance for an account."""
        key = f"{self.PREFIX_ACCOUNT_BALANCE}{account_id}"
        return await self.redis.delete(key) > 0

    # ==================== Daily Equity Tracking ====================

    async def set_daily_equity(
        self,
        user_id: str,
        date: str,
        equity: float,
        account_breakdown: Optional[dict] = None,
        ttl: int = 172800  # 48 hours - keep yesterday's snapshot
    ) -> bool:
        """
        Store daily equity snapshot for P&L calculations.

        Args:
            user_id: User UUID
            date: Date string in format 'YYYY-MM-DD'
            equity: Total equity value
            account_breakdown: Optional dict of {account_id: equity}
            ttl: Time-to-live in seconds (default 48 hours)

        Returns:
            True if successfully stored
        """
        key = f"{self.PREFIX_DAILY_EQUITY}{user_id}:{date}"
        data = {
            "equity": equity,
            "accounts": account_breakdown or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.redis.setex(key, ttl, json.dumps(data))
        return True

    async def get_daily_equity(
        self,
        user_id: str,
        date: str
    ) -> Optional[dict]:
        """
        Get daily equity snapshot.

        Args:
            user_id: User UUID
            date: Date string in format 'YYYY-MM-DD'

        Returns:
            Dict with equity, accounts breakdown, and timestamp
            or None if not found
        """
        key = f"{self.PREFIX_DAILY_EQUITY}{user_id}:{date}"
        result = await self.redis.get(key)
        if result:
            return json.loads(result.decode())
        return None

    async def get_today_start_equity(
        self,
        user_id: str
    ) -> Optional[float]:
        """
        Get equity at start of today (midnight UTC).

        This is used to calculate daily P&L.

        Returns:
            Equity value at midnight or None if not available
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = await self.get_daily_equity(user_id, today)
        if data:
            return data.get("equity")
        return None

    # ==================== Utility ====================

    async def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return await self.redis.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Close Redis connection"""
        await self.redis.close()


# ==================== Singleton Management ====================

_redis_client: Optional[redis.Redis] = None
_redis_service: Optional[RedisService] = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client.

    Includes health check: if the cached client cannot ping, it is
    discarded and a fresh connection is created (automatic reconnect).
    """
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.ping()
        except Exception:
            logger.warning("Redis client health check failed, reconnecting...")
            try:
                await _redis_client.close()
            except Exception:
                pass
            _redis_client = None

    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(
            str(settings.redis_url),
            encoding="utf-8",
            decode_responses=False,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


async def get_redis_service() -> RedisService:
    """Get or create RedisService instance"""
    global _redis_service
    if _redis_service is None:
        client = await get_redis_client()
        _redis_service = RedisService(client)
    return _redis_service


async def close_redis() -> None:
    """Close Redis connections"""
    global _redis_client, _redis_service
    if _redis_service:
        await _redis_service.close()
    _redis_client = None
    _redis_service = None
