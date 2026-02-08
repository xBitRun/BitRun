"""
Execution Worker for background strategy processing.

Supports two modes:
1. Legacy Mode: In-process workers (single process, no scaling)
2. Distributed Mode: ARQ task queue (scalable, fault-tolerant)

Manages the lifecycle of strategy execution:
- Scheduling based on intervals
- Running decision cycles
- Logging and error handling
- Graceful shutdown
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Dict, Optional

from ..core.config import get_settings
from ..db.database import AsyncSessionLocal
from ..db.models import DecisionRecordDB, ExchangeAccountDB, StrategyDB
from ..db.repositories.account import AccountRepository
from ..db.repositories.decision import DecisionRepository
from ..db.repositories.strategy import StrategyRepository
from ..services.ai import BaseAIClient, get_ai_client
from ..services.strategy_engine import StrategyEngine
from ..traders.base import BaseTrader, TradeError
from ..traders.ccxt_trader import CCXTTrader, EXCHANGE_ID_MAP, create_trader_from_account

logger = logging.getLogger(__name__)


class ExecutionWorker:
    """
    Worker for executing a single strategy.

    Runs the strategy's decision cycle at configured intervals.

    Lifecycle:
    1. Initialize (connect to exchange)
    2. Run decision cycles
    3. Handle errors and update status
    4. Graceful shutdown
    """

    def __init__(
        self,
        strategy_id: str,
        trader: BaseTrader,
        ai_client: Optional[BaseAIClient] = None,
        interval_minutes: int = 30,
    ):
        """
        Initialize execution worker.

        Args:
            strategy_id: UUID of strategy to execute
            trader: Exchange trading adapter
            ai_client: AI client for decisions (if None, auto-created per strategy)
            interval_minutes: Minutes between decision cycles
        """
        self.strategy_id = uuid.UUID(strategy_id)
        self.trader = trader
        self.ai_client = ai_client  # May be None, will be created per strategy
        self.interval_minutes = interval_minutes

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
        self._error_count = 0

        # Get max errors from settings
        settings = get_settings()
        self._max_errors = settings.worker_max_consecutive_errors

    async def start(self) -> None:
        """Start the worker"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Started worker for strategy {self.strategy_id}")

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the worker gracefully with timeout"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Worker for strategy {self.strategy_id} did not stop within {timeout}s, forcing")
            except asyncio.CancelledError:
                pass

        # Close trader connection to avoid resource leaks
        if self.trader:
            try:
                await self.trader.close()
            except Exception as e:
                logger.warning(f"Error closing trader for strategy {self.strategy_id}: {e}")

        logger.info(f"Stopped worker for strategy {self.strategy_id}")

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
                logger.error(f"Error in strategy {self.strategy_id}: {e}")
                self._error_count += 1

                if self._error_count >= self._max_errors:
                    logger.error(f"Too many errors, pausing strategy {self.strategy_id}")
                    await self._update_strategy_status("error", str(e))
                    break

                # Wait before retry
                await asyncio.sleep(60)

    async def _run_cycle(self) -> None:
        """Run one decision cycle"""
        async with AsyncSessionLocal() as session:
            # Get strategy from database
            repo = StrategyRepository(session)
            strategy = await repo.get_by_id(self.strategy_id)

            if not strategy or strategy.status != "active":
                logger.info(f"Strategy {self.strategy_id} not active, stopping")
                self._running = False
                return

            # Create strategy engine with db_session for decision persistence
            # AI client is created by StrategyEngine based on strategy's ai_model
            engine = StrategyEngine(
                strategy=strategy,
                trader=self.trader,
                ai_client=self.ai_client,  # May be None, engine creates based on strategy config
                db_session=session,  # Pass session for decision persistence
            )

            # Run decision cycle (decision is saved inside run_cycle)
            result = await engine.run_cycle()

            # Update strategy timestamps
            await repo.update(
                self.strategy_id,
                strategy.user_id,
                last_run_at=datetime.now(UTC),
                next_run_at=datetime.now(UTC) + timedelta(minutes=self.interval_minutes),
            )

            await session.commit()
            self._last_run = datetime.now(UTC)

            logger.info(
                f"Strategy {self.strategy_id} cycle completed: "
                f"success={result['success']}, "
                f"tokens={result['tokens_used']}, "
                f"latency={result['latency_ms']}ms"
            )


    async def _update_strategy_status(self, status: str, error: Optional[str] = None) -> None:
        """Update strategy status in database"""
        async with AsyncSessionLocal() as session:
            repo = StrategyRepository(session)
            await repo.update_status(self.strategy_id, status, error)
            await session.commit()


