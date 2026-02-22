"""
Execution Worker for background agent processing.

Supports two modes:
1. Legacy Mode: In-process workers (single process, no scaling)
2. Distributed Mode: ARQ task queue (scalable, fault-tolerant)

Manages the lifecycle of agent execution:
- Scheduling based on intervals
- Running decision cycles
- Heartbeat tracking for crash recovery
- Logging and error handling
- Graceful shutdown

Architecture (v2 - Agent-based):
- Workers bind to agent_id (not strategy_id)
- Multiple agents can share the same strategy
- Each agent has independent execution state
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Dict, Optional

from ..core.config import get_settings
from ..db.database import AsyncSessionLocal
from ..db.models import AgentDB, DecisionRecordDB, ExchangeAccountDB, StrategyDB
from ..db.repositories.account import AccountRepository
from ..db.repositories.agent import AgentRepository
from ..db.repositories.decision import DecisionRepository
from ..db.repositories.strategy import StrategyRepository
from ..services.ai import BaseAIClient, get_ai_client
from ..services.worker_heartbeat import (
    get_worker_instance_id,
    update_heartbeat,
    clear_heartbeat,
    is_agent_running,
)
from ..services.strategy_engine import StrategyEngine
from ..traders.base import BaseTrader, TradeError
from ..traders.ccxt_trader import CCXTTrader, EXCHANGE_ID_MAP, create_trader_from_account

logger = logging.getLogger(__name__)


class ExecutionWorker:
    """
    Worker for executing a single agent.

    Runs the agent's decision cycle at configured intervals.
    Binds to agent_id (not strategy_id) to support multiple agents per strategy.

    Lifecycle:
    1. Initialize (connect to exchange/mock)
    2. Run decision cycles with heartbeat updates
    3. Handle errors and update status
    4. Graceful shutdown with heartbeat cleanup
    """

    def __init__(
        self,
        agent_id: str,
        trader: BaseTrader,
        ai_client: Optional[BaseAIClient] = None,
        interval_minutes: int = 30,
    ):
        """
        Initialize execution worker.

        Args:
            agent_id: UUID of agent to execute
            trader: Exchange trading adapter
            ai_client: AI client for decisions (if None, auto-created per agent)
            interval_minutes: Minutes between decision cycles
        """
        self.agent_id = uuid.UUID(agent_id)
        self.trader = trader
        self.ai_client = ai_client  # May be None, will be created per agent
        self.interval_minutes = interval_minutes

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
        self._error_count = 0
        self._worker_instance_id = get_worker_instance_id()

        # Get max errors from settings
        settings = get_settings()
        self._max_errors = settings.worker_max_consecutive_errors

    async def start(self) -> None:
        """Start the worker"""
        if self._running:
            return

        self._running = True

        # Send initial heartbeat immediately to avoid "not running" status
        # during the gap between API activation and first cycle execution
        try:
            async with AsyncSessionLocal() as session:
                await update_heartbeat(session, self.agent_id, self._worker_instance_id)
        except Exception as e:
            logger.warning(f"Failed to send initial heartbeat for agent {self.agent_id}: {e}")

        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Started worker for agent {self.agent_id}")

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the worker gracefully with timeout"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Worker for agent {self.agent_id} did not stop within {timeout}s, forcing")
            except asyncio.CancelledError:
                pass

        # Clear heartbeat on shutdown
        try:
            async with AsyncSessionLocal() as session:
                await clear_heartbeat(session, self.agent_id)
        except Exception as e:
            logger.warning(f"Failed to clear heartbeat for agent {self.agent_id}: {e}")

        # Close trader connection to avoid resource leaks
        if self.trader:
            try:
                await self.trader.close()
            except Exception as e:
                logger.warning(f"Error closing trader for agent {self.agent_id}: {e}")

        logger.info(f"Stopped worker for agent {self.agent_id}")

    async def _run_loop(self) -> None:
        """Main execution loop"""
        while self._running:
            try:
                await self._run_cycle()
                self._error_count = 0  # Reset on success

                # Wait for next interval
                await asyncio.sleep(self.interval_minutes * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in agent {self.agent_id}: {e}")
                self._error_count += 1

                if self._error_count >= self._max_errors:
                    error_msg = f"Execution failed after {self._error_count} retries: {str(e)}"
                    logger.error(f"Too many errors, stopping agent {self.agent_id}")
                    await self._update_agent_status("error", error_msg)
                    break

                # Wait before retry
                await asyncio.sleep(60)

    async def _run_cycle(self) -> None:
        """Run one decision cycle"""
        async with AsyncSessionLocal() as session:
            # Update heartbeat at start of cycle
            await update_heartbeat(session, self.agent_id, self._worker_instance_id)

            # Get agent from database
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

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
                logger.info(f"Agent {self.agent_id} is not active (status={agent.status}), stopping")
                self._running = False
                return

            strategy = agent.strategy
            if not strategy:
                logger.warning(f"Agent {self.agent_id} has no strategy, stopping")
                self._running = False
                return

            # Create agent position service
            from ..services.redis_service import get_redis_service
            from ..services.agent_position_service import AgentPositionService
            try:
                redis_service = await get_redis_service()
            except Exception:
                redis_service = None
            position_service = AgentPositionService(db=session, redis=redis_service)

            # Create strategy engine with db_session for decision persistence
            # AI client is created by StrategyEngine based on agent's ai_model
            engine = StrategyEngine(
                agent=agent,
                trader=self.trader,
                ai_client=self.ai_client,  # May be None, engine creates based on agent config
                db_session=session,  # Pass session for decision persistence
                position_service=position_service,
            )

            # Run decision cycle (decision is saved inside run_cycle)
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


    async def _update_agent_status(self, status: str, error: Optional[str] = None) -> None:
        """Update agent status in database."""
        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            await agent_repo.update_status(self.agent_id, status, error)
            await session.commit()
            logger.info(f"Updated agent {self.agent_id} status to '{status}'")


class WorkerManager:
    """
    Manages agent execution workers.

    Supports two modes:
    1. Legacy Mode (distributed=False): In-process workers, single process
    2. Distributed Mode (distributed=True): ARQ task queue, scalable

    Responsibilities:
    - Start/stop workers for agents
    - Monitor worker health
    - Handle agent status changes
    - Recover from crashes using heartbeat
    """

    def __init__(self, distributed: bool = False):
        """
        Initialize WorkerManager.

        Args:
            distributed: If True, use ARQ task queue. If False, use in-process workers.
        """
        self._distributed = distributed
        self._workers: Dict[str, ExecutionWorker] = {}  # agent_id -> ExecutionWorker
        self._task_queue = None  # For distributed mode
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    @property
    def is_distributed(self) -> bool:
        """Check if running in distributed mode."""
        return self._distributed

    async def start(self) -> None:
        """Start the worker manager"""
        if self._running:
            return

        self._running = True

        if self._distributed:
            # Initialize task queue service
            from .queue import get_task_queue_service
            self._task_queue = await get_task_queue_service()
            logger.info("Worker manager started in DISTRIBUTED mode (ARQ)")
        else:
            # Legacy mode: Load active agents and start in-process workers
            await self._load_active_agents()

            # Start monitoring task
            self._monitor_task = asyncio.create_task(self._monitor_loop())

            logger.info("Worker manager started in LEGACY mode (in-process)")

    async def stop(self) -> None:
        """Stop all workers"""
        self._running = False

        if self._distributed:
            # Close task queue
            from .queue import close_task_queue
            await close_task_queue()
            self._task_queue = None
        else:
            # Legacy mode: Stop monitoring and workers
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            # Stop all workers
            for worker in self._workers.values():
                await worker.stop()

            self._workers.clear()

        logger.info("Worker manager stopped")

    async def start_agent(
        self,
        agent_id: str,
        credentials: Optional[dict] = None,
        account: Optional[ExchangeAccountDB] = None,
    ) -> bool:
        """
        Start worker for an agent.

        Args:
            agent_id: Agent UUID
            credentials: Exchange credentials (decrypted). If None, will fetch from account.
            account: Exchange account. If None, will fetch from agent.

        Returns:
            True if started successfully
        """
        if self._distributed:
            # Distributed mode: Submit to task queue
            if not self._task_queue:
                logger.error("Task queue not initialized")
                return False

            job_id = await self._task_queue.start_agent(agent_id)
            if job_id:
                logger.info(f"Scheduled agent {agent_id} via task queue (job: {job_id})")
                return True
            return False

        # Legacy mode: Start in-process worker
        if agent_id in self._workers:
            return True  # Already running

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
                    logger.error(f"Agent {agent_id} not found")
                    return False

                if agent.status != "active":
                    logger.warning(f"Agent {agent_id} is not active (status={agent.status})")
                    return False

                strategy = agent.strategy
                if not strategy:
                    logger.error(f"Agent {agent_id} has no strategy")
                    return False

                trader = None
                if agent.execution_mode == "mock":
                    # Mock mode: create MockTrader
                    from .tasks import create_mock_trader
                    trader, error = await create_mock_trader(agent, session, symbols=strategy.symbols)
                    if error:
                        logger.error(error)
                        await self._set_agent_error(agent.id, f"Worker startup failed: {error}", session)
                        return False
                else:
                    # Live mode: require account
                    if not agent.account_id:
                        error_msg = f"Agent {agent_id} has no account configured"
                        logger.error(error_msg)
                        await self._set_agent_error(agent.id, f"Worker startup failed: No exchange account", session)
                        return False

                    # Get account if not provided
                    if account is None:
                        account_repo = AccountRepository(session)
                        account = await account_repo.get_by_id(agent.account_id)
                        if not account:
                            error_msg = f"Account {agent.account_id} not found for agent {agent_id}"
                            logger.error(error_msg)
                            await self._set_agent_error(agent.id, f"Worker startup failed: Account not found", session)
                            return False

                    # Get credentials if not provided
                    if credentials is None:
                        account_repo = AccountRepository(session)
                        credentials = await account_repo.get_decrypted_credentials(
                            agent.account_id, agent.user_id
                        )
                        if not credentials:
                            error_msg = f"Failed to get credentials for account {agent.account_id}"
                            logger.error(error_msg)
                            await self._set_agent_error(agent.id, "Worker startup failed: Invalid API credentials", session)
                            return False

                    # Create trader using the helper function
                    try:
                        trader = create_trader_from_account(account, credentials)
                        await trader.initialize()
                    except ValueError as e:
                        error_msg = f"Trader initialization failed: {str(e)}"
                        logger.error(f"Failed to create trader for agent {agent_id}: {e}")
                        if trader:
                            try:
                                await trader.close()
                            except Exception:
                                pass
                        await self._set_agent_error(agent.id, error_msg, session)
                        return False
                    except TradeError as e:
                        error_msg = f"Trader initialization failed: {e.message}"
                        logger.error(f"Failed to initialize trader for agent {agent_id}: {e.message}")
                        if trader:
                            try:
                                await trader.close()
                            except Exception:
                                pass
                        await self._set_agent_error(agent.id, error_msg, session)
                        return False

                # Get interval from agent
                interval = agent.execution_interval_minutes or 30

                # Create and start worker
                worker = ExecutionWorker(
                    agent_id=agent_id,
                    trader=trader,
                    ai_client=None,  # Let StrategyEngine create based on config
                    interval_minutes=interval,
                )

                await worker.start()
                self._workers[agent_id] = worker

                mode = "mock" if agent.execution_mode == "mock" else "live"
                logger.info(f"Started worker for agent {agent_id} ({mode} mode)")
                return True

        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {e}")
            return False

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

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop worker for an agent"""
        if self._distributed:
            # Distributed mode: Cancel task queue job
            if not self._task_queue:
                logger.error("Task queue not initialized")
                return False

            return await self._task_queue.stop_agent(agent_id)

        # Legacy mode: Stop in-process worker
        worker = self._workers.get(agent_id)
        if not worker:
            return True  # Not running

        await worker.stop()
        del self._workers[agent_id]
        return True

    # Backward compatibility aliases
    async def start_strategy(
        self,
        strategy_id: str,
        credentials: Optional[dict] = None,
        account: Optional[ExchangeAccountDB] = None,
    ) -> bool:
        """
        Start worker for a strategy (backward compatibility).

        Finds all active agents for the strategy and starts workers.
        Note: This is for backward compatibility. Prefer start_agent().
        """
        # Find active agents for this strategy
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = select(AgentDB).where(
                AgentDB.strategy_id == uuid.UUID(strategy_id),
                AgentDB.status == "active",
            ).limit(1)
            result = await session.execute(stmt)
            agent = result.scalar_one_or_none()

            if agent:
                return await self.start_agent(str(agent.id), credentials, account)
            else:
                logger.warning(f"No active agent found for strategy {strategy_id}")
                return False

    async def stop_strategy(self, strategy_id: str) -> bool:
        """
        Stop worker for a strategy (backward compatibility).

        Finds the worker for the strategy's agent and stops it.
        Note: This is for backward compatibility. Prefer stop_agent().
        """
        # Find agents for this strategy and stop their workers
        for agent_id, worker in list(self._workers.items()):
            # Check if this worker's agent uses this strategy
            # We'd need to query the DB to know for sure, so for now
            # just stop by agent_id
            pass
        return True

    async def trigger_manual_execution(
        self,
        strategy_id: str,
        user_id: str | None = None,
        agent_id: str | None = None,
    ) -> dict:
        """
        Manually trigger an agent execution (Run Now).

        Supports both distributed and legacy modes.

        Args:
            strategy_id: Strategy UUID (for backward compatibility)
            user_id: Optional user UUID for ownership verification
            agent_id: Optional agent UUID (preferred)

        Returns:
            Dict with execution result:
              - distributed: {"job_id": str}
              - legacy: {"success": bool, "decision_id": str | None, "error": str | None}
        """
        if self._distributed:
            if not self._task_queue:
                logger.error("Task queue not initialized")
                return {"success": False, "error": "Task queue not initialized"}

            # Use agent_id if provided, otherwise find by strategy
            target_id = agent_id or strategy_id
            job_id = await self._task_queue.trigger_agent_execution(target_id)
            if job_id:
                return {"success": True, "job_id": job_id}
            return {"success": False, "error": "Failed to enqueue job"}

        # Legacy mode: run a single cycle directly
        trader = None
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                # Determine which agent to run
                if agent_id:
                    agent_stmt = (
                        select(AgentDB)
                        .where(
                            AgentDB.id == uuid.UUID(agent_id),
                            AgentDB.status == "active",
                        )
                        .options(selectinload(AgentDB.strategy))
                    )
                    if user_id:
                        agent_stmt = agent_stmt.where(AgentDB.user_id == uuid.UUID(user_id))
                else:
                    # Backward compatibility: find first active agent by strategy
                    agent_stmt = (
                        select(AgentDB)
                        .where(
                            AgentDB.strategy_id == uuid.UUID(strategy_id),
                            AgentDB.status == "active",
                        )
                        .options(selectinload(AgentDB.strategy))
                        .limit(1)
                    )

                agent_result = await session.execute(agent_stmt)
                agent = agent_result.scalar_one_or_none()

                if not agent:
                    return {"success": False, "error": "Agent not found or not active"}

                strategy = agent.strategy
                if not strategy:
                    return {"success": False, "error": "Strategy not found"}

                if agent.execution_mode == "mock":
                    # Mock mode: use MockTrader
                    from .tasks import create_mock_trader
                    trader, error = await create_mock_trader(agent, session, symbols=strategy.symbols)
                    if error:
                        return {"success": False, "error": error}
                else:
                    # Live mode: use exchange credentials
                    if not agent.account_id:
                        return {"success": False, "error": "Agent has no account configured"}

                    account_repo = AccountRepository(session)
                    account = await account_repo.get_by_id(agent.account_id)
                    if not account:
                        return {"success": False, "error": "Account not found"}

                    credentials = await account_repo.get_decrypted_credentials(
                        agent.account_id, agent.user_id,
                    )
                    if not credentials:
                        return {"success": False, "error": "Failed to decrypt account credentials"}

                    trader = create_trader_from_account(account, credentials)
                    await trader.initialize()

                # Create agent position service
                from ..services.redis_service import get_redis_service
                from ..services.agent_position_service import AgentPositionService
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
                    f"Manual execution for agent {agent.id}: "
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
            logger.error(f"Manual execution failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Clean up trader connection to avoid resource leaks
            if trader:
                try:
                    await trader.close()
                except Exception as e:
                    logger.warning(f"Error closing trader: {e}")

    async def _load_active_agents(self) -> None:
        """Load and start workers for all active agents (legacy mode only)"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from ..services.worker_heartbeat import (
            mark_stale_agents_as_error,
            clear_all_heartbeats_for_active_agents,
        )

        async with AsyncSessionLocal() as session:
            # Phase 1: Mark stale agents as error
            stale_count = await mark_stale_agents_as_error(session)
            if stale_count > 0:
                logger.info(f"Marked {stale_count} stale agents as error")

            # Phase 2: Clear all heartbeats for active agents (clean slate)
            cleared = await clear_all_heartbeats_for_active_agents(session)

            # Phase 3: Query active agents with their strategies
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
                if not strategy:
                    logger.warning(f"Agent {agent.id} has no strategy, skipping")
                    continue

                # Handle Mock mode - no account needed
                if agent.execution_mode == "mock":
                    success = await self.start_agent(str(agent.id))
                    if success:
                        logger.info(f"Auto-started worker for mock agent {agent.id}")
                    else:
                        logger.error(f"Failed to auto-start worker for mock agent {agent.id}")
                    await asyncio.sleep(1)
                    continue

                # Live mode - requires account
                if not agent.account_id:
                    logger.warning(f"Agent {agent.id} is live mode but has no account, skipping")
                    continue

                account = agent.account
                if not account:
                    logger.warning(f"Account not found for agent {agent.id}, skipping")
                    continue

                credentials = await account_repo.get_decrypted_credentials(
                    agent.account_id,
                    agent.user_id
                )
                if not credentials:
                    logger.warning(f"Failed to get credentials for agent {agent.id}, skipping")
                    continue

                # Start the worker
                success = await self.start_agent(
                    str(agent.id),
                    credentials=credentials,
                    account=account,
                )

                if success:
                    logger.info(f"Auto-started worker for agent {agent.id}")
                else:
                    logger.error(f"Failed to auto-start worker for agent {agent.id}")

                # Brief delay between initialisations
                await asyncio.sleep(1)

    async def _monitor_loop(self) -> None:
        """Monitor workers and sync with database (legacy mode only)"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from ..services.worker_heartbeat import detect_stale_agents, mark_stale_agents_as_error

        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute

                async with AsyncSessionLocal() as session:
                    # Check for stale workers (heartbeat timeout)
                    stale_agents = await detect_stale_agents(session)
                    for agent in stale_agents:
                        agent_id_str = str(agent.id)
                        if agent_id_str in self._workers:
                            # Worker in memory but heartbeat timed out - likely hung
                            logger.warning(f"Worker for agent {agent_id_str} appears hung, stopping")
                            await self.stop_agent(agent_id_str)

                    # Mark any remaining stale agents as error
                    if stale_agents:
                        await mark_stale_agents_as_error(session)

                    account_repo = AccountRepository(session)

                    # Load full agent data
                    stmt = (
                        select(AgentDB)
                        .where(AgentDB.status == "active")
                        .options(
                            selectinload(AgentDB.strategy),
                            selectinload(AgentDB.account),
                        )
                    )
                    result = await session.execute(stmt)
                    active_agents = result.scalars().all()
                    active_agent_ids = {str(agent.id) for agent in active_agents}

                    # Stop workers for deactivated agents
                    for agent_id in list(self._workers.keys()):
                        if agent_id not in active_agent_ids:
                            await self.stop_agent(agent_id)

                    # Start workers for newly active agents
                    current_worker_ids = set(self._workers.keys())
                    for agent in active_agents:
                        if str(agent.id) not in current_worker_ids:
                            await self._start_worker_for_agent(agent, account_repo)
                            await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")

    async def _start_worker_for_agent(
        self,
        agent: "AgentDB",
        account_repo: AccountRepository,
    ) -> None:
        """Start a worker for a single agent if not already running."""
        strategy = agent.strategy
        if not strategy:
            logger.warning(f"Agent {agent.id} has no strategy, skipping")
            return

        # Handle Mock mode - no account needed
        if agent.execution_mode == "mock":
            success = await self.start_agent(str(agent.id))
            if success:
                logger.info(f"Monitor started worker for mock agent {agent.id}")
            else:
                logger.error(f"Failed to start worker for mock agent {agent.id}")
            return

        # Live mode - requires account
        if not agent.account_id:
            logger.warning(f"Agent {agent.id} is live mode but has no account, skipping")
            return

        account = agent.account
        if not account:
            logger.warning(f"Account not found for agent {agent.id}, skipping")
            return

        credentials = await account_repo.get_decrypted_credentials(
            agent.account_id,
            agent.user_id,
        )
        if not credentials:
            logger.warning(f"Failed to get credentials for agent {agent.id}, skipping")
            return

        success = await self.start_agent(
            str(agent.id),
            credentials=credentials,
            account=account,
        )
        if success:
            logger.info(f"Monitor started worker for agent {agent.id}")
        else:
            logger.error(f"Failed to start worker for agent {agent.id}")

    def get_worker_status(self, agent_id: str) -> Optional[dict]:
        """Get status of a worker"""
        if self._distributed:
            return {
                "running": True,
                "last_run": None,
                "error_count": 0,
                "mode": "distributed",
            }

        worker = self._workers.get(agent_id)
        if not worker:
            return None

        return {
            "running": worker._running,
            "last_run": worker._last_run.isoformat() if worker._last_run else None,
            "error_count": worker._error_count,
            "mode": "legacy",
        }

    async def get_distributed_status(self, agent_id: str) -> Optional[dict]:
        """Get status from task queue (distributed mode only)"""
        if not self._distributed or not self._task_queue:
            return None

        return await self._task_queue.get_agent_job_status(agent_id)

    async def get_queue_info(self) -> Optional[dict]:
        """Get task queue info (distributed mode only)"""
        if not self._distributed or not self._task_queue:
            return None

        return await self._task_queue.get_queue_info()

    def list_workers(self) -> list[str]:
        """List all running worker agent IDs"""
        if self._distributed:
            return []

        return list(self._workers.keys())


# Global worker manager instance
_worker_manager: Optional[WorkerManager] = None


async def get_worker_manager(distributed: Optional[bool] = None) -> WorkerManager:
    """
    Get or create worker manager singleton.

    This function provides backward compatibility by returning a wrapper
    that delegates to UnifiedWorkerManager. The actual worker management
    is now handled by the unified system.

    Args:
        distributed: If True, use ARQ task queue. If False, use in-process workers.
                    If None, uses WORKER_DISTRIBUTED setting from config.
                    Note: distributed mode is deprecated; unified manager uses in-process.

    Returns:
        WorkerManager instance (wrapper around UnifiedWorkerManager)
    """
    global _worker_manager
    if _worker_manager is None:
        # Import here to avoid circular import
        from .unified_manager import get_unified_worker_manager

        # Get the unified manager and create a compatibility wrapper
        unified = await get_unified_worker_manager()
        _worker_manager = _WorkerManagerCompatibilityWrapper(unified)
    return _worker_manager


async def reset_worker_manager() -> None:
    """Reset worker manager (for testing)"""
    global _worker_manager
    if _worker_manager:
        await _worker_manager.stop()
    _worker_manager = None


class _WorkerManagerCompatibilityWrapper:
    """
    Compatibility wrapper that provides the WorkerManager interface
    but delegates to UnifiedWorkerManager.
    """

    def __init__(self, unified_manager):
        self._unified = unified_manager
        self._distributed = False

    @property
    def is_distributed(self) -> bool:
        return False

    @property
    def _running(self) -> bool:
        """Delegate running status to unified manager."""
        return self._unified._running

    async def start(self) -> None:
        await self._unified.start()

    async def stop(self) -> None:
        await self._unified.stop()

    async def start_agent(
        self,
        agent_id: str,
        credentials=None,
        account=None,
    ) -> bool:
        return await self._unified.start_agent(agent_id)

    async def stop_agent(self, agent_id: str) -> bool:
        return await self._unified.stop_agent(agent_id)

    async def start_strategy(
        self,
        strategy_id: str,
        credentials=None,
        account=None,
    ) -> bool:
        return await self._unified.start_strategy(strategy_id, credentials, account)

    async def stop_strategy(self, strategy_id: str) -> bool:
        return await self._unified.stop_strategy(strategy_id)

    async def trigger_manual_execution(
        self,
        strategy_id: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> dict:
        return await self._unified.trigger_manual_execution(
            strategy_id, user_id, agent_id
        )

    def get_worker_status(self, agent_id: str) -> Optional[dict]:
        return self._unified.get_worker_status(agent_id)

    async def get_distributed_status(self, agent_id: str) -> Optional[dict]:
        return await self._unified.get_distributed_status(agent_id)

    async def get_queue_info(self) -> Optional[dict]:
        return await self._unified.get_queue_info()

    def list_workers(self) -> list[str]:
        return self._unified.list_workers()
