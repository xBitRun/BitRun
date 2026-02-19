"""
Tests for task queue service and task definitions.

Covers: TaskQueueService, task functions (execute_strategy_cycle, etc.)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.workers.queue import TaskQueueService
from app.workers.tasks import (
    create_trader_from_account,
    execute_strategy_cycle,
    start_strategy_execution,
    stop_strategy_execution,
    sync_active_strategies,
    get_worker_settings,
    WorkerSettings,
)


# ============================================================================
# TaskQueueService Tests
# ============================================================================

class TestTaskQueueService:
    """Tests for TaskQueueService"""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis pool"""
        redis = AsyncMock()
        
        # Mock job enqueue
        mock_job = MagicMock()
        mock_job.job_id = "test-job-id"
        redis.enqueue_job = AsyncMock(return_value=mock_job)
        
        # Mock ping
        redis.ping = AsyncMock(return_value=True)
        
        # Mock queue info methods
        redis.zcard = AsyncMock(return_value=5)
        redis.hlen = AsyncMock(return_value=10)
        
        return redis

    @pytest.fixture
    def service(self, mock_redis):
        """Create TaskQueueService instance"""
        return TaskQueueService(mock_redis)

    @pytest.mark.asyncio
    async def test_start_strategy(self, service, mock_redis):
        """Test scheduling strategy start"""
        strategy_id = str(uuid4())
        
        job_id = await service.start_strategy(strategy_id)
        
        assert job_id == "test-job-id"
        mock_redis.enqueue_job.assert_called_once()
        call_kwargs = mock_redis.enqueue_job.call_args
        assert call_kwargs[0][0] == "start_strategy_execution"
        assert call_kwargs[0][1] == strategy_id

    @pytest.mark.asyncio
    async def test_start_strategy_with_delay(self, service, mock_redis):
        """Test scheduling strategy start with delay"""
        strategy_id = str(uuid4())
        
        job_id = await service.start_strategy(strategy_id, defer_seconds=60)
        
        assert job_id == "test-job-id"
        call_kwargs = mock_redis.enqueue_job.call_args
        assert call_kwargs[1].get("_defer_by") is not None

    @pytest.mark.asyncio
    async def test_start_strategy_failure(self, service, mock_redis):
        """Test handling start failure"""
        mock_redis.enqueue_job.side_effect = Exception("Redis error")
        
        job_id = await service.start_strategy(str(uuid4()))
        
        assert job_id is None

    @pytest.mark.asyncio
    async def test_stop_strategy(self, service, mock_redis):
        """Test stopping strategy"""
        strategy_id = str(uuid4())
        
        result = await service.stop_strategy(strategy_id)
        
        assert result is True
        mock_redis.enqueue_job.assert_called_once()
        call_kwargs = mock_redis.enqueue_job.call_args
        assert call_kwargs[0][0] == "stop_strategy_execution"

    @pytest.mark.asyncio
    async def test_stop_strategy_failure(self, service, mock_redis):
        """Test handling stop failure"""
        mock_redis.enqueue_job.side_effect = Exception("Redis error")
        
        result = await service.stop_strategy(str(uuid4()))
        
        assert result is False

    @pytest.mark.asyncio
    async def test_trigger_strategy_execution(self, service, mock_redis):
        """Test manual trigger"""
        strategy_id = str(uuid4())
        
        job_id = await service.trigger_strategy_execution(strategy_id)
        
        assert job_id == "test-job-id"
        call_kwargs = mock_redis.enqueue_job.call_args
        assert call_kwargs[0][0] == "execute_strategy_cycle"

    @pytest.mark.asyncio
    async def test_get_job_status(self, service, mock_redis):
        """Test getting job status"""
        with patch("app.workers.queue.Job") as MockJob:
            mock_job = MagicMock()
            mock_info = MagicMock()
            mock_info.function = "execute_strategy_cycle"
            mock_info.status = MagicMock(value="queued")
            mock_info.enqueue_time = datetime.now(UTC)
            mock_info.start_time = None
            mock_info.finish_time = None
            mock_info.success = None
            mock_info.result = None
            mock_info.score = 1
            mock_job.info = AsyncMock(return_value=mock_info)
            MockJob.return_value = mock_job
            
            status = await service.get_job_status("test-job-id")
            
            assert status is not None
            assert status["job_id"] == "test-job-id"
            assert status["function"] == "execute_strategy_cycle"
            assert status["status"] == "queued"

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, service, mock_redis):
        """Test getting status of non-existent job"""
        with patch("app.workers.queue.Job") as MockJob:
            mock_job = MagicMock()
            mock_job.info = AsyncMock(return_value=None)
            MockJob.return_value = mock_job
            
            status = await service.get_job_status("nonexistent")
            
            assert status is None

    @pytest.mark.asyncio
    async def test_get_strategy_job_status(self, service, mock_redis):
        """Test getting strategy-specific job status"""
        strategy_id = str(uuid4())
        
        with patch.object(service, "get_job_status") as mock_get:
            mock_get.return_value = {"status": "queued"}
            
            status = await service.get_strategy_job_status(strategy_id)
            
            mock_get.assert_called_once_with(f"strategy:{strategy_id}")

    @pytest.mark.asyncio
    async def test_is_strategy_scheduled_true(self, service, mock_redis):
        """Test checking if strategy is scheduled (yes)"""
        with patch.object(service, "get_strategy_job_status") as mock_get:
            mock_get.return_value = {"status": "queued"}
            
            result = await service.is_strategy_scheduled(str(uuid4()))
            
            assert result is True

    @pytest.mark.asyncio
    async def test_is_strategy_scheduled_false(self, service, mock_redis):
        """Test checking if strategy is scheduled (no)"""
        with patch.object(service, "get_strategy_job_status") as mock_get:
            mock_get.return_value = None
            
            result = await service.is_strategy_scheduled(str(uuid4()))
            
            assert result is False

    @pytest.mark.asyncio
    async def test_is_strategy_scheduled_completed(self, service, mock_redis):
        """Test checking if completed strategy is scheduled"""
        with patch.object(service, "get_strategy_job_status") as mock_get:
            mock_get.return_value = {"status": "complete"}
            
            result = await service.is_strategy_scheduled(str(uuid4()))
            
            assert result is False

    @pytest.mark.asyncio
    async def test_cancel_job(self, service, mock_redis):
        """Test canceling job"""
        with patch("app.workers.queue.Job") as MockJob:
            mock_job = MagicMock()
            mock_job.abort = AsyncMock()
            MockJob.return_value = mock_job
            
            result = await service.cancel_job("test-job-id")
            
            assert result is True
            mock_job.abort.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_job_failure(self, service, mock_redis):
        """Test cancel job failure"""
        with patch("app.workers.queue.Job") as MockJob:
            mock_job = MagicMock()
            mock_job.abort = AsyncMock(side_effect=Exception("Error"))
            MockJob.return_value = mock_job
            
            result = await service.cancel_job("test-job-id")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_get_queue_info(self, service, mock_redis):
        """Test getting queue info"""
        info = await service.get_queue_info()
        
        assert info["queue_name"] == "bitrun:tasks"
        assert info["queued"] == 5
        assert info["in_progress"] == 5
        assert info["completed"] == 10

    @pytest.mark.asyncio
    async def test_get_queue_info_error(self, service, mock_redis):
        """Test queue info on error"""
        mock_redis.zcard.side_effect = Exception("Redis error")
        
        info = await service.get_queue_info()
        
        assert "error" in info

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, service, mock_redis):
        """Test health check when healthy"""
        health = await service.health_check()
        
        assert health["healthy"] is True
        assert health["redis_connected"] is True
        assert "queue" in health

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, service, mock_redis):
        """Test health check when unhealthy"""
        mock_redis.ping.side_effect = Exception("Connection refused")
        
        health = await service.health_check()
        
        assert health["healthy"] is False
        assert "error" in health


