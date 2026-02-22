"""
Tests for Worker Lifecycle Utilities.

Covers:
- get_instance_id: Process instance ID generation
- send_initial_heartbeat: Heartbeat initialization with retry
- clear_heartbeat_on_stop: Heartbeat cleanup on shutdown
- close_trader_safely: Safe trader connection closure
- try_acquire_ownership: Redis leader election
- refresh_ownership: Ownership TTL refresh
- release_ownership: Ownership release
- acquire_execution_lock: Single-cycle execution lock
- release_execution_lock: Execution lock release
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Test get_instance_id ───────────────────────────────────────────────


@pytest.mark.unit
class TestGetInstanceId:
    """Tests for get_instance_id function."""

    def test_returns_string(self):
        """Should return a string instance ID."""
        from app.workers.lifecycle import get_instance_id

        instance_id = get_instance_id()
        assert isinstance(instance_id, str)
        assert len(instance_id) > 0

    def test_returns_same_id_on_multiple_calls(self):
        """Should return the same ID on multiple calls within a process."""
        from app.workers.lifecycle import get_instance_id

        id1 = get_instance_id()
        id2 = get_instance_id()
        assert id1 == id2

    def test_instance_id_format(self):
        """Should have format 'pid:hex'."""
        from app.workers.lifecycle import get_instance_id
        import os

        instance_id = get_instance_id()
        pid = str(os.getpid())
        assert instance_id.startswith(f"{pid}:")


# ── Test send_initial_heartbeat ─────────────────────────────────────────


@pytest.mark.unit
class TestSendInitialHeartbeat:
    """Tests for send_initial_heartbeat function."""

    @pytest.mark.asyncio
    async def test_heartbeat_success(self):
        """Should return True when heartbeat sent successfully."""
        from app.workers.lifecycle import send_initial_heartbeat

        agent_id = uuid.uuid4()
        worker_instance_id = "test-instance-123"

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.services.worker_heartbeat.update_heartbeat_with_retry",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_heartbeat:
                result = await send_initial_heartbeat(agent_id, worker_instance_id)

                assert result is True

    @pytest.mark.asyncio
    async def test_heartbeat_failure_returns_false(self):
        """Should return False when heartbeat fails."""
        from app.workers.lifecycle import send_initial_heartbeat

        agent_id = uuid.uuid4()
        worker_instance_id = "test-instance-123"

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session_local.side_effect = Exception("DB connection failed")

            result = await send_initial_heartbeat(agent_id, worker_instance_id)

            assert result is False


# ── Test clear_heartbeat_on_stop ────────────────────────────────────────


@pytest.mark.unit
class TestClearHeartbeatOnStop:
    """Tests for clear_heartbeat_on_stop function."""

    @pytest.mark.asyncio
    async def test_clear_success(self):
        """Should return True when heartbeat cleared."""
        from app.workers.lifecycle import clear_heartbeat_on_stop

        agent_id = uuid.uuid4()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.services.worker_heartbeat.clear_heartbeat", new_callable=AsyncMock
            ):
                result = await clear_heartbeat_on_stop(agent_id)

                assert result is True

    @pytest.mark.asyncio
    async def test_clear_failure_returns_false(self):
        """Should return False when clear fails."""
        from app.workers.lifecycle import clear_heartbeat_on_stop

        agent_id = uuid.uuid4()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session_local.side_effect = Exception("DB error")

            result = await clear_heartbeat_on_stop(agent_id)

            assert result is False


# ── Test close_trader_safely ────────────────────────────────────────────


@pytest.mark.unit
class TestCloseTraderSafely:
    """Tests for close_trader_safely function."""

    @pytest.mark.asyncio
    async def test_close_none_trader(self):
        """Should handle None trader gracefully."""
        from app.workers.lifecycle import close_trader_safely

        await close_trader_safely(None, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_close_trader_success(self):
        """Should close trader successfully."""
        from app.workers.lifecycle import close_trader_safely

        trader = AsyncMock()
        trader.close = AsyncMock()

        await close_trader_safely(trader, uuid.uuid4())

        trader.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_trader_exception_handled(self):
        """Should not raise when close fails."""
        from app.workers.lifecycle import close_trader_safely

        trader = AsyncMock()
        trader.close = AsyncMock(side_effect=Exception("Close failed"))

        # Should not raise
        await close_trader_safely(trader, uuid.uuid4())


# ── Test Ownership Functions ────────────────────────────────────────────


@pytest.mark.unit
class TestOwnershipFunctions:
    """Tests for Redis ownership functions."""

    @pytest.mark.asyncio
    async def test_try_acquire_ownership_success(self):
        """Should return True when ownership claimed."""
        from app.workers.lifecycle import try_acquire_ownership

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_redis_service = AsyncMock()
            mock_redis_service.redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis_service

            result = await try_acquire_ownership(agent_id)

            assert result is True

    @pytest.mark.asyncio
    async def test_try_acquire_ownership_already_owned(self):
        """Should return False when already owned."""
        from app.workers.lifecycle import try_acquire_ownership

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_redis_service = AsyncMock()
            mock_redis_service.redis.set = AsyncMock(return_value=None)
            mock_get_redis.return_value = mock_redis_service

            result = await try_acquire_ownership(agent_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_try_acquire_ownership_redis_error(self):
        """Should return False on Redis error."""
        from app.workers.lifecycle import try_acquire_ownership

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_get_redis.side_effect = Exception("Redis error")

            result = await try_acquire_ownership(agent_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_refresh_ownership_success(self):
        """Should return True when ownership refreshed."""
        from app.workers.lifecycle import refresh_ownership

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_redis_service = AsyncMock()
            mock_redis_service.redis.eval = AsyncMock(return_value=1)
            mock_get_redis.return_value = mock_redis_service

            result = await refresh_ownership(agent_id)

            assert result is True

    @pytest.mark.asyncio
    async def test_refresh_ownership_reclaim_expired(self):
        """Should reclaim ownership when key expired."""
        from app.workers.lifecycle import refresh_ownership

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_redis_service = AsyncMock()
            # eval returns -1 = key missing
            mock_redis_service.redis.eval = AsyncMock(return_value=-1)
            mock_redis_service.redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis_service

            result = await refresh_ownership(agent_id)

            assert result is True

    @pytest.mark.asyncio
    async def test_refresh_ownership_lost_to_another(self):
        """Should return False when owned by another instance."""
        from app.workers.lifecycle import refresh_ownership

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_redis_service = AsyncMock()
            # eval returns 0 = owned by another
            mock_redis_service.redis.eval = AsyncMock(return_value=0)
            mock_get_redis.return_value = mock_redis_service

            result = await refresh_ownership(agent_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_refresh_ownership_redis_error_keeps_running(self):
        """Should return True on Redis error (fail-safe)."""
        from app.workers.lifecycle import refresh_ownership

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_get_redis.side_effect = Exception("Redis down")

            result = await refresh_ownership(agent_id)

            # Fail-safe: keep running
            assert result is True

    @pytest.mark.asyncio
    async def test_release_ownership_success(self):
        """Should release ownership atomically."""
        from app.workers.lifecycle import release_ownership

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_redis_service = AsyncMock()
            mock_redis_service.redis.eval = AsyncMock(return_value=1)
            mock_get_redis.return_value = mock_redis_service

            await release_ownership(agent_id)

            mock_redis_service.redis.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_ownership_error_silent(self):
        """Should silently handle release errors."""
        from app.workers.lifecycle import release_ownership

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_get_redis.side_effect = Exception("Redis error")

            # Should not raise
            await release_ownership(agent_id)


# ── Test Execution Lock Functions ───────────────────────────────────────


@pytest.mark.unit
class TestExecutionLock:
    """Tests for execution lock functions."""

    @pytest.mark.asyncio
    async def test_acquire_lock_success(self):
        """Should acquire lock and return key."""
        from app.workers.lifecycle import acquire_execution_lock

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_redis_service = AsyncMock()
            mock_redis_service.redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis_service

            acquired, lock_key = await acquire_execution_lock(agent_id)

            assert acquired is True
            assert lock_key is not None
            assert agent_id in lock_key

    @pytest.mark.asyncio
    async def test_acquire_lock_already_held(self):
        """Should return False when lock held by another."""
        from app.workers.lifecycle import acquire_execution_lock

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_redis_service = AsyncMock()
            mock_redis_service.redis.set = AsyncMock(return_value=None)
            mock_get_redis.return_value = mock_redis_service

            acquired, lock_key = await acquire_execution_lock(agent_id)

            assert acquired is False
            assert lock_key is None

    @pytest.mark.asyncio
    async def test_acquire_lock_error_failsafe(self):
        """Should return False on Redis error (fail-safe)."""
        from app.workers.lifecycle import acquire_execution_lock

        agent_id = str(uuid.uuid4())

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_get_redis.side_effect = Exception("Redis error")

            acquired, lock_key = await acquire_execution_lock(agent_id)

            # Fail-safe: do NOT proceed without lock
            assert acquired is False
            assert lock_key is None

    @pytest.mark.asyncio
    async def test_release_lock_success(self):
        """Should release lock by deleting key."""
        from app.workers.lifecycle import release_execution_lock

        lock_key = "exec_lock:agent:test-id"

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_redis_service = AsyncMock()
            mock_redis_service.redis.delete = AsyncMock()
            mock_get_redis.return_value = mock_redis_service

            await release_execution_lock(lock_key)

            mock_redis_service.redis.delete.assert_called_once_with(lock_key)

    @pytest.mark.asyncio
    async def test_release_lock_none_key(self):
        """Should handle None lock key."""
        from app.workers.lifecycle import release_execution_lock

        # Should not raise
        await release_execution_lock(None)

    @pytest.mark.asyncio
    async def test_release_lock_error_silent(self):
        """Should silently handle release errors."""
        from app.workers.lifecycle import release_execution_lock

        lock_key = "exec_lock:agent:test-id"

        with patch("app.services.redis_service.get_redis_service") as mock_get_redis:
            mock_get_redis.side_effect = Exception("Redis error")

            # Should not raise
            await release_execution_lock(lock_key)


# ── Test try_reconnect_trader ───────────────────────────────────────────


@pytest.mark.unit
class TestTryReconnectTrader:
    """Tests for try_reconnect_trader function."""

    @pytest.mark.asyncio
    async def test_reconnect_success(self):
        """Should create new trader connection."""
        from app.workers.lifecycle import try_reconnect_trader

        account_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_trader = AsyncMock()
        mock_trader.close = AsyncMock()

        mock_account = MagicMock()
        mock_account.id = account_id

        mock_new_trader = AsyncMock()
        mock_new_trader.initialize = AsyncMock()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.account.AccountRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=mock_account)
                mock_repo.get_decrypted_credentials = AsyncMock(
                    return_value={"api_key": "test"}
                )
                mock_repo_class.return_value = mock_repo

                with patch(
                    "app.traders.ccxt_trader.create_trader_from_account",
                    return_value=mock_new_trader,
                ):
                    result = await try_reconnect_trader(
                        mock_trader, account_id, user_id
                    )

                    assert result is mock_new_trader
                    mock_new_trader.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_account_not_found(self):
        """Should return None if account not found."""
        from app.workers.lifecycle import try_reconnect_trader

        account_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.account.AccountRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=None)
                mock_repo_class.return_value = mock_repo

                result = await try_reconnect_trader(None, account_id, user_id)

                assert result is None

    @pytest.mark.asyncio
    async def test_reconnect_credentials_failed(self):
        """Should return None if credentials cannot be decrypted."""
        from app.workers.lifecycle import try_reconnect_trader

        account_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_account = MagicMock()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.account.AccountRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=mock_account)
                mock_repo.get_decrypted_credentials = AsyncMock(return_value=None)
                mock_repo_class.return_value = mock_repo

                result = await try_reconnect_trader(None, account_id, user_id)

                assert result is None

    @pytest.mark.asyncio
    async def test_reconnect_closes_existing_trader(self):
        """Should close existing trader before reconnecting."""
        from app.workers.lifecycle import try_reconnect_trader

        account_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_trader = AsyncMock()
        mock_trader.close = AsyncMock()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.account.AccountRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_by_id = AsyncMock(return_value=None)
                mock_repo_class.return_value = mock_repo

                await try_reconnect_trader(mock_trader, account_id, user_id)

                mock_trader.close.assert_called_once()


# ── Test clear_heartbeats_for_quant_strategies ───────────────────────────


@pytest.mark.unit
class TestClearHeartbeatsForQuantStrategies:
    """Tests for clear_heartbeats_for_quant_strategies function."""

    @pytest.mark.asyncio
    async def test_clear_no_active_strategies(self):
        """Should return 0 when no active strategies."""
        from app.workers.lifecycle import clear_heartbeats_for_quant_strategies

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.quant_strategy.QuantStrategyRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_active_strategies = AsyncMock(return_value=[])
                mock_repo_class.return_value = mock_repo

                result = await clear_heartbeats_for_quant_strategies()

                assert result == 0

    @pytest.mark.asyncio
    async def test_clear_with_active_strategies(self):
        """Should clear heartbeats for active strategies."""
        from app.workers.lifecycle import clear_heartbeats_for_quant_strategies

        mock_strategy1 = MagicMock()
        mock_strategy1.id = uuid.uuid4()
        mock_strategy2 = MagicMock()
        mock_strategy2.id = uuid.uuid4()

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.quant_strategy.QuantStrategyRepository"
            ) as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_active_strategies = AsyncMock(
                    return_value=[mock_strategy1, mock_strategy2]
                )
                mock_repo_class.return_value = mock_repo

                mock_session.execute = AsyncMock()
                mock_session.commit = AsyncMock()

                result = await clear_heartbeats_for_quant_strategies()

                assert result == 2
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_error_returns_zero(self):
        """Should return 0 on error."""
        from app.workers.lifecycle import clear_heartbeats_for_quant_strategies

        with patch("app.db.database.AsyncSessionLocal") as mock_session_local:
            mock_session_local.side_effect = Exception("DB error")

            result = await clear_heartbeats_for_quant_strategies()

            assert result == 0
