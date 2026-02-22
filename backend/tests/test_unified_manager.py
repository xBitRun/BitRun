"""
Tests for Unified Worker Manager.

Covers:
- UnifiedWorkerManager: Unified management for AI and Quant backends
- get_unified_worker_manager: Singleton management
- Backend routing based on strategy type
- Backward compatibility methods
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Test UnifiedWorkerManager ───────────────────────────────────────────


@pytest.mark.unit
class TestUnifiedWorkerManager:
    """Tests for UnifiedWorkerManager class."""

    def test_init(self):
        """Should initialize with both backends."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        assert manager._ai_backend is not None
        assert manager._quant_backend is not None
        assert manager._running is False

    def test_backend_type_properties(self):
        """Should have correct backend properties."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        assert manager.ai_backend is manager._ai_backend
        assert manager.quant_backend is manager._quant_backend

    @pytest.mark.asyncio
    async def test_start(self):
        """Should start both backends."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        # Mock backends
        manager._ai_backend.start = AsyncMock()
        manager._ai_backend.list_running_agents = MagicMock(return_value=[])
        manager._quant_backend.start = AsyncMock()
        manager._quant_backend.list_running_agents = MagicMock(return_value=[])

        await manager.start()

        assert manager._running is True
        manager._ai_backend.start.assert_called_once()
        manager._quant_backend.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """Should not start again if already running."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        manager._running = True

        manager._ai_backend.start = AsyncMock()
        manager._quant_backend.start = AsyncMock()

        await manager.start()

        manager._ai_backend.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Should stop both backends."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        manager._running = True

        manager._ai_backend.stop = AsyncMock()
        manager._quant_backend.stop = AsyncMock()

        await manager.stop()

        assert manager._running is False
        manager._ai_backend.stop.assert_called_once()
        manager._quant_backend.stop.assert_called_once()

    def test_get_backend_for_strategy_type_ai(self):
        """Should return AI backend for 'ai' strategy type."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        backend = manager._get_backend_for_strategy_type("ai")

        assert backend is manager._ai_backend

    def test_get_backend_for_strategy_type_quant(self):
        """Should return Quant backend for non-ai types."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        for strategy_type in ["grid", "dca", "rsi", "unknown"]:
            backend = manager._get_backend_for_strategy_type(strategy_type)
            assert backend is manager._quant_backend

    def test_list_running_agents(self):
        """Should combine agents from both backends."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        manager._ai_backend.list_running_agents = MagicMock(
            return_value=["ai-1", "ai-2"]
        )
        manager._quant_backend.list_running_agents = MagicMock(
            return_value=["quant-1"]
        )

        agents = manager.list_running_agents()

        assert "ai-1" in agents
        assert "ai-2" in agents
        assert "quant-1" in agents
        assert len(agents) == 3

    def test_list_ai_agents(self):
        """Should return only AI agents."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        manager._ai_backend.list_running_agents = MagicMock(
            return_value=["ai-1", "ai-2"]
        )

        agents = manager.list_ai_agents()

        assert agents == ["ai-1", "ai-2"]

    def test_list_quant_agents(self):
        """Should return only Quant agents."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        manager._quant_backend.list_running_agents = MagicMock(
            return_value=["quant-1", "quant-2"]
        )

        agents = manager.list_quant_agents()

        assert agents == ["quant-1", "quant-2"]

    def test_get_worker_status_ai(self):
        """Should get status from AI backend."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        expected_status = {"running": True, "mode": "ai"}
        manager._ai_backend.get_worker_status = MagicMock(return_value=expected_status)
        manager._quant_backend.get_worker_status = MagicMock(return_value=None)

        status = manager.get_worker_status("some-agent-id")

        assert status == expected_status

    def test_get_worker_status_quant(self):
        """Should get status from Quant backend if AI returns None."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        expected_status = {"running": True, "mode": "quant"}
        manager._ai_backend.get_worker_status = MagicMock(return_value=None)
        manager._quant_backend.get_worker_status = MagicMock(return_value=expected_status)

        status = manager.get_worker_status("some-agent-id")

        assert status == expected_status

    def test_is_distributed(self):
        """Should return False for unified manager."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        assert manager.is_distributed is False

    @pytest.mark.asyncio
    async def test_get_distributed_status(self):
        """Should return None (not applicable)."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        status = await manager.get_distributed_status("some-agent-id")

        assert status is None

    @pytest.mark.asyncio
    async def test_get_queue_info(self):
        """Should return None (not applicable)."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        info = await manager.get_queue_info()

        assert info is None

    def test_list_workers(self):
        """Should delegate to list_running_agents."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        manager._ai_backend.list_running_agents = MagicMock(return_value=["a1"])
        manager._quant_backend.list_running_agents = MagicMock(return_value=["q1"])

        workers = manager.list_workers()

        assert workers == ["a1", "q1"]