# ============================================================================
# Task Function Tests
# ============================================================================

class TestCreateTraderFromAccount:
    """Tests for create_trader_from_account helper (unified CCXTTrader)"""

    def test_create_hyperliquid_trader(self):
        """Test creating CCXTTrader for Hyperliquid"""
        account = MagicMock()
        account.exchange = "hyperliquid"
        account.is_testnet = True

        credentials = {"private_key": "0x" + "a" * 64}

        with patch("app.traders.ccxt_trader.CCXTTrader") as MockTrader:
            trader = create_trader_from_account(account, credentials)

            MockTrader.assert_called_once_with(
                exchange_id="hyperliquid",
                credentials=credentials,
                testnet=True,
                margin_mode="isolated",
            )

    def test_create_binance_trader(self):
        """Test creating CCXTTrader for Binance"""
        account = MagicMock()
        account.exchange = "binance"
        account.is_testnet = False

        credentials = {"api_key": "key", "api_secret": "secret"}

        with patch("app.traders.ccxt_trader.CCXTTrader") as MockTrader:
            trader = create_trader_from_account(account, credentials)

            MockTrader.assert_called_once_with(
                exchange_id="binanceusdm",
                credentials=credentials,
                testnet=False,
                margin_mode="isolated",
            )

    def test_create_bybit_trader(self):
        """Test creating CCXTTrader for Bybit"""
        account = MagicMock()
        account.exchange = "bybit"
        account.is_testnet = True

        credentials = {"api_key": "key", "api_secret": "secret"}

        with patch("app.traders.ccxt_trader.CCXTTrader") as MockTrader:
            trader = create_trader_from_account(account, credentials)

            MockTrader.assert_called_once_with(
                exchange_id="bybit",
                credentials=credentials,
                testnet=True,
                margin_mode="isolated",
            )

    def test_create_okx_trader(self):
        """Test creating CCXTTrader for OKX"""
        account = MagicMock()
        account.exchange = "okx"
        account.is_testnet = False

        credentials = {
            "api_key": "key",
            "api_secret": "secret",
            "passphrase": "pass",
        }

        with patch("app.traders.ccxt_trader.CCXTTrader") as MockTrader:
            trader = create_trader_from_account(account, credentials)

            MockTrader.assert_called_once_with(
                exchange_id="okx",
                credentials=credentials,
                testnet=False,
                margin_mode="isolated",
            )

    def test_create_unsupported_exchange(self):
        """Test error on unsupported exchange"""
        account = MagicMock()
        account.exchange = "unsupported"

        with pytest.raises(ValueError, match="Unsupported exchange"):
            create_trader_from_account(account, {})


