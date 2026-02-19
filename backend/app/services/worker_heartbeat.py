"""
Worker Heartbeat Service

Provides heartbeat tracking for execution workers to enable:
- Crash detection and recovery
- Stale agent identification
- Worker health monitoring

Heartbeat Lifecycle:
1. Worker starts → clears any existing heartbeat
2. Worker runs cycle → updates heartbeat with current timestamp
3. If worker crashes → heartbeat becomes stale
4. On next startup or periodic check → stale agents are marked as error
"""

import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AgentDB

logger = logging.getLogger(__name__)

# Heartbeat configuration constants
HEARTBEAT_INTERVAL_SECONDS = 60  # Worker should update heartbeat every 60 seconds
HEARTBEAT_TIMEOUT_SECONDS = 180  # 3 minutes without heartbeat = stale
STARTUP_GRACE_SECONDS = 60  # Grace period for worker startup (no heartbeat yet)


def get_worker_instance_id() -> str:
    """
    Generate a unique identifier for this worker process.

    Format: {hostname}:{pid}
    This allows tracking which process is managing which agent.
    """
    hostname = os.uname().nodename
    pid = os.getpid()
    return f"{hostname}:{pid}"


async def update_heartbeat(
    session: AsyncSession,
    agent_id: uuid.UUID,
    worker_instance_id: Optional[str] = None,
) -> bool:
    """
    Update the heartbeat timestamp for an agent.

    Called by the worker at the start of each execution cycle to indicate
    that it is still actively managing this agent.

    Args:
        session: Database session
        agent_id: UUID of the agent to update
        worker_instance_id: Optional worker identifier. If None, generates one.

    Returns:
        True if heartbeat was updated successfully
    """
    if worker_instance_id is None:
        worker_instance_id = get_worker_instance_id()

    now = datetime.now(UTC)

    stmt = (
        update(AgentDB)
        .where(AgentDB.id == agent_id)
        .values(
            worker_heartbeat_at=now,
            worker_instance_id=worker_instance_id,
        )
    )

    try:
        await session.execute(stmt)
        await session.commit()
        logger.debug(f"Heartbeat updated for agent {agent_id} at {now.isoformat()}")
        return True
    except Exception as e:
        logger.error(f"Failed to update heartbeat for agent {agent_id}: {e}")
        await session.rollback()
        return False


async def clear_heartbeat(
    session: AsyncSession,
    agent_id: uuid.UUID,
) -> bool:
    """
    Clear the heartbeat for an agent.

    Called when a worker stops managing an agent (graceful shutdown).

    Args:
        session: Database session
        agent_id: UUID of the agent

    Returns:
        True if heartbeat was cleared successfully
    """
    stmt = (
        update(AgentDB)
        .where(AgentDB.id == agent_id)
        .values(
            worker_heartbeat_at=None,
            worker_instance_id=None,
        )
    )

    try:
        await session.execute(stmt)
        await session.commit()
        logger.debug(f"Heartbeat cleared for agent {agent_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear heartbeat for agent {agent_id}: {e}")
        await session.rollback()
        return False