# ── Test stop_agent routing ─────────────────────────────────────────────


@pytest.mark.unit
class TestStopAgentRouting:
    """Tests for stop_agent routing to correct backend."""

    @pytest.mark.asyncio
    async def test_stop_ai_agent(self):
        """Should stop agent in AI backend."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        agent_id = str(uuid.uuid4())

        manager._ai_backend.list_running_agents = MagicMock(return_value=[agent_id])
        manager._ai_backend.stop_agent = AsyncMock(return_value=True)
        manager._quant_backend.list_running_agents = MagicMock(return_value=[])
        manager._quant_backend.stop_agent = AsyncMock(return_value=True)

        result = await manager.stop_agent(agent_id)

        assert result is True
        manager._ai_backend.stop_agent.assert_called_once_with(agent_id)
        manager._quant_backend.stop_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_quant_agent(self):
        """Should stop agent in Quant backend."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        agent_id = str(uuid.uuid4())

        manager._ai_backend.list_running_agents = MagicMock(return_value=[])
        manager._ai_backend.stop_agent = AsyncMock(return_value=True)
        manager._quant_backend.list_running_agents = MagicMock(return_value=[agent_id])
        manager._quant_backend.stop_agent = AsyncMock(return_value=True)

        result = await manager.stop_agent(agent_id)

        assert result is True
        manager._quant_backend.stop_agent.assert_called_once_with(agent_id)

    @pytest.mark.asyncio
    async def test_stop_not_running_agent(self):
        """Should return True if agent not running."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        agent_id = str(uuid.uuid4())

        manager._ai_backend.list_running_agents = MagicMock(return_value=[])
        manager._quant_backend.list_running_agents = MagicMock(return_value=[])
        manager._ai_backend.stop_agent = AsyncMock(return_value=True)
        manager._quant_backend.stop_agent = AsyncMock(return_value=True)

        result = await manager.stop_agent(agent_id)

        assert result is True


# ── Test backward compatibility methods ──────────────────────────────────


@pytest.mark.unit
class TestBackwardCompatibility:
    """Tests for backward compatibility methods."""

    @pytest.mark.asyncio
    async def test_start_strategy(self):
        """Should delegate to start_agent."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        strategy_id = str(uuid.uuid4())

        with patch.object(
            manager, "start_agent", new_callable=AsyncMock, return_value=True
        ) as mock_start:
            result = await manager.start_strategy(strategy_id)

            assert result is True
            mock_start.assert_called_once_with(strategy_id)

    @pytest.mark.asyncio
    async def test_stop_strategy(self):
        """Should delegate to stop_agent."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        strategy_id = str(uuid.uuid4())

        with patch.object(
            manager, "stop_agent", new_callable=AsyncMock, return_value=True
        ) as mock_stop:
            result = await manager.stop_strategy(strategy_id)

            assert result is True
            mock_stop.assert_called_once_with(strategy_id)

    @pytest.mark.asyncio
    async def test_trigger_manual_execution_with_agent_id(self):
        """Should use agent_id if provided."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        strategy_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())

        with patch.object(
            manager,
            "trigger_execution",
            new_callable=AsyncMock,
            return_value={"success": True},
        ) as mock_trigger:
            result = await manager.trigger_manual_execution(
                strategy_id=strategy_id,
                agent_id=agent_id,
            )

            assert result["success"] is True
            mock_trigger.assert_called_once_with(agent_id, None)

    @pytest.mark.asyncio
    async def test_trigger_manual_execution_fallback_to_strategy(self):
        """Should use strategy_id if agent_id not provided."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        strategy_id = str(uuid.uuid4())

        with patch.object(
            manager,
            "trigger_execution",
            new_callable=AsyncMock,
            return_value={"success": True},
        ) as mock_trigger:
            result = await manager.trigger_manual_execution(
                strategy_id=strategy_id,
            )

            assert result["success"] is True
            mock_trigger.assert_called_once_with(strategy_id, None)


# ── Test Singleton Management ───────────────────────────────────────────


@pytest.mark.unit
class TestSingletonManagement:
    """Tests for singleton management functions."""

    @pytest.mark.asyncio
    async def test_get_unified_worker_manager_creates_singleton(self):
        """Should create singleton on first call."""
        from app.workers.unified_manager import (
            get_unified_worker_manager,
            reset_unified_worker_manager,
        )

        # Reset first
        await reset_unified_worker_manager()

        manager = await get_unified_worker_manager()

        assert manager is not None
        assert isinstance(manager.__class__.__name__, str)

        # Cleanup
        await reset_unified_worker_manager()

    @pytest.mark.asyncio
    async def test_get_unified_worker_manager_returns_same_instance(self):
        """Should return same instance on multiple calls."""
        from app.workers.unified_manager import (
            get_unified_worker_manager,
            reset_unified_worker_manager,
        )

        # Reset first
        await reset_unified_worker_manager()

        manager1 = await get_unified_worker_manager()
        manager2 = await get_unified_worker_manager()

        assert manager1 is manager2

        # Cleanup
        await reset_unified_worker_manager()

    @pytest.mark.asyncio
    async def test_reset_unified_worker_manager(self):
        """Should reset singleton."""
        from app.workers.unified_manager import (
            get_unified_worker_manager,
            reset_unified_worker_manager,
            _unified_manager as global_manager,
        )

        # Create instance
        await get_unified_worker_manager()

        # Reset
        await reset_unified_worker_manager()

        # Check it's None after import
        import app.workers.unified_manager as um
        assert um._unified_manager is None


# ── Test _get_backend_for_agent ──────────────────────────────────────────


@pytest.mark.unit
class TestGetBackendForAgent:
    """Tests for _get_backend_for_agent method."""

    @pytest.mark.asyncio
    async def test_get_backend_ai_strategy(self):
        """Should return AI backend for AI strategy."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        mock_agent = MagicMock()
        mock_agent.strategy = MagicMock()
        mock_agent.strategy.type = "ai"

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_agent
            mock_session.execute = AsyncMock(return_value=mock_result)

            backend = await manager._get_backend_for_agent(str(uuid.uuid4()))

            assert backend is manager._ai_backend

    @pytest.mark.asyncio
    async def test_get_backend_quant_strategy(self):
        """Should return Quant backend for grid strategy."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        mock_agent = MagicMock()
        mock_agent.strategy = MagicMock()
        mock_agent.strategy.type = "grid"

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_agent
            mock_session.execute = AsyncMock(return_value=mock_result)

            backend = await manager._get_backend_for_agent(str(uuid.uuid4()))

            assert backend is manager._quant_backend

    @pytest.mark.asyncio
    async def test_get_backend_agent_not_found(self):
        """Should return None if agent not found."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)

            backend = await manager._get_backend_for_agent(str(uuid.uuid4()))

            assert backend is None

    @pytest.mark.asyncio
    async def test_get_backend_no_strategy(self):
        """Should return None if agent has no strategy."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        mock_agent = MagicMock()
        mock_agent.strategy = None

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_agent
            mock_session.execute = AsyncMock(return_value=mock_result)

            backend = await manager._get_backend_for_agent(str(uuid.uuid4()))

            assert backend is None

    @pytest.mark.asyncio
    async def test_get_backend_db_error(self):
        """Should return None on database error."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session_local.side_effect = Exception("DB error")

            backend = await manager._get_backend_for_agent(str(uuid.uuid4()))

            assert backend is None