class TestExecuteStrategyCycle:
    """Tests for execute_strategy_cycle task"""

    @pytest.mark.asyncio
    async def test_strategy_not_found(self):
        """Test handling non-existent strategy"""
        ctx = {"redis": AsyncMock()}
        strategy_id = str(uuid4())
        
        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            MockSession.return_value = mock_session
            
            with patch("app.workers.tasks.StrategyRepository") as MockRepo:
                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=None)
                MockRepo.return_value = mock_repo
                
                with patch("app.workers.tasks.AccountRepository"):
                    result = await execute_strategy_cycle(ctx, strategy_id)
                
                    assert result["success"] is False
                    assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_no_active_agent(self):
        """Test handling when no active agent found for strategy"""
        ctx = {"redis": AsyncMock()}
        strategy_id = str(uuid4())

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.commit = AsyncMock()

            # Mock session.execute for the agent query → no active agent found
            mock_agent_result = MagicMock()
            mock_agent_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_agent_result)

            MockSession.return_value = mock_session

            with patch("app.workers.tasks.StrategyRepository") as MockRepo:
                mock_strategy = MagicMock()
                mock_strategy.id = uuid4()

                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=mock_strategy)
                MockRepo.return_value = mock_repo

                with patch("app.workers.tasks.AccountRepository"):
                    result = await execute_strategy_cycle(ctx, strategy_id)

                    assert result["success"] is False
                    assert "No active agent" in result["error"]

    @pytest.mark.asyncio
    async def test_strategy_no_account(self):
        """Test handling strategy without account (no agent bound)"""
        ctx = {"redis": AsyncMock()}
        strategy_id = str(uuid4())

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.commit = AsyncMock()

            # Mock session.execute for the agent query → no active agent found
            mock_agent_result = MagicMock()
            mock_agent_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_agent_result)

            MockSession.return_value = mock_session

            with patch("app.workers.tasks.StrategyRepository") as MockRepo:
                mock_strategy = MagicMock()
                mock_strategy.account_id = None
                mock_strategy.id = uuid4()

                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=mock_strategy)
                mock_repo.update_status = AsyncMock()
                MockRepo.return_value = mock_repo

                with patch("app.workers.tasks.AccountRepository"):
                    result = await execute_strategy_cycle(ctx, strategy_id)

                    assert result["success"] is False
                    assert "No active agent" in result["error"]


