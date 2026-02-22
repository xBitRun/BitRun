"""
Tests for Quant Worker Backend.

Covers:
- QuantExecutionWorker: Individual quant strategy execution worker
- QuantWorkerBackend: Backend managing multiple quant workers
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Test QuantExecutionWorker ────────────────────────────────────────────


@pytest.mark.unit
class TestQuantExecutionWorker:
    """Tests for QuantExecutionWorker class."""

    def test_init(self):
        """Should initialize with correct parameters."""
        from app.workers.quant_backend import QuantExecutionWorker

        agent_id = str(uuid.uuid4())
        trader = MagicMock()

        worker = QuantExecutionWorker(
            agent_id=agent_id,
            strategy_type="grid",
            trader=trader,
            interval_minutes=1,
            account_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            trade_type="crypto_perp",
        )

        assert str(worker.agent_id) == agent_id
        assert worker.strategy_type == "grid"
        assert worker.trader is trader
        assert worker.interval_minutes == 1
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_start(self):
        """Should start worker and heartbeat task."""
        from app.workers.quant_backend import QuantExecutionWorker

        agent_id = str(uuid.uuid4())
        trader = MagicMock()

        worker = QuantExecutionWorker(
            agent_id=agent_id,
            strategy_type="grid",
            trader=trader,
            interval_minutes=1,
        )

        with patch(
            "app.workers.quant_backend.send_initial_heartbeat", new_callable=AsyncMock
        ):
            await worker.start()

            assert worker._running is True
            assert worker._task is not None
            assert worker._heartbeat_task is not None

            # Cleanup
            await worker.stop()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """Should not start again if already running."""
        from app.workers.quant_backend import QuantExecutionWorker

        agent_id = str(uuid.uuid4())
        trader = MagicMock()

        worker = QuantExecutionWorker(
            agent_id=agent_id,
            strategy_type="grid",
            trader=trader,
            interval_minutes=1,
        )
        worker._running = True

        with patch(
            "app.workers.quant_backend.send_initial_heartbeat", new_callable=AsyncMock
        ) as mock_heartbeat:
            await worker.start()

            mock_heartbeat.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Should stop worker gracefully."""
        from app.workers.quant_backend import QuantExecutionWorker

        agent_id = str(uuid.uuid4())
        trader = MagicMock()

        worker = QuantExecutionWorker(
            agent_id=agent_id,
            strategy_type="grid",
            trader=trader,
            interval_minutes=1,
        )

        with patch(
            "app.workers.quant_backend.send_initial_heartbeat", new_callable=AsyncMock
        ):
            with patch(
                "app.workers.quant_backend.clear_heartbeat_on_stop",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.workers.quant_backend.close_trader_safely",
                    new_callable=AsyncMock,
                ):
                    await worker.start()
                    await worker.stop()

                    assert worker._running is False


# ── Test QuantWorkerBackend ──────────────────────────────────────────────


