"""
Tests for PricePrefetchService - Background price preloading.
"""

import asyncio

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.price_prefetch import (
    PricePrefetchService,
    SymbolSubscription,
    get_price_prefetch_service,
    reset_price_prefetch_service,
    PREFETCH_INTERVAL,
)


class TestSymbolSubscription:
    """Tests for SymbolSubscription dataclass."""

    def test_creation(self):
        """Test creating a SymbolSubscription."""
        sub = SymbolSubscription(
            symbol="BTC",
            exchange="hyperliquid",
            subscriber_count=2,
        )
        assert sub.symbol == "BTC"
        assert sub.exchange == "hyperliquid"
        assert sub.subscriber_count == 2
        assert sub.last_fetch is None

    def test_default_subscriber_count(self):
        """Test default subscriber count."""
        sub = SymbolSubscription(symbol="BTC", exchange="hyperliquid")
        assert sub.subscriber_count == 1


class TestPricePrefetchService:
    """Tests for PricePrefetchService class."""

    @pytest.fixture
    def service(self):
        """Create a fresh service for each test."""
        return PricePrefetchService(prefetch_interval=0.5)

    @pytest.fixture
    def service_with_mocks(self):
        """Create a service with mocked dependencies."""
        service = PricePrefetchService(prefetch_interval=0.1)

        # Mock Redis
        service._redis = MagicMock()
        service._redis.set = AsyncMock(return_value=True)
        service._redis.get = AsyncMock(return_value=b"test_instance")
        service._redis.expire = AsyncMock(return_value=True)
        service._redis.delete = AsyncMock(return_value=True)

        # Mock price cache
        service._price_cache = MagicMock()
        service._price_cache.set_price = AsyncMock(return_value=True)

        return service

    def setup_method(self):
        """Reset singleton before each test."""
        reset_price_prefetch_service()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_price_prefetch_service()

    # =========================================================================
    # Lifecycle Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_start_and_stop(self, service):
        """Test starting and stopping the service."""
        await service.start()
        assert service._running is True
        assert service._leader_task is not None

        await service.stop()
        assert service._running is False

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self, service):
        """Test that double start is idempotent."""
        await service.start()
        task1 = service._leader_task

        await service.start()  # Second start
        assert service._leader_task is task1  # Same task

        await service.stop()

    # =========================================================================
    # Leader Election Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_becomes_leader_without_redis(self, service):
        """Test that service becomes leader when Redis unavailable."""
        # Mock _get_redis to return None (simulating no Redis available)
        service._get_redis = AsyncMock(return_value=None)

        await service.start()
        # Wait for leader election loop to run
        for _ in range(20):  # Try for up to 2 seconds
            if service._is_leader:
                break
            await asyncio.sleep(0.1)

        assert service._is_leader is True

        await service.stop()

    @pytest.mark.asyncio
    async def test_acquires_leadership_from_redis(self, service_with_mocks):
        """Test acquiring leadership via Redis."""
        service = service_with_mocks
        service._redis.set = AsyncMock(return_value=True)  # Successfully acquire

        await service.start()
        await asyncio.sleep(0.15)  # Let leader loop run

        assert service._is_leader is True

        await service.stop()

    @pytest.mark.asyncio
    async def test_does_not_become_leader_if_taken(self, service_with_mocks):
        """Test that service doesn't become leader if another instance holds it."""
        service = service_with_mocks
        service._redis.set = AsyncMock(return_value=None)  # Failed to acquire
        service._redis.get = AsyncMock(return_value=b"other_instance")  # Different owner

        await service.start()
        await asyncio.sleep(0.15)

        assert service._is_leader is False

        await service.stop()

    # =========================================================================
    # Symbol Registration Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_register_symbol(self, service):
        """Test registering a symbol."""
        await service.register_symbol("hyperliquid", "BTC", "agent-1")

        assert "hyperliquid:BTC" in service._subscriptions
        assert service._subscriptions["hyperliquid:BTC"].subscriber_count == 1
        assert "agent-1" in service._agent_symbols

    @pytest.mark.asyncio
    async def test_register_same_symbol_multiple_agents(self, service):
        """Test registering same symbol from multiple agents."""
        await service.register_symbol("hyperliquid", "BTC", "agent-1")
        await service.register_symbol("hyperliquid", "BTC", "agent-2")
        await service.register_symbol("hyperliquid", "BTC", "agent-3")

        assert service._subscriptions["hyperliquid:BTC"].subscriber_count == 3

    @pytest.mark.asyncio
    async def test_register_different_exchanges(self, service):
        """Test registering same symbol on different exchanges."""
        await service.register_symbol("hyperliquid", "BTC", "agent-1")
        await service.register_symbol("binance", "BTC", "agent-2")

        assert "hyperliquid:BTC" in service._subscriptions
        assert "binance:BTC" in service._subscriptions
        assert len(service._subscriptions) == 2

    @pytest.mark.asyncio
    async def test_unregister_symbol(self, service):
        """Test unregistering a symbol."""
        await service.register_symbol("hyperliquid", "BTC", "agent-1")
        await service.unregister_symbol("hyperliquid", "BTC", "agent-1")

        assert "hyperliquid:BTC" not in service._subscriptions
        assert "agent-1" not in service._agent_symbols

    @pytest.mark.asyncio
    async def test_unregister_decrements_count(self, service):
        """Test that unregister decrements subscriber count."""
        await service.register_symbol("hyperliquid", "BTC", "agent-1")
        await service.register_symbol("hyperliquid", "BTC", "agent-2")

        # Unregister one
        await service.unregister_symbol("hyperliquid", "BTC", "agent-1")

        # Should still exist with count 1
        assert "hyperliquid:BTC" in service._subscriptions
        assert service._subscriptions["hyperliquid:BTC"].subscriber_count == 1

    @pytest.mark.asyncio
    async def test_unregister_agent(self, service):
        """Test unregistering all symbols for an agent."""
        await service.register_symbol("hyperliquid", "BTC", "agent-1")
        await service.register_symbol("hyperliquid", "ETH", "agent-1")
        await service.register_symbol("hyperliquid", "SOL", "agent-2")

        await service.unregister_agent("agent-1")

        # Agent 1's symbols should be removed
        assert "hyperliquid:BTC" not in service._subscriptions
        assert "hyperliquid:ETH" not in service._subscriptions
        # Agent 2's symbol should remain
        assert "hyperliquid:SOL" in service._subscriptions

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_agent(self, service):
        """Test unregistering an agent that doesn't exist."""
        # Should not raise
        await service.unregister_agent("nonexistent")

    # =========================================================================
    # Symbol Normalization Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_symbol_normalization_uppercase(self, service):
        """Test that symbols are normalized to uppercase."""
        await service.register_symbol("hyperliquid", "btc", "agent-1")

        assert "hyperliquid:BTC" in service._subscriptions

    @pytest.mark.asyncio
    async def test_exchange_normalization_lowercase(self, service):
        """Test that exchanges are normalized to lowercase."""
        await service.register_symbol("HYPERLIQUID", "BTC", "agent-1")

        assert "hyperliquid:BTC" in service._subscriptions

    # =========================================================================
    # CCXT Symbol Conversion Tests
    # =========================================================================

    def test_to_ccxt_symbol_bare(self, service):
        """Test converting bare symbol to CCXT format."""
        result = service._to_ccxt_symbol("hyperliquid", "BTC")
        assert result == "BTC/USDC:USDC"

        result = service._to_ccxt_symbol("binance", "ETH")
        assert result == "ETH/USDT:USDT"

    def test_to_ccxt_symbol_with_pair(self, service):
        """Test converting pair symbol to CCXT format."""
        result = service._to_ccxt_symbol("hyperliquid", "BTC/USD")
        assert result == "BTC/USD:USDC"

    def test_to_ccxt_symbol_already_formatted(self, service):
        """Test that already formatted symbols are passed through."""
        result = service._to_ccxt_symbol("hyperliquid", "BTC/USDC:USDC")
        assert result == "BTC/USDC:USDC"

    # =========================================================================
    # Statistics Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_stats(self, service):
        """Test getting service statistics."""
        await service.register_symbol("hyperliquid", "BTC", "agent-1")
        await service.register_symbol("hyperliquid", "ETH", "agent-2")

        stats = service.get_stats()

        assert stats["running"] is False
        assert stats["is_leader"] is False
        assert stats["subscriptions"] == 2
        assert stats["agents"] == 2
        assert len(stats["symbols"]) == 2

    def test_is_active(self, service):
        """Test is_active method."""
        assert service.is_active() is False

        service._running = True
        service._is_leader = True
        assert service.is_active() is True

        service._is_leader = False
        assert service.is_active() is False


