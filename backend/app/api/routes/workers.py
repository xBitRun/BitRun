"""Worker management routes"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...core.dependencies import CurrentUserDep
from ...workers.execution_worker import get_worker_manager

router = APIRouter(prefix="/workers", tags=["Workers"])
logger = logging.getLogger(__name__)


# ==================== Response Models ====================


class WorkerStatus(BaseModel):
    """Individual worker status"""

    strategy_id: str
    running: bool
    last_run: Optional[str] = None
    error_count: int = 0
    mode: str = "legacy"  # "legacy" or "distributed"


class QueueInfo(BaseModel):
    """Task queue information"""

    queue_name: str
    queued: int = 0
    in_progress: int = 0
    completed: int = 0
    error: Optional[str] = None


class WorkerManagerStatus(BaseModel):
    """Worker manager status"""

    running: bool
    distributed: bool
    total_workers: int
    workers: list[WorkerStatus]
    queue: Optional[QueueInfo] = None


# ==================== Routes ====================


@router.get("/status", response_model=WorkerManagerStatus)
async def get_workers_status(
    user_id: CurrentUserDep,
):
    """
    Get status of all running workers.

    Returns worker manager status and list of active workers.
    In distributed mode, also returns queue information.
    """
    worker_manager = await get_worker_manager()

    worker_ids = worker_manager.list_workers()
    workers = []

    for strategy_id in worker_ids:
        worker_status = worker_manager.get_worker_status(strategy_id)
        if worker_status:
            workers.append(
                WorkerStatus(
                    strategy_id=strategy_id,
                    running=worker_status["running"],
                    last_run=worker_status.get("last_run"),
                    error_count=worker_status.get("error_count", 0),
                    mode=worker_status.get("mode", "legacy"),
                )
            )

    # Get queue info if in distributed mode
    queue_info = None
    if worker_manager.is_distributed:
        queue_data = await worker_manager.get_queue_info()
        if queue_data:
            queue_info = QueueInfo(**queue_data)

    return WorkerManagerStatus(
        running=worker_manager._running,
        distributed=worker_manager.is_distributed,
        total_workers=len(workers),
        workers=workers,
        queue=queue_info,
    )


@router.post("/{strategy_id}/start")
async def start_worker(
    strategy_id: str,
    user_id: CurrentUserDep,
):
    """
    Manually start a worker for a strategy.

    The strategy must be in 'active' status.
    """
    worker_manager = await get_worker_manager()

    success = await worker_manager.start_strategy(strategy_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to start worker. Check that the strategy exists, is active, and has a valid account.",
        )

    return {"message": f"Worker started for strategy {strategy_id}"}


@router.post("/{strategy_id}/stop")
async def stop_worker(
    strategy_id: str,
    user_id: CurrentUserDep,
):
    """
    Manually stop a worker for a strategy.

    This only stops the worker, it does not change the strategy status.
    """
    worker_manager = await get_worker_manager()

    await worker_manager.stop_strategy(strategy_id)

    return {"message": f"Worker stopped for strategy {strategy_id}"}


@router.post("/{strategy_id}/trigger")
async def trigger_execution(
    strategy_id: str,
    user_id: CurrentUserDep,
):
    """
    Manually trigger a strategy execution cycle (Run Now).

    Supports both legacy (in-process) and distributed (ARQ) modes.
    In legacy mode, runs the cycle directly and returns results.
    In distributed mode, enqueues the job and returns the job ID.
    """
    worker_manager = await get_worker_manager()

    result = await worker_manager.trigger_manual_execution(strategy_id, user_id=user_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to trigger execution"),
        )

    return {
        "message": f"Execution triggered for strategy {strategy_id}",
        "job_id": result.get("job_id"),
        "decision_id": result.get("decision_id"),
        "success": True,
    }


class JobStatus(BaseModel):
    """Distributed job status"""

    job_id: str
    function: Optional[str] = None
    status: str
    enqueue_time: Optional[str] = None
    start_time: Optional[str] = None
    finish_time: Optional[str] = None
    success: Optional[bool] = None
    result: Optional[Any] = None


@router.get("/{strategy_id}/status", response_model=Optional[WorkerStatus])
async def get_worker_status(
    strategy_id: str,
    user_id: CurrentUserDep,
):
    """
    Get status of a specific worker.

    Returns None if no worker is running for this strategy.
    """
    worker_manager = await get_worker_manager()

    worker_status = worker_manager.get_worker_status(strategy_id)

    if not worker_status:
        return None

    return WorkerStatus(
        strategy_id=strategy_id,
        running=worker_status["running"],
        last_run=worker_status.get("last_run"),
        error_count=worker_status.get("error_count", 0),
        mode=worker_status.get("mode", "legacy"),
    )


@router.get("/{strategy_id}/job", response_model=Optional[JobStatus])
async def get_job_status(
    strategy_id: str,
    user_id: CurrentUserDep,
):
    """
    Get distributed job status for a strategy.

    Only available in distributed mode. Returns the status of the
    scheduled execution job for the strategy.
    """
    worker_manager = await get_worker_manager()

    if not worker_manager.is_distributed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job status only available in distributed mode",
        )

    job_info = await worker_manager.get_distributed_status(strategy_id)

    if not job_info:
        return None

    return JobStatus(**job_info)
