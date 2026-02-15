"""
Quant Strategy Worker for background execution of traditional strategies.

Manages Grid, DCA, and RSI strategy workers using the same pattern
as the AI strategy ExecutionWorker/WorkerManager, but with
QuantEngine instead of StrategyEngine.

Distributed safety:
- Each cycle acquires a Redis execution lock to prevent concurrent
  execution across multiple application instances.
- Worker ownership is claimed via a Redis key so that only one
  instance runs the worker for each strategy (leader election).
- A periodic sync task re-checks active strategies and reclaims
  orphaned workers.
"""

import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Dict, Optional

from ..core.config import get_settings
from ..db.database import AsyncSessionLocal
from ..db.repositories.quant_strategy import QuantStrategyRepository
from ..db.repositories.account import AccountRepository
from ..services.quant_engine import create_engine
from ..traders.base import BaseTrader, TradeError
from ..traders.ccxt_trader import create_trader_from_account
from ..traders.mock_trader import MockTrader
from .tasks import _restore_mock_trader_state

logger = logging.getLogger(__name__)

# Default cycle intervals per strategy type (minutes)
DEFAULT_INTERVALS = {
    "grid": 1,    # Grid checks every minute
    "dca": 60,    # DCA default: check every hour (actual interval from config)
    "rsi": 5,     # RSI checks every 5 minutes
}

# Unique identifier for this process instance (used for leader election)
_INSTANCE_ID = f"{os.getpid()}:{uuid.uuid4().hex[:8]}"

# Redis key prefix for worker ownership claims
_WORKER_OWNER_PREFIX = "quant_worker_owner:"
# Ownership TTL – must be refreshed periodically
_OWNER_TTL_SECONDS = 120
# How often to refresh ownership and sync strategies (seconds)
_SYNC_INTERVAL_SECONDS = 60


