"""
Quant Worker Backend - Handles quantitative strategy execution.

This backend wraps the existing QuantExecutionWorker and QuantWorkerManager
to implement the WorkerBackend interface, enabling unified management
through UnifiedWorkerManager.

Supports Grid, DCA, and RSI strategies with Redis-based distributed safety.
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
    try_reconnect_trader,
    clear_heartbeats_for_quant_strategies,
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
from ..db.repositories.quant_strategy import QuantStrategyRepository
from ..db.repositories.decision import DecisionRepository
from ..services.quant_engine import create_engine
from ..services.worker_heartbeat import get_worker_instance_id
from ..traders.base import BaseTrader, TradeError
from ..traders.ccxt_trader import create_trader_from_account

logger = logging.getLogger(__name__)

# Default cycle intervals per strategy type (minutes)
DEFAULT_INTERVALS = {
    "grid": 1,    # Grid checks every minute
    "dca": 60,    # DCA default: check every hour
    "rsi": 5,     # RSI checks every 5 minutes
}


class QuantExecutionWorker:
    """
    Worker for executing a single quant strategy.

    Runs the strategy engine's cycle at configured intervals.
    Includes trader health checks and automatic reconnection.
    Enhanced with error window tracking and exponential backoff.
    """

    def __init__(
        self,
        agent_id: str,
        strategy_type: str,
        trader: BaseTrader,
        interval_minutes: int = 5,
        account_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        trade_type: str = "crypto_perp",
    ):
        self.agent_id = uuid.UUID(agent_id)
        self.strategy_type = strategy_type
        self.trader = trader
        self.interval_minutes = interval_minutes
        self._account_id = account_id
        self._user_id = user_id
        self._trade_type = trade_type
        self._instance_id = get_instance_id()

        self._running = False
        self._task: Optional[asyncio.Task] = None
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

        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"Started quant worker for {self.strategy_type} strategy {self.agent_id}"
        )

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the worker gracefully with timeout."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Quant worker for strategy {self.agent_id} "
                    f"did not stop within {timeout}s, forcing"
                )
            except asyncio.CancelledError:
                pass

        # Clear heartbeat on shutdown
        await clear_heartbeat_on_stop(self.agent_id)

        # Release ownership
        await release_ownership(str(self.agent_id), self._instance_id)

        # Close trader connection
        await close_trader_safely(self.trader, self.agent_id)

        logger.info(f"Stopped quant worker for strategy {self.agent_id}")

    async def _run_loop(self) -> None:
        """Main execution loop with enhanced error handling."""
        while self._running:
            try:
                # Timeout protection: prevent cycles from hanging indefinitely
                await asyncio.wait_for(
                    self._run_cycle(), timeout=300.0  # 5 minute timeout
                )
                # Success: reset error window and counters
                self._error_count = 0
                self._error_window.reset()
                await asyncio.sleep(self.interval_minutes * 60)

            except asyncio.CancelledError:
                break
            except asyncio.TimeoutError:
                logger.error(
                    f"Quant strategy {self.agent_id} cycle timed out (>300s)"
                )
                self._error_count += 1
                self._error_window.record_error()

                if self._error_window.should_stop:
                    await self._update_status("error", "Cycle execution timed out repeatedly")
                    break

                delay = calculate_backoff_delay(
                    attempt=min(self._error_count - 1, 5),
                    base_delay=self._retry_base_delay,
                    max_delay=self._retry_max_delay,
                    jitter=self._retry_jitter,
                )
                logger.info(
                    f"Quant strategy {self.agent_id} timeout, "
                    f"retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
            except Exception as e:
                error_type = classify_error(e)
                logger.exception(f"Error in quant strategy {self.agent_id} (type: {error_type.value})")

                # Permanent errors: stop immediately
                if error_type == ErrorType.PERMANENT:
                    await self._update_status("error", f"Permanent error: {str(e)}")
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
                    logger.error(f"Error threshold reached, pausing quant strategy {self.agent_id}")
                    await self._update_status("error", error_msg)
                    break

                # On connection-related errors, try to reconnect the trader
                await self._try_reconnect_trader()

                # Calculate backoff delay
                delay = calculate_backoff_delay(
                    attempt=min(self._error_count - 1, 5),
                    base_delay=self._retry_base_delay,
                    max_delay=self._retry_max_delay,
                    jitter=self._retry_jitter,
                )
                logger.info(
                    f"Quant strategy {self.agent_id} transient error, "
                    f"retrying in {delay:.1f}s (error {self._error_count}/{self._max_errors})"
                )
                await asyncio.sleep(delay)

    async def _try_reconnect_trader(self) -> None:
        """Attempt to recreate the trader connection."""
        if not self._account_id or not self._user_id:
            return

        logger.info(
            f"Quant worker {self.agent_id}: attempting trader reconnection"
        )

        new_trader = await try_reconnect_trader(
            self.trader,
            self._account_id,
            self._user_id,
            self._trade_type,
        )

        if new_trader:
            self.trader = new_trader

    async def _run_cycle(self) -> None:
        """Run one strategy cycle with execution lock and position isolation."""
        # Acquire execution lock
        acquired, lock_key = await acquire_execution_lock(str(self.agent_id))
        if not acquired:
            logger.warning(
                f"Quant strategy {self.agent_id} already executing "
                f"(concurrent lock), skipping"
            )
            return

        try:
            from ..services.redis_service import get_redis_service
            try:
                redis_service = await get_redis_service()
            except Exception:
                redis_service = None

            await self._run_cycle_inner(redis_service)
        finally:
            await release_execution_lock(lock_key)

    async def _run_cycle_inner(self, redis_service=None) -> None:
        """Inner cycle logic after lock is acquired."""
        from ..services.position_service import PositionService

        async with AsyncSessionLocal() as session:
            # Update heartbeat at start of cycle with retry
            from ..services.worker_heartbeat import update_heartbeat_with_retry
            heartbeat_ok = await update_heartbeat_with_retry(
                session, self.agent_id, self._worker_instance_id
            )
            if not heartbeat_ok:
                logger.warning(
                    f"Heartbeat update failed for quant strategy {self.agent_id}, "
                    "continuing execution cycle"
                )

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
                agent_id=str(strategy.id),
                trader=self.trader,
                symbol=strategy.symbol,
                config=strategy.config,
                runtime_state=strategy.runtime_state or {},
                account_id=str(strategy.account_id) if strategy.account_id else None,
                position_service=position_service,
                strategy=strategy,
                trade_type=strategy.trade_type,
            )

            # Run cycle
            result = await engine.run_cycle()

            # Save decision record for audit trail
            await self._save_decision_record(session, strategy, result)

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

    async def _save_decision_record(
        self, session, strategy, result: dict
    ) -> None:
        """Save a decision record for the quant execution."""
        try:
            decision_repo = DecisionRepository(session)
            trades_executed = result.get("trades_executed", 0)
            pnl_change = result.get("pnl_change", 0.0)
            total_size_usd = result.get("total_size_usd", 0.0)
            message = result.get("message", "")
            success = result.get("success", False)

            # Determine action
            if trades_executed > 0:
                action = "close_long" if pnl_change > 0 else "open_long"
                action_desc = "卖出平仓" if pnl_change > 0 else "买入开仓"
            else:
                action = "hold"
                action_desc = "持有/观望"

            strategy_names = {"grid": "网格交易", "dca": "定投", "rsi": "RSI指标"}
            strategy_name = strategy_names.get(
                strategy.strategy_type, strategy.strategy_type
            )

            chain_of_thought = f"[{strategy_name}] {message}"
            if trades_executed > 0:
                chain_of_thought += f"\n执行了 {trades_executed} 笔交易"
            if pnl_change != 0:
                chain_of_thought += f"\n盈亏变化: ${pnl_change:.2f}"

            leverage = strategy.config.get("leverage", 1) if strategy.config else 1

            await decision_repo.create(
                agent_id=strategy.id,
                system_prompt=f"Quant Strategy: {strategy_name}",
                user_prompt=f"Symbol: {strategy.symbol}, Config: {strategy.config}",
                raw_response=str(result),
                chain_of_thought=chain_of_thought,
                market_assessment=(
                    f"交易对: {strategy.symbol}\n"
                    f"执行状态: {'成功' if success else '失败'}"
                ),
                decisions=[{
                    "action": action,
                    "symbol": strategy.symbol,
                    "confidence": 100,
                    "reasoning": action_desc,
                    "leverage": leverage,
                    "position_size_usd": total_size_usd,
                    "risk_usd": 0,
                }],
                overall_confidence=100,
                ai_model=f"quant:{strategy.strategy_type}",
                tokens_used=0,
                latency_ms=0,
            )
        except Exception as e:
            logger.warning(f"Failed to save quant decision record: {e}")

    async def _update_status(
        self, status: str, error: Optional[str] = None
    ) -> None:
        """Update strategy status in database."""
        async with AsyncSessionLocal() as session:
            repo = QuantStrategyRepository(session)
            await repo.update_status(self.agent_id, status, error)
            await session.commit()


class QuantWorkerBackend(BaseWorkerBackend):
    """
    Quant Worker Backend implementing WorkerBackend interface.

    Manages quant strategy execution workers with Redis-based distributed safety:
    - Leader election per strategy via Redis ownership keys
    - Execution locks to prevent concurrent cycles
    - Periodic sync to refresh ownership and pick up orphaned workers
    """

    def __init__(self):
        super().__init__()
        self._workers: Dict[str, QuantExecutionWorker] = {}
        self._sync_task: Optional[asyncio.Task] = None

    @property
    def backend_type(self) -> str:
        return "quant"

    async def start(self) -> None:
        """Start the quant backend."""
        if self._running:
            return
        self._running = True

        # Clear heartbeats for all active quant strategies on startup
        await clear_heartbeats_for_quant_strategies()

        # Load active strategies
        await self._load_active_strategies()

        # Start periodic sync task
        self._sync_task = asyncio.create_task(self._periodic_sync())

        logger.info(
            f"Quant Worker Backend: Started with {len(self._workers)} active strategies"
        )

    async def stop(self) -> None:
        """Stop the quant backend."""
        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Stop all workers
        for agent_id in list(self._workers.keys()):
            await self._stop_and_release(agent_id)

        self._workers.clear()
        logger.info("Quant Worker Backend: Stopped")

    async def start_agent(self, agent_id: str) -> bool:
        """Start a worker for a quant agent."""
        if agent_id in self._workers:
            logger.info(f"Quant worker already running for {agent_id}")
            return True

        # Try to claim ownership via Redis
        if not await try_acquire_ownership(agent_id):
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
                    await release_ownership(agent_id)
                    return False

                # Skip AI strategies - they are handled by AIWorkerBackend
                strategy_type = strategy.strategy_type
                if strategy_type == "ai":
                    logger.warning(
                        f"Agent {agent_id} is an AI strategy, "
                        "skipping quant worker. Use AIWorkerBackend instead."
                    )
                    await release_ownership(agent_id)
                    return False

                # Validate strategy type
                if strategy_type not in ("grid", "dca", "rsi"):
                    logger.error(
                        f"Unknown strategy type '{strategy_type}' for {agent_id}. "
                        "QuantWorker only supports grid, dca, rsi."
                    )
                    await release_ownership(agent_id)
                    return False

                trader = None
                if strategy.execution_mode == "mock":
                    # Mock mode: create MockTrader
                    from .tasks import create_mock_trader
                    symbols = [strategy.symbol] if strategy.symbol else ["BTC"]
                    trader, error = await create_mock_trader(
                        strategy, session, symbols=symbols
                    )
                    if error:
                        logger.error(error)
                        await repo.update_status(
                            uuid.UUID(agent_id), "error", error
                        )
                        await session.commit()
                        await release_ownership(agent_id)
                        return False
                else:
                    # Live mode: require account
                    if not strategy.account_id:
                        logger.error(f"Quant agent {agent_id} has no account")
                        await repo.update_status(
                            uuid.UUID(agent_id), "error", "No associated account"
                        )
                        await session.commit()
                        await release_ownership(agent_id)
                        return False

                    # Create trader from account
                    account_repo = AccountRepository(session)
                    account = await account_repo.get_by_id(strategy.account_id)
                    if not account:
                        logger.error(f"Account not found for quant agent {agent_id}")
                        await repo.update_status(
                            uuid.UUID(agent_id),
                            "error",
                            "Associated account not found",
                        )
                        await session.commit()
                        await release_ownership(agent_id)
                        return False

                    credentials = await account_repo.get_decrypted_credentials(
                        strategy.account_id, strategy.user_id
                    )
                    if not credentials:
                        logger.error(
                            f"Failed to get credentials for quant agent {agent_id}"
                        )
                        await release_ownership(agent_id)
                        return False

                    trader = create_trader_from_account(
                        account, credentials, trade_type=strategy.trade_type
                    )
                    await trader.initialize()

                # Determine cycle interval
                if strategy.execution_interval_minutes:
                    interval = strategy.execution_interval_minutes
                elif strategy.strategy_type == "dca":
                    interval = strategy.config.get("interval_minutes", 60)
                else:
                    interval = DEFAULT_INTERVALS.get(strategy.strategy_type, 5)

                worker = QuantExecutionWorker(
                    agent_id=agent_id,
                    strategy_type=strategy.strategy_type,
                    trader=trader,
                    interval_minutes=interval,
                    account_id=(
                        strategy.account_id
                        if strategy.execution_mode != "mock" else None
                    ),
                    user_id=strategy.user_id,
                    trade_type=strategy.trade_type,
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
            await release_ownership(agent_id)
            return False

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a worker for a quant agent."""
        await self._stop_and_release(agent_id)
        return True

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
        # Note: ownership is released in worker.stop()
        logger.info(f"Stopped quant worker for {agent_id}")

    async def trigger_execution(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """Trigger a single execution cycle for a quant strategy."""
        from ..services.position_service import PositionService
        from ..services.redis_service import get_redis_service
        from ..traders.mock_trader import MockTrader

        try:
            async with AsyncSessionLocal() as session:
                repo = QuantStrategyRepository(session)
                strategy = await repo.get_by_id(uuid.UUID(agent_id))

                if not strategy:
                    return {"success": False, "error": "Strategy not found"}

                if strategy.status != "active":
                    return {
                        "success": False,
                        "error": f"Strategy is not active (status={strategy.status})",
                    }

                # Create trader
                trader = None
                if strategy.execution_mode == "mock":
                    from .tasks import create_mock_trader
                    symbols = [strategy.symbol] if strategy.symbol else ["BTC"]
                    trader, error = await create_mock_trader(
                        strategy, session, symbols=symbols
                    )
                    if error:
                        return {"success": False, "error": error}
                else:
                    if not strategy.account_id:
                        return {
                            "success": False,
                            "error": "No account configured for live trading",
                        }

                    account_repo = AccountRepository(session)
                    account = await account_repo.get_by_id(strategy.account_id)
                    if not account:
                        return {"success": False, "error": "Account not found"}

                    credentials = await account_repo.get_decrypted_credentials(
                        strategy.account_id, strategy.user_id
                    )
                    if not credentials:
                        return {
                            "success": False,
                            "error": "Failed to decrypt credentials",
                        }

                    trader = create_trader_from_account(
                        account, credentials, trade_type=strategy.trade_type
                    )
                    await trader.initialize()

                # Create position service
                try:
                    redis_service = await get_redis_service()
                except Exception:
                    redis_service = None
                position_service = PositionService(db=session, redis=redis_service)

                # Create engine and run one cycle
                strategy_type = strategy.strategy_type
                if not strategy_type or strategy_type not in ("grid", "dca", "rsi"):
                    return {
                        "success": False,
                        "error": f"Unsupported strategy type: {strategy_type}",
                    }

                engine = create_engine(
                    strategy_type=strategy_type,
                    agent_id=agent_id,
                    trader=trader,
                    symbol=strategy.symbol,
                    config=strategy.config or {},
                    runtime_state=strategy.runtime_state or {},
                    account_id=(
                        str(strategy.account_id) if strategy.account_id else None
                    ),
                    position_service=position_service,
                    strategy=strategy,
                    trade_type=strategy.trade_type,
                )

                result = await engine.run_cycle()

                # Update runtime state if changed
                if result.get("updated_state"):
                    await repo.update_runtime_state(
                        uuid.UUID(agent_id),
                        result["updated_state"],
                    )

                # Update timestamps
                interval = strategy.execution_interval_minutes or 5
                await repo.update(
                    uuid.UUID(agent_id),
                    strategy.user_id,
                    last_run_at=datetime.now(UTC),
                    next_run_at=datetime.now(UTC) + timedelta(minutes=interval),
                )
                await session.commit()

                return {
                    "success": True,
                    "message": result.get("message", "Cycle completed"),
                }

        except Exception as e:
            logger.exception(f"Failed to trigger quant cycle for agent {agent_id}")
            return {"success": False, "error": str(e)}

    def get_worker_status(self, agent_id: str) -> Optional[dict]:
        """Get status of a worker."""
        worker = self._workers.get(agent_id)
        if not worker:
            return None

        return {
            "running": worker._running,
            "last_run": None,
            "error_count": worker._error_count,
            "mode": "quant",
            "strategy_type": worker.strategy_type,
        }

    def list_running_agents(self) -> list[str]:
        """List all running quant agent IDs."""
        return list(self._workers.keys())

    def get_worker_count(self) -> int:
        """Get the number of running workers."""
        return len(self._workers)

    async def _load_active_strategies(self) -> None:
        """Load and start workers for all active quant strategies."""
        try:
            async with AsyncSessionLocal() as session:
                repo = QuantStrategyRepository(session)
                active = await repo.get_active_strategies()

                for strategy in active:
                    sid = str(strategy.id)
                    if sid not in self._workers:
                        await self.start_agent(sid)

        except Exception as e:
            logger.exception("Failed to load active quant strategies")

    async def _periodic_sync(self) -> None:
        """Periodically refresh ownership and pick up orphaned strategies."""
        from .lifecycle import refresh_ownership

        while self._running:
            try:
                await asyncio.sleep(60)  # Sync every minute
                if not self._running:
                    break

                # 1. Refresh ownership for strategies we're running
                lost = []
                for sid in list(self._workers.keys()):
                    if not await refresh_ownership(sid):
                        lost.append(sid)

                # Stop workers we lost ownership of
                for sid in lost:
                    logger.warning(
                        f"Lost ownership of quant strategy {sid}, "
                        "stopping local worker"
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