# ── Test start_agent with backend routing ─────────────────────────────────


@pytest.mark.unit
class TestStartAgentRouting:
    """Tests for start_agent routing."""

    @pytest.mark.asyncio
    async def test_start_agent_backend_not_found(self):
        """Should return False if backend cannot be determined."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        agent_id = str(uuid.uuid4())

        with patch.object(
            manager, "_get_backend_for_agent", new_callable=AsyncMock, return_value=None
        ):
            result = await manager.start_agent(agent_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_start_agent_success(self):
        """Should start agent in correct backend."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        agent_id = str(uuid.uuid4())

        mock_backend = MagicMock()
        mock_backend.start_agent = AsyncMock(return_value=True)

        with patch.object(
            manager,
            "_get_backend_for_agent",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            result = await manager.start_agent(agent_id)

            assert result is True
            mock_backend.start_agent.assert_called_once_with(agent_id)


# ── Test trigger_execution routing ─────────────────────────────────────────


@pytest.mark.unit
class TestTriggerExecutionRouting:
    """Tests for trigger_execution routing."""

    @pytest.mark.asyncio
    async def test_trigger_execution_backend_not_found(self):
        """Should return error if backend not found."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        agent_id = str(uuid.uuid4())

        with patch.object(
            manager, "_get_backend_for_agent", new_callable=AsyncMock, return_value=None
        ):
            result = await manager.trigger_execution(agent_id)

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_trigger_execution_success(self):
        """Should trigger execution in correct backend."""
        from app.workers.unified_manager import UnifiedWorkerManager

        manager = UnifiedWorkerManager(distributed_safety=False)
        agent_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        mock_backend = MagicMock()
        mock_backend.trigger_execution = AsyncMock(
            return_value={"success": True, "decision_id": str(uuid.uuid4())}
        )

        with patch.object(
            manager,
            "_get_backend_for_agent",
            new_callable=AsyncMock,
            return_value=mock_backend,
        ):
            result = await manager.trigger_execution(agent_id, user_id)

            assert result["success"] is True
            mock_backend.trigger_execution.assert_called_once_with(agent_id, user_id)
