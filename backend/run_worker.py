#!/usr/bin/env python
"""
ARQ Worker Entry Point.

Run distributed workers for strategy execution.

Usage:
    # Single worker
    python run_worker.py

    # Multiple workers (separate processes)
    python run_worker.py &
    python run_worker.py &
    python run_worker.py &

    # Using arq CLI directly
    arq app.workers.tasks.WorkerSettings

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
    REDIS_URL: Redis connection string (used for task queue)
    LOG_LEVEL: Logging level (default: INFO)
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arq import run_worker
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.tasks import WorkerSettings


def setup_logging() -> None:
    """Configure logging for the worker."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Reduce noise from libraries
    logging.getLogger("arq").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_redis_settings() -> RedisSettings:
    """Get Redis settings from application config."""
    settings = get_settings()
    
    return RedisSettings(
        host=settings.redis_url.host or "localhost",
        port=settings.redis_url.port or 6379,
        password=settings.redis_url.password,
        database=0,
    )


class GracefulWorker:
    """
    Wrapper for running ARQ worker with graceful shutdown.
    """
    
    def __init__(self):
        self._shutdown_event: Optional[asyncio.Event] = None
        self._worker_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)
    
    async def start(self) -> None:
        """Start the worker with signal handlers."""
        self._shutdown_event = asyncio.Event()
        
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_shutdown)
        
        self.logger.info("Starting ARQ worker...")
        self.logger.info(f"Redis: {get_redis_settings().host}:{get_redis_settings().port}")
        self.logger.info(f"Queue: {WorkerSettings.queue_name}")
        
        # Run worker
        settings = get_settings()
        
        try:
            # Create worker settings with dynamic config
            redis_settings = get_redis_settings()
            
            await run_worker(
                WorkerSettings,
                redis_settings=redis_settings,
                max_jobs=settings.worker_max_concurrent_jobs,
                job_timeout=settings.worker_job_timeout,
                max_tries=settings.worker_max_consecutive_errors,
            )
        except asyncio.CancelledError:
            self.logger.info("Worker cancelled, shutting down...")
        except Exception as e:
            self.logger.exception(f"Worker error: {e}")
            raise
    
    def _handle_shutdown(self) -> None:
        """Handle shutdown signal."""
        self.logger.info("Shutdown signal received")
        if self._shutdown_event:
            self._shutdown_event.set()


def main() -> int:
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Validate environment
    settings = get_settings()
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Worker distributed mode: {settings.worker_distributed}")
    
    if not settings.worker_distributed:
        logger.warning(
            "WORKER_DISTRIBUTED is not enabled. "
            "This worker will run but the API may use in-process workers. "
            "Set WORKER_DISTRIBUTED=true to use distributed task queue."
        )
    
    # Run worker
    worker = GracefulWorker()
    
    try:
        asyncio.run(worker.start())
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Worker failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
