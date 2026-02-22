"""
Task Queue Service for submitting jobs to ARQ.

This module provides a service for the API to submit tasks to the
distributed task queue without needing to manage workers directly.
"""

import logging
from datetime import timedelta
from typing import Any, Optional

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from arq.jobs import Job

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class TaskQueueService:
    """
    Service for interacting with the ARQ task queue.

    Provides methods to:
    - Submit tasks for execution
    - Check job status
    - Cancel pending jobs
    - Query queue statistics
    """

    QUEUE_NAME = "bitrun:tasks"

    def __init__(self, redis_pool: ArqRedis):
        self.redis = redis_pool

    # ==================== Strategy Tasks ====================

    async def start_strategy(
        self,
        strategy_id: str,
        defer_seconds: int = 0,
    ) -> Optional[str]:
        """
        Start execution for a strategy.

        Schedules the first execution cycle.

        Args:
            strategy_id: UUID of the strategy
            defer_seconds: Optional delay before first execution

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            job = await self.redis.enqueue_job(
                "start_strategy_execution",
                strategy_id,
                _defer_by=(
                    timedelta(seconds=defer_seconds) if defer_seconds > 0 else None
                ),
                _job_id=f"start:{strategy_id}",
                _queue_name=self.QUEUE_NAME,
            )
            logger.info(f"Scheduled start for strategy {strategy_id}")
            return job.job_id if job else None
        except Exception as e:
            logger.error(f"Failed to schedule start for strategy {strategy_id}: {e}")
            return None

    async def stop_strategy(self, strategy_id: str) -> bool:
        """
        Stop execution for a strategy.

        Cancels any pending execution jobs.

        Args:
            strategy_id: UUID of the strategy

        Returns:
            True if successful
        """
        try:
            # Submit stop task
            await self.redis.enqueue_job(
                "stop_strategy_execution",
                strategy_id,
                _queue_name=self.QUEUE_NAME,
            )

            # Also try to abort the execution job directly
            job_id = f"strategy:{strategy_id}"
            job = Job(job_id, self.redis)
            try:
                await job.abort()
            except Exception:
                pass  # Job may not exist

            logger.info(f"Stopped strategy {strategy_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop strategy {strategy_id}: {e}")
            return False

    async def trigger_strategy_execution(
        self,
        strategy_id: str,
    ) -> Optional[str]:
        """
        Manually trigger a strategy execution cycle.

        This is used for manual "Run Now" functionality.

        Args:
            strategy_id: UUID of the strategy

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            # Use a unique job ID for manual triggers
            import uuid

            manual_job_id = f"manual:{strategy_id}:{uuid.uuid4().hex[:8]}"

            job = await self.redis.enqueue_job(
                "execute_strategy_cycle",
                strategy_id,
                _job_id=manual_job_id,
                _queue_name=self.QUEUE_NAME,
            )
            logger.info(f"Triggered manual execution for strategy {strategy_id}")
            return job.job_id if job else None
        except Exception as e:
            logger.error(f"Failed to trigger execution for strategy {strategy_id}: {e}")
            return None

    # ==================== Agent Tasks ====================

    async def start_agent(
        self,
        agent_id: str,
        defer_seconds: int = 0,
    ) -> Optional[str]:
        """
        Start execution for an agent.

        Schedules the first execution cycle.

        Args:
            agent_id: UUID of the agent
            defer_seconds: Optional delay before first execution

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            job = await self.redis.enqueue_job(
                "start_agent_execution",
                agent_id,
                _defer_by=(
                    timedelta(seconds=defer_seconds) if defer_seconds > 0 else None
                ),
                _job_id=f"agent:{agent_id}",
                _queue_name=self.QUEUE_NAME,
            )
            logger.info(f"Scheduled start for agent {agent_id}")
            return job.job_id if job else None
        except Exception as e:
            logger.error(f"Failed to schedule start for agent {agent_id}: {e}")
            return None

    async def stop_agent(self, agent_id: str) -> bool:
        """
        Stop execution for an agent.

        Cancels any pending execution jobs.

        Args:
            agent_id: UUID of the agent

        Returns:
            True if successful
        """
        try:
            # Submit stop task
            await self.redis.enqueue_job(
                "stop_agent_execution",
                agent_id,
                _queue_name=self.QUEUE_NAME,
            )

            # Also try to abort the execution job directly
            job_id = f"agent:{agent_id}"
            job = Job(job_id, self.redis)
            try:
                await job.abort()
            except Exception:
                pass  # Job may not exist

            logger.info(f"Stopped agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop agent {agent_id}: {e}")
            return False

    async def trigger_agent_execution(
        self,
        agent_id: str,
    ) -> Optional[str]:
        """
        Manually trigger an agent execution cycle.

        This is used for manual "Run Now" functionality.

        Args:
            agent_id: UUID of the agent

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            # Use a unique job ID for manual triggers
            import uuid

            manual_job_id = f"manual:agent:{agent_id}:{uuid.uuid4().hex[:8]}"

            job = await self.redis.enqueue_job(
                "execute_agent_cycle",
                agent_id,
                _job_id=manual_job_id,
                _queue_name=self.QUEUE_NAME,
            )
            logger.info(f"Triggered manual execution for agent {agent_id}")
            return job.job_id if job else None
        except Exception as e:
            logger.error(f"Failed to trigger execution for agent {agent_id}: {e}")
            return None

    # ==================== Job Status ====================

    async def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """
        Get status of a job.

        Args:
            job_id: Job identifier

        Returns:
            Dict with job status info or None if not found
        """
        try:
            job = Job(job_id, self.redis)
            info = await job.info()

            if info is None:
                return None

            return {
                "job_id": job_id,
                "function": info.function,
                "status": info.status.value if info.status else "unknown",
                "enqueue_time": (
                    info.enqueue_time.isoformat() if info.enqueue_time else None
                ),
                "start_time": info.start_time.isoformat() if info.start_time else None,
                "finish_time": (
                    info.finish_time.isoformat() if info.finish_time else None
                ),
                "success": info.success,
                "result": info.result,
                "score": info.score,
            }
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None

    async def get_strategy_job_status(
        self, strategy_id: str
    ) -> Optional[dict[str, Any]]:
        """
        Get status of the scheduled job for a strategy.

        Args:
            strategy_id: UUID of the strategy

        Returns:
            Dict with job status or None if no job exists
        """
        job_id = f"strategy:{strategy_id}"
        return await self.get_job_status(job_id)

    async def get_agent_job_status(self, agent_id: str) -> Optional[dict[str, Any]]:
        """
        Get status of the scheduled job for an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            Dict with job status or None if no job exists
        """
        job_id = f"agent:{agent_id}"
        return await self.get_job_status(job_id)

    async def is_strategy_scheduled(self, strategy_id: str) -> bool:
        """
        Check if a strategy has a scheduled execution job.

        Args:
            strategy_id: UUID of the strategy

        Returns:
            True if job exists and is pending/deferred
        """
        status = await self.get_strategy_job_status(strategy_id)
        if status is None:
            return False

        return status.get("status") in ["deferred", "queued", "in_progress"]

    # ==================== Queue Operations ====================

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending job.

        Args:
            job_id: Job identifier

        Returns:
            True if canceled successfully
        """
        try:
            job = Job(job_id, self.redis)
            await job.abort()
            logger.info(f"Canceled job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to cancel job {job_id}: {e}")
            return False

    async def get_queue_info(self) -> dict[str, Any]:
        """
        Get information about the task queue.

        Returns:
            Dict with queue statistics
        """
        try:
            # Get queue length
            queued_key = f"arq:{self.QUEUE_NAME}"
            queued_count = await self.redis.zcard(queued_key)

            # Get in-progress count
            in_progress_key = f"arq:{self.QUEUE_NAME}:in-progress"
            in_progress_count = await self.redis.zcard(in_progress_key)

            # Get results count (completed jobs)
            results_key = f"arq:{self.QUEUE_NAME}:results"
            results_count = await self.redis.hlen(results_key)

            return {
                "queue_name": self.QUEUE_NAME,
                "queued": queued_count,
                "in_progress": in_progress_count,
                "completed": results_count,
            }
        except Exception as e:
            logger.error(f"Failed to get queue info: {e}")
            return {
                "queue_name": self.QUEUE_NAME,
                "error": str(e),
            }

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of the task queue system.

        Returns:
            Dict with health status
        """
        try:
            # Ping Redis
            pong = await self.redis.ping()

            # Get queue info
            queue_info = await self.get_queue_info()

            return {
                "healthy": pong,
                "redis_connected": pong,
                "queue": queue_info,
            }
        except Exception as e:
            logger.error(f"Task queue health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
            }


# ==================== Singleton Management ====================

_task_queue_service: Optional[TaskQueueService] = None
_redis_pool: Optional[ArqRedis] = None


async def get_redis_pool() -> ArqRedis:
    """Get or create the ARQ Redis pool."""
    global _redis_pool

    if _redis_pool is None:
        settings = get_settings()

        redis_settings = RedisSettings(
            host=settings.redis_url.host or "localhost",
            port=settings.redis_url.port or 6379,
            password=settings.redis_url.password,
            database=0,
        )

        _redis_pool = await create_pool(redis_settings)
        logger.info("Created ARQ Redis pool")

    return _redis_pool


async def get_task_queue_service() -> TaskQueueService:
    """Get or create the TaskQueueService singleton."""
    global _task_queue_service

    if _task_queue_service is None:
        pool = await get_redis_pool()
        _task_queue_service = TaskQueueService(pool)
        logger.info("Created TaskQueueService")

    return _task_queue_service


async def close_task_queue() -> None:
    """Close task queue connections."""
    global _task_queue_service, _redis_pool

    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None

    _task_queue_service = None
    logger.info("Closed task queue connections")
