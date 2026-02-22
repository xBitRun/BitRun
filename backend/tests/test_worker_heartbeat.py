"""
Tests for Worker Heartbeat Service.

Covers:
- get_worker_instance_id: Process identifier generation
- update_heartbeat: Heartbeat timestamp update
- update_heartbeat_with_retry: Retry logic with exponential backoff
- clear_heartbeat: Heartbeat removal
- detect_stale_agents: Finding timed-out agents
- mark_stale_agents_as_error: Marking crashed agents
- clear_all_heartbeats_for_active_agents: Bulk cleanup
- is_agent_running: Running status detection
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.worker_heartbeat import (
    HEARTBEAT_TIMEOUT_SECONDS,
    STARTUP_GRACE_SECONDS,
    get_worker_instance_id,
    is_agent_running,
)


# ── Test get_worker_instance_id ─────────────────────────────────────────


@pytest.mark.unit
class TestGetWorkerInstanceId:
    """Tests for get_worker_instance_id function."""

    def test_returns_string(self):
        """Should return a string identifier."""
        instance_id = get_worker_instance_id()
        assert isinstance(instance_id, str)
        assert len(instance_id) > 0

    def test_format_contains_pid(self):
        """Should contain hostname and pid."""
        import os

        instance_id = get_worker_instance_id()
        pid = str(os.getpid())
        assert pid in instance_id
        assert ":" in instance_id

    def test_multiple_calls_same_result(self):
        """Should return same ID on multiple calls."""
        id1 = get_worker_instance_id()
        id2 = get_worker_instance_id()
        assert id1 == id2


# ── Test update_heartbeat ───────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateHeartbeat:
    """Tests for update_heartbeat function."""

    @pytest.mark.asyncio
    async def test_update_success(self):
        """Should update heartbeat successfully."""
        from app.services.worker_heartbeat import update_heartbeat

        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        agent_id = uuid.uuid4()

        result = await update_heartbeat(session, agent_id, "test-worker")

        assert result is True
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_generates_instance_id_if_none(self):
        """Should generate instance ID if not provided."""
        from app.services.worker_heartbeat import update_heartbeat

        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        agent_id = uuid.uuid4()

        result = await update_heartbeat(session, agent_id, None)

        assert result is True

    @pytest.mark.asyncio
    async def test_update_rollback_on_error(self):
        """Should rollback on database error."""
        from app.services.worker_heartbeat import update_heartbeat

        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock(side_effect=Exception("DB error"))
        session.rollback = AsyncMock()

        agent_id = uuid.uuid4()

        result = await update_heartbeat(session, agent_id, "test-worker")

        assert result is False
        session.rollback.assert_called_once()


# ── Test update_heartbeat_with_retry ─────────────────────────────────────


@pytest.mark.unit
class TestUpdateHeartbeatWithRetry:
    """Tests for update_heartbeat_with_retry function."""

    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        """Should succeed on first attempt."""
        from app.services.worker_heartbeat import update_heartbeat_with_retry

        session = AsyncMock(spec=AsyncSession)

        with patch(
            "app.services.worker_heartbeat.update_heartbeat",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_update:
            result = await update_heartbeat_with_retry(
                session, uuid.uuid4(), "test-worker", max_attempts=3
            )

            assert result is True
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """Should succeed after retries."""
        from app.services.worker_heartbeat import update_heartbeat_with_retry

        session = AsyncMock(spec=AsyncSession)

        # Fail first, succeed second
        call_count = [0]

        async def mock_update_func(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return False
            return True

        with patch(
            "app.services.worker_heartbeat.update_heartbeat",
            side_effect=mock_update_func,
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await update_heartbeat_with_retry(
                    session, uuid.uuid4(), "test-worker", max_attempts=3, base_delay=0.01
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_fail_all_attempts(self):
        """Should return False after all attempts fail."""
        from app.services.worker_heartbeat import update_heartbeat_with_retry

        session = AsyncMock(spec=AsyncSession)

        with patch(
            "app.services.worker_heartbeat.update_heartbeat",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await update_heartbeat_with_retry(
                    session, uuid.uuid4(), "test-worker", max_attempts=2, base_delay=0.01
                )

                assert result is False


# ── Test clear_heartbeat ────────────────────────────────────────────────


@pytest.mark.unit
class TestClearHeartbeat:
    """Tests for clear_heartbeat function."""

    @pytest.mark.asyncio
    async def test_clear_success(self):
        """Should clear heartbeat successfully."""
        from app.services.worker_heartbeat import clear_heartbeat

        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        result = await clear_heartbeat(session, uuid.uuid4())

        assert result is True
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_rollback_on_error(self):
        """Should rollback on error."""
        from app.services.worker_heartbeat import clear_heartbeat

        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock(side_effect=Exception("DB error"))
        session.rollback = AsyncMock()

        result = await clear_heartbeat(session, uuid.uuid4())

        assert result is False
        session.rollback.assert_called_once()


# ── Test detect_stale_agents ────────────────────────────────────────────


@pytest.mark.unit
class TestDetectStaleAgents:
    """Tests for detect_stale_agents function."""

    @pytest.mark.asyncio
    async def test_no_stale_agents(self):
        """Should return empty list when no stale agents."""
        from app.services.worker_heartbeat import detect_stale_agents

        session = AsyncMock(spec=AsyncSession)

        # Create proper mock for scalars().all()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        stale = await detect_stale_agents(session)

        assert stale == []

    @pytest.mark.asyncio
    async def test_detects_stale_agents(self):
        """Should detect agents with old heartbeat."""
        from app.services.worker_heartbeat import detect_stale_agents

        session = AsyncMock(spec=AsyncSession)

        mock_agent = MagicMock()
        mock_agent.id = uuid.uuid4()
        mock_agent.status = "active"
        mock_agent.worker_heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)

        # Create proper mock for scalars().all()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_agent]
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        stale = await detect_stale_agents(session, timeout_seconds=300)

        assert len(stale) == 1
        assert stale[0] == mock_agent


# ── Test mark_stale_agents_as_error ──────────────────────────────────────


@pytest.mark.unit
class TestMarkStaleAgentsAsError:
    """Tests for mark_stale_agents_as_error function."""

    @pytest.mark.asyncio
    async def test_no_stale_agents(self):
        """Should return 0 when no stale agents."""
        from app.services.worker_heartbeat import mark_stale_agents_as_error

        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()

        with patch(
            "app.services.worker_heartbeat.detect_stale_agents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            count = await mark_stale_agents_as_error(session)

            assert count == 0

    @pytest.mark.asyncio
    async def test_marks_agents_as_error(self):
        """Should mark stale agents with error status."""
        from app.services.worker_heartbeat import mark_stale_agents_as_error

        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        mock_agent = MagicMock()
        mock_agent.id = uuid.uuid4()
        mock_agent.worker_heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)
        mock_agent.last_run_at = datetime.now(UTC) - timedelta(minutes=10)

        with patch(
            "app.services.worker_heartbeat.detect_stale_agents",
            new_callable=AsyncMock,
            return_value=[mock_agent],
        ):
            count = await mark_stale_agents_as_error(session)

            assert count == 1
            session.execute.assert_called_once()
            session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_marks_agents_without_heartbeat(self):
        """Should mark agents without heartbeat but with old last_run_at."""
        from app.services.worker_heartbeat import mark_stale_agents_as_error

        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        mock_agent = MagicMock()
        mock_agent.id = uuid.uuid4()
        mock_agent.worker_heartbeat_at = None
        mock_agent.last_run_at = datetime.now(UTC) - timedelta(minutes=10)

        with patch(
            "app.services.worker_heartbeat.detect_stale_agents",
            new_callable=AsyncMock,
            return_value=[mock_agent],
        ):
            count = await mark_stale_agents_as_error(session)

            assert count == 1


# ── Test clear_all_heartbeats_for_active_agents ───────────────────────────


@pytest.mark.unit
class TestClearAllHeartbeats:
    """Tests for clear_all_heartbeats_for_active_agents function."""

    @pytest.mark.asyncio
    async def test_clear_success(self):
        """Should clear heartbeats for active agents."""
        from app.services.worker_heartbeat import clear_all_heartbeats_for_active_agents

        session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.rowcount = 5
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        count = await clear_all_heartbeats_for_active_agents(session)

        assert count == 5

    @pytest.mark.asyncio
    async def test_clear_rollback_on_error(self):
        """Should rollback and return 0 on error."""
        from app.services.worker_heartbeat import clear_all_heartbeats_for_active_agents

        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock(side_effect=Exception("DB error"))
        session.rollback = AsyncMock()

        count = await clear_all_heartbeats_for_active_agents(session)

        assert count == 0
        session.rollback.assert_called_once()


# ── Test is_agent_running ────────────────────────────────────────────────


@pytest.mark.unit
class TestIsAgentRunning:
    """Tests for is_agent_running function."""

    def test_not_running_if_status_not_active(self):
        """Should return False if status is not active."""
        agent = MagicMock()
        agent.status = "paused"
        agent.worker_heartbeat_at = datetime.now(UTC)

        assert is_agent_running(agent) is False

    def test_running_with_recent_heartbeat(self):
        """Should return True with recent heartbeat."""
        agent = MagicMock()
        agent.status = "active"
        agent.worker_heartbeat_at = datetime.now(UTC) - timedelta(seconds=60)

        assert is_agent_running(agent, timeout_seconds=300) is True

    def test_not_running_with_stale_heartbeat(self):
        """Should return False with stale heartbeat."""
        agent = MagicMock()
        agent.status = "active"
        agent.worker_heartbeat_at = datetime.now(UTC) - timedelta(minutes=10)

        assert is_agent_running(agent, timeout_seconds=300) is False

    def test_running_in_startup_grace_period(self):
        """Should return True if recently activated within grace period."""
        agent = MagicMock()
        agent.status = "active"
        agent.worker_heartbeat_at = None
        agent.updated_at = datetime.now(UTC) - timedelta(seconds=30)

        assert is_agent_running(agent, startup_grace_seconds=60) is True

    def test_not_running_outside_grace_period(self):
        """Should return False if outside grace period without heartbeat."""
        agent = MagicMock()
        agent.status = "active"
        agent.worker_heartbeat_at = None
        agent.updated_at = datetime.now(UTC) - timedelta(minutes=5)

        assert is_agent_running(agent, startup_grace_seconds=60) is False

    def test_not_running_no_heartbeat_no_updated_at(self):
        """Should return False if no heartbeat and no updated_at."""
        agent = MagicMock()
        agent.status = "active"
        agent.worker_heartbeat_at = None
        agent.updated_at = None

        assert is_agent_running(agent) is False

    def test_heartbeat_at_exact_boundary(self):
        """Should return False when heartbeat is exactly at cutoff."""
        timeout = 300
        agent = MagicMock()
        agent.status = "active"
        # Heartbeat exactly at the cutoff time (not greater than)
        agent.worker_heartbeat_at = datetime.now(UTC) - timedelta(seconds=timeout)

        assert is_agent_running(agent, timeout_seconds=timeout) is False
