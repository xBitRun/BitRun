"""
Distributed Task Definitions for ARQ (Async Redis Queue).

This module defines all background tasks that can be executed by workers.
Tasks are submitted to Redis and distributed across worker instances.

Architecture (v2 - Agent-based):
- Tasks bind to agent_id (not strategy_id)
- Multiple agents can share the same strategy
- Each agent has independent execution state
- Heartbeat tracking for crash recovery
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from arq import ArqRedis
from arq.jobs import Job

from ..core.config import get_settings
from ..db.database import AsyncSessionLocal
from ..db.models import DecisionRecordDB, ExchangeAccountDB, StrategyDB, AgentDB
from ..db.repositories.account import AccountRepository
from ..db.repositories.agent import AgentRepository
from ..db.repositories.strategy import StrategyRepository
from ..services.strategy_engine import StrategyEngine
from ..services.worker_heartbeat import (
    get_worker_instance_id,
    update_heartbeat,
    clear_heartbeat,
    mark_stale_agents_as_error,
    clear_all_heartbeats_for_active_agents,
    is_agent_running,
)
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


async def create_mock_trader(
    agent,
    session,
    symbols: Optional[list[str]] = None,
) -> tuple[Optional[Any], Optional[str]]:
    """
    Create and initialize a MockTrader for an agent.

    This is a shared utility function used by:
    - ExecutionWorker (AI strategies)
    - QuantWorker (grid/dca/rsi strategies)
    - API routes (manual trigger)

    Args:
        agent: AgentDB instance with execution_mode="mock"
        session: AsyncSession for state restoration
        symbols: Optional list of symbols. If not provided, uses agent.symbol or ["BTC"]

    Returns:
        Tuple of (trader, error_message). If successful, error_message is None.
    """
    from ..traders.mock_trader import MockTrader

    # Determine symbols
    if symbols is None:
        # For quant strategies, agent.symbol is a single string
        # For AI strategies, agent.strategy.symbols is a list
        if hasattr(agent, 'symbol') and agent.symbol:
            symbols = [agent.symbol]
        elif hasattr(agent, 'strategy') and agent.strategy and hasattr(agent.strategy, 'symbols'):
            symbols = agent.strategy.symbols or ["BTC"]
        else:
            symbols = ["BTC"]

    mock_balance = agent.mock_initial_balance or 10000.0

    try:
        trader = MockTrader(
            initial_balance=mock_balance,
            symbols=symbols,
        )
        await trader.initialize()

        # Restore state from persisted positions
        await _restore_mock_trader_state(
            session,
            agent.id,
            mock_balance,
            trader,
        )

        logger.info(
            f"MockTrader created for agent {agent.id}: "
            f"balance=${mock_balance:,.0f}, symbols={symbols}"
        )
        return trader, None

    except Exception as e:
        error_msg = f"Failed to create MockTrader for agent {agent.id}: {e}"
        logger.exception(error_msg)
        return None, error_msg


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

            # ── Load active agent for this strategy ──
            # Note: StrategyDB has no status field; status is on AgentDB
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

            if not agent:
                result["error"] = f"No active agent found for strategy {strategy_id}"
                logger.info(result["error"])
                return result

            # ── Determine execution mode and create trader ──
            if agent and agent.execution_mode == "mock":
                # Mock mode: use MockTrader
                trader, error = await create_mock_trader(agent, session, symbols=strategy.symbols)
                if error:
                    result["error"] = error
                    return result

            else:
                # Live mode: use CCXTTrader with exchange credentials
                account_id = agent.account_id if agent else strategy.account_id
                if not account_id:
                    result["error"] = f"Strategy {strategy_id} has no account configured"
                    logger.error(result["error"])
                    if agent:
                        from ..db.repositories.agent import AgentRepository
                        agent_repo = AgentRepository(session)
                        await agent_repo.update_status(agent.id, "error", result["error"])
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
                    if agent:
                        from ..db.repositories.agent import AgentRepository
                        agent_repo = AgentRepository(session)
                        await agent_repo.update_status(agent.id, "error", error_msg)
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

        # Update agent status on repeated failures
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                from ..db.models import AgentDB
                from ..db.repositories.agent import AgentRepository

                # Find active agent for this strategy
                stmt = select(AgentDB).where(
                    AgentDB.strategy_id == uuid.UUID(strategy_id),
                    AgentDB.status == "active",
                )
                db_result = await session.execute(stmt)
                agent = db_result.scalar_one_or_none()

                if agent:
                    # Check error count from job retries
                    job_try = ctx.get("job_try", 1)
                    settings = get_settings()
                    if job_try >= settings.worker_max_consecutive_errors:
                        agent_repo = AgentRepository(session)
                        await agent_repo.update_status(
                            agent.id,
                            "error",
                            f"Too many errors: {str(e)}"
                        )
                        await session.commit()
                        logger.error(f"Agent {agent.id} paused due to repeated errors")
        except Exception as update_error:
            logger.exception("Failed to update agent status after strategy execution error")
    
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


# ==================== Agent-Based Tasks (v2) ====================

async def execute_agent_cycle(
    ctx: dict,
    agent_id: str,
) -> dict[str, Any]:
    """
    Execute a single decision cycle for an agent.

    This is the preferred execution method (v2 architecture) that binds
    directly to agent_id instead of strategy_id. This allows multiple
    agents to share the same strategy with independent execution.

    Includes heartbeat tracking for crash recovery.

    Args:
        ctx: ARQ context (contains redis connection)
        agent_id: UUID of the agent to execute

    Returns:
        Dict with execution results
    """
    logger.info(f"Starting agent cycle for {agent_id}")

    result = {
        "agent_id": agent_id,
        "success": False,
        "error": None,
        "tokens_used": 0,
        "latency_ms": 0,
        "executed_at": datetime.now(UTC).isoformat(),
    }

    trader = None
    worker_instance_id = get_worker_instance_id()

    # Agent-level execution lock
    redis: ArqRedis = ctx["redis"]
    lock_key = f"exec_lock:agent:{agent_id}"
    lock_acquired = False
    try:
        lock_acquired = await redis.set(lock_key, worker_instance_id, nx=True, ex=300)
    except Exception as e:
        logger.error(f"Failed to acquire exec lock for agent {agent_id}: {e}")
        result["error"] = f"Redis lock unavailable: {e}"
        return result

    if not lock_acquired:
        result["error"] = f"Agent {agent_id} is already executing. Skipping this cycle."
        logger.warning(result["error"])
        return result

    try:
        async with AsyncSessionLocal() as session:
            # Get agent from database with strategy
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            agent_stmt = (
                select(AgentDB)
                .where(AgentDB.id == uuid.UUID(agent_id))
                .options(selectinload(AgentDB.strategy))
            )
            agent_result = await session.execute(agent_stmt)
            agent = agent_result.scalar_one_or_none()

            if not agent:
                result["error"] = f"Agent {agent_id} not found"
                logger.error(result["error"])
                return result

            if agent.status != "active":
                result["error"] = f"Agent {agent_id} is not active (status={agent.status})"
                logger.info(result["error"])
                return result

            strategy = agent.strategy
            if not strategy:
                result["error"] = f"Agent {agent_id} has no strategy"
                logger.error(result["error"])
                return result

            # Update heartbeat
            await update_heartbeat(session, uuid.UUID(agent_id), worker_instance_id)

            # Determine execution mode and create trader
            account_repo = AccountRepository(session)
            agent_repo = AgentRepository(session)

            if agent.execution_mode == "mock":
                trader, error = await create_mock_trader(agent, session, symbols=strategy.symbols)
                if error:
                    result["error"] = error
                    await agent_repo.update_status(agent.id, "error", f"Worker startup failed: {error}")
                    await session.commit()
                    return result
            else:
                # Live mode
                if not agent.account_id:
                    error_msg = "No exchange account configured"
                    result["error"] = error_msg
                    await agent_repo.update_status(agent.id, "error", f"Worker startup failed: {error_msg}")
                    await session.commit()
                    return result

                account = await account_repo.get_by_id(agent.account_id)
                if not account:
                    error_msg = "Exchange account not found"
                    result["error"] = error_msg
                    await agent_repo.update_status(agent.id, "error", f"Worker startup failed: {error_msg}")
                    await session.commit()
                    return result

                credentials = await account_repo.get_decrypted_credentials(
                    agent.account_id, agent.user_id
                )
                if not credentials:
                    error_msg = "Invalid API credentials"
                    result["error"] = error_msg
                    await agent_repo.update_status(agent.id, "error", f"Worker startup failed: {error_msg}")
                    await session.commit()
                    return result

                try:
                    trader = create_trader_from_account(account, credentials)
                    await trader.initialize()
                except (ValueError, TradeError) as e:
                    error_msg = str(e) if isinstance(e, ValueError) else e.message
                    result["error"] = f"Trader initialization failed: {error_msg}"
                    logger.error(result["error"])
                    await agent_repo.update_status(agent.id, "error", f"Trader initialization failed: {error_msg}")
                    await session.commit()
                    return result

            # Create position service
            from ..services.redis_service import get_redis_service
            from ..services.agent_position_service import AgentPositionService
            try:
                redis_service = await get_redis_service()
            except Exception:
                redis_service = None
            position_service = AgentPositionService(db=session, redis=redis_service)

            # Create strategy engine and run cycle
            engine = StrategyEngine(
                agent=agent,
                strategy=strategy,
                trader=trader,
                ai_client=None,
                db_session=session,
                position_service=position_service,
            )

            cycle_result = await engine.run_cycle()

            # Update agent timestamps
            interval_minutes = agent.execution_interval_minutes or 30
            await agent_repo.update(
                agent.id,
                agent.user_id,
                last_run_at=datetime.now(UTC),
                next_run_at=datetime.now(UTC) + timedelta(minutes=interval_minutes),
            )
            await session.commit()

            # Schedule next execution
            await redis.enqueue_job(
                "execute_agent_cycle",
                agent_id,
                _defer_by=timedelta(minutes=interval_minutes),
                _job_id=f"agent:{agent_id}",
            )

            result["success"] = cycle_result.get("success", False)
            result["tokens_used"] = cycle_result.get("tokens_used", 0)
            result["latency_ms"] = cycle_result.get("latency_ms", 0)

            logger.info(
                f"Agent {agent_id} cycle completed: "
                f"success={result['success']}, "
                f"tokens={result['tokens_used']}, "
                f"latency={result['latency_ms']}ms"
            )

    except Exception as e:
        result["error"] = str(e)
        logger.exception(f"Error executing agent {agent_id}: {e}")

        # Update agent status on repeated failures
        try:
            async with AsyncSessionLocal() as session:
                agent_repo = AgentRepository(session)
                agent = await agent_repo.get_by_id(uuid.UUID(agent_id))

                if agent:
                    job_try = ctx.get("job_try", 1)
                    settings = get_settings()
                    if job_try >= settings.worker_max_consecutive_errors:
                        await agent_repo.update_status(
                            agent.id,
                            "error",
                            f"Execution failed after {job_try} retries: {str(e)}"
                        )
                        await session.commit()
                        logger.error(f"Agent {agent.id} marked as error due to repeated failures")
        except Exception as update_error:
            logger.exception("Failed to update agent status after execution error")

    finally:
        if trader:
            try:
                await trader.close()
            except Exception as e:
                logger.warning(f"Error closing trader: {e}")

        try:
            await redis.delete(lock_key)
        except Exception:
            pass

    return result


async def start_agent_execution(
    ctx: dict,
    agent_id: str,
) -> dict[str, Any]:
    """
    Start execution for an agent by scheduling the first cycle.

    Args:
        ctx: ARQ context
        agent_id: UUID of the agent to start

    Returns:
        Dict with status
    """
    logger.info(f"Starting execution for agent {agent_id}")

    redis: ArqRedis = ctx["redis"]

    # Schedule immediate execution
    job = await redis.enqueue_job(
        "execute_agent_cycle",
        agent_id,
        _job_id=f"agent:{agent_id}",
    )

    return {
        "agent_id": agent_id,
        "status": "scheduled",
        "job_id": job.job_id if job else None,
    }


async def stop_agent_execution(
    ctx: dict,
    agent_id: str,
) -> dict[str, Any]:
    """
    Stop execution for an agent by canceling pending jobs.

    Also clears the heartbeat for this agent.

    Args:
        ctx: ARQ context
        agent_id: UUID of the agent to stop

    Returns:
        Dict with status
    """
    logger.info(f"Stopping execution for agent {agent_id}")

    redis: ArqRedis = ctx["redis"]

    # Try to abort the pending job
    job_id = f"agent:{agent_id}"
    job = Job(job_id, redis)

    try:
        await job.abort()
        logger.info(f"Aborted job for agent {agent_id}")
    except Exception as e:
        logger.warning(f"Could not abort job for agent {agent_id}: {e}")

    # Clear heartbeat
    try:
        async with AsyncSessionLocal() as session:
            await clear_heartbeat(session, uuid.UUID(agent_id))
    except Exception as e:
        logger.warning(f"Could not clear heartbeat for agent {agent_id}: {e}")

    return {
        "agent_id": agent_id,
        "status": "stopped",
    }


async def sync_active_strategies(ctx: dict) -> dict[str, Any]:
    """
    Sync active agents with the task queue.

    This is a periodic task that ensures all active agents have
    scheduled jobs, and stopped agents don't.

    Also handles heartbeat recovery:
    - Marks stale agents (heartbeat timeout) as error
    - Clears old heartbeats before scheduling

    Args:
        ctx: ARQ context

    Returns:
        Dict with sync results
    """
    logger.info("Syncing active agents with task queue")

    redis: ArqRedis = ctx["redis"]
    started = 0
    skipped = 0
    errors = 0
    stale_recovered = 0

    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            # Phase 1: Mark stale agents as error (crash recovery)
            stale_count = await mark_stale_agents_as_error(session)
            if stale_count > 0:
                stale_recovered = stale_count
                logger.info(f"Marked {stale_count} stale agents as error")

            # Phase 2: Clear heartbeats for active agents (clean slate)
            await clear_all_heartbeats_for_active_agents(session)

            # Phase 3: Query active agents with their strategies
            stmt = (
                select(AgentDB)
                .where(AgentDB.status == "active")
                .options(selectinload(AgentDB.strategy))
            )
            db_result = await session.execute(stmt)
            agents = db_result.scalars().all()

            for agent in agents:
                strategy = agent.strategy
                if not strategy:
                    continue

                # Use agent-based job ID (v2 architecture)
                agent_id = str(agent.id)
                job_id = f"agent:{agent_id}"

                # Check if job already exists
                job = Job(job_id, redis)
                job_info = await job.info()

                if job_info is None:
                    now = datetime.now(UTC)
                    interval_minutes = agent.execution_interval_minutes or 30

                    # ===== Check if we should skip scheduling =====
                    # ARQ's job.info() returns None for deferred jobs, so we need
                    # to check next_run_at to avoid creating duplicate jobs.

                    # Case: next_run_at is in the reasonable future
                    # - Normal case: task already scheduled via _defer_by
                    # - Max reasonable delay = 1.5 × execution interval (tolerates some latency)
                    if agent.next_run_at and agent.next_run_at > now:
                        time_until_next = (agent.next_run_at - now).total_seconds() / 60
                        max_reasonable_delay = interval_minutes * 1.5

                        if time_until_next <= max_reasonable_delay:
                            # Check heartbeat to confirm worker hasn't crashed
                            if is_agent_running(agent):
                                # Everything looks normal - job is scheduled, worker is alive
                                skipped += 1
                                logger.debug(
                                    f"Agent {agent_id} already scheduled for "
                                    f"{agent.next_run_at}, heartbeat OK, skipping"
                                )
                                continue
                            else:
                                # Heartbeat timeout but next_run_at in future = worker crashed
                                # during the wait period
                                logger.warning(
                                    f"Agent {agent_id} has future next_run_at but heartbeat "
                                    f"timeout, will reschedule immediately"
                                )
                                # Fall through to reschedule
                        else:
                            # next_run_at too far in future (config change?), reschedule
                            logger.info(
                                f"Agent {agent_id} next_run_at too far in future "
                                f"({time_until_next:.1f}min > {max_reasonable_delay:.1f}min), "
                                f"rescheduling"
                            )
                            # Fall through to reschedule

                    # ===== Schedule the job =====
                    try:
                        # Calculate delay based on next_run_at if set and in future
                        delay = timedelta(seconds=0)
                        if agent.next_run_at and agent.next_run_at > now:
                            delay = agent.next_run_at - now

                        await redis.enqueue_job(
                            "execute_agent_cycle",
                            agent_id,
                            _defer_by=delay,
                            _job_id=job_id,
                        )
                        started += 1
                        logger.info(f"Scheduled agent job for {agent_id} with delay {delay}")
                    except Exception as e:
                        errors += 1
                        logger.exception(f"Failed to schedule job for agent {agent_id}")
                else:
                    skipped += 1
                    logger.debug(f"Job already exists for agent {agent_id}")

    except Exception as e:
        logger.exception(f"Error syncing agents: {e}")
        return {"error": str(e)}

    return {
        "started": started,
        "skipped": skipped,
        "errors": errors,
        "stale_recovered": stale_recovered,
    }


# ==================== Position Reconciliation ====================

async def create_daily_snapshots(ctx: dict) -> dict[str, Any]:
    """
    Create daily snapshots for all active accounts and agents.

    This task runs at UTC midnight to capture equity and performance
    metrics for historical tracking and P&L analysis.

    Returns:
        Dict with snapshot creation results
    """
    logger.info("Starting daily snapshot creation...")

    result = {
        "accounts_snapshotted": 0,
        "agents_snapshotted": 0,
        "errors": 0,
    }

    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from ..db.models import AgentDB, ExchangeAccountDB
            from ..services.pnl_service import PnLService

            pnl_service = PnLService(session)

            # Get all connected accounts
            accounts_stmt = select(ExchangeAccountDB).where(
                ExchangeAccountDB.is_connected == True
            )
            accounts_result = await session.execute(accounts_stmt)
            accounts = accounts_result.scalars().all()

            # Create snapshots for each account
            for account in accounts:
                try:
                    # Get account balance from exchange
                    account_repo = AccountRepository(session)
                    credentials = await account_repo.get_decrypted_credentials(
                        account.id, account.user_id
                    )

                    if credentials:
                        trader = None
                        try:
                            trader = create_trader_from_account(account, credentials)
                            await trader.initialize()
                            state = await trader.get_account_state()

                            # Get open positions
                            positions = await trader.get_positions()
                            position_summary = [
                                {
                                    "symbol": p.symbol,
                                    "side": p.side,
                                    "size": p.size,
                                    "unrealized_pnl": p.unrealized_pnl,
                                }
                                for p in positions
                            ]

                            await pnl_service.create_account_snapshot(
                                account_id=account.id,
                                equity=state.equity,
                                available_balance=state.available_balance,
                                unrealized_pnl=state.unrealized_pnl,
                                margin_used=state.total_margin_used,
                                open_positions=len(positions),
                                position_summary=position_summary,
                                source="scheduled",
                            )
                            result["accounts_snapshotted"] += 1

                        except Exception as e:
                            logger.warning(
                                f"Failed to create snapshot for account {account.id}: {e}"
                            )
                            result["errors"] += 1
                        finally:
                            if trader:
                                try:
                                    await trader.close()
                                except Exception:
                                    pass

                except Exception as e:
                    logger.exception(f"Error creating snapshot for account {account.id}")
                    result["errors"] += 1

            # Get all active agents
            agents_stmt = (
                select(AgentDB)
                .where(AgentDB.status == "active")
                .options(selectinload(AgentDB.strategy))
            )
            agents_result = await session.execute(agents_stmt)
            agents = agents_result.scalars().all()

            # Create snapshots for each agent
            for agent in agents:
                try:
                    await pnl_service.create_agent_snapshot(
                        agent_id=agent.id,
                        source="scheduled",
                    )
                    result["agents_snapshotted"] += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to create snapshot for agent {agent.id}: {e}"
                    )
                    result["errors"] += 1

            await session.commit()

    except Exception as e:
        logger.exception(f"Daily snapshot creation failed: {e}")
        result["error"] = str(e)

    logger.info(f"Daily snapshot creation complete: {result}")
    return result


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
                    logger.exception(f"Reconciliation error for account {account_id}")
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
            # Strategy-based functions (backward compatibility)
            execute_strategy_cycle,
            start_strategy_execution,
            stop_strategy_execution,
            # Agent-based functions (v2 architecture - preferred)
            execute_agent_cycle,
            start_agent_execution,
            stop_agent_execution,
            # Utility functions
            sync_active_strategies,
            reconcile_positions,
            create_daily_snapshots,
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
            # Sync agents every 5 minutes (handles heartbeat recovery)
            {
                "coroutine": sync_active_strategies,
                "cron": "*/5 * * * *",  # Every 5 minutes
                "unique": True,
            },
            # Reconcile positions every 2 minutes
            {
                "coroutine": reconcile_positions,
                "cron": "*/2 * * * *",  # Every 2 minutes
                "unique": True,
            },
            # Create daily snapshots at UTC midnight
            {
                "coroutine": create_daily_snapshots,
                "cron": "0 0 * * *",  # Every day at 00:00 UTC
                "unique": True,
            },
        ],
    }


# Export worker class for arq CLI
class WorkerSettings:
    """ARQ Worker Settings class for CLI."""

    functions = [
        # Strategy-based functions (backward compatibility)
        execute_strategy_cycle,
        start_strategy_execution,
        stop_strategy_execution,
        # Agent-based functions (v2 architecture - preferred)
        execute_agent_cycle,
        start_agent_execution,
        stop_agent_execution,
        # Utility functions
        sync_active_strategies,
        reconcile_positions,
        create_daily_snapshots,
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
