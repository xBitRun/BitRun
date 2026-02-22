"""
Tests for AI Worker Backend.

Covers:
- AIExecutionWorker: Individual agent execution worker
- AIWorkerBackend: Backend managing multiple AI workers
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Test AIExecutionWorker ───────────────────────────────────────────────


@pytest.mark.unit
class TestAIExecutionWorker:
    """Tests for AIExecutionWorker class."""

    def test_init(self):
        """Should initialize with correct parameters."""
        from app.workers.ai_backend import AIExecutionWorker

        agent_id = str(uuid.uuid4())
        trader = MagicMock()

        worker = AIExecutionWorker(
            agent_id=agent_id,
            trader=trader,
            interval_minutes=15,
            distributed_safety=False,
        )

        assert str(worker.agent_id) == agent_id
        assert worker.trader is trader
        assert worker.interval_minutes == 15
        assert worker._running is False
        assert worker._distributed_safety is False

    @pytest.mark.asyncio
    async def test_start(self):
        """Should start worker and heartbeat task."""
        from app.workers.ai_backend import AIExecutionWorker

        agent_id = str(uuid.uuid4())
        trader = MagicMock()

        worker = AIExecutionWorker(
            agent_id=agent_id,
            trader=trader,
            interval_minutes=15,
            distributed_safety=False,
        )

        with patch(
            "app.workers.ai_backend.send_initial_heartbeat", new_callable=AsyncMock
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
        from app.workers.ai_backend import AIExecutionWorker

        agent_id = str(uuid.uuid4())
        trader = MagicMock()

        worker = AIExecutionWorker(
            agent_id=agent_id,
            trader=trader,
            interval_minutes=15,
        )
        worker._running = True

        with patch(
            "app.workers.ai_backend.send_initial_heartbeat", new_callable=AsyncMock
        ) as mock_heartbeat:
            await worker.start()

            mock_heartbeat.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Should stop worker gracefully."""
        from app.workers.ai_backend import AIExecutionWorker

        agent_id = str(uuid.uuid4())
        trader = MagicMock()

        worker = AIExecutionWorker(
            agent_id=agent_id,
            trader=trader,
            interval_minutes=15,
            distributed_safety=False,
        )

        with patch(
            "app.workers.ai_backend.send_initial_heartbeat", new_callable=AsyncMock
        ):
            with patch(
                "app.workers.ai_backend.clear_heartbeat_on_stop", new_callable=AsyncMock
            ):
                with patch(
                    "app.workers.ai_backend.close_trader_safely", new_callable=AsyncMock
                ):
                    await worker.start()
                    await worker.stop()

                    assert worker._running is False

    @pytest.mark.asyncio
    async def test_stop_releases_ownership_with_distributed_safety(self):
        """Should release ownership if distributed safety enabled."""
        from app.workers.ai_backend import AIExecutionWorker

        agent_id = str(uuid.uuid4())
        trader = MagicMock()

        worker = AIExecutionWorker(
            agent_id=agent_id,
            trader=trader,
            interval_minutes=15,
            distributed_safety=True,
        )

        with patch(
            "app.workers.ai_backend.send_initial_heartbeat", new_callable=AsyncMock
        ):
            with patch(
                "app.workers.ai_backend.clear_heartbeat_on_stop", new_callable=AsyncMock
            ):
                with patch(
                    "app.workers.ai_backend.release_ownership", new_callable=AsyncMock
                ) as mock_release:
                    with patch(
                        "app.workers.ai_backend.close_trader_safely",
                        new_callable=AsyncMock,
                    ):
                        await worker.start()
                        await worker.stop()

                        mock_release.assert_called_once()


# ── Test AIWorkerBackend ─────────────────────────────────────────────────


@pytest.mark.unit
class TestAIWorkerBackend:
    """Tests for AIWorkerBackend class."""

    def test_init(self):
        """Should initialize correctly."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend(distributed_safety=False)

        assert backend.backend_type == "ai"
        assert backend._workers == {}
        assert backend._distributed_safety is False
        assert backend._running is False

    def test_backend_type(self):
        """Should return 'ai' as backend type."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend()
        assert backend.backend_type == "ai"

    @pytest.mark.asyncio
    async def test_start(self):
        """Should start the backend."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend(distributed_safety=False)

        await backend.start()

        assert backend._running is True

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """Should not start again if already running."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend(distributed_safety=False)
        backend._running = True

        await backend.start()

        assert backend._running is True

    @pytest.mark.asyncio
    async def test_stop(self):
        """Should stop the backend."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend(distributed_safety=False)
        backend._running = True

        await backend.stop()

        assert backend._running is False

    def test_list_running_agents_empty(self):
        """Should return empty list when no workers."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend()

        agents = backend.list_running_agents()

        assert agents == []

    def test_list_running_agents_with_workers(self):
        """Should return list of running agent IDs."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend()

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
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend()

        status = backend.get_worker_status(str(uuid.uuid4()))

        assert status is None

    def test_get_worker_status_found(self):
        """Should return status for known agent."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend()

        agent_id = str(uuid.uuid4())
        mock_worker = MagicMock()
        mock_worker._running = True
        mock_worker._last_run = datetime.now(UTC)
        mock_worker._error_count = 0

        backend._workers = {agent_id: mock_worker}

        status = backend.get_worker_status(agent_id)

        assert status is not None
        assert status["running"] is True
        assert status["mode"] == "ai"

    @pytest.mark.asyncio
    async def test_stop_agent_not_running(self):
        """Should return True if agent not running."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend()

        result = await backend.stop_agent(str(uuid.uuid4()))

        assert result is True

    @pytest.mark.asyncio
    async def test_stop_agent_running(self):
        """Should stop running agent."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend()

        agent_id = str(uuid.uuid4())
        mock_worker = AsyncMock()
        mock_worker.stop = AsyncMock()

        backend._workers = {agent_id: mock_worker}

        result = await backend.stop_agent(agent_id)

        assert result is True
        mock_worker.stop.assert_called_once()
        assert agent_id not in backend._workers

    @pytest.mark.asyncio
    async def test_trigger_execution_not_running(self):
        """Should return error if agent not running."""
        from app.workers.ai_backend import AIWorkerBackend

        backend = AIWorkerBackend()

        result = await backend.trigger_execution(str(uuid.uuid4()))

        assert result["success"] is False
        assert "error" in result


# ── Test BaseWorkerBackend ───────────────────────────────────────────────


@pytest.mark.unit
class TestBaseWorkerBackend:
    """Tests for BaseWorkerBackend abstract class."""

    def test_is_running_property(self):
        """Should return _running value."""
        from app.workers.base_backend import BaseWorkerBackend

        # Create a concrete implementation
        class ConcreteBackend(BaseWorkerBackend):
            @property
            def backend_type(self) -> str:
                return "concrete"

            async def start_agent(self, agent_id: str) -> bool:
                return True

            async def stop_agent(self, agent_id: str) -> bool:
                return True

            async def trigger_execution(
                self, agent_id: str, user_id=None
            ):
                return {"success": True}

            def get_worker_status(self, agent_id: str):
                return None

            def list_running_agents(self):
                return []

            async def start(self):
                pass

            async def stop(self):
                pass

        backend = ConcreteBackend()

        assert backend.is_running is False

        backend._running = True
        assert backend.is_running is True