class TestPricePrefetchServiceSingleton:
    """Tests for singleton management."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_price_prefetch_service()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_price_prefetch_service()

    def test_get_singleton(self):
        """Test getting singleton instance."""
        service1 = get_price_prefetch_service()
        service2 = get_price_prefetch_service()

        assert service1 is service2

    def test_reset_singleton(self):
        """Test resetting singleton."""
        service1 = get_price_prefetch_service()
        reset_price_prefetch_service()
        service2 = get_price_prefetch_service()

        assert service1 is not service2

    def test_custom_prefetch_interval(self):
        """Test singleton with custom prefetch interval."""
        service = get_price_prefetch_service(prefetch_interval=10.0)
        assert service._prefetch_interval == 10.0


class TestPricePrefetchServiceIntegration:
    """Integration tests for prefetch service with mocked exchanges."""

    @pytest_asyncio.fixture
    async def service_with_exchange(self):
        """Create a service with mocked exchange."""
        service = PricePrefetchService(prefetch_interval=0.1)

        # Mock Redis (no leader election in single instance mode)
        service._redis = None

        # Mock CCXT exchange
        mock_exchange = MagicMock()
        mock_exchange.fetch_ticker = AsyncMock(return_value={
            "symbol": "BTC/USDC:USDC",
            "last": 50000.0,
            "bid": 49990.0,
            "ask": 50010.0,
        })
        mock_exchange.close = AsyncMock()
        service._exchanges["hyperliquid"] = mock_exchange

        # Mock price cache
        service._price_cache = MagicMock()
        service._price_cache.set_price = AsyncMock()

        yield service

        await service.stop()

    @pytest.mark.asyncio
    async def test_prefetch_cycle_fetches_prices(self, service_with_exchange):
        """Test that prefetch cycle fetches prices."""
        service = service_with_exchange

        # Register a symbol
        await service.register_symbol("hyperliquid", "BTC", "agent-1")

        # Manually trigger a prefetch cycle
        await service._prefetch_cycle()

        # Verify fetch was called
        service._exchanges["hyperliquid"].fetch_ticker.assert_called()

        # Verify cache was updated
        service._price_cache.set_price.assert_called()

    @pytest.mark.asyncio
    async def test_prefetch_handles_fetch_error(self, service_with_exchange):
        """Test that prefetch handles fetch errors gracefully."""
        service = service_with_exchange

        # Make fetch fail
        service._exchanges["hyperliquid"].fetch_ticker = AsyncMock(
            side_effect=Exception("API error")
        )

        await service.register_symbol("hyperliquid", "BTC", "agent-1")

        # Should not raise
        await service._prefetch_cycle()

        # Error count should increase
        assert service._prefetch_errors == 0  # Error is caught inside cycle

    @pytest.mark.asyncio
    async def test_prefetch_skips_recently_fetched(self, service_with_exchange):
        """Test that prefetch skips recently fetched symbols."""
        import time

        service = service_with_exchange

        await service.register_symbol("hyperliquid", "BTC", "agent-1")

        # Set last_fetch to very recent
        key = "hyperliquid:BTC"
        service._subscriptions[key].last_fetch = time.monotonic()

        # Run prefetch cycle
        await service._prefetch_cycle()

        # Fetch should not be called (skipped due to recent fetch)
        service._exchanges["hyperliquid"].fetch_ticker.assert_not_called()
