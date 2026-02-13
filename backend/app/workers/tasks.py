"""
Distributed Task Definitions for ARQ (Async Redis Queue).

This module defines all background tasks that can be executed by workers.
Tasks are submitted to Redis and distributed across worker instances.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from arq import ArqRedis
from arq.jobs import Job

from ..core.config import get_settings
from ..db.database import AsyncSessionLocal
from ..db.models import DecisionRecordDB, ExchangeAccountDB, StrategyDB
from ..db.repositories.account import AccountRepository
from ..db.repositories.strategy import StrategyRepository
from ..services.strategy_engine import StrategyEngine
from ..traders.base import BaseTrader, TradeError
from ..traders.ccxt_trader import CCXTTrader, EXCHANGE_ID_MAP, create_trader_from_account

logger = logging.getLogger(__name__)


# ==================== Mock State Restoration ====================

async def _restore_mock_trader_state(
    session,
    agent_id: uuid.UUID,
    initial_balance: float,
    trader,
) -> None:
    """
    Restore MockTrader state from persisted AgentPositionDB data.

    Reconstructs the SimulatedTrader's in-memory balance and open positions
    so that mock agents survive worker restarts.

    Args:
        session: AsyncSession
        agent_id: UUID of the agent
        initial_balance: Agent's mock_initial_balance
        trader: MockTrader instance (already initialized)
    """
    from sqlalchemy import select, func
    from ..db.models import AgentPositionDB

    # Load open positions
    open_stmt = (
        select(AgentPositionDB)
        .where(
            AgentPositionDB.agent_id == agent_id,
            AgentPositionDB.status == "open",
        )
    )
    open_result = await session.execute(open_stmt)
    open_positions = open_result.scalars().all()

    # Calculate realized PnL from closed positions to reconstruct balance
    pnl_stmt = (
        select(func.coalesce(func.sum(AgentPositionDB.realized_pnl), 0.0))
        .where(
            AgentPositionDB.agent_id == agent_id,
            AgentPositionDB.status == "closed",
        )
    )
    pnl_result = await session.execute(pnl_stmt)
    total_realized_pnl = float(pnl_result.scalar_one())

    # Reconstruct balance
    restored_balance = initial_balance + total_realized_pnl

    # Build position data for restoration
    positions_data = []
    for pos in open_positions:
        positions_data.append({
            "symbol": pos.symbol,
            "side": pos.side,
            "size": pos.size,
            "entry_price": pos.entry_price,
            "leverage": pos.leverage,
            "opened_at": pos.opened_at,
        })

    if positions_data or total_realized_pnl != 0.0:
        trader.restore_state(
            balance=restored_balance,
            positions=positions_data,
        )
        logger.info(
            f"Restored mock state for agent {agent_id}: "
            f"balance=${restored_balance:,.2f} "
            f"(initial=${initial_balance:,.0f} + pnl=${total_realized_pnl:,.2f}), "
            f"{len(positions_data)} open positions"
        )


# ==================== Task Definitions ====================

async def execute_strategy_cycle(
    ctx: dict,
    strategy_id: str,
) -> dict[str, Any]:
    """
    Execute a single decision cycle for a strategy.

    Loads the strategy's active agent to determine execution mode:
    - live: uses CCXTTrader with exchange credentials
    - mock: uses MockTrader with real-time public market data

    This task is submitted to the queue and executed by a worker.
    After execution, it schedules the next cycle based on agent config.

    Args:
        ctx: ARQ context (contains redis connection)
        strategy_id: UUID of the strategy to execute

    Returns:
        Dict with execution results
    """
    logger.info(f"Starting strategy cycle for {strategy_id}")
    
    result = {
        "strategy_id": strategy_id,
        "success": False,
        "error": None,
        "tokens_used": 0,
        "latency_ms": 0,
        "executed_at": datetime.now(UTC).isoformat(),
    }
    
    trader = None

    # ── Strategy-level execution lock ──
    # Prevents concurrent execution of the same strategy (e.g. manual trigger
    # running alongside a scheduled cycle).
    redis: ArqRedis = ctx["redis"]
    lock_key = f"exec_lock:strategy:{strategy_id}"
    lock_acquired = False
    try:
        # SET NX with 5-minute TTL (matches job_timeout)
        lock_acquired = await redis.set(lock_key, "1", nx=True, ex=300)
    except Exception as e:
        logger.error(f"Failed to acquire exec lock for {strategy_id}: {e}")
        result["error"] = f"Redis lock unavailable: {e}"
        return result

    if not lock_acquired:
        result["error"] = (
            f"Strategy {strategy_id} is already executing (concurrent lock). "
            "Skipping this cycle."
        )
        logger.warning(result["error"])
        return result

    try:
        async with AsyncSessionLocal() as session:
            # Get strategy from database
            strategy_repo = StrategyRepository(session)
            account_repo = AccountRepository(session)
            
            strategy = await strategy_repo.get_by_id(uuid.UUID(strategy_id))
            
            if not strategy:
                result["error"] = f"Strategy {strategy_id} not found"
                logger.error(result["error"])
                return result
            
            if strategy.status != "active":
                result["error"] = f"Strategy {strategy_id} is not active (status: {strategy.status})"
                logger.info(result["error"])
                return result
            
            # ── Load active agent for this strategy ──
            from ..db.repositories.agent import AgentRepository
            from ..db.models import AgentDB
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            agent_stmt = (
                select(AgentDB)
                .where(
                    AgentDB.strategy_id == strategy.id,
                    AgentDB.status == "active",
                )
                .options(selectinload(AgentDB.strategy))
                .limit(1)
            )
            agent_result = await session.execute(agent_stmt)
            agent = agent_result.scalar_one_or_none()

            # ── Determine execution mode and create trader ──
            if agent and agent.execution_mode == "mock":
                # Mock mode: use MockTrader with real-time public prices
                from ..traders.mock_trader import MockTrader

                symbols = strategy.symbols or ["BTC"]
                mock_balance = agent.mock_initial_balance or 10000.0
                trader = MockTrader(
                    initial_balance=mock_balance,
                    symbols=symbols,
                )
                try:
                    await trader.initialize()
                    # Restore state from persisted positions (survives restarts)
                    await _restore_mock_trader_state(
                        session, agent.id, mock_balance, trader,
                    )
                except Exception as e:
                    result["error"] = f"Failed to initialize MockTrader: {e}"
                    logger.error(result["error"])
                    return result

            else:
                # Live mode: use CCXTTrader with exchange credentials
                account_id = agent.account_id if agent else strategy.account_id
                if not account_id:
                    result["error"] = f"Strategy {strategy_id} has no account configured"
                    logger.error(result["error"])
                    await strategy_repo.update_status(strategy.id, "error", result["error"])
                    await session.commit()
                    return result

                account = await account_repo.get_by_id(account_id)
                if not account:
                    result["error"] = f"Account not found for strategy {strategy_id}"
                    logger.error(result["error"])
                    return result

                user_id = agent.user_id if agent else strategy.user_id
                credentials = await account_repo.get_decrypted_credentials(
                    account_id, user_id
                )
                if not credentials:
                    result["error"] = f"Failed to get credentials for strategy {strategy_id}"
                    logger.error(result["error"])
                    return result

                try:
                    trader = create_trader_from_account(account, credentials)
                    await trader.initialize()
                except (ValueError, TradeError) as e:
                    error_msg = str(e) if isinstance(e, ValueError) else e.message
                    result["error"] = f"Failed to initialize trader: {error_msg}"
                    logger.error(result["error"])
                    await strategy_repo.update_status(strategy.id, "error", error_msg)
                    await session.commit()
                    return result
            
            # Create agent position service
            from ..services.redis_service import get_redis_service
            from ..services.agent_position_service import AgentPositionService
            try:
                redis_service = await get_redis_service()
            except Exception:
                redis_service = None
            position_service = AgentPositionService(db=session, redis=redis_service)

            # Create strategy engine and run cycle
            engine = StrategyEngine(
                agent=agent if agent else None,
                strategy=strategy,
                trader=trader,
                ai_client=None,  # Engine creates based on agent/strategy config
                db_session=session,
                position_service=position_service,
            )
            
            cycle_result = await engine.run_cycle()
            
            # Get interval from agent or strategy config
            if agent:
                interval_minutes = agent.execution_interval_minutes or 30
            else:
                config = strategy.config or {}
                interval_minutes = config.get("execution_interval_minutes", 30)
            
            # Update strategy timestamps
            await strategy_repo.update(
                strategy.id,
                strategy.user_id,
                last_run_at=datetime.now(UTC),
                next_run_at=datetime.now(UTC) + timedelta(minutes=interval_minutes),
            )
            await session.commit()
            
            # Schedule next execution
            redis: ArqRedis = ctx["redis"]
            await redis.enqueue_job(
                "execute_strategy_cycle",
                strategy_id,
                _defer_by=timedelta(minutes=interval_minutes),
                _job_id=f"strategy:{strategy_id}",  # Unique job ID prevents duplicates
            )
            
            result["success"] = cycle_result.get("success", False)
            result["tokens_used"] = cycle_result.get("tokens_used", 0)
            result["latency_ms"] = cycle_result.get("latency_ms", 0)
            
            logger.info(
                f"Strategy {strategy_id} cycle completed: "
                f"success={result['success']}, "
                f"tokens={result['tokens_used']}, "
                f"latency={result['latency_ms']}ms"
            )
            
    except Exception as e:
        result["error"] = str(e)
        logger.exception(f"Error executing strategy {strategy_id}: {e}")
        
        # Update strategy status on repeated failures
        try:
            async with AsyncSessionLocal() as session:
                strategy_repo = StrategyRepository(session)
                strategy = await strategy_repo.get_by_id(uuid.UUID(strategy_id))
                if strategy:
                    # Check error count from job retries
                    job_try = ctx.get("job_try", 1)
                    settings = get_settings()
                    if job_try >= settings.worker_max_consecutive_errors:
                        await strategy_repo.update_status(
                            strategy.id, 
                            "error", 
                            f"Too many errors: {str(e)}"
                        )
                        await session.commit()
                        logger.error(f"Strategy {strategy_id} paused due to repeated errors")
        except Exception as update_error:
            logger.error(f"Failed to update strategy status: {update_error}")
    
    finally:
        # Clean up trader connection
        if trader:
            try:
                await trader.close()
            except Exception as e:
                logger.warning(f"Error closing trader: {e}")

        # Release strategy execution lock
        try:
            await redis.delete(lock_key)
        except Exception:
            pass  # Lock will expire via TTL
    
    return result


async def start_strategy_execution(
    ctx: dict,
    strategy_id: str,
) -> dict[str, Any]:
    """
    Start execution for a strategy by scheduling the first cycle.

    This is called when a strategy is activated.

    Args:
        ctx: ARQ context
        strategy_id: UUID of the strategy to start

    Returns:
        Dict with status
    """
    logger.info(f"Starting execution for strategy {strategy_id}")
    
    redis: ArqRedis = ctx["redis"]
    
    # Schedule immediate execution
    job = await redis.enqueue_job(
        "execute_strategy_cycle",
        strategy_id,
        _job_id=f"strategy:{strategy_id}",
    )
    
    return {
        "strategy_id": strategy_id,
        "status": "scheduled",
        "job_id": job.job_id if job else None,
    }


async def stop_strategy_execution(
    ctx: dict,
    strategy_id: str,
) -> dict[str, Any]:
    """
    Stop execution for a strategy by canceling pending jobs.

    This is called when a strategy is deactivated.

    Args:
        ctx: ARQ context
        strategy_id: UUID of the strategy to stop

    Returns:
        Dict with status
    """
    logger.info(f"Stopping execution for strategy {strategy_id}")
    
    redis: ArqRedis = ctx["redis"]
    
    # Try to abort the pending job
    job_id = f"strategy:{strategy_id}"
    job = Job(job_id, redis)
    
    try:
        await job.abort()
        logger.info(f"Aborted job for strategy {strategy_id}")
    except Exception as e:
        logger.warning(f"Could not abort job for strategy {strategy_id}: {e}")
    
    return {
        "strategy_id": strategy_id,
        "status": "stopped",
    }


async def sync_active_strategies(ctx: dict) -> dict[str, Any]:
    """
    Sync active strategies with the task queue.

    This is a periodic task that ensures all active strategies have
    scheduled jobs, and stopped strategies don't.

    Args:
        ctx: ARQ context

    Returns:
        Dict with sync results
    """
    logger.info("Syncing active strategies with task queue")
    
    redis: ArqRedis = ctx["redis"]
    started = 0
    skipped = 0
    errors = 0
    
    try:
        async with AsyncSessionLocal() as session:
            strategy_repo = StrategyRepository(session)
            strategies = await strategy_repo.get_active_strategies()
            
            for strategy in strategies:
                strategy_id = str(strategy.id)
                job_id = f"strategy:{strategy_id}"
                
                # Check if job already exists
                job = Job(job_id, redis)
                job_info = await job.info()
                
                if job_info is None:
                    # No job exists, schedule one
                    try:
                        config = strategy.config or {}
                        interval_minutes = config.get("execution_interval_minutes", 30)
                        
                        # Calculate delay based on next_run_at if set
                        delay = timedelta(seconds=0)
                        if strategy.next_run_at and strategy.next_run_at > datetime.now(UTC):
                            delay = strategy.next_run_at - datetime.now(UTC)
                        
                        await redis.enqueue_job(
                            "execute_strategy_cycle",
                            strategy_id,
                            _defer_by=delay,
                            _job_id=job_id,
                        )
                        started += 1
                        logger.info(f"Scheduled job for strategy {strategy_id}")
                    except Exception as e:
                        errors += 1
                        logger.error(f"Failed to schedule job for strategy {strategy_id}: {e}")
                else:
                    skipped += 1
                    logger.debug(f"Job already exists for strategy {strategy_id}")
    
    except Exception as e:
        logger.exception(f"Error syncing strategies: {e}")
        return {"error": str(e)}
    
    return {
        "started": started,
        "skipped": skipped,
        "errors": errors,
    }


# ==================== Position Reconciliation ====================

async def reconcile_positions(ctx: dict) -> dict[str, Any]:
    """
    Periodic reconciliation: compare DB position records with exchange state.

    Uses AgentPositionService for agent-level position isolation.

    Detects and handles:
    - Zombie records (DB=open, exchange=no position) → mark closed
    - Orphan positions (exchange has it, DB doesn't) → log warning
    - Size drift → sync from exchange
    - Stale pending claims → delete

    Runs every 5 minutes via cron job + once on startup.
    """
    logger.info("Starting position reconciliation...")
    total_summary: dict[str, int] = {
        "accounts_checked": 0,
        "zombies_closed": 0,
        "orphans_found": 0,
        "size_synced": 0,
        "stale_cleaned": 0,
    }

    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select, distinct
            from ..db.models import AgentPositionDB
            from ..services.agent_position_service import AgentPositionService

            # Find all accounts that have open/pending agent positions
            stmt = (
                select(distinct(AgentPositionDB.account_id))
                .where(AgentPositionDB.status.in_(["open", "pending"]))
            )
            result = await session.execute(stmt)
            account_ids = [row[0] for row in result.all()]

            if not account_ids:
                logger.info("No accounts with open positions – reconciliation skipped")
                return total_summary

            account_repo = AccountRepository(session)
            from ..services.redis_service import get_redis_service
            try:
                redis_service = await get_redis_service()
            except Exception:
                redis_service = None
            agent_position_service = AgentPositionService(db=session, redis=redis_service)

            for account_id in account_ids:
                trader = None
                try:
                    account = await account_repo.get_by_id(account_id)
                    if not account:
                        continue

                    credentials = await account_repo.get_decrypted_credentials(
                        account_id, account.user_id
                    )
                    if not credentials:
                        continue

                    trader = create_trader_from_account(account, credentials)
                    await trader.initialize()
                    exchange_positions = await trader.get_positions()

                    summary = await agent_position_service.reconcile(
                        account_id=account_id,
                        exchange_positions=exchange_positions,
                    )

                    # Clean stale pending claims
                    stale = await agent_position_service.cleanup_stale_pending()

                    total_summary["accounts_checked"] += 1
                    total_summary["zombies_closed"] += summary["zombies_closed"]
                    total_summary["orphans_found"] += summary["orphans_found"]
                    total_summary["size_synced"] += summary["size_synced"]
                    total_summary["stale_cleaned"] += stale

                except Exception as e:
                    logger.error(f"Reconciliation error for account {account_id}: {e}")
                finally:
                    if trader:
                        try:
                            await trader.close()
                        except Exception:
                            pass

            await session.commit()

    except Exception as e:
        logger.exception(f"Position reconciliation failed: {e}")
        total_summary["error"] = str(e)

    logger.info(f"Position reconciliation complete: {total_summary}")
    return total_summary


# ==================== Worker Startup/Shutdown ====================

async def startup(ctx: dict) -> None:
    """Worker startup hook - runs when worker starts."""
    logger.info("ARQ Worker starting up...")
    
    # Sync active strategies on startup
    await sync_active_strategies(ctx)

    # Run position reconciliation on startup
    await reconcile_positions(ctx)
    
    logger.info("ARQ Worker startup complete")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown hook - runs when worker stops."""
    logger.info("ARQ Worker shutting down...")


# ==================== Worker Settings ====================

def get_worker_settings() -> dict:
    """
    Get ARQ worker settings.

    Returns:
        Dict with worker configuration
    """
    settings = get_settings()
    
    return {
        "functions": [
            execute_strategy_cycle,
            start_strategy_execution,
            stop_strategy_execution,
            sync_active_strategies,
            reconcile_positions,
        ],
        "on_startup": startup,
        "on_shutdown": shutdown,
        "redis_settings": {
            "host": settings.redis_url.host or "localhost",
            "port": settings.redis_url.port or 6379,
            "password": settings.redis_url.password,
            "database": 0,
        },
        "max_jobs": 10,  # Max concurrent jobs per worker
        "job_timeout": 300,  # 5 minute timeout per job
        "max_tries": settings.worker_max_consecutive_errors,
        "retry_delay": 60,  # 1 minute between retries
        "health_check_interval": 30,  # Health check every 30 seconds
        "queue_name": "bitrun:tasks",
        "cron_jobs": [
            # Sync strategies every 5 minutes
            {
                "coroutine": sync_active_strategies,
                "cron": "*/5 * * * *",  # Every 5 minutes
                "unique": True,
            },
            # Reconcile positions every 2 minutes (reduced from 5min to
            # detect SL/TP fills and liquidations more quickly)
            {
                "coroutine": reconcile_positions,
                "cron": "*/2 * * * *",  # Every 2 minutes
                "unique": True,
            },
        ],
    }


# Export worker class for arq CLI
class WorkerSettings:
    """ARQ Worker Settings class for CLI."""
    
    functions = [
        execute_strategy_cycle,
        start_strategy_execution,
        stop_strategy_execution,
        sync_active_strategies,
        reconcile_positions,
    ]
    
    on_startup = startup
    on_shutdown = shutdown
    
    max_jobs = 10
    job_timeout = 300
    max_tries = 3
    retry_delay = 60
    health_check_interval = 30
    queue_name = "bitrun:tasks"
    
    @staticmethod
    def redis_settings():
        settings = get_settings()
        return {
            "host": settings.redis_url.host or "localhost",
            "port": settings.redis_url.port or 6379,
            "password": settings.redis_url.password,
            "database": 0,
        }
