"""
Worker Lifecycle Utilities - Shared functions for worker management.

This module provides common lifecycle management functions used by
all worker backends, including heartbeat management, trader cleanup,
and distributed lock utilities.
"""

import logging
import os
import uuid
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Unique identifier for this process instance (used for leader election)
_INSTANCE_ID: Optional[str] = None

# Redis key prefixes
WORKER_OWNER_PREFIX = "worker_owner:"
EXEC_LOCK_PREFIX = "exec_lock:agent:"
OWNER_TTL_SECONDS = 120
EXEC_LOCK_TTL_SECONDS = 300


def get_instance_id() -> str:
    """
    Get or create the unique instance ID for this process.

    Used for distributed ownership claims and leader election.
    """
    global _INSTANCE_ID
    if _INSTANCE_ID is None:
        _INSTANCE_ID = f"{os.getpid()}:{uuid.uuid4().hex[:8]}"
    return _INSTANCE_ID


async def send_initial_heartbeat(
    agent_id: uuid.UUID,
    worker_instance_id: str,
) -> bool:
    """
    Send an initial heartbeat for an agent.

    This should be called immediately when starting a worker to avoid
    the "not running" status gap between API activation and first cycle.

    Args:
        agent_id: UUID of the agent
        worker_instance_id: Instance ID of the worker

    Returns:
        True if heartbeat sent successfully, False otherwise
    """
    from ..db.database import AsyncSessionLocal
    from ..services.worker_heartbeat import update_heartbeat

    try:
        async with AsyncSessionLocal() as session:
            await update_heartbeat(session, agent_id, worker_instance_id)
        return True
    except Exception as e:
        logger.warning(
            f"Failed to send initial heartbeat for agent {agent_id}: {e}"
        )
        return False


async def clear_heartbeat_on_stop(agent_id: uuid.UUID) -> bool:
    """
    Clear the heartbeat when a worker stops.

    This should be called during graceful shutdown to allow
    immediate restart without waiting for heartbeat timeout.

    Args:
        agent_id: UUID of the agent

    Returns:
        True if heartbeat cleared successfully, False otherwise
    """
    from ..db.database import AsyncSessionLocal
    from ..services.worker_heartbeat import clear_heartbeat

    try:
        async with AsyncSessionLocal() as session:
            await clear_heartbeat(session, agent_id)
        return True
    except Exception as e:
        logger.warning(
            f"Failed to clear heartbeat for agent {agent_id}: {e}"
        )
        return False


async def close_trader_safely(trader, agent_id: uuid.UUID) -> None:
    """
    Safely close a trader connection.

    Args:
        trader: The trader instance to close
        agent_id: UUID of the agent (for logging)
    """
    if trader is None:
        return

    try:
        await trader.close()
    except Exception as e:
        logger.warning(
            f"Error closing trader for agent {agent_id}: {e}"
        )


