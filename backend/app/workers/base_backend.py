"""
Worker Backend Protocol - Abstract interface for agent execution backends.

This module defines the protocol that all worker backends must implement,
enabling UnifiedWorkerManager to delegate to the appropriate backend
based on strategy type.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Protocol

logger = logging.getLogger(__name__)


class WorkerBackend(Protocol):
    """
    Protocol defining the interface for worker backends.

    Each backend (AI, Quant) implements this interface to handle
    strategy-specific execution logic while sharing common lifecycle
    management through UnifiedWorkerManager.
    """

    @property
    def backend_type(self) -> str:
        """Return the backend type identifier (e.g., 'ai', 'quant')."""
        ...

    async def start_agent(self, agent_id: str) -> bool:
        """
        Start a worker for the given agent.

        Args:
            agent_id: UUID of the agent to start

        Returns:
            True if started successfully, False otherwise
        """
        ...

    async def stop_agent(self, agent_id: str) -> bool:
        """
        Stop the worker for the given agent.

        Args:
            agent_id: UUID of the agent to stop

        Returns:
            True if stopped successfully, False otherwise
        """
        ...

    async def trigger_execution(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """
        Manually trigger an execution cycle for the agent.

        Args:
            agent_id: UUID of the agent
            user_id: Optional user UUID for ownership verification

        Returns:
            Dict with execution result:
              - success: bool
              - decision_id: Optional[str]
              - error: Optional[str]
              - job_id: Optional[str] (for distributed mode)
        """
        ...

    def get_worker_status(self, agent_id: str) -> Optional[dict]:
        """
        Get the status of a worker.

        Args:
            agent_id: UUID of the agent

        Returns:
            Dict with status info or None if not running:
              - running: bool
              - last_run: Optional[str]
              - error_count: int
              - mode: str
        """
        ...

    def list_running_agents(self) -> list[str]:
        """
        List all agent IDs currently running in this backend.

        Returns:
            List of agent UUID strings
        """
        ...

    async def start(self) -> None:
        """Start the backend (load active agents, start sync tasks, etc.)."""
        ...

    async def stop(self) -> None:
        """Stop the backend (stop all workers, cleanup resources)."""
        ...


class BaseWorkerBackend(ABC):
    """
    Abstract base class providing common functionality for worker backends.

    Subclasses should implement:
    - start_agent()
    - stop_agent()
    - trigger_execution()
    - get_worker_status()
    - list_running_agents()
    - start()
    - stop()
    """

    def __init__(self):
        self._running = False

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Return the backend type identifier."""
        pass

    @abstractmethod
    async def start_agent(self, agent_id: str) -> bool:
        pass

    @abstractmethod
    async def stop_agent(self, agent_id: str) -> bool:
        pass

    @abstractmethod
    async def trigger_execution(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
    ) -> dict:
        pass

    @abstractmethod
    def get_worker_status(self, agent_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_running_agents(self) -> list[str]:
        pass

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @property
    def is_running(self) -> bool:
        """Check if the backend is running."""
        return self._running
