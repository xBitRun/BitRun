"""
Tests for Redis service.

Covers: RedisService caching, JWT blacklist, rate limiting, session management
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.redis_service import RedisService


class TestRedisService:
    """Tests for RedisService"""

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create a mock Redis client"""
        redis = AsyncMock()
        
        # Storage for mock data
        storage = {}
        
        async def mock_setex(key, ttl, value):
            storage[key] = value
            return True
        
        async def mock_set(key, value):
            storage[key] = value
            return True
        
        async def mock_get(key):
            value = storage.get(key)
            if value is not None:
                if isinstance(value, str):
                    return value.encode()
                return value
            return None
        
        async def mock_delete(key):
            if key in storage:
                del storage[key]
                return 1
            return 0
        
        async def mock_exists(key):
            return 1 if key in storage else 0
        
        async def mock_incr(key):
            if key not in storage:
                storage[key] = b"0"
            current = int(storage[key])
            storage[key] = str(current + 1).encode()
            return current + 1
        
        async def mock_expire(key, ttl):
            return True
        
        async def mock_ttl(key):
            return 300 if key in storage else -2
        
        redis.setex = AsyncMock(side_effect=mock_setex)
        redis.set = mock_set
        redis.get = mock_get
        redis.delete = mock_delete
        redis.exists = mock_exists
        redis.incr = mock_incr
        redis.expire = mock_expire
        redis.ttl = mock_ttl
        redis.ping = AsyncMock(return_value=True)
        redis.close = AsyncMock()
        
        # Mock pipeline
        pipeline = MagicMock()
        pipeline.incr = MagicMock()
        pipeline.expire = MagicMock()
        pipeline.execute = AsyncMock(return_value=[1, True])
        redis.pipeline = MagicMock(return_value=pipeline)
        
        redis._storage = storage  # Expose storage for testing
        
        return redis

    @pytest_asyncio.fixture
    async def service(self, mock_redis):
        """Create RedisService with mocked Redis"""
        return RedisService(mock_redis)

    # ==================== JWT Blacklist Tests ====================

    @pytest.mark.asyncio
    async def test_blacklist_token(self, service, mock_redis):
        """Test adding token to blacklist"""
        result = await service.blacklist_token("token_jti_123", expires_in=3600)
        
        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self, service, mock_redis):
        """Test checking blacklisted token"""
        # Add token to blacklist
        await service.blacklist_token("token_123")
        
        result = await service.is_token_blacklisted("token_123")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self, service, mock_redis):
        """Test checking non-blacklisted token"""
        result = await service.is_token_blacklisted("nonexistent_token")
        
        assert result is False

    # ==================== Strategy Status Cache Tests ====================

    @pytest.mark.asyncio
    async def test_set_strategy_status(self, service, mock_redis):
        """Test setting strategy status"""
        result = await service.set_strategy_status(
            "strategy-uuid-123", "active", ttl=300
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_strategy_status(self, service, mock_redis):
        """Test getting strategy status"""
        await service.set_strategy_status("strategy-123", "active")
        
        result = await service.get_strategy_status("strategy-123")
        
        assert result == "active"

    @pytest.mark.asyncio
    async def test_get_strategy_status_not_found(self, service, mock_redis):
        """Test getting non-existent strategy status"""
        result = await service.get_strategy_status("nonexistent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_strategy_status(self, service, mock_redis):
        """Test deleting strategy status"""
        await service.set_strategy_status("strategy-123", "active")
        
        result = await service.delete_strategy_status("strategy-123")
        
        assert result is True
        
        # Verify deleted
        status = await service.get_strategy_status("strategy-123")
        assert status is None

    # ==================== User Session Tests ====================

    @pytest.mark.asyncio
    async def test_set_user_session(self, service, mock_redis):
        """Test setting user session"""
        session_data = {"role": "admin", "permissions": ["read", "write"]}
        
        result = await service.set_user_session(
            "user-123", session_data, ttl=86400
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_user_session(self, service, mock_redis):
        """Test getting user session"""
        session_data = {"role": "admin", "login_time": "2024-01-01"}
        await service.set_user_session("user-123", session_data)
        
        result = await service.get_user_session("user-123")
        
        assert result == session_data

    @pytest.mark.asyncio
    async def test_get_user_session_not_found(self, service, mock_redis):
        """Test getting non-existent session"""
        result = await service.get_user_session("nonexistent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_user_session(self, service, mock_redis):
        """Test deleting user session"""
        await service.set_user_session("user-123", {"data": "test"})
        
        result = await service.delete_user_session("user-123")
        
        assert result is True

    # ==================== Login Failure Tracking Tests ====================

    @pytest.mark.asyncio
    async def test_track_login_failure(self, service, mock_redis):
        """Test tracking login failure"""
        count = await service.track_login_failure("test@example.com")
        
        assert count == 1

    @pytest.mark.asyncio
    async def test_track_multiple_login_failures(self, service, mock_redis):
        """Test tracking multiple login failures"""
        await service.track_login_failure("test@example.com")
        await service.track_login_failure("test@example.com")
        count = await service.track_login_failure("test@example.com")
        
        assert count == 3

    @pytest.mark.asyncio
    async def test_track_login_failure_case_insensitive(self, service, mock_redis):
        """Test that email is case insensitive"""
        await service.track_login_failure("Test@Example.COM")
        count = await service.track_login_failure("test@example.com")
        
        assert count == 2

    @pytest.mark.asyncio
    async def test_is_account_locked_false(self, service, mock_redis):
        """Test account not locked with few failures"""
        await service.track_login_failure("test@example.com")
        
        result = await service.is_account_locked("test@example.com")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_is_account_locked_true(self, service, mock_redis):
        """Test account locked after threshold"""
        for _ in range(5):
            await service.track_login_failure("test@example.com")
        
        result = await service.is_account_locked("test@example.com")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_login_failure_count(self, service, mock_redis):
        """Test getting login failure count"""
        await service.track_login_failure("test@example.com")
        await service.track_login_failure("test@example.com")
        
        count = await service.get_login_failure_count("test@example.com")
        
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_login_failure_count_zero(self, service, mock_redis):
        """Test getting failure count for new email"""
        count = await service.get_login_failure_count("new@example.com")
        
        assert count == 0

    @pytest.mark.asyncio
    async def test_clear_login_failures(self, service, mock_redis):
        """Test clearing login failures"""
        await service.track_login_failure("test@example.com")
        
        result = await service.clear_login_failures("test@example.com")
        
        assert result is True
        
        count = await service.get_login_failure_count("test@example.com")
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_lockout_remaining_time(self, service, mock_redis):
        """Test getting lockout remaining time"""
        for _ in range(5):
            await service.track_login_failure("test@example.com")
        
        remaining = await service.get_lockout_remaining_time("test@example.com")
        
        # Mock returns 300 for TTL
        assert remaining == 300

    # ==================== Rate Limiting Tests ====================

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, service, mock_redis):
        """Test rate limit check when allowed"""
        allowed, remaining = await service.check_rate_limit(
            "user-123", max_requests=10, window_seconds=60
        )
        
        assert allowed is True
        assert remaining == 9

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, service, mock_redis):
        """Test rate limit check when exceeded"""
        # Manually set the count to max
        key = f"{service.PREFIX_RATE_LIMIT}user-123"
        mock_redis._storage[key] = b"10"
        
        allowed, remaining = await service.check_rate_limit(
            "user-123", max_requests=10, window_seconds=60
        )
        
        assert allowed is False
        assert remaining == 0

    # ==================== General Cache Tests ====================

    @pytest.mark.asyncio
    async def test_set_string_value(self, service, mock_redis):
        """Test caching string value"""
        result = await service.set("my_key", "my_value", ttl=300)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_set_dict_value(self, service, mock_redis):
        """Test caching dict value"""
        data = {"name": "test", "count": 42}
        
        result = await service.set("my_dict", data, ttl=300)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_set_list_value(self, service, mock_redis):
        """Test caching list value"""
        data = [1, 2, 3, "four"]
        
        result = await service.set("my_list", data)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_string_value(self, service, mock_redis):
        """Test getting cached string"""
        await service.set("key", "value")
        
        result = await service.get("key")
        
        assert result == "value"

    @pytest.mark.asyncio
    async def test_get_dict_value(self, service, mock_redis):
        """Test getting cached dict"""
        data = {"name": "test"}
        await service.set("key", data)
        
        result = await service.get("key")
        
        assert result == data

    @pytest.mark.asyncio
    async def test_get_not_found(self, service, mock_redis):
        """Test getting non-existent key"""
        result = await service.get("nonexistent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_key(self, service, mock_redis):
        """Test deleting cached value"""
        await service.set("key", "value")
        
        result = await service.delete("key")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_true(self, service, mock_redis):
        """Test key exists"""
        await service.set("key", "value")
        
        result = await service.exists("key")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, service, mock_redis):
        """Test key not exists"""
        result = await service.exists("nonexistent")
        
        assert result is False

    # ==================== Dashboard Cache Tests ====================

    @pytest.mark.asyncio
    async def test_cache_dashboard_stats(self, service, mock_redis):
        """Test caching dashboard stats"""
        stats = {
            "total_equity": 10000.0,
            "daily_pnl": 500.0,
            "active_strategies": 3,
        }
        
        result = await service.cache_dashboard_stats("user-123", stats)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_cached_dashboard_stats(self, service, mock_redis):
        """Test getting cached dashboard stats"""
        stats = {"total_equity": 10000.0}
        await service.cache_dashboard_stats("user-123", stats)
        
        result = await service.get_cached_dashboard_stats("user-123")
        
        assert result == stats

    @pytest.mark.asyncio
    async def test_get_cached_dashboard_stats_not_found(self, service, mock_redis):
        """Test getting non-cached dashboard stats"""
        result = await service.get_cached_dashboard_stats("user-123")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_dashboard_cache(self, service, mock_redis):
        """Test invalidating dashboard cache"""
        await service.cache_dashboard_stats("user-123", {"data": "test"})
        
        result = await service.invalidate_dashboard_cache("user-123")
        
        assert result is True

    # ==================== Market Data Cache Tests ====================

    @pytest.mark.asyncio
    async def test_cache_market_price(self, service, mock_redis):
        """Test caching market price"""
        result = await service.cache_market_price(
            "BTC", "binance", 50000.0, ttl=10
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_cached_market_price(self, service, mock_redis):
        """Test getting cached market price"""
        await service.cache_market_price("BTC", "binance", 50000.0)
        
        result = await service.get_cached_market_price("BTC", "binance")
        
        assert result == 50000.0

    @pytest.mark.asyncio
    async def test_get_cached_market_price_not_found(self, service, mock_redis):
        """Test getting non-cached market price"""
        result = await service.get_cached_market_price("ETH", "okx")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_market_data(self, service, mock_redis):
        """Test caching full market data"""
        data = {
            "price": 50000.0,
            "volume": 1000000.0,
            "change_24h": 2.5,
        }
        
        result = await service.cache_market_data("BTC", "binance", data)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_cached_market_data(self, service, mock_redis):
        """Test getting cached market data"""
        data = {"price": 50000.0, "volume": 1000000.0}
        await service.cache_market_data("BTC", "binance", data)
        
        result = await service.get_cached_market_data("BTC", "binance")
        
        assert result == data

    # ==================== Daily Equity Tests ====================

    @pytest.mark.asyncio
    async def test_set_daily_equity(self, service, mock_redis):
        """Test setting daily equity"""
        result = await service.set_daily_equity(
            "user-123",
            "2024-01-15",
            10000.0,
            account_breakdown={"account-1": 6000.0, "account-2": 4000.0}
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_daily_equity(self, service, mock_redis):
        """Test getting daily equity"""
        await service.set_daily_equity("user-123", "2024-01-15", 10000.0)
        
        result = await service.get_daily_equity("user-123", "2024-01-15")
        
        assert result is not None
        assert result["equity"] == 10000.0
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_daily_equity_not_found(self, service, mock_redis):
        """Test getting non-existent daily equity"""
        result = await service.get_daily_equity("user-123", "2020-01-01")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_today_start_equity(self, service, mock_redis):
        """Test getting today's start equity"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await service.set_daily_equity("user-123", today, 15000.0)
        
        result = await service.get_today_start_equity("user-123")
        
        assert result == 15000.0

    @pytest.mark.asyncio
    async def test_get_today_start_equity_not_set(self, service, mock_redis):
        """Test getting today's start equity when not set"""
        result = await service.get_today_start_equity("user-123")
        
        assert result is None

    # ==================== Utility Tests ====================

    @pytest.mark.asyncio
    async def test_ping_success(self, service, mock_redis):
        """Test successful ping"""
        result = await service.ping()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self, service, mock_redis):
        """Test failed ping"""
        mock_redis.ping.side_effect = Exception("Connection refused")
        
        result = await service.ping()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_close(self, service, mock_redis):
        """Test closing connection"""
        await service.close()
        
        mock_redis.close.assert_called_once()

    # ==================== Account Balance Cache Tests ====================

    @pytest.mark.asyncio
    async def test_cache_account_balance(self, service, mock_redis):
        """Test caching account balance"""
        balance_data = {
            "equity": 10000.0,
            "available_balance": 5000.0,
            "positions": [],
        }
        
        result = await service.cache_account_balance("account-123", balance_data)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_cached_account_balance(self, service, mock_redis):
        """Test getting cached account balance"""
        balance_data = {"equity": 10000.0}
        await service.cache_account_balance("account-123", balance_data)
        
        result = await service.get_cached_account_balance("account-123")
        
        assert result == balance_data

    @pytest.mark.asyncio
    async def test_get_cached_account_balance_not_found(self, service, mock_redis):
        """Test getting non-cached account balance"""
        result = await service.get_cached_account_balance("nonexistent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_account_balance(self, service, mock_redis):
        """Test invalidating account balance cache"""
        await service.cache_account_balance("account-123", {"equity": 10000.0})
        
        result = await service.invalidate_account_balance("account-123")
        
        assert result is True
        
        cached = await service.get_cached_account_balance("account-123")
        assert cached is None

    # ==================== Additional Edge Case Tests ====================

    @pytest.mark.asyncio
    async def test_check_account_lockout_pipeline(self, service, mock_redis):
        """Test check_account_lockout uses pipeline for efficiency"""
        # Setup pipeline mock to return locked state
        pipeline = MagicMock()
        pipeline.get = MagicMock()
        pipeline.ttl = MagicMock()
        pipeline.execute = AsyncMock(return_value=[b"5", 300])
        mock_redis.pipeline = MagicMock(return_value=pipeline)
        
        is_locked, remaining = await service.check_account_lockout("test@example.com")
        
        assert is_locked is True
        assert remaining == 300
        mock_redis.pipeline.assert_called_once_with(transaction=False)

    @pytest.mark.asyncio
    async def test_check_account_lockout_not_locked(self, service, mock_redis):
        """Test check_account_lockout when not locked"""
        pipeline = MagicMock()
        pipeline.get = MagicMock()
        pipeline.ttl = MagicMock()
        pipeline.execute = AsyncMock(return_value=[b"2", 300])  # Below threshold
        mock_redis.pipeline = MagicMock(return_value=pipeline)
        
        is_locked, remaining = await service.check_account_lockout("test@example.com")
        
        assert is_locked is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_check_account_lockout_no_failures(self, service, mock_redis):
        """Test check_account_lockout with no failures"""
        pipeline = MagicMock()
        pipeline.get = MagicMock()
        pipeline.ttl = MagicMock()
        pipeline.execute = AsyncMock(return_value=[None, -2])
        mock_redis.pipeline = MagicMock(return_value=pipeline)
        
        is_locked, remaining = await service.check_account_lockout("new@example.com")
        
        assert is_locked is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_get_lockout_remaining_time_not_locked(self, service, mock_redis):
        """Test lockout remaining time when not locked"""
        # Account has some failures but not locked
        await service.track_login_failure("test@example.com")
        
        remaining = await service.get_lockout_remaining_time("test@example.com")
        
        # Not locked (only 1 failure), so remaining should be 0
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_set_numeric_value(self, service, mock_redis):
        """Test caching numeric value (stored as string, returned as JSON parsed value)"""
        result = await service.set("my_number", 42)
        
        assert result is True
        
        # Value is stored as string "42", but get() parses JSON, so returns int 42
        cached = await service.get("my_number")
        assert cached == 42

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, service, mock_redis):
        """Test caching value without TTL"""
        result = await service.set("key_no_ttl", "value")
        
        assert result is True
        
        # Verify redis.set was used (not setex)
        cached = await service.get("key_no_ttl")
        assert cached == "value"

    @pytest.mark.asyncio
    async def test_delete_strategy_status_not_exists(self, service, mock_redis):
        """Test deleting non-existent strategy status"""
        result = await service.delete_strategy_status("nonexistent-strategy")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_login_failures_no_failures(self, service, mock_redis):
        """Test clearing login failures when none exist"""
        result = await service.clear_login_failures("clean@example.com")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_dashboard_cache_not_exists(self, service, mock_redis):
        """Test invalidating non-existent dashboard cache"""
        result = await service.invalidate_dashboard_cache("nonexistent-user")
        
        assert result is False


class TestRedisServiceSingleton:
    """Tests for Redis singleton management"""

    @pytest.mark.asyncio
    async def test_get_redis_service(self):
        """Test getting Redis service singleton"""
        with patch("app.services.redis_service.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            
            with patch("app.services.redis_service.redis.from_url") as mock_from_url:
                mock_client = AsyncMock()
                mock_from_url.return_value = mock_client
                
                from app.services.redis_service import (
                    get_redis_service,
                    close_redis,
                    _redis_service,
                    _redis_client,
                )
                
                # Reset globals
                import app.services.redis_service as redis_module
                redis_module._redis_service = None
                redis_module._redis_client = None
                
                service = await get_redis_service()
                
                assert service is not None
                assert isinstance(service, RedisService)
                
                # Cleanup
                await close_redis()

    @pytest.mark.asyncio
    async def test_close_redis(self):
        """Test closing Redis connections"""
        with patch("app.services.redis_service.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            
            with patch("app.services.redis_service.redis.from_url") as mock_from_url:
                mock_client = AsyncMock()
                mock_from_url.return_value = mock_client
                
                import app.services.redis_service as redis_module
                redis_module._redis_service = None
                redis_module._redis_client = None
                
                service = await redis_module.get_redis_service()
                
                await redis_module.close_redis()
                
                assert redis_module._redis_service is None
                assert redis_module._redis_client is None

    @pytest.mark.asyncio
    async def test_get_redis_client_reconnect_on_ping_failure(self):
        """Test that get_redis_client reconnects when ping fails"""
        import app.services.redis_service as redis_module
        
        with patch("app.services.redis_service.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            
            # First client will fail ping
            old_client = AsyncMock()
            old_client.ping = AsyncMock(side_effect=Exception("Connection lost"))
            old_client.close = AsyncMock()
            
            # New client will succeed
            new_client = AsyncMock()
            new_client.ping = AsyncMock(return_value=True)
            
            with patch("app.services.redis_service.redis.from_url") as mock_from_url:
                mock_from_url.return_value = new_client
                
                # Set the old failing client
                redis_module._redis_client = old_client
                redis_module._redis_service = None
                
                # Should reconnect
                client = await redis_module.get_redis_client()
                
                # Old client should have been closed
                old_client.close.assert_called_once()
                
                # Should return new client
                assert client is new_client
                
                # Cleanup
                redis_module._redis_client = None

    @pytest.mark.asyncio
    async def test_get_redis_client_reconnect_close_error_handled(self):
        """Test that close error during reconnect is handled gracefully"""
        import app.services.redis_service as redis_module
        
        with patch("app.services.redis_service.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            
            # Old client fails ping AND close
            old_client = AsyncMock()
            old_client.ping = AsyncMock(side_effect=Exception("Connection lost"))
            old_client.close = AsyncMock(side_effect=Exception("Close failed"))
            
            new_client = AsyncMock()
            new_client.ping = AsyncMock(return_value=True)
            
            with patch("app.services.redis_service.redis.from_url") as mock_from_url:
                mock_from_url.return_value = new_client
                
                redis_module._redis_client = old_client
                redis_module._redis_service = None
                
                # Should handle close error and still reconnect
                client = await redis_module.get_redis_client()
                
                assert client is new_client
                
                # Cleanup
                redis_module._redis_client = None