async def try_acquire_ownership(
    agent_id: str,
    instance_id: Optional[str] = None,
) -> bool:
    """
    Try to claim ownership of an agent worker via Redis SET NX.

    This implements leader election for distributed deployments.
    Only one instance can own a worker at a time.

    Args:
        agent_id: UUID string of the agent
        instance_id: Optional instance ID (defaults to current instance)

    Returns:
        True if ownership claimed, False if owned by another instance
    """
    if instance_id is None:
        instance_id = get_instance_id()

    try:
        from ..services.redis_service import get_redis_service
        redis_service = await get_redis_service()
        key = f"{WORKER_OWNER_PREFIX}{agent_id}"
        claimed = await redis_service.redis.set(
            key, instance_id, nx=True, ex=OWNER_TTL_SECONDS
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


async def refresh_ownership(
    agent_id: str,
    instance_id: Optional[str] = None,
) -> bool:
    """
    Refresh ownership TTL atomically.

    Uses a Lua script for atomic GET + EXPIRE to prevent race conditions.

    Args:
        agent_id: UUID string of the agent
        instance_id: Optional instance ID (defaults to current instance)

    Returns:
        True if ownership refreshed or reclaimed, False if lost to another instance
    """
    if instance_id is None:
        instance_id = get_instance_id()

    try:
        from ..services.redis_service import get_redis_service
        redis_service = await get_redis_service()
        key = f"{WORKER_OWNER_PREFIX}{agent_id}"

        result = await redis_service.redis.eval(
            _REFRESH_LUA, 1, key,
            instance_id, OWNER_TTL_SECONDS,
        )

        if result == 1:
            return True
        elif result == -1:
            # Key expired – try to reclaim atomically
            claimed = await redis_service.redis.set(
                key, instance_id, nx=True, ex=OWNER_TTL_SECONDS
            )
            return bool(claimed)
        else:
            # Another instance owns it
            return False
    except Exception:
        # Redis down – keep running; the per-cycle execution lock
        # still prevents duplicate execution.
        return True


async def release_ownership(
    agent_id: str,
    instance_id: Optional[str] = None,
) -> None:
    """
    Release ownership of an agent worker atomically.

    Uses a Lua script to ensure we only delete the key if we still
    own it, preventing accidental deletion of another instance's claim.

    Args:
        agent_id: UUID string of the agent
        instance_id: Optional instance ID (defaults to current instance)
    """
    if instance_id is None:
        instance_id = get_instance_id()

    try:
        from ..services.redis_service import get_redis_service
        redis_service = await get_redis_service()
        key = f"{WORKER_OWNER_PREFIX}{agent_id}"
        await redis_service.redis.eval(
            _RELEASE_LUA, 1, key, instance_id
        )
    except Exception:
        pass  # Best-effort; TTL will clean up


async def acquire_execution_lock(agent_id: str) -> Tuple[bool, Optional[str]]:
    """
    Try to acquire the execution lock for a single cycle.

    Prevents concurrent execution across all instances.

    Args:
        agent_id: UUID string of the agent

    Returns:
        Tuple of (acquired: bool, lock_key: Optional[str])
        If acquired is False, should skip this cycle.
    """
    try:
        from ..services.redis_service import get_redis_service
        redis_service = await get_redis_service()
        lock_key = f"{EXEC_LOCK_PREFIX}{agent_id}"
        acquired = await redis_service.redis.set(
            lock_key, "1", nx=True, ex=EXEC_LOCK_TTL_SECONDS
        )
        return bool(acquired), lock_key if acquired else None
    except Exception as e:
        logger.warning(
            f"Failed to acquire exec lock for {agent_id}: {e}"
        )
        # Fail-safe: do NOT proceed without lock to prevent duplicate execution
        return False, None


async def release_execution_lock(lock_key: str) -> None:
    """
    Release the execution lock after a cycle completes.

    Args:
        lock_key: The lock key returned by acquire_execution_lock
    """
    if not lock_key:
        return

    try:
        from ..services.redis_service import get_redis_service
        redis_service = await get_redis_service()
        await redis_service.redis.delete(lock_key)
    except Exception:
        pass  # Lock will expire via TTL


async def try_reconnect_trader(
    trader,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
    trade_type: str = "crypto_perp",
):
    """
    Attempt to recreate a trader connection.

    Handles cases where the exchange API key was rotated, network
    connection dropped, or exchange went through maintenance.

    Args:
        trader: Current trader instance (will be closed)
        account_id: UUID of the exchange account
        user_id: UUID of the user
        trade_type: Type of trading (crypto_perp, crypto_spot, etc.)

    Returns:
        New trader instance if successful, None otherwise
    """
    from ..db.database import AsyncSessionLocal
    from ..db.repositories.account import AccountRepository
    from ..traders.ccxt_trader import create_trader_from_account

    logger.info(f"Attempting trader reconnection for account {account_id}")

    # Close existing connection
    if trader:
        try:
            await trader.close()
        except Exception:
            pass

    try:
        async with AsyncSessionLocal() as session:
            account_repo = AccountRepository(session)
            account = await account_repo.get_by_id(account_id, user_id)
            if not account:
                logger.error(
                    f"Account {account_id} not found during reconnect"
                )
                return None

            credentials = await account_repo.get_decrypted_credentials(
                account_id, user_id
            )
            if not credentials:
                logger.error(
                    f"Failed to get credentials during reconnect"
                )
                return None

            new_trader = create_trader_from_account(
                account, credentials, trade_type=trade_type
            )
            await new_trader.initialize()
            logger.info(f"Trader reconnected for account {account_id}")
            return new_trader

    except Exception as e:
        logger.exception(f"Trader reconnection failed: {e}")
        return None


async def clear_heartbeats_for_quant_strategies() -> int:
    """
    Clear heartbeats for all active quant strategies on startup.

    This prevents WorkerManager's _monitor_loop from incorrectly marking
    quant strategies as stale before they have a chance to send their
    first heartbeat.

    Returns:
        Number of heartbeats cleared
    """
    from sqlalchemy import update
    from ..db.database import AsyncSessionLocal
    from ..db.models import AgentDB
    from ..db.repositories.quant_strategy import QuantStrategyRepository

    try:
        async with AsyncSessionLocal() as session:
            repo = QuantStrategyRepository(session)
            active = await repo.get_active_strategies()

            if not active:
                return 0

            active_ids = [s.id for s in active]

            stmt = (
                update(AgentDB)
                .where(AgentDB.id.in_(active_ids))
                .values(
                    worker_heartbeat_at=None,
                    worker_instance_id=None,
                )
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(
                f"Cleared heartbeats for {len(active_ids)} active quant strategies"
            )
            return len(active_ids)

    except Exception as e:
        logger.warning(f"Failed to clear quant heartbeats: {e}")
        return 0