class QuantExecutionWorker:
    """
    Worker for executing a single quant strategy.

    Runs the strategy engine's cycle at configured intervals.
    Includes trader health checks and automatic reconnection.
    """

    def __init__(
        self,
        agent_id: str,
        strategy_type: str,
        trader: BaseTrader,
        interval_minutes: int = 5,
        account_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
    ):
        # Note: agent_id is AgentDB.id (QuantStrategyDB is alias for AgentDB)
        self.agent_id = uuid.UUID(agent_id)
        self.strategy_type = strategy_type
        self.trader = trader
        self.interval_minutes = interval_minutes
        self._account_id = account_id
        self._user_id = user_id

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._error_count = 0

        settings = get_settings()
        self._max_errors = settings.worker_max_consecutive_errors

    async def start(self) -> None:
        """Start the worker"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Started quant worker for {self.strategy_type} strategy {self.agent_id}")

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the worker gracefully with timeout.

        Stops the loop first, THEN removes from the dict (caller handles
        removal after this method returns successfully).
        """
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Quant worker for strategy {self.agent_id} did not stop within {timeout}s, forcing")
            except asyncio.CancelledError:
                pass

        # Close trader connection to avoid resource leaks
        if self.trader:
            try:
                await self.trader.close()
            except Exception as e:
                logger.warning(f"Error closing trader for quant strategy {self.agent_id}: {e}")

        logger.info(f"Stopped quant worker for strategy {self.agent_id}")

    async def _run_loop(self) -> None:
        """Main execution loop"""
        while self._running:
            try:
                # Timeout protection: prevent cycles from hanging indefinitely
                await asyncio.wait_for(
                    self._run_cycle(), timeout=300.0  # 5 minute timeout
                )
                self._error_count = 0
                await asyncio.sleep(self.interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except asyncio.TimeoutError:
                logger.error(
                    f"Quant strategy {self.agent_id} cycle timed out (>300s)"
                )
                self._error_count += 1
                if self._error_count >= self._max_errors:
                    await self._update_status("error", "Cycle execution timed out")
                    break
                await asyncio.sleep(60)
            except Exception as e:
                logger.exception(f"Error in quant strategy {self.agent_id}")
                self._error_count += 1
                if self._error_count >= self._max_errors:
                    logger.error(f"Too many errors, pausing quant strategy {self.agent_id}")
                    await self._update_status("error", str(e))
                    break
                # On connection-related errors, try to reconnect the trader
                await self._try_reconnect_trader()
                await asyncio.sleep(60)

    async def _try_reconnect_trader(self) -> None:
        """
        Attempt to recreate the trader connection.

        Handles cases where the exchange API key was rotated, the
        network connection dropped, or the exchange went through
        maintenance.
        """
        if not self._account_id or not self._user_id:
            return

        logger.info(
            f"Quant worker {self.agent_id}: attempting trader reconnection"
        )
        try:
            # Close existing connection
            if self.trader:
                try:
                    await self.trader.close()
                except Exception:
                    pass

            # Recreate from fresh credentials
            async with AsyncSessionLocal() as session:
                account_repo = AccountRepository(session)
                account = await account_repo.get_by_id(self._account_id, self._user_id)
                if not account:
                    logger.error(
                        f"Quant worker {self.agent_id}: account "
                        f"{self._account_id} not found during reconnect"
                    )
                    return

                credentials = await account_repo.get_decrypted_credentials(
                    self._account_id, self._user_id
                )
                if not credentials:
                    logger.error(
                        f"Quant worker {self.agent_id}: failed to get "
                        "credentials during reconnect"
                    )
                    return

                new_trader = create_trader_from_account(account, credentials)
                await new_trader.initialize()
                self.trader = new_trader
                logger.info(
                    f"Quant worker {self.agent_id}: trader reconnected"
                )
        except Exception as e:
            logger.exception(
                f"Quant worker {self.agent_id}: reconnection failed"
            )

    async def _run_cycle(self) -> None:
        """Run one strategy cycle with execution lock and position isolation."""
        # ── Execution lock ──
        # Prevents concurrent cycles across all instances
        from ..services.redis_service import get_redis_service
        lock_key = f"exec_lock:quant_strategy:{self.agent_id}"
        redis_service = None
        lock_acquired = False
        try:
            redis_service = await get_redis_service()
            lock_acquired = await redis_service.redis.set(lock_key, "1", nx=True, ex=300)
        except Exception as e:
            logger.warning(f"Failed to acquire exec lock for quant {self.agent_id}: {e}")
            # Fail-safe: do NOT proceed without lock to prevent duplicate execution
            return

        if not lock_acquired:
            logger.warning(
                f"Quant strategy {self.agent_id} already executing (concurrent lock), skipping"
            )
            return

        try:
            await self._run_cycle_inner(redis_service)
        finally:
            try:
                if redis_service:
                    await redis_service.redis.delete(lock_key)
            except Exception:
                pass  # Lock will expire via TTL

    async def _run_cycle_inner(self, redis_service=None) -> None:
        """Inner cycle logic after lock is acquired."""
        from ..services.position_service import PositionService

        async with AsyncSessionLocal() as session:
            repo = QuantStrategyRepository(session)
            strategy = await repo.get_by_id(self.agent_id)

            if not strategy or strategy.status != "active":
                logger.info(f"Quant strategy {self.agent_id} not active, stopping")
                self._running = False
                return

            # Create position service for strategy isolation
            position_service = PositionService(db=session, redis=redis_service)

            # Create appropriate engine with position isolation
            engine = create_engine(
                strategy_type=strategy.strategy_type,
                strategy_id=str(strategy.id),
                trader=self.trader,
                symbol=strategy.symbol,
                config=strategy.config,
                runtime_state=strategy.runtime_state or {},
                account_id=str(strategy.account_id) if strategy.account_id else None,
                position_service=position_service,
                strategy=strategy,
            )

            # Run cycle
            result = await engine.run_cycle()

            # Update runtime state
            if result.get("updated_state"):
                await repo.update_runtime_state(
                    self.agent_id,
                    result["updated_state"],
                )

            # Update performance if trades were executed
            if result.get("trades_executed", 0) > 0:
                pnl = result.get("pnl_change", 0.0)
                count = result["trades_executed"]
                # Use total pnl for a single performance update instead of
                # splitting evenly (avoids inaccurate per-trade is_win)
                await repo.update_performance(
                    self.agent_id,
                    pnl_change=pnl,
                    is_win=pnl > 0,
                    trade_count=count,
                )

            # Update timestamps
            await repo.update(
                self.agent_id,
                strategy.user_id,
                last_run_at=datetime.now(UTC),
                next_run_at=datetime.now(UTC) + timedelta(minutes=self.interval_minutes),
            )

            await session.commit()

            logger.info(
                f"Quant strategy {self.agent_id} ({self.strategy_type}) cycle: "
                f"{result.get('message', 'completed')}"
            )

    async def _update_status(self, status: str, error: Optional[str] = None) -> None:
        """Update strategy status in database"""
        async with AsyncSessionLocal() as session:
            repo = QuantStrategyRepository(session)
            await repo.update_status(self.agent_id, status, error)
            await session.commit()


class QuantWorkerManager:
    """
    Manages quant strategy execution workers.

    Distributed safety:
    - Uses Redis-based leader election per strategy so that only
      one application instance runs the worker for a given strategy.
    - A periodic sync task refreshes ownership, detects orphaned
      workers, and starts workers for newly-activated strategies.
    """

    def __init__(self):
        self._workers: Dict[str, QuantExecutionWorker] = {}
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the quant worker manager and load active strategies"""
        if self._running:
            return
        self._running = True
        await self._load_active_strategies()
        # Start periodic sync task to handle:
        # - Refreshing ownership TTLs
        # - Picking up strategies whose owner instance crashed
        # - Restarting failed workers
        self._sync_task = asyncio.create_task(self._periodic_sync())
        logger.info(f"Quant Worker Manager ({_INSTANCE_ID}): Started with {len(self._workers)} active strategies")

    async def stop(self) -> None:
        """Stop all workers and release ownership"""
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Stop workers and release ownership
        for sid in list(self._workers.keys()):
            await self._stop_and_release(sid)
        self._workers.clear()
        logger.info("Quant Worker Manager: Stopped")

    async def start_strategy(self, agent_id: str) -> bool:
        """Start a worker for a quant agent (with distributed ownership claim).

        Args:
            agent_id: AgentDB.id (not StrategyDB.id)
        """
        if agent_id in self._workers:
            logger.info(f"Quant worker already running for {agent_id}")
            return True

        # Try to claim ownership via Redis
        if not await self._try_claim_ownership(agent_id):
            logger.debug(
                f"Quant agent {agent_id} is owned by another instance, skipping"
            )
            return False

        try:
            async with AsyncSessionLocal() as session:
                repo = QuantStrategyRepository(session)
                strategy = await repo.get_by_id(uuid.UUID(agent_id))

                if not strategy:
                    logger.error(f"Quant agent {agent_id} not found")
                    await self._release_ownership(agent_id)
                    return False

                # Skip AI strategies - they are handled by ExecutionWorker
                strategy_type = strategy.strategy_type
                if strategy_type == "ai":
                    logger.warning(
                        f"Agent {agent_id} is an AI strategy, "
                        "skipping quant worker. Use ExecutionWorker instead."
                    )
                    await self._release_ownership(agent_id)
                    return False

                # Validate strategy type
                if strategy_type not in ("grid", "dca", "rsi"):
                    logger.error(
                        f"Unknown strategy type '{strategy_type}' for {agent_id}. "
                        "QuantWorker only supports grid, dca, rsi."
                    )
                    await self._release_ownership(agent_id)
                    return False

                trader = None
                if strategy.execution_mode == "mock":
                    # Mock mode: create MockTrader
                    from .tasks import create_mock_trader
                    symbols = [strategy.symbol] if strategy.symbol else ["BTC"]
                    trader, error = await create_mock_trader(strategy, session, symbols=symbols)
                    if error:
                        logger.error(error)
                        await repo.update_status(uuid.UUID(agent_id), "error", error)
                        await session.commit()
                        await self._release_ownership(agent_id)
                        return False
                else:
                    # Live mode: require account
                    if not strategy.account_id:
                        logger.error(f"Quant agent {agent_id} has no account")
                        await repo.update_status(uuid.UUID(agent_id), "error", "No associated account")
                        await session.commit()
                        await self._release_ownership(agent_id)
                        return False

                    # Create trader from account
                    account_repo = AccountRepository(session)
                    account = await account_repo.get_by_id(strategy.account_id)
                    if not account:
                        logger.error(f"Account not found for quant agent {agent_id}")
                        await repo.update_status(uuid.UUID(agent_id), "error", "Associated account not found")
                        await session.commit()
                        await self._release_ownership(agent_id)
                        return False

                    credentials = await account_repo.get_decrypted_credentials(
                        strategy.account_id, strategy.user_id
                    )
                    if not credentials:
                        logger.error(f"Failed to get credentials for quant agent {agent_id}")
                        await self._release_ownership(agent_id)
                        return False

                    trader = create_trader_from_account(account, credentials)
                    await trader.initialize()

                # Determine cycle interval
                interval = DEFAULT_INTERVALS.get(strategy.strategy_type, 5)
                # For DCA, use the config interval
                if strategy.strategy_type == "dca":
                    interval = strategy.config.get("interval_minutes", 60)

                worker = QuantExecutionWorker(
                    agent_id=agent_id,
                    strategy_type=strategy.strategy_type,
                    trader=trader,
                    interval_minutes=interval,
                    account_id=strategy.account_id if strategy.execution_mode != "mock" else None,
                    user_id=strategy.user_id,
                )

                await worker.start()
                self._workers[agent_id] = worker

                logger.info(
                    f"Started quant worker: {strategy.strategy_type} agent "
                    f"{agent_id} (interval: {interval}min)"
                )
                return True

        except Exception as e:
            logger.exception(f"Failed to start quant worker for {agent_id}")
            await self._release_ownership(agent_id)
            return False

    async def stop_strategy(self, agent_id: str) -> None:
        """Stop a worker for a quant agent and release ownership."""
        await self._stop_and_release(agent_id)

    async def _stop_and_release(self, agent_id: str) -> None:
        """Stop worker and release Redis ownership (safe ordering)."""
        worker = self._workers.get(agent_id)
        if worker:
            try:
                await worker.stop()
            except Exception as e:
                logger.warning(f"Error stopping quant worker {agent_id}: {e}")
            # Only remove from dict AFTER stop succeeds
            self._workers.pop(agent_id, None)
        await self._release_ownership(agent_id)
        logger.info(f"Stopped quant worker for {agent_id}")

    # ------------------------------------------------------------------
    # Distributed ownership via Redis
    # ------------------------------------------------------------------

    async def _try_claim_ownership(self, agent_id: str) -> bool:
        """Try to claim ownership of an agent worker via Redis SET NX.

        Returns False when Redis is unavailable — consistent with the
        cycle-level execution lock which also refuses to proceed without
        Redis.  The periodic sync task will retry claiming on the next
        iteration (every 60 s).
        """
        try:
            from ..services.redis_service import get_redis_service
            redis_service = await get_redis_service()
            key = f"{_WORKER_OWNER_PREFIX}{agent_id}"
            claimed = await redis_service.redis.set(
                key, _INSTANCE_ID, nx=True, ex=_OWNER_TTL_SECONDS
            )
            return bool(claimed)
        except Exception as e:
            logger.warning(
                f"Redis ownership claim failed for {agent_id}: {e}. "
                "Will retry on next sync cycle."
            )
            return False

    # Lua script: atomically compare owner and refresh TTL.
    # Returns 1 if refreshed, 0 if owned by someone else, -1 if key missing.
    _REFRESH_LUA = """
    local cur = redis.call('GET', KEYS[1])
    if cur == false then
        return -1
    elseif cur == ARGV[1] then
        redis.call('EXPIRE', KEYS[1], ARGV[2])
        return 1
    else
        return 0
    end
    """

    # Lua script: atomically compare owner and delete.
    # Returns 1 if deleted, 0 otherwise.
    _RELEASE_LUA = """
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        return redis.call('DEL', KEYS[1])
    else
        return 0
    end
    """

    async def _refresh_ownership(self, agent_id: str) -> bool:
        """Refresh ownership TTL atomically. Returns False if we lost ownership.

        Uses a Lua script so that the GET + EXPIRE is executed as a
        single atomic Redis operation, preventing the race where the key
        expires between the two calls and another instance claims it.
        """
        try:
            from ..services.redis_service import get_redis_service
            redis_service = await get_redis_service()
            key = f"{_WORKER_OWNER_PREFIX}{agent_id}"

            result = await redis_service.redis.eval(
                self._REFRESH_LUA, 1, key,
                _INSTANCE_ID, _OWNER_TTL_SECONDS,
            )

            if result == 1:
                return True
            elif result == -1:
                # Key expired – try to reclaim atomically
                claimed = await redis_service.redis.set(
                    key, _INSTANCE_ID, nx=True, ex=_OWNER_TTL_SECONDS
                )
                return bool(claimed)
            else:
                # Another instance owns it
                return False
        except Exception:
            # Redis down – keep running; the per-cycle execution lock
            # still prevents duplicate execution.
            return True

    async def _release_ownership(self, agent_id: str) -> None:
        """Release ownership of an agent worker atomically.

        Uses a Lua script to ensure we only delete the key if we still
        own it, preventing accidental deletion of another instance's
        ownership claim.
        """
        try:
            from ..services.redis_service import get_redis_service
            redis_service = await get_redis_service()
            key = f"{_WORKER_OWNER_PREFIX}{agent_id}"
            await redis_service.redis.eval(
                self._RELEASE_LUA, 1, key, _INSTANCE_ID
            )
        except Exception:
            pass  # Best-effort; TTL will clean up

    # ------------------------------------------------------------------
    # Periodic sync
    # ------------------------------------------------------------------

    async def _periodic_sync(self) -> None:
        """Periodically refresh ownership and pick up orphaned strategies."""
        while self._running:
            try:
                await asyncio.sleep(_SYNC_INTERVAL_SECONDS)
                if not self._running:
                    break

                # 1. Refresh ownership for strategies we're running
                lost = []
                for sid in list(self._workers.keys()):
                    if not await self._refresh_ownership(sid):
                        lost.append(sid)

                # Stop workers we lost ownership of
                for sid in lost:
                    logger.warning(
                        f"Lost ownership of quant strategy {sid}, stopping local worker"
                    )
                    worker = self._workers.pop(sid, None)
                    if worker:
                        await worker.stop()

                # 2. Try to claim orphaned active strategies
                await self._load_active_strategies()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Quant worker sync error")
                await asyncio.sleep(30)

    async def _load_active_strategies(self) -> None:
        """Load and start workers for all active quant strategies (if not owned by another instance)."""
        try:
            async with AsyncSessionLocal() as session:
                repo = QuantStrategyRepository(session)
                active = await repo.get_active_strategies()

                for strategy in active:
                    sid = str(strategy.id)
                    if sid not in self._workers:
                        await self.start_strategy(sid)

        except Exception as e:
            logger.exception("Failed to load active quant strategies")

    def get_worker_count(self) -> int:
        """Get the number of running workers"""
        return len(self._workers)

    def get_running_strategies(self) -> list[str]:
        """Get list of running strategy IDs"""
        return list(self._workers.keys())


# Singleton
_quant_worker_manager: Optional[QuantWorkerManager] = None


async def get_quant_worker_manager() -> QuantWorkerManager:
    """Get the singleton QuantWorkerManager instance"""
    global _quant_worker_manager
    if _quant_worker_manager is None:
        _quant_worker_manager = QuantWorkerManager()
    return _quant_worker_manager