class TestStartStrategyExecution:
    """Tests for start_strategy_execution task"""

    @pytest.mark.asyncio
    async def test_start_strategy(self):
        """Test starting strategy execution"""
        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        mock_redis.enqueue_job = AsyncMock(return_value=mock_job)
        
        ctx = {"redis": mock_redis}
        strategy_id = str(uuid4())
        
        result = await start_strategy_execution(ctx, strategy_id)
        
        assert result["status"] == "scheduled"
        assert result["job_id"] == "job-123"
        mock_redis.enqueue_job.assert_called_once()


class TestStopStrategyExecution:
    """Tests for stop_strategy_execution task"""

    @pytest.mark.asyncio
    async def test_stop_strategy(self):
        """Test stopping strategy execution"""
        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}
        strategy_id = str(uuid4())
        
        with patch("app.workers.tasks.Job") as MockJob:
            mock_job = MagicMock()
            mock_job.abort = AsyncMock()
            MockJob.return_value = mock_job
            
            result = await stop_strategy_execution(ctx, strategy_id)
            
            assert result["status"] == "stopped"
            mock_job.abort.assert_called_once()


class TestSyncActiveStrategies:
    """Tests for sync_active_strategies task"""

    @pytest.mark.asyncio
    async def test_sync_no_strategies(self):
        """Test sync with no active strategies"""
        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            MockSession.return_value = mock_session

            with patch("app.workers.tasks.StrategyRepository") as MockRepo:
                mock_repo = MagicMock()
                mock_repo.get_active_strategies = AsyncMock(return_value=[])
                MockRepo.return_value = mock_repo

                result = await sync_active_strategies(ctx)

                assert result["started"] == 0
                assert result["skipped"] == 0
                assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_sync_with_existing_job(self):
        """Test sync when job already exists"""
        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            MockSession.return_value = mock_session

            # Mock heartbeat functions
            with patch("app.workers.tasks.mark_stale_agents_as_error", AsyncMock(return_value=0)):
                with patch("app.workers.tasks.clear_all_heartbeats_for_active_agents", AsyncMock(return_value=0)):
                    # Mock agent query
                    mock_agent = MagicMock()
                    mock_agent.id = uuid4()
                    mock_agent.strategy = MagicMock()
                    mock_agent.execution_interval_minutes = 30
                    mock_agent.next_run_at = None

                    mock_scalars = MagicMock()
                    mock_scalars.all.return_value = [mock_agent]

                    mock_result = MagicMock()
                    mock_result.scalars.return_value = mock_scalars

                    mock_session.execute = AsyncMock(return_value=mock_result)

                    with patch("app.workers.tasks.Job") as MockJob:
                        mock_job = MagicMock()
                        mock_job.info = AsyncMock(return_value=MagicMock())  # Job exists
                        MockJob.return_value = mock_job

                        result = await sync_active_strategies(ctx)

                        assert result["skipped"] == 1
                        assert result["started"] == 0

    # ========================================================================
    # Edge Case Tests for Interval Fix
    # ========================================================================

    @pytest.mark.asyncio
    async def test_sync_skips_when_next_run_at_in_future_and_heartbeat_ok(self):
        """
        Case 1: Normal execution - next_run_at in future, heartbeat OK
        Expected: Skip scheduling (job already scheduled via _defer_by)
        """
        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}
        agent_id = uuid4()

        now = datetime.now(UTC)
        next_run = now + timedelta(minutes=10)  # 10 min in future, within 1.5x of 15min interval

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            MockSession.return_value = mock_session

            with patch("app.workers.tasks.mark_stale_agents_as_error", AsyncMock(return_value=0)):
                with patch("app.workers.tasks.clear_all_heartbeats_for_active_agents", AsyncMock(return_value=0)):
                    # Mock agent with next_run_at in future and recent heartbeat
                    mock_agent = MagicMock()
                    mock_agent.id = agent_id
                    mock_agent.strategy = MagicMock()
                    mock_agent.execution_interval_minutes = 15
                    mock_agent.next_run_at = next_run
                    mock_agent.worker_heartbeat_at = now - timedelta(seconds=30)  # Recent heartbeat
                    mock_agent.status = "active"
                    mock_agent.updated_at = now

                    mock_scalars = MagicMock()
                    mock_scalars.all.return_value = [mock_agent]

                    mock_result = MagicMock()
                    mock_result.scalars.return_value = mock_scalars

                    mock_session.execute = AsyncMock(return_value=mock_result)

                    with patch("app.workers.tasks.Job") as MockJob:
                        # job.info() returns None for deferred jobs (ARQ behavior)
                        mock_job = MagicMock()
                        mock_job.info = AsyncMock(return_value=None)
                        MockJob.return_value = mock_job

                        result = await sync_active_strategies(ctx)

                        # Should skip because next_run_at is in future and heartbeat OK
                        assert result["skipped"] == 1
                        assert result["started"] == 0
                        # Should NOT have enqueued a new job
                        mock_redis.enqueue_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_reschedules_when_heartbeat_timeout(self):
        """
        Case 2: Worker crashed - next_run_at in future but heartbeat timeout
        Expected: Reschedule immediately (worker crashed during wait)
        """
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test-job"))
        ctx = {"redis": mock_redis}
        agent_id = uuid4()

        now = datetime.now(UTC)
        next_run = now + timedelta(minutes=10)  # 10 min in future

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            MockSession.return_value = mock_session

            with patch("app.workers.tasks.mark_stale_agents_as_error", AsyncMock(return_value=0)):
                with patch("app.workers.tasks.clear_all_heartbeats_for_active_agents", AsyncMock(return_value=0)):
                    # Mock agent with next_run_at in future but OLD heartbeat (timeout)
                    mock_agent = MagicMock()
                    mock_agent.id = agent_id
                    mock_agent.strategy = MagicMock()
                    mock_agent.execution_interval_minutes = 15
                    mock_agent.next_run_at = next_run
                    mock_agent.worker_heartbeat_at = now - timedelta(minutes=10)  # Old heartbeat (timeout)
                    mock_agent.status = "active"
                    mock_agent.updated_at = now - timedelta(minutes=10)

                    mock_scalars = MagicMock()
                    mock_scalars.all.return_value = [mock_agent]

                    mock_result = MagicMock()
                    mock_result.scalars.return_value = mock_scalars

                    mock_session.execute = AsyncMock(return_value=mock_result)

                    with patch("app.workers.tasks.Job") as MockJob:
                        mock_job = MagicMock()
                        mock_job.info = AsyncMock(return_value=None)
                        MockJob.return_value = mock_job

                        result = await sync_active_strategies(ctx)

                        # Should start new job because heartbeat timeout
                        assert result["started"] == 1
                        assert result["skipped"] == 0
                        # Should have enqueued a job
                        mock_redis.enqueue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_reschedules_when_next_run_at_too_far(self):
        """
        Case 3: Config changed - next_run_at too far in future (>1.5x interval)
        Expected: Reschedule immediately (adapt to new interval)
        """
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test-job"))
        ctx = {"redis": mock_redis}
        agent_id = uuid4()

        now = datetime.now(UTC)
        # 50 min in future, way beyond 1.5x of 15min (22.5min)
        next_run = now + timedelta(minutes=50)

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            MockSession.return_value = mock_session

            with patch("app.workers.tasks.mark_stale_agents_as_error", AsyncMock(return_value=0)):
                with patch("app.workers.tasks.clear_all_heartbeats_for_active_agents", AsyncMock(return_value=0)):
                    mock_agent = MagicMock()
                    mock_agent.id = agent_id
                    mock_agent.strategy = MagicMock()
                    mock_agent.execution_interval_minutes = 15
                    mock_agent.next_run_at = next_run
                    mock_agent.worker_heartbeat_at = now - timedelta(seconds=30)
                    mock_agent.status = "active"
                    mock_agent.updated_at = now

                    mock_scalars = MagicMock()
                    mock_scalars.all.return_value = [mock_agent]

                    mock_result = MagicMock()
                    mock_result.scalars.return_value = mock_scalars

                    mock_session.execute = AsyncMock(return_value=mock_result)

                    with patch("app.workers.tasks.Job") as MockJob:
                        mock_job = MagicMock()
                        mock_job.info = AsyncMock(return_value=None)
                        MockJob.return_value = mock_job

                        result = await sync_active_strategies(ctx)

                        # Should start new job because next_run_at is too far
                        assert result["started"] == 1
                        mock_redis.enqueue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_schedules_immediately_when_next_run_at_in_past(self):
        """
        Case 4: Catch up - next_run_at is in the past
        Expected: Schedule immediately (delay=0)
        """
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test-job"))
        ctx = {"redis": mock_redis}
        agent_id = uuid4()

        now = datetime.now(UTC)
        # next_run_at in the past
        next_run = now - timedelta(minutes=5)

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            MockSession.return_value = mock_session

            with patch("app.workers.tasks.mark_stale_agents_as_error", AsyncMock(return_value=0)):
                with patch("app.workers.tasks.clear_all_heartbeats_for_active_agents", AsyncMock(return_value=0)):
                    mock_agent = MagicMock()
                    mock_agent.id = agent_id
                    mock_agent.strategy = MagicMock()
                    mock_agent.execution_interval_minutes = 15
                    mock_agent.next_run_at = next_run
                    mock_agent.worker_heartbeat_at = now
                    mock_agent.status = "active"
                    mock_agent.updated_at = now

                    mock_scalars = MagicMock()
                    mock_scalars.all.return_value = [mock_agent]

                    mock_result = MagicMock()
                    mock_result.scalars.return_value = mock_scalars

                    mock_session.execute = AsyncMock(return_value=mock_result)

                    with patch("app.workers.tasks.Job") as MockJob:
                        mock_job = MagicMock()
                        mock_job.info = AsyncMock(return_value=None)
                        MockJob.return_value = mock_job

                        result = await sync_active_strategies(ctx)

                        # Should start new job immediately
                        assert result["started"] == 1
                        # Check delay is 0 (immediate)
                        call_kwargs = mock_redis.enqueue_job.call_args
                        assert call_kwargs[1]["_defer_by"] == timedelta(seconds=0)

    @pytest.mark.asyncio
    async def test_sync_schedules_immediately_when_no_next_run_at(self):
        """
        Case 5: New agent - no next_run_at (first run or just activated)
        Expected: Schedule immediately (delay=0)
        """
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test-job"))
        ctx = {"redis": mock_redis}
        agent_id = uuid4()

        now = datetime.now(UTC)

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            MockSession.return_value = mock_session

            with patch("app.workers.tasks.mark_stale_agents_as_error", AsyncMock(return_value=0)):
                with patch("app.workers.tasks.clear_all_heartbeats_for_active_agents", AsyncMock(return_value=0)):
                    mock_agent = MagicMock()
                    mock_agent.id = agent_id
                    mock_agent.strategy = MagicMock()
                    mock_agent.execution_interval_minutes = 15
                    mock_agent.next_run_at = None  # No next_run_at
                    mock_agent.worker_heartbeat_at = None
                    mock_agent.status = "active"
                    mock_agent.updated_at = now

                    mock_scalars = MagicMock()
                    mock_scalars.all.return_value = [mock_agent]

                    mock_result = MagicMock()
                    mock_result.scalars.return_value = mock_scalars

                    mock_session.execute = AsyncMock(return_value=mock_result)

                    with patch("app.workers.tasks.Job") as MockJob:
                        mock_job = MagicMock()
                        mock_job.info = AsyncMock(return_value=None)
                        MockJob.return_value = mock_job

                        result = await sync_active_strategies(ctx)

                        # Should start new job immediately
                        assert result["started"] == 1
                        # Check delay is 0 (immediate)
                        call_kwargs = mock_redis.enqueue_job.call_args
                        assert call_kwargs[1]["_defer_by"] == timedelta(seconds=0)

    @pytest.mark.asyncio
    async def test_sync_respects_future_delay_when_appropriate(self):
        """
        Verify that when next_run_at is in future but outside reasonable window,
        the delay is set to the remaining time.
        """
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test-job"))
        ctx = {"redis": mock_redis}
        agent_id = uuid4()

        now = datetime.now(UTC)
        # 30 min in future, beyond 1.5x of 15min (22.5min) but still valid delay target
        next_run = now + timedelta(minutes=30)

        with patch("app.workers.tasks.AsyncSessionLocal") as MockSession:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            MockSession.return_value = mock_session

            with patch("app.workers.tasks.mark_stale_agents_as_error", AsyncMock(return_value=0)):
                with patch("app.workers.tasks.clear_all_heartbeats_for_active_agents", AsyncMock(return_value=0)):
                    mock_agent = MagicMock()
                    mock_agent.id = agent_id
                    mock_agent.strategy = MagicMock()
                    mock_agent.execution_interval_minutes = 15
                    mock_agent.next_run_at = next_run
                    mock_agent.worker_heartbeat_at = now
                    mock_agent.status = "active"
                    mock_agent.updated_at = now

                    mock_scalars = MagicMock()
                    mock_scalars.all.return_value = [mock_agent]

                    mock_result = MagicMock()
                    mock_result.scalars.return_value = mock_scalars

                    mock_session.execute = AsyncMock(return_value=mock_result)

                    with patch("app.workers.tasks.Job") as MockJob:
                        mock_job = MagicMock()
                        mock_job.info = AsyncMock(return_value=None)
                        MockJob.return_value = mock_job

                        result = await sync_active_strategies(ctx)

                        # Should start new job
                        assert result["started"] == 1
                        # Check delay is set to remaining time (should be ~30min)
                        call_kwargs = mock_redis.enqueue_job.call_args
                        delay = call_kwargs[1]["_defer_by"]
                        # Allow 1 second tolerance for test execution time
                        assert abs(delay.total_seconds() - 1800) < 2  # ~30 minutes


