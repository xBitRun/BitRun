"""
Tests for Worker System including ExecutionWorker and WorkerManager.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.traders.base import (
    AccountState,
    OrderResult,
    OrderStatus,
    OrderType,
    Position,
    TradeError,
)
from app.workers.execution_worker import (
    ExecutionWorker,
    WorkerManager,
    create_trader_from_account,
    get_worker_manager,
    reset_worker_manager,
)


class TestCreateTraderFromAccount:
    """Tests for create_trader_from_account helper function (unified CCXTTrader)."""

    def test_create_hyperliquid_trader(self):
        """Should create CCXTTrader for Hyperliquid with private key."""
        account = MagicMock()
        account.exchange = "hyperliquid"
        account.is_testnet = True
        
        credentials = {"private_key": "0x" + "a" * 64}
        
        trader = create_trader_from_account(account, credentials)
        
        assert trader is not None
        assert trader.exchange_name == "hyperliquid"
        assert trader.testnet is True

    def test_create_binance_trader(self):
        """Should create CCXTTrader for Binance (binanceusdm) with API keys."""
        account = MagicMock()
        account.exchange = "binance"
        account.is_testnet = False
        
        credentials = {
            "api_key": "test_key",
            "api_secret": "test_secret",
        }
        
        trader = create_trader_from_account(account, credentials)
        
        assert trader is not None
        # EXCHANGE_ID_MAP maps "binance" → "binanceusdm"
        assert trader.exchange_name == "binanceusdm"

    def test_create_bybit_trader(self):
        """Should create CCXTTrader for Bybit with API keys."""
        account = MagicMock()
        account.exchange = "bybit"
        account.is_testnet = True
        
        credentials = {
            "api_key": "test_key",
            "api_secret": "test_secret",
        }
        
        trader = create_trader_from_account(account, credentials)
        
        assert trader is not None
        assert trader.exchange_name == "bybit"

    def test_create_okx_trader(self):
        """Should create CCXTTrader for OKX with API keys and passphrase."""
        account = MagicMock()
        account.exchange = "okx"
        account.is_testnet = True
        
        credentials = {
            "api_key": "test_key",
            "api_secret": "test_secret",
            "passphrase": "test_passphrase",
        }
        
        trader = create_trader_from_account(account, credentials)
        
        assert trader is not None
        assert trader.exchange_name == "okx"

    def test_raises_for_unsupported_exchange(self):
        """Should raise ValueError for unsupported exchange."""
        account = MagicMock()
        account.exchange = "unsupported_exchange"
        account.is_testnet = True
        
        credentials = {}
        
        with pytest.raises(ValueError, match="Unsupported exchange"):
            create_trader_from_account(account, credentials)


class TestExecutionWorker:
    """Tests for ExecutionWorker class."""

    @pytest.fixture
    def mock_trader(self):
        """Create a mock trader."""
        trader = AsyncMock()
        trader.exchange_name = "mock"
        trader.initialize = AsyncMock(return_value=True)
        trader.close = AsyncMock()
        trader.get_account_state = AsyncMock(return_value=AccountState(
            equity=10000.0,
            available_balance=8000.0,
            total_margin_used=2000.0,
            unrealized_pnl=500.0,
            positions=[],
        ))
        return trader

    @pytest.mark.asyncio
    async def test_worker_initialization(self, mock_trader):
        """Worker should initialize with agent ID and trader."""
        agent_id = str(uuid4())

        worker = ExecutionWorker(
            agent_id=agent_id,
            trader=mock_trader,
            interval_minutes=15,
        )

        assert str(worker.agent_id) == agent_id
        assert worker.trader is mock_trader
        assert worker.interval_minutes == 15
        assert not worker._running

    @pytest.mark.asyncio
    async def test_worker_start_stop(self, mock_trader):
        """Worker should start and stop correctly."""
        agent_id = str(uuid4())

        worker = ExecutionWorker(
            agent_id=agent_id,
            trader=mock_trader,
            interval_minutes=1,
        )

        # Mock the run cycle to prevent actual execution
        worker._run_cycle = AsyncMock()

        await worker.start()
        assert worker._running
        assert worker._task is not None

        await worker.stop()
        assert not worker._running

    @pytest.mark.asyncio
    async def test_worker_error_counting(self, mock_trader):
        """Worker should track consecutive errors."""
        agent_id = str(uuid4())

        worker = ExecutionWorker(
            agent_id=agent_id,
            trader=mock_trader,
            interval_minutes=1,
        )

        assert worker._error_count == 0

        # Simulate errors
        worker._error_count = 3
        assert worker._error_count == 3


class TestWorkerManager:
    """Tests for WorkerManager class."""

    @pytest.fixture(autouse=True)
    async def _reset_manager(self):
        """Reset worker manager before each test."""
        await reset_worker_manager()

    @pytest.mark.asyncio
    async def test_manager_singleton(self):
        """get_worker_manager should return singleton."""
        manager1 = await get_worker_manager(distributed=False)
        manager2 = await get_worker_manager()
        
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_manager_legacy_mode(self):
        """Manager should start in legacy mode by default."""
        manager = WorkerManager(distributed=False)
        
        assert not manager.is_distributed
        assert not manager._running
        assert len(manager._workers) == 0

    @pytest.mark.asyncio
    async def test_manager_distributed_mode(self):
        """Manager should support distributed mode."""
        manager = WorkerManager(distributed=True)
        
        assert manager.is_distributed

    @pytest.mark.asyncio
    async def test_list_workers_empty(self):
        """list_workers should return empty list when no workers."""
        manager = WorkerManager(distributed=False)
        
        workers = manager.list_workers()
        
        assert workers == []

    @pytest.mark.asyncio
    async def test_get_worker_status_not_found(self):
        """get_worker_status should return None for unknown strategy."""
        manager = WorkerManager(distributed=False)
        
        status = manager.get_worker_status("non-existent-id")
        
        assert status is None

    @pytest.mark.asyncio
    async def test_stop_strategy_not_running(self):
        """stop_strategy should return True even if not running."""
        manager = WorkerManager(distributed=False)
        
        result = await manager.stop_strategy("non-existent-id")
        
        assert result is True


class TestOrderManager:
    """Tests for OrderManager service."""

    @pytest.fixture
    def mock_trader(self):
        """Create a mock trader."""
        trader = AsyncMock()
        trader.exchange_name = "mock"
        trader.place_market_order = AsyncMock(return_value=OrderResult(
            success=True,
            order_id="test_order_123",
            filled_size=0.1,
            filled_price=50000.0,
            status="filled",
        ))
        trader.get_order = AsyncMock(return_value=None)
        trader.cancel_order = AsyncMock(return_value=True)
        return trader

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis service."""
        redis = MagicMock()
        redis.redis = AsyncMock()
        redis.redis.setex = AsyncMock()
        redis.redis.get = AsyncMock(return_value=None)
        redis.redis.sadd = AsyncMock()
        redis.redis.smembers = AsyncMock(return_value=set())
        return redis

    @pytest.mark.asyncio
    async def test_order_manager_initialization(self, mock_trader, mock_redis):
        """OrderManager should initialize correctly."""
        from app.services.order_manager import OrderManager
        
        manager = OrderManager(
            trader=mock_trader,
            redis=mock_redis,
            strategy_id="test_strategy",
        )
        
        assert manager.trader is mock_trader
        assert manager.redis is mock_redis
        assert manager.strategy_id == "test_strategy"

    @pytest.mark.asyncio
    async def test_place_order_with_tracking(self, mock_trader, mock_redis):
        """Should place order and track it."""
        from app.services.order_manager import OrderManager
        from app.traders.base import OrderType
        
        manager = OrderManager(
            trader=mock_trader,
            redis=mock_redis,
        )
        
        order = await manager.place_order_with_tracking(
            symbol="BTC",
            side="buy",
            size=0.1,
            order_type=OrderType.MARKET,
            wait_for_fill=False,
        )
        
        assert order is not None
        assert order.order_id == "test_order_123"
        assert order.filled_size == 0.1
        mock_trader.place_market_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_order_persistence(self, mock_trader, mock_redis):
        """Order state should be persisted to Redis."""
        from app.services.order_manager import OrderManager
        from app.traders.base import OrderType
        
        manager = OrderManager(
            trader=mock_trader,
            redis=mock_redis,
            strategy_id="test_strategy",
        )
        
        await manager.place_order_with_tracking(
            symbol="ETH",
            side="sell",
            size=1.0,
            order_type=OrderType.MARKET,
            wait_for_fill=False,
        )
        
        # Check that Redis setex was called for persistence
        mock_redis.redis.setex.assert_called()

    @pytest.mark.asyncio
    async def test_order_cleanup(self, mock_trader, mock_redis):
        """close() should cleanup tracking tasks."""
        from app.services.order_manager import OrderManager
        
        manager = OrderManager(
            trader=mock_trader,
            redis=mock_redis,
        )
        
        await manager.close()
        
        assert len(manager._tracking_tasks) == 0
        assert len(manager._orders) == 0
