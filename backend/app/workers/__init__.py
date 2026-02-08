"""
Background workers for strategy execution.

Supports two modes:
1. Legacy Mode: In-process workers (single process, no scaling)
2. Distributed Mode: ARQ task queue (scalable, fault-tolerant)

Set WORKER_DISTRIBUTED=true in environment to use distributed mode.
"""

from .execution_worker import (
    ExecutionWorker,
    WorkerManager,
    get_worker_manager,
    reset_worker_manager,
    create_trader_from_account,
)
from .queue import (
    TaskQueueService,
    get_task_queue_service,
    close_task_queue,
)
from .tasks import (
    WorkerSettings,
    execute_strategy_cycle,
    start_strategy_execution,
    stop_strategy_execution,
    sync_active_strategies,
)

__all__ = [
    # Legacy worker
    "ExecutionWorker",
    "WorkerManager",
    "get_worker_manager",
    "reset_worker_manager",
    "create_trader_from_account",
    # Task queue
    "TaskQueueService",
    "get_task_queue_service",
    "close_task_queue",
    # ARQ tasks
    "WorkerSettings",
    "execute_strategy_cycle",
    "start_strategy_execution",
    "stop_strategy_execution",
    "sync_active_strategies",
]