class TestWorkerSettings:
    """Tests for worker settings"""

    def test_get_worker_settings(self):
        """Test getting worker settings"""
        with patch("app.workers.tasks.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                redis_url=MagicMock(
                    host="localhost",
                    port=6379,
                    password=None,
                ),
                worker_max_consecutive_errors=3,
            )
            
            settings = get_worker_settings()

            assert "functions" in settings
            # 5 original + 3 agent-based + 1 utility (create_daily_snapshots)
            assert len(settings["functions"]) == 9
            assert "on_startup" in settings
            assert "on_shutdown" in settings
            assert settings["max_jobs"] == 10
            assert settings["job_timeout"] == 300

    def test_worker_settings_class(self):
        """Test WorkerSettings class"""
        # 5 original + 3 agent-based + 1 utility (create_daily_snapshots)
        assert len(WorkerSettings.functions) == 9
        assert WorkerSettings.max_jobs == 10
        assert WorkerSettings.job_timeout == 300
        assert WorkerSettings.queue_name == "bitrun:tasks"

    def test_worker_settings_redis_settings(self):
        """Test WorkerSettings redis_settings method"""
        with patch("app.workers.tasks.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                redis_url=MagicMock(
                    host="redis.example.com",
                    port=6380,
                    password="secret",
                ),
            )
            
            redis_settings = WorkerSettings.redis_settings()
            
            assert redis_settings["host"] == "redis.example.com"
            assert redis_settings["port"] == 6380
            assert redis_settings["password"] == "secret"