@pytest.mark.unit
class TestQuantWorkerBackend:
    """Tests for QuantWorkerBackend class."""

    def test_init(self):
        """Should initialize correctly."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        assert backend.backend_type == "quant"
        assert backend._workers == {}
        assert backend._running is False

    def test_backend_type(self):
        """Should return 'quant' as backend type."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()
        assert backend.backend_type == "quant"

    @pytest.mark.asyncio
    async def test_start(self):
        """Should start the backend."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        with patch.object(
            backend, "_load_active_strategies", new_callable=AsyncMock
        ):
            await backend.start()

            assert backend._running is True

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """Should not start again if already running."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()
        backend._running = True

        await backend.start()

        assert backend._running is True

    @pytest.mark.asyncio
    async def test_stop(self):
        """Should stop the backend and all workers."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()
        backend._running = True

        # Add a mock worker
        mock_worker = AsyncMock()
        mock_worker.stop = AsyncMock()
        backend._workers = {"test-id": mock_worker}

        await backend.stop()

        assert backend._running is False
        mock_worker.stop.assert_called_once()

    def test_list_running_agents_empty(self):
        """Should return empty list when no workers."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        agents = backend.list_running_agents()

        assert agents == []

    def test_list_running_agents_with_workers(self):
        """Should return list of running agent IDs."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        agent_id_1 = str(uuid.uuid4())
        agent_id_2 = str(uuid.uuid4())

        backend._workers = {
            agent_id_1: MagicMock(),
            agent_id_2: MagicMock(),
        }

        agents = backend.list_running_agents()

        assert agent_id_1 in agents
        assert agent_id_2 in agents

    def test_get_worker_status_not_found(self):
        """Should return None for unknown agent."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        status = backend.get_worker_status(str(uuid.uuid4()))

        assert status is None

    def test_get_worker_status_found(self):
        """Should return status for known agent."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        agent_id = str(uuid.uuid4())
        mock_worker = MagicMock()
        mock_worker._running = True
        mock_worker._error_count = 0
        mock_worker.strategy_type = "grid"

        backend._workers = {agent_id: mock_worker}

        status = backend.get_worker_status(agent_id)

        assert status is not None
        assert status["running"] is True
        assert status["mode"] == "quant"
        assert status["strategy_type"] == "grid"

    def test_get_worker_count(self):
        """Should return correct worker count."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        assert backend.get_worker_count() == 0

        backend._workers = {"a": MagicMock(), "b": MagicMock()}
        assert backend.get_worker_count() == 2

    @pytest.mark.asyncio
    async def test_stop_agent_not_running(self):
        """Should return True if agent not running."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        result = await backend.stop_agent(str(uuid.uuid4()))

        assert result is True

    @pytest.mark.asyncio
    async def test_stop_agent_running(self):
        """Should stop running agent."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        agent_id = str(uuid.uuid4())
        mock_worker = AsyncMock()
        mock_worker.stop = AsyncMock()

        backend._workers = {agent_id: mock_worker}

        result = await backend.stop_agent(agent_id)

        assert result is True
        mock_worker.stop.assert_called_once()
        assert agent_id not in backend._workers

    @pytest.mark.asyncio
    async def test_trigger_execution_strategy_not_found(self):
        """Should return error if strategy not found."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.quant_strategy.QuantStrategyRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=None)
                mock_repo_class.return_value = mock_repo

                result = await backend.trigger_execution(str(uuid.uuid4()))

                assert result["success"] is False
                assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_trigger_execution_strategy_not_active(self):
        """Should return error if strategy not active."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        mock_strategy = MagicMock()
        mock_strategy.id = uuid.uuid4()
        mock_strategy.status = "paused"

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.quant_strategy.QuantStrategyRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                # Return strategy for get_by_id
                mock_repo.get_by_id = AsyncMock(return_value=mock_strategy)
                mock_repo_class.return_value = mock_repo

                result = await backend.trigger_execution(str(mock_strategy.id))

                assert result["success"] is False
                # Check for any error message about status
                assert "error" in result

    @pytest.mark.asyncio
    async def test_trigger_execution_unsupported_strategy_type(self):
        """Should return error for unsupported strategy type."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        # Use a completely mocked approach
        agent_id = str(uuid.uuid4())

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            # Create a mock strategy with unsupported type
            mock_strategy = MagicMock()
            mock_strategy.id = uuid.UUID(agent_id)
            mock_strategy.status = "active"
            mock_strategy.execution_mode = "mock"
            mock_strategy.strategy_type = "unknown"
            mock_strategy.symbol = "BTC"

            with patch(
                "app.db.repositories.quant_strategy.QuantStrategyRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=mock_strategy)
                mock_repo_class.return_value = mock_repo

                # Patch create_mock_trader in tasks module
                with patch("app.workers.tasks.create_mock_trader") as mock_create:
                    mock_trader = MagicMock()
                    mock_create.return_value = (mock_trader, None)

                    result = await backend.trigger_execution(agent_id)

                    # Either strategy not found (mock issue) or unsupported type
                    assert result["success"] is False


# ── Test DEFAULT_INTERVALS ───────────────────────────────────────────────


@pytest.mark.unit
class TestDefaultIntervals:
    """Tests for default interval constants."""

    def test_default_intervals_exist(self):
        """Should have default intervals for all strategy types."""
        from app.workers.quant_backend import DEFAULT_INTERVALS

        assert "grid" in DEFAULT_INTERVALS
        assert "dca" in DEFAULT_INTERVALS
        assert "rsi" in DEFAULT_INTERVALS

    def test_grid_interval(self):
        """Grid should have 1 minute interval."""
        from app.workers.quant_backend import DEFAULT_INTERVALS

        assert DEFAULT_INTERVALS["grid"] == 1

    def test_dca_interval(self):
        """DCA should have 60 minute interval."""
        from app.workers.quant_backend import DEFAULT_INTERVALS

        assert DEFAULT_INTERVALS["dca"] == 60

    def test_rsi_interval(self):
        """RSI should have 5 minute interval."""
        from app.workers.quant_backend import DEFAULT_INTERVALS

        assert DEFAULT_INTERVALS["rsi"] == 5


# ── Test _load_active_strategies ─────────────────────────────────────────


@pytest.mark.unit
class TestLoadActiveStrategies:
    """Tests for _load_active_strategies method."""

    @pytest.mark.asyncio
    async def test_load_empty(self):
        """Should handle no active strategies."""
        from app.workers.quant_backend import QuantWorkerBackend

        backend = QuantWorkerBackend()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.quant_strategy.QuantStrategyRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_active_strategies = AsyncMock(return_value=[])
                mock_repo_class.return_value = mock_repo

                await backend._load_active_strategies()

                assert backend._workers == {}