async def detect_stale_agents(
    session: AsyncSession,
    timeout_seconds: int = HEARTBEAT_TIMEOUT_SECONDS,
) -> list[AgentDB]:
    """
    Find all active agents whose heartbeat has timed out.

    An agent is considered stale if:
    - Its status is 'active'
    - Its last heartbeat was more than timeout_seconds ago
    - OR it has no heartbeat but last_run_at is also older than timeout_seconds
      (this allows a grace period for workers to start up and send first heartbeat)

    Args:
        session: Database session
        timeout_seconds: Seconds without heartbeat to consider stale

    Returns:
        List of stale AgentDB objects
    """
    cutoff_time = datetime.now(UTC) - timedelta(seconds=timeout_seconds)

    # Find active agents with stale or missing heartbeat
    # Note: For agents without heartbeat, we also require last_run_at to be older than
    # the cutoff time. This provides a grace period for workers to start up.
    stmt = (
        select(AgentDB)
        .where(
            AgentDB.status == "active",
            (
                # Either has a heartbeat that's too old
                (AgentDB.worker_heartbeat_at.isnot(None)) & (AgentDB.worker_heartbeat_at < cutoff_time)
                |
                # Or has no heartbeat AND last_run is also older than cutoff
                # (grace period for worker startup)
                (AgentDB.worker_heartbeat_at.is_(None))
                & (AgentDB.last_run_at.isnot(None))
                & (AgentDB.last_run_at < cutoff_time)
            ),
        )
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_stale_agents_as_error(
    session: AsyncSession,
    timeout_seconds: int = HEARTBEAT_TIMEOUT_SECONDS,
) -> int:
    """
    Mark all stale agents as 'error' status with detailed error message.

    This is typically called during worker startup to recover from crashes.

    Error message format includes:
    - Type of failure (heartbeat timeout / startup failure)
    - Last known state (heartbeat time, last run time)
    - Timeout threshold

    Args:
        session: Database session
        timeout_seconds: Seconds without heartbeat to consider stale

    Returns:
        Number of agents marked as error
    """
    stale_agents = await detect_stale_agents(session, timeout_seconds)

    if not stale_agents:
        logger.debug("No stale agents detected")
        return 0

    count = 0
    for agent in stale_agents:
        # Build descriptive error message
        if agent.worker_heartbeat_at:
            last_heartbeat = agent.worker_heartbeat_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            error_msg = (
                f"Worker heartbeat timeout - agent may have crashed "
                f"(last heartbeat: {last_heartbeat}, timeout: {timeout_seconds // 60}min)"
            )
        else:
            # No heartbeat but has last_run_at - worker started but never sent heartbeat
            last_run = agent.last_run_at.strftime("%Y-%m-%d %H:%M:%S UTC") if agent.last_run_at else "never"
            error_msg = (
                f"Worker startup incomplete - no heartbeat received "
                f"(last run: {last_run})"
            )

        stmt = (
            update(AgentDB)
            .where(AgentDB.id == agent.id)
            .values(
                status="error",
                error_message=error_msg,
                worker_heartbeat_at=None,
                worker_instance_id=None,
            )
        )

        try:
            await session.execute(stmt)
            count += 1
            logger.warning(f"Marked agent {agent.id} as error: {error_msg}")
        except Exception as e:
            logger.error(f"Failed to mark agent {agent.id} as error: {e}")

    await session.commit()
    logger.info(f"Marked {count} stale agents as error")
    return count


async def clear_all_heartbeats_for_active_agents(
    session: AsyncSession,
) -> int:
    """
    Clear heartbeat fields for all active agents.

    Called during worker startup to ensure clean state before
    starting workers. This prevents false positives from previous runs.

    Args:
        session: Database session

    Returns:
        Number of agents updated
    """
    stmt = (
        update(AgentDB)
        .where(AgentDB.status == "active")
        .values(
            worker_heartbeat_at=None,
            worker_instance_id=None,
        )
    )

    try:
        result = await session.execute(stmt)
        await session.commit()
        count = result.rowcount
        logger.info(f"Cleared heartbeats for {count} active agents")
        return count
    except Exception as e:
        logger.error(f"Failed to clear heartbeats: {e}")
        await session.rollback()
        return 0


def is_agent_running(
    agent: AgentDB,
    timeout_seconds: int = HEARTBEAT_TIMEOUT_SECONDS,
    startup_grace_seconds: int = STARTUP_GRACE_SECONDS,
) -> bool:
    """
    Check if an agent is actually running based on heartbeat.

    An agent is considered running if:
    - Its status is 'active'
    - It has a heartbeat within the timeout window
    - OR it was recently activated (within startup grace period) and has no heartbeat yet

    This is used to distinguish between:
    - status='active', running=True: Agent is actively executing
    - status='active', running=False: Agent should be running but worker crashed

    The startup grace period prevents false "not running" status during the
    brief window between API activation and the worker sending its first heartbeat.

    Args:
        agent: AgentDB instance
        timeout_seconds: Seconds without heartbeat to consider not running
        startup_grace_seconds: Grace period for newly activated agents

    Returns:
        True if agent appears to be actively running
    """
    if agent.status != "active":
        return False

    if agent.worker_heartbeat_at is None:
        # No heartbeat yet - check if within startup grace period
        # Use updated_at as a proxy for when the agent was last activated
        if agent.updated_at:
            startup_cutoff = datetime.now(UTC) - timedelta(seconds=startup_grace_seconds)
            if agent.updated_at > startup_cutoff:
                # Recently activated, allow grace period for worker to start
                return True
        return False

    cutoff_time = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
    return agent.worker_heartbeat_at > cutoff_time