class WorkerManager:
    """
    Manages strategy execution workers.

    Supports two modes:
    1. Legacy Mode (distributed=False): In-process workers, single process
    2. Distributed Mode (distributed=True): ARQ task queue, scalable

    Responsibilities:
    - Start/stop workers for strategies
    - Monitor worker health
    - Handle strategy status changes
    """

    def __init__(self, distributed: bool = False):
        """
        Initialize WorkerManager.

        Args:
            distributed: If True, use ARQ task queue. If False, use in-process workers.
        """
        self._distributed = distributed
        self._workers: Dict[str, ExecutionWorker] = {}  # For legacy mode
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
            # Legacy mode: Load active strategies and start in-process workers
            await self._load_active_strategies()
            
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

    async def start_strategy(
        self,
        strategy_id: str,
        credentials: Optional[dict] = None,
        account: Optional[ExchangeAccountDB] = None,
    ) -> bool:
        """
        Start worker for a strategy.

        Args:
            strategy_id: Strategy UUID
            credentials: Exchange credentials (decrypted). If None, will fetch from account.
            account: Exchange account. If None, will fetch from strategy.

        Returns:
            True if started successfully
        """
        if self._distributed:
            # Distributed mode: Submit to task queue
            if not self._task_queue:
                logger.error("Task queue not initialized")
                return False
            
            job_id = await self._task_queue.start_strategy(strategy_id)
            if job_id:
                logger.info(f"Scheduled strategy {strategy_id} via task queue (job: {job_id})")
                return True
            return False
        
        # Legacy mode: Start in-process worker
        if strategy_id in self._workers:
            return True  # Already running

        try:
            async with AsyncSessionLocal() as session:
                repo = StrategyRepository(session)
                strategy = await repo.get_by_id(uuid.UUID(strategy_id))

                if not strategy:
                    logger.error(f"Strategy {strategy_id} not found")
                    return False

                if not strategy.account_id:
                    logger.error(f"Strategy {strategy_id} has no account configured")
                    return False

                # Get account if not provided
                if account is None:
                    account_repo = AccountRepository(session)
                    account = await account_repo.get_by_id(strategy.account_id)
                    if not account:
                        logger.error(f"Account {strategy.account_id} not found for strategy {strategy_id}")
                        return False

                # Get credentials if not provided
                if credentials is None:
                    account_repo = AccountRepository(session)
                    credentials = await account_repo.get_decrypted_credentials(
                        strategy.account_id,
                        strategy.user_id
                    )
                    if not credentials:
                        logger.error(f"Failed to get credentials for account {strategy.account_id}")
                        return False

                # Create trader using the helper function
                try:
                    trader = create_trader_from_account(account, credentials)
                    await trader.initialize()
                except ValueError as e:
                    logger.error(f"Failed to create trader for strategy {strategy_id}: {e}")
                    await repo.update_status(strategy.id, "error", str(e))
                    await session.commit()
                    return False
                except TradeError as e:
                    logger.error(f"Failed to initialize trader for strategy {strategy_id}: {e.message}")
                    await repo.update_status(strategy.id, "error", e.message)
                    await session.commit()
                    return False

                # Get interval from config
                config = strategy.config or {}
                interval = config.get("execution_interval_minutes", 30)

                # Create and start worker
                # AI client is created per strategy by StrategyEngine based on strategy.ai_model
                worker = ExecutionWorker(
                    strategy_id=strategy_id,
                    trader=trader,
                    ai_client=None,  # Let StrategyEngine create based on strategy config
                    interval_minutes=interval,
                )

                await worker.start()
                self._workers[strategy_id] = worker

                logger.info(f"Started worker for strategy {strategy_id} on {account.exchange}")
                return True

        except Exception as e:
            logger.error(f"Failed to start strategy {strategy_id}: {e}")
            return False

    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop worker for a strategy"""
        if self._distributed:
            # Distributed mode: Cancel task queue job
            if not self._task_queue:
                logger.error("Task queue not initialized")
                return False
            
            return await self._task_queue.stop_strategy(strategy_id)
        
        # Legacy mode: Stop in-process worker
        worker = self._workers.get(strategy_id)
        if not worker:
            return True  # Not running

        await worker.stop()
        del self._workers[strategy_id]
        return True

    async def trigger_manual_execution(self, strategy_id: str, user_id: str | None = None) -> dict:
        """
        Manually trigger a strategy execution (Run Now).
        
        Supports both distributed and legacy modes.
        
        Args:
            strategy_id: Strategy UUID
            user_id: Optional user UUID for ownership verification
            
        Returns:
            Dict with execution result:
              - distributed: {"job_id": str}
              - legacy: {"success": bool, "decision_id": str | None, "error": str | None}
        """
        if self._distributed:
            if not self._task_queue:
                logger.error("Task queue not initialized")
                return {"success": False, "error": "Task queue not initialized"}
            
            job_id = await self._task_queue.trigger_strategy_execution(strategy_id)
            if job_id:
                return {"success": True, "job_id": job_id}
            return {"success": False, "error": "Failed to enqueue job"}

        # Legacy mode: run a single cycle directly
        trader = None
        try:
            async with AsyncSessionLocal() as session:
                repo = StrategyRepository(session)
                # Verify ownership if user_id is provided
                uid = uuid.UUID(user_id) if user_id else None
                strategy = await repo.get_by_id(uuid.UUID(strategy_id), user_id=uid)

                if not strategy:
                    return {"success": False, "error": "Strategy not found"}

                if not strategy.account_id:
                    return {"success": False, "error": "Strategy has no account configured"}

                # Get account & credentials
                account_repo = AccountRepository(session)
                account = await account_repo.get_by_id(strategy.account_id)
                if not account:
                    return {"success": False, "error": "Account not found"}

                credentials = await account_repo.get_decrypted_credentials(
                    strategy.account_id,
                    strategy.user_id,
                )
                if not credentials:
                    return {"success": False, "error": "Failed to decrypt account credentials"}

                # Create trader
                trader = create_trader_from_account(account, credentials)
                await trader.initialize()

                # Create engine and run one cycle
                engine = StrategyEngine(
                    strategy=strategy,
                    trader=trader,
                    ai_client=None,
                    db_session=session,
                )

                result = await engine.run_cycle()

                # Update strategy timestamps
                config = strategy.config or {}
                interval = config.get("execution_interval_minutes", 30)
                await repo.update(
                    strategy.id,
                    strategy.user_id,
                    last_run_at=datetime.now(UTC),
                    next_run_at=datetime.now(UTC) + timedelta(minutes=interval),
                )
                await session.commit()

                logger.info(
                    f"Manual execution for strategy {strategy_id}: "
                    f"success={result['success']}, "
                    f"tokens={result['tokens_used']}, "
                    f"latency={result['latency_ms']}ms"
                )

                # The trigger itself succeeded (the cycle ran).
                # Cycle-level errors (e.g. risk limits) are informational, not trigger failures.
                return {
                    "success": True,
                    "decision_id": result.get("decision_record_id"),
                    "cycle_success": result["success"],
                    "error": result.get("error"),
                }

        except Exception as e:
            logger.error(f"Manual execution failed for strategy {strategy_id}: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Clean up trader connection to avoid resource leaks
            if trader:
                try:
                    await trader.close()
                except Exception as e:
                    logger.warning(f"Error closing trader: {e}")

    async def _load_active_strategies(self) -> None:
        """Load and start workers for all active strategies (legacy mode only)"""
        async with AsyncSessionLocal() as session:
            strategy_repo = StrategyRepository(session)
            account_repo = AccountRepository(session)

            strategies = await strategy_repo.get_active_strategies()

            for strategy in strategies:
                if not strategy.account_id:
                    logger.warning(f"Strategy {strategy.id} has no account, skipping")
                    continue

                # Get the account (should be loaded via relationship)
                account = strategy.account
                if not account:
                    logger.warning(f"Account not found for strategy {strategy.id}, skipping")
                    continue

                # Get decrypted credentials
                credentials = await account_repo.get_decrypted_credentials(
                    strategy.account_id,
                    strategy.user_id
                )
                if not credentials:
                    logger.warning(f"Failed to get credentials for strategy {strategy.id}, skipping")
                    continue

                # Start the worker
                success = await self.start_strategy(
                    str(strategy.id),
                    credentials=credentials,
                    account=account,
                )

                if success:
                    logger.info(f"Auto-started worker for strategy {strategy.id}")
                else:
                    logger.error(f"Failed to auto-start worker for strategy {strategy.id}")

    async def _monitor_loop(self) -> None:
        """Monitor workers and sync with database (legacy mode only)"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Sync with database
                async with AsyncSessionLocal() as session:
                    repo = StrategyRepository(session)
                    active = await repo.get_active_strategies()
                    active_ids = {str(s.id) for s in active}

                    # Stop workers for deactivated strategies
                    for strategy_id in list(self._workers.keys()):
                        if strategy_id not in active_ids:
                            await self.stop_strategy(strategy_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")

    def get_worker_status(self, strategy_id: str) -> Optional[dict]:
        """Get status of a worker"""
        if self._distributed:
            # In distributed mode, we don't track workers locally
            # Status comes from the task queue
            return {
                "running": True,  # Assume running if using distributed mode
                "last_run": None,
                "error_count": 0,
                "mode": "distributed",
            }
        
        worker = self._workers.get(strategy_id)
        if not worker:
            return None

        return {
            "running": worker._running,
            "last_run": worker._last_run.isoformat() if worker._last_run else None,
            "error_count": worker._error_count,
            "mode": "legacy",
        }

    async def get_distributed_status(self, strategy_id: str) -> Optional[dict]:
        """Get status from task queue (distributed mode only)"""
        if not self._distributed or not self._task_queue:
            return None
        
        return await self._task_queue.get_strategy_job_status(strategy_id)

    async def get_queue_info(self) -> Optional[dict]:
        """Get task queue info (distributed mode only)"""
        if not self._distributed or not self._task_queue:
            return None
        
        return await self._task_queue.get_queue_info()

    def list_workers(self) -> list[str]:
        """List all running worker strategy IDs"""
        if self._distributed:
            # In distributed mode, we don't track workers locally
            return []
        
        return list(self._workers.keys())


# Global worker manager instance
_worker_manager: Optional[WorkerManager] = None


async def get_worker_manager(distributed: Optional[bool] = None) -> WorkerManager:
    """
    Get or create worker manager singleton.
    
    Args:
        distributed: If True, use ARQ task queue. If False, use in-process workers.
                    If None, uses WORKER_DISTRIBUTED setting from config.
    
    Returns:
        WorkerManager instance
    """
    global _worker_manager
    if _worker_manager is None:
        # Determine distributed mode from config if not specified
        if distributed is None:
            settings = get_settings()
            distributed = getattr(settings, 'worker_distributed', False)
        
        _worker_manager = WorkerManager(distributed=distributed)
    return _worker_manager


async def reset_worker_manager() -> None:
    """Reset worker manager (for testing)"""
    global _worker_manager
    if _worker_manager:
        await _worker_manager.stop()
    _worker_manager = None
