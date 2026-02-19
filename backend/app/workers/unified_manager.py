"""
Unified Worker Manager - Single entry point for all worker management.

This module provides a unified interface for managing both AI and Quant
strategy workers, routing requests to the appropriate backend based on
strategy type.

Architecture:
    UnifiedWorkerManager
    ├── AIWorkerBackend → AIExecutionWorker → StrategyEngine
    └── QuantWorkerBackend → QuantExecutionWorker → QuantEngine
"""

import logging
from typing import Optional

from .base_backend import WorkerBackend
from .ai_backend import AIWorkerBackend
from .quant_backend import QuantWorkerBackend
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class UnifiedWorkerManager:
    """
    Unified manager for AI and Quant strategy workers.

    Provides a single entry point for all worker operations, automatically
    routing to the appropriate backend based on strategy type.

    Features:
    - Unified start/stop/trigger API
    - Automatic backend detection based on strategy type
    - Distributed safety (Redis ownership locks, execution locks)
    - Backward compatibility with legacy WorkerManager/QuantWorkerManager
    """

    def __init__(self, distributed_safety: bool = True):
        """
        Initialize the UnifiedWorkerManager.

        Args:
            distributed_safety: If True, use Redis locks for distributed safety.
                               Set to False for single-instance deployments.
        """
        self._ai_backend = AIWorkerBackend(distributed_safety=distributed_safety)
        self._quant_backend = QuantWorkerBackend()
        self._running = False

    @property
    def ai_backend(self) -> AIWorkerBackend:
        """Get the AI backend."""
        return self._ai_backend

    @property
    def quant_backend(self) -> QuantWorkerBackend:
        """Get the Quant backend."""
        return self._quant_backend

    async def start(self) -> None:
        """Start both backends."""
        if self._running:
            return
        self._running = True

        await self._ai_backend.start()
        await self._quant_backend.start()

        ai_count = len(self._ai_backend.list_running_agents())
        quant_count = len(self._quant_backend.list_running_agents())
        logger.info(
            f"Unified Worker Manager: Started "
            f"({ai_count} AI agents, {quant_count} quant agents)"
        )

    async def stop(self) -> None:
        """Stop both backends."""
        self._running = False
        await self._ai_backend.stop()
        await self._quant_backend.stop()
        logger.info("Unified Worker Manager: Stopped")

    def _get_backend_for_strategy_type(self, strategy_type: str) -> WorkerBackend:
        """
        Get the appropriate backend for a strategy type.

        Args:
            strategy_type: Strategy type ('ai', 'grid', 'dca', 'rsi')

        Returns:
            The appropriate WorkerBackend instance
        """
        if strategy_type == "ai":
            return self._ai_backend
        else:
            return self._quant_backend

    async def _get_backend_for_agent(self, agent_id: str) -> Optional[WorkerBackend]:
        """
        Determine the appropriate backend for an agent by querying the database.

        Args:
            agent_id: UUID string of the agent

        Returns:
            The appropriate WorkerBackend instance or None if agent not found
        """
        import uuid
        from ..db.database import AsyncSessionLocal
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from ..db.models import AgentDB

        try:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(AgentDB)
                    .where(AgentDB.id == uuid.UUID(agent_id))
                    .options(selectinload(AgentDB.strategy))
                )
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()

                if not agent or not agent.strategy:
                    return None

                return self._get_backend_for_strategy_type(agent.strategy.type)
        except Exception as e:
            logger.error(f"Failed to determine backend for agent {agent_id}: {e}")
            return None

    async def start_agent(self, agent_id: str) -> bool:
        """
        Start a worker for an agent (auto-detects strategy type).

        Args:
            agent_id: UUID string of the agent

        Returns:
            True if started successfully, False otherwise
        """
        backend = await self._get_backend_for_agent(agent_id)
        if not backend:
            logger.error(f"Cannot determine backend for agent {agent_id}")
            return False

        return await backend.start_agent(agent_id)

    async def stop_agent(self, agent_id: str) -> bool:
        """
        Stop a worker for an agent (auto-detects strategy type).

        Args:
            agent_id: UUID string of the agent

        Returns:
            True if stopped successfully, False otherwise
        """
        # Try both backends since we may not have DB access during shutdown
        # Try AI backend first
        if agent_id in self._ai_backend.list_running_agents():
            return await self._ai_backend.stop_agent(agent_id)

        # Try quant backend
        if agent_id in self._quant_backend.list_running_agents():
            return await self._quant_backend.stop_agent(agent_id)

        # Not running in either backend
        return True

    async def trigger_execution(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
        strategy_id: Optional[str] = None,  # For backward compatibility
    ) -> dict:
        """
        Manually trigger an execution cycle for an agent.

        Args:
            agent_id: UUID string of the agent
            user_id: Optional user UUID for ownership verification
            strategy_id: Optional strategy ID (for backward compatibility)

        Returns:
            Dict with execution result
        """
        backend = await self._get_backend_for_agent(agent_id)
        if not backend:
            return {
                "success": False,
                "error": f"Cannot determine backend for agent {agent_id}",
            }

        return await backend.trigger_execution(agent_id, user_id)

    def get_worker_status(self, agent_id: str) -> Optional[dict]:
        """
        Get status of a worker.

        Args:
            agent_id: UUID string of the agent

        Returns:
            Dict with status info or None if not running
        """
        # Try AI backend first
        status = self._ai_backend.get_worker_status(agent_id)
        if status:
            return status

        # Try quant backend
        return self._quant_backend.get_worker_status(agent_id)

    def list_running_agents(self) -> list[str]:
        """
        List all running agent IDs across both backends.

        Returns:
            List of agent UUID strings
        """
        return (
            self._ai_backend.list_running_agents() +
            self._quant_backend.list_running_agents()
        )

    def list_ai_agents(self) -> list[str]:
        """List running AI agents only."""
        return self._ai_backend.list_running_agents()

    def list_quant_agents(self) -> list[str]:
        """List running quant agents only."""
        return self._quant_backend.list_running_agents()

    # ========================================
    # Backward Compatibility Methods
    # ========================================

    async def start_strategy(
        self,
        strategy_id: str,
        credentials: Optional[dict] = None,
        account=None,
    ) -> bool:
        """
        Start a worker for a strategy (backward compatibility).

        Args:
            strategy_id: Strategy UUID
            credentials: Exchange credentials (unused, kept for compat)
            account: Exchange account (unused, kept for compat)

        Returns:
            True if started successfully
        """
        # For backward compatibility, treat strategy_id as agent_id
        # In the new architecture, agents are the execution units
        return await self.start_agent(strategy_id)

    async def stop_strategy(self, strategy_id: str) -> bool:
        """
        Stop a worker for a strategy (backward compatibility).

        Args:
            strategy_id: Strategy UUID

        Returns:
            True if stopped successfully
        """
        return await self.stop_agent(strategy_id)

    async def trigger_manual_execution(
        self,
        strategy_id: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> dict:
        """
        Manually trigger an execution (backward compatibility).

        Args:
            strategy_id: Strategy UUID
            user_id: Optional user UUID
            agent_id: Optional agent UUID (preferred)

        Returns:
            Dict with execution result
        """
        # Use agent_id if provided, otherwise fall back to strategy_id
        target_id = agent_id or strategy_id
        return await self.trigger_execution(target_id, user_id)

    @property
    def is_distributed(self) -> bool:
        """Check if running in distributed mode (for compatibility)."""
        return False  # Unified manager uses in-process workers

    async def get_distributed_status(self, agent_id: str) -> Optional[dict]:
        """Get distributed status (for compatibility)."""
        return None  # Not applicable for unified manager

    async def get_queue_info(self) -> Optional[dict]:
        """Get queue info (for compatibility)."""
        return None  # Not applicable for unified manager

    def list_workers(self) -> list[str]:
        """List all running workers (for compatibility)."""
        return self.list_running_agents()


# Singleton instance
_unified_manager: Optional[UnifiedWorkerManager] = None


async def get_unified_worker_manager(
    distributed_safety: Optional[bool] = None,
) -> UnifiedWorkerManager:
    """
    Get or create the UnifiedWorkerManager singleton.

    Args:
        distributed_safety: If True, use Redis locks for distributed safety.
                           If None, defaults to True.

    Returns:
        UnifiedWorkerManager instance
    """
    global _unified_manager
    if _unified_manager is None:
        if distributed_safety is None:
            distributed_safety = True
        _unified_manager = UnifiedWorkerManager(distributed_safety=distributed_safety)
    return _unified_manager


async def reset_unified_worker_manager() -> None:
    """Reset the unified manager (for testing)."""
    global _unified_manager
    if _unified_manager:
        await _unified_manager.stop()
    _unified_manager = None