# ============================================================================
# Singleton Management Tests
# ============================================================================

class TestSingletonManagement:
    """Tests for singleton management functions"""

    @pytest.mark.asyncio
    async def test_get_redis_pool(self):
        """Test getting Redis pool"""
        with patch("app.workers.queue.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                redis_url=MagicMock(
                    host="localhost",
                    port=6379,
                    password=None,
                ),
            )
            
            with patch("app.workers.queue.create_pool") as mock_create:
                mock_pool = AsyncMock()
                mock_create.return_value = mock_pool
                
                import app.workers.queue as queue_module
                queue_module._redis_pool = None
                
                pool = await queue_module.get_redis_pool()
                
                assert pool is not None
                mock_create.assert_called_once()
                
                # Cleanup
                queue_module._redis_pool = None

    @pytest.mark.asyncio
    async def test_get_task_queue_service(self):
        """Test getting task queue service"""
        with patch("app.workers.queue.get_redis_pool") as mock_get_pool:
            mock_pool = AsyncMock()
            mock_get_pool.return_value = mock_pool
            
            import app.workers.queue as queue_module
            queue_module._task_queue_service = None
            queue_module._redis_pool = None
            
            service = await queue_module.get_task_queue_service()
            
            assert service is not None
            assert isinstance(service, TaskQueueService)
            
            # Cleanup
            queue_module._task_queue_service = None
            queue_module._redis_pool = None

    @pytest.mark.asyncio
    async def test_close_task_queue(self):
        """Test closing task queue"""
        import app.workers.queue as queue_module
        
        # Setup mocks
        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock()
        queue_module._redis_pool = mock_pool
        queue_module._task_queue_service = MagicMock()
        
        await queue_module.close_task_queue()
        
        assert queue_module._redis_pool is None
        assert queue_module._task_queue_service is None
        mock_pool.close.assert_called_once()
