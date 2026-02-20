"""
AI Worker Backend - Handles AI strategy execution.

This backend wraps the existing ExecutionWorker and WorkerManager
to implement the WorkerBackend interface, enabling unified management
through UnifiedWorkerManager.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Dict, Optional

from .base_backend import BaseWorkerBackend
from .lifecycle import (
    get_instance_id,
    send_initial_heartbeat,
    clear_heartbeat_on_stop,
    close_trader_safely,
    try_acquire_ownership,
    release_ownership,
    acquire_execution_lock,
    release_execution_lock,
    OWNER_TTL_SECONDS,
)
from ..core.config import get_settings
from ..core.retry_utils import (
    ErrorWindow,
    ErrorType,
    classify_error,
    calculate_backoff_delay,
)
from ..db.database import AsyncSessionLocal
from ..db.models import AgentDB
from ..db.repositories.account import AccountRepository
from ..db.repositories.agent import AgentRepository
from ..services.strategy_engine import StrategyEngine
from ..services.worker_heartbeat import get_worker_instance_id
from ..traders.base import BaseTrader, TradeError
from ..traders.ccxt_trader import create_trader_from_account

logger = logging.getLogger(__name__)


class AIExecutionWorker:
    """
    Worker for executing a single AI agent.

    Extends the original ExecutionWorker with distributed safety features:
    - Redis ownership lock for leader election
    - Execution lock to prevent concurrent cycles
    - Error window tracking with configurable thresholds
    - Exponential backoff retry with jitter
    """

    def __init__(
        self,
        agent_id: str,
        trader: BaseTrader,
        interval_minutes: int = 30,
        distributed_safety: bool = True,
    ):
        self.agent_id = uuid.UUID(agent_id)
        self.trader = trader
        self.interval_minutes = interval_minutes
        self._distributed_safety = distributed_safety
        self._instance_id = get_instance_id()

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 60  # Send heartbeat every 60 seconds
        self._last_run: Optional[datetime] = None
        self._error_count = 0
        self._worker_instance_id = get_worker_instance_id()

        settings = get_settings()
        self._max_errors = settings.worker_max_consecutive_errors

        # Enhanced error handling
        self._error_window = ErrorWindow(
            window_seconds=settings.worker_error_window_seconds,
            max_errors=settings.worker_max_consecutive_errors,
        )
        self._retry_base_delay = settings.worker_retry_base_delay
        self._retry_max_delay = settings.worker_retry_max_delay
        self._retry_jitter = settings.worker_retry_jitter

    async def start(self) -> None:
        """Start the worker."""
        if self._running:
            return
        self._running = True

        # Send initial heartbeat immediately
        await send_initial_heartbeat(self.agent_id, self._worker_instance_id)

        # Start background heartbeat task (independent of execution cycle)
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Started AI worker for agent {self.agent_id}")

    async def _heartbeat_loop(self) -> None:
        """Background heartbeat task - sends heartbeat every 60 seconds."""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                if not self._running:
                    break
                await self._send_background_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat error for AI agent {self.agent_id}: {e}")

    async def _send_background_heartbeat(self) -> None:
        """Send background heartbeat independent of execution cycle."""
        try:
            async with AsyncSessionLocal() as session:
                from ..services.worker_heartbeat import update_heartbeat_with_retry
                await update_heartbeat_with_retry(
                    session, self.agent_id, self._worker_instance_id
                )
        except Exception as e:
            logger.warning(f"Background heartbeat failed for AI agent {self.agent_id}: {e}")

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the worker gracefully with timeout."""
        self._running = False

        # Stop heartbeat task first
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await asyncio.wait_for(self._heartbeat_task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    f"AI worker for agent {self.agent_id} did not stop within {timeout}s"
                )
            except asyncio.CancelledError:
                pass

        # Clear heartbeat on shutdown
        await clear_heartbeat_on_stop(self.agent_id)

        # Release ownership if using distributed safety
        if self._distributed_safety:
            await release_ownership(str(self.agent_id), self._instance_id)

        # Close trader connection
        await close_trader_safely(self.trader, self.agent_id)

        logger.info(f"Stopped AI worker for agent {self.agent_id}")

    async def _run_loop(self) -> None:
        """Main execution loop with enhanced error handling."""
        while self._running:
            try:
                await self._run_cycle()
                # Success: reset error window and counters
                self._error_count = 0
                self._error_window.reset()

                # Wait for next interval
                await asyncio.sleep(self.interval_minutes * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                error_type = classify_error(e)
                logger.error(f"Error in AI agent {self.agent_id}: {e} (type: {error_type.value})")

                # Permanent errors: stop immediately
                if error_type == ErrorType.PERMANENT:
                    error_msg = f"Permanent error: {str(e)}"
                    logger.error(f"Permanent error, stopping agent {self.agent_id}")
                    await self._update_agent_status("error", error_msg)
                    break

                # Record error in window
                self._error_count += 1
                self._error_window.record_error()

                # Check if error threshold reached within window
                if self._error_window.should_stop:
                    error_msg = (
                        f"Too many errors within error window "
                        f"({self._error_window.error_count} errors in "
                        f"{self._error_window.window_seconds}s): {str(e)}"
                    )
                    logger.error(f"Error threshold reached, stopping agent {self.agent_id}")
                    await self._update_agent_status("error", error_msg)
                    break

                # Calculate backoff delay with jitter
                delay = calculate_backoff_delay(
                    attempt=min(self._error_count - 1, 5),  # Cap attempt for backoff
                    base_delay=self._retry_base_delay,
                    max_delay=self._retry_max_delay,
                    jitter=self._retry_jitter,
                )
                logger.info(
                    f"Transient error, retrying agent {self.agent_id} "
                    f"in {delay:.1f}s (error {self._error_count}/{self._max_errors})"
                )
                await asyncio.sleep(delay)

    async def _run_cycle(self) -> None:
        """Run one decision cycle with optional execution lock."""
        # Acquire execution lock if using distributed safety
        lock_key = None
        if self._distributed_safety:
            acquired, lock_key = await acquire_execution_lock(str(self.agent_id))
            if not acquired:
                logger.warning(
                    f"AI agent {self.agent_id} already executing (concurrent lock), skipping"
                )
                return

        try:
            await self._run_cycle_inner()
        finally:
            if lock_key:
                await release_execution_lock(lock_key)

    async def _run_cycle_inner(self) -> None:
        """Inner cycle logic after lock is acquired."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from ..services.redis_service import get_redis_service
        from ..services.agent_position_service import AgentPositionService

        async with AsyncSessionLocal() as session:
            # Update heartbeat at start of cycle with retry
            from ..services.worker_heartbeat import update_heartbeat_with_retry
            heartbeat_ok = await update_heartbeat_with_retry(
                session, self.agent_id, self._worker_instance_id
            )
            if not heartbeat_ok:
                logger.warning(
                    f"Heartbeat update failed for agent {self.agent_id}, "
                    "continuing execution cycle"
                )

            # Get agent from database
            agent_stmt = (
                select(AgentDB)
                .where(AgentDB.id == self.agent_id)
                .options(selectinload(AgentDB.strategy))
            )
            result = await session.execute(agent_stmt)
            agent = result.scalar_one_or_none()

            if not agent:
                logger.info(f"Agent {self.agent_id} not found, stopping")
                self._running = False
                return

            if agent.status != "active":
                logger.info(
                    f"Agent {self.agent_id} is not active (status={agent.status}), stopping"
                )
                self._running = False
                return

            strategy = agent.strategy
            if not strategy:
                logger.warning(f"Agent {self.agent_id} has no strategy, stopping")
                self._running = False
                return

            # Create agent position service
            try:
                redis_service = await get_redis_service()
            except Exception:
                redis_service = None
            position_service = AgentPositionService(db=session, redis=redis_service)

            # Create strategy engine
            engine = StrategyEngine(
                agent=agent,
                trader=self.trader,
                ai_client=None,  # Let StrategyEngine create based on config
                db_session=session,
                position_service=position_service,
            )

            # Run decision cycle
            cycle_result = await engine.run_cycle()

            # Update agent timestamps
            agent_repo = AgentRepository(session)
            await agent_repo.update(
                agent.id,
                agent.user_id,
                last_run_at=datetime.now(UTC),
                next_run_at=datetime.now(UTC) + timedelta(minutes=self.interval_minutes),
            )

            await session.commit()
            self._last_run = datetime.now(UTC)

            logger.info(
                f"Agent {self.agent_id} cycle completed: "
                f"success={cycle_result['success']}, "
                f"tokens={cycle_result['tokens_used']}, "
                f"latency={cycle_result['latency_ms']}ms"
            )

    async def _update_agent_status(
        self, status: str, error: Optional[str] = None
    ) -> None:
        """Update agent status in database."""
        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            await agent_repo.update_status(self.agent_id, status, error)
            await session.commit()
            logger.info(f"Updated agent {self.agent_id} status to '{status}'")


class AIWorkerBackend(BaseWorkerBackend):
    """
    AI Worker Backend implementing WorkerBackend interface.

    Manages AI strategy execution workers with distributed safety.
    """

    def __init__(self, distributed_safety: bool = True):
        super().__init__()
        self._workers: Dict[str, AIExecutionWorker] = {}
        self._distributed_safety = distributed_safety
        self._sync_task: Optional[asyncio.Task] = None

    @property
    def backend_type(self) -> str:
        return "ai"

    async def start(self) -> None:
        """Start the AI backend."""
        if self._running:
            return
        self._running = True

        # Load active AI agents
        await self._load_active_agents()

        # Start ownership refresh task if using distributed safety
        if self._distributed_safety:
            self._sync_task = asyncio.create_task(self._periodic_sync())

        logger.info(
            f"AI Worker Backend: Started with {len(self._workers)} active agents "
            f"(distributed_safety={self._distributed_safety})"
        )

    async def stop(self) -> None:
        """Stop the AI backend."""
        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Stop all workers
        for agent_id in list(self._workers.keys()):
            await self.stop_agent(agent_id)

        self._workers.clear()
        logger.info("AI Worker Backend: Stopped")

    async def start_agent(self, agent_id: str) -> bool:
        """Start a worker for an AI agent."""
        if agent_id in self._workers:
            return True  # Already running

        # Try to claim ownership if using distributed safety
        if self._distributed_safety:
            if not await try_acquire_ownership(agent_id):
                logger.debug(
                    f"AI agent {agent_id} is owned by another instance, skipping"
                )
                return False

        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                # Get agent with strategy and account
                agent_stmt = (
                    select(AgentDB)
                    .where(AgentDB.id == uuid.UUID(agent_id))
                    .options(
                        selectinload(AgentDB.strategy),
                        selectinload(AgentDB.account),
                    )
                )
                agent_result = await session.execute(agent_stmt)
                agent = agent_result.scalar_one_or_none()

                if not agent:
                    logger.error(f"AI agent {agent_id} not found")
                    if self._distributed_safety:
                        await release_ownership(agent_id)
                    return False

                if agent.status != "active":
                    logger.warning(
                        f"AI agent {agent_id} is not active (status={agent.status})"
                    )
                    if self._distributed_safety:
                        await release_ownership(agent_id)
                    return False

                strategy = agent.strategy
                if not strategy:
                    logger.error(f"AI agent {agent_id} has no strategy")
                    if self._distributed_safety:
                        await release_ownership(agent_id)
                    return False

                # Only handle AI strategies
                if strategy.type != "ai":
                    logger.debug(
                        f"Agent {agent_id} is not an AI strategy (type={strategy.type})"
                    )
                    if self._distributed_safety:
                        await release_ownership(agent_id)
                    return False

                # Create trader
                trader = None
                if agent.execution_mode == "mock":
                    from .tasks import create_mock_trader
                    trader, error = await create_mock_trader(
                        agent, session, symbols=strategy.symbols
                    )
                    if error:
                        logger.error(error)
                        await self._set_agent_error(
                            agent.id, f"Worker startup failed: {error}", session
                        )
                        if self._distributed_safety:
                            await release_ownership(agent_id)
                        return False
                else:
                    # Live mode
                    if not agent.account_id:
                        error_msg = f"AI agent {agent_id} has no account configured"
                        logger.error(error_msg)
                        await self._set_agent_error(
                            agent.id, "Worker startup failed: No exchange account", session
                        )
                        if self._distributed_safety:
                            await release_ownership(agent_id)
                        return False

                    account_repo = AccountRepository(session)
                    account = await account_repo.get_by_id(agent.account_id)
                    if not account:
                        error_msg = f"Account {agent.account_id} not found"
                        logger.error(error_msg)
                        await self._set_agent_error(
                            agent.id, "Worker startup failed: Account not found", session
                        )
                        if self._distributed_safety:
                            await release_ownership(agent_id)
                        return False

                    credentials = await account_repo.get_decrypted_credentials(
                        agent.account_id, agent.user_id
                    )
                    if not credentials:
                        error_msg = f"Failed to get credentials for account {agent.account_id}"
                        logger.error(error_msg)
                        await self._set_agent_error(
                            agent.id, "Worker startup failed: Invalid API credentials", session
                        )
                        if self._distributed_safety:
                            await release_ownership(agent_id)
                        return False

                    try:
                        trader = create_trader_from_account(account, credentials)
                        await trader.initialize()
                    except (ValueError, TradeError) as e:
                        error_msg = f"Trader initialization failed: {str(e)}"
                        logger.error(f"Failed to create trader for agent {agent_id}: {e}")
                        if trader:
                            await close_trader_safely(trader, agent.id)
                        await self._set_agent_error(agent.id, error_msg, session)
                        if self._distributed_safety:
                            await release_ownership(agent_id)
                        return False

                # Get interval from agent
                interval = agent.execution_interval_minutes or 30

                # Create and start worker
                worker = AIExecutionWorker(
                    agent_id=agent_id,
                    trader=trader,
                    interval_minutes=interval,
                    distributed_safety=self._distributed_safety,
                )

                await worker.start()
                self._workers[agent_id] = worker

                mode = "mock" if agent.execution_mode == "mock" else "live"
                logger.info(
                    f"Started AI worker for agent {agent_id} ({mode} mode)"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to start AI agent {agent_id}: {e}")
            if self._distributed_safety:
                await release_ownership(agent_id)
            return False

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a worker for an AI agent."""
        worker = self._workers.get(agent_id)
        if not worker:
            return True  # Not running

        try:
            await worker.stop()
        except Exception as e:
            logger.warning(f"Error stopping AI worker {agent_id}: {e}")

        self._workers.pop(agent_id, None)
        return True

    async def trigger_execution(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """Manually trigger an AI agent execution."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from ..services.redis_service import get_redis_service
        from ..services.agent_position_service import AgentPositionService

        trader = None
        try:
            async with AsyncSessionLocal() as session:
                agent_stmt = (
                    select(AgentDB)
                    .where(
                        AgentDB.id == uuid.UUID(agent_id),
                        AgentDB.status == "active",
                    )
                    .options(selectinload(AgentDB.strategy))
                )
                if user_id:
                    agent_stmt = agent_stmt.where(
                        AgentDB.user_id == uuid.UUID(user_id)
                    )

                agent_result = await session.execute(agent_stmt)
                agent = agent_result.scalar_one_or_none()

                if not agent:
                    return {"success": False, "error": "Agent not found or not active"}

                strategy = agent.strategy
                if not strategy:
                    return {"success": False, "error": "Strategy not found"}

                # Create trader
                if agent.execution_mode == "mock":
                    from .tasks import create_mock_trader
                    trader, error = await create_mock_trader(
                        agent, session, symbols=strategy.symbols
                    )
                    if error:
                        return {"success": False, "error": error}
                else:
                    if not agent.account_id:
                        return {
                            "success": False,
                            "error": "Agent has no account configured",
                        }

                    account_repo = AccountRepository(session)
                    account = await account_repo.get_by_id(agent.account_id)
                    if not account:
                        return {"success": False, "error": "Account not found"}

                    credentials = await account_repo.get_decrypted_credentials(
                        agent.account_id, agent.user_id
                    )
                    if not credentials:
                        return {
                            "success": False,
                            "error": "Failed to decrypt account credentials",
                        }

                    trader = create_trader_from_account(account, credentials)
                    await trader.initialize()

                # Create position service
                try:
                    redis_service = await get_redis_service()
                except Exception:
                    redis_service = None
                position_service = AgentPositionService(db=session, redis=redis_service)

                # Create engine and run one cycle
                engine = StrategyEngine(
                    agent=agent,
                    strategy=strategy,
                    trader=trader,
                    ai_client=None,
                    db_session=session,
                    position_service=position_service,
                )

                result = await engine.run_cycle()

                # Update agent timestamps
                agent_repo = AgentRepository(session)
                interval = agent.execution_interval_minutes or 30
                await agent_repo.update(
                    agent.id,
                    agent.user_id,
                    last_run_at=datetime.now(UTC),
                    next_run_at=datetime.now(UTC) + timedelta(minutes=interval),
                )
                await session.commit()

                logger.info(
                    f"Manual execution for AI agent {agent.id}: "
                    f"success={result['success']}, "
                    f"tokens={result['tokens_used']}, "
                    f"latency={result['latency_ms']}ms"
                )

                return {
                    "success": True,
                    "decision_id": result.get("decision_record_id"),
                    "cycle_success": result["success"],
                    "error": result.get("error"),
                }

        except Exception as e:
            logger.error(f"Manual execution failed for AI agent {agent_id}: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if trader:
                await close_trader_safely(trader, uuid.UUID(agent_id))

    def get_worker_status(self, agent_id: str) -> Optional[dict]:
        """Get status of a worker."""
        worker = self._workers.get(agent_id)
        if not worker:
            return None

        return {
            "running": worker._running,
            "last_run": worker._last_run.isoformat() if worker._last_run else None,
            "error_count": worker._error_count,
            "mode": "ai",
            "distributed_safety": self._distributed_safety,
        }

    def list_running_agents(self) -> list[str]:
        """List all running AI agent IDs."""
        return list(self._workers.keys())

    async def _set_agent_error(
        self,
        agent_id: uuid.UUID,
        error_message: str,
        session,
    ) -> None:
        """Set agent status to error with detailed message."""
        try:
            agent_repo = AgentRepository(session)
            await agent_repo.update_status(agent_id, "error", error_message)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to set agent {agent_id} error status: {e}")

    async def _load_active_agents(self, clear_heartbeats: bool = True) -> None:
        """Load and start workers for all active AI agents.

        Args:
            clear_heartbeats: If True, clear heartbeats before loading (for initial startup).
                             If False, just try to claim orphaned agents (for periodic sync).
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from ..services.worker_heartbeat import (
            clear_all_heartbeats_for_active_agents,
        )

        async with AsyncSessionLocal() as session:
            # Only clear heartbeats on initial startup, not during periodic sync
            # This prevents interfering with running workers' heartbeats
            if clear_heartbeats:
                await clear_all_heartbeats_for_active_agents(session)

            # NOTE: We do NOT call mark_stale_agents_as_error here.
            # Service restart is expected, and we should try to recover active agents
            # rather than immediately marking them as error.
            # Stale detection happens via heartbeat timeout in worker_heartbeat service.

            # Query active AI agents
            account_repo = AccountRepository(session)

            stmt = (
                select(AgentDB)
                .where(AgentDB.status == "active")
                .options(
                    selectinload(AgentDB.strategy),
                    selectinload(AgentDB.account),
                )
            )
            result = await session.execute(stmt)
            agents = result.scalars().all()

            for agent in agents:
                strategy = agent.strategy
                if not strategy or strategy.type != "ai":
                    continue

                # Start the worker
                success = await self.start_agent(str(agent.id))
                if success:
                    logger.info(f"Auto-started AI worker for agent {agent.id}")
                else:
                    logger.error(
                        f"Failed to auto-start AI worker for agent {agent.id}"
                    )

                await asyncio.sleep(1)

    async def _periodic_sync(self) -> None:
        """Periodically refresh ownership and pick up orphaned agents."""
        from .lifecycle import refresh_ownership

        while self._running:
            try:
                await asyncio.sleep(60)  # Sync every minute
                if not self._running:
                    break

                # 1. Refresh ownership for agents we're running
                lost = []
                for agent_id in list(self._workers.keys()):
                    if not await refresh_ownership(agent_id):
                        lost.append(agent_id)

                # Stop workers we lost ownership of
                for agent_id in lost:
                    logger.warning(
                        f"Lost ownership of AI agent {agent_id}, stopping local worker"
                    )
                    await self.stop_agent(agent_id)

                # 2. Try to claim orphaned active agents (without clearing heartbeats)
                await self._load_active_agents(clear_heartbeats=False)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("AI worker sync error")
                await asyncio.sleep(30)
