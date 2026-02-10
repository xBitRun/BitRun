"""
FastAPI application entry point.

BITRUN - AI-Powered Trading Agent
"""

import json
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from ..core.config import get_settings
from ..db.database import close_db, init_db
from ..services.redis_service import close_redis, get_redis_service
from ..traders.exchange_pool import ExchangePool
from .routes import accounts, auth, backtest, crypto, dashboard, data, decisions, metrics, models, notifications, providers, quant_strategies, strategies, workers, ws
from ..monitoring.middleware import setup_prometheus_middleware
from ..monitoring.metrics import get_metrics_collector
from ..monitoring.sentry import init_sentry
from ..workers.execution_worker import get_worker_manager
from ..workers.quant_worker import get_quant_worker_manager


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def _configure_logging() -> None:
    """Configure logging based on environment."""
    _settings = get_settings()

    if _settings.environment == "production":
        # Structured JSON logs for production (easier to aggregate/parse)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
        logging.root.handlers = [handler]
        logging.root.setLevel(logging.INFO)
    else:
        # Human-readable logs for development
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


_configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    settings = get_settings()

    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug: {settings.is_debug}")
    logger.info(f"Transport Encryption: {settings.transport_encryption_enabled}")
    
    # Initialize Sentry for error tracking
    if init_sentry():
        logger.info("Sentry: Initialized for error tracking and performance monitoring")
    else:
        logger.info("Sentry: Disabled (no DSN configured or SDK not available)")

    # Initialize database (create tables if they don't exist)
    # Note: In production, use Alembic migrations instead
    if settings.is_debug:
        try:
            await init_db()
            logger.info("Database: Connected and initialized")
        except Exception as e:
            logger.error(f"Database: Connection failed - {e}")

    # Initialize Redis
    try:
        redis = await get_redis_service()
        if await redis.ping():
            logger.info("Redis: Connected")
        else:
            logger.warning("Redis: Connection failed (ping returned false)")
    except Exception as e:
        logger.error(f"Redis: Connection failed - {e}")

    # Initialize metrics
    collector = get_metrics_collector()
    collector.set_app_info(settings.app_version, settings.environment)
    logger.info("Prometheus Metrics: Enabled")

    # Initialize Worker Manager for strategy execution
    worker_manager = None
    if settings.worker_enabled:
        try:
            worker_manager = await get_worker_manager(distributed=settings.worker_distributed)
            await worker_manager.start()
            mode = "DISTRIBUTED (ARQ)" if settings.worker_distributed else "LEGACY (in-process)"
            logger.info(f"Worker Manager: Started in {mode} mode")
            if settings.worker_distributed:
                logger.info("Worker Manager: Tasks will be processed by external ARQ workers")
            else:
                logger.info("Worker Manager: Auto-loading active strategies")
        except Exception as e:
            logger.error(f"Worker Manager: Failed to start - {e}")
    else:
        logger.info("Worker Manager: Disabled (set WORKER_ENABLED=true to enable)")

    # Initialize Quant Worker Manager for traditional strategy execution
    quant_worker_manager = None
    if settings.worker_enabled:
        try:
            quant_worker_manager = await get_quant_worker_manager()
            await quant_worker_manager.start()
            logger.info(f"Quant Worker Manager: Started with {quant_worker_manager.get_worker_count()} active strategies")
        except Exception as e:
            logger.error(f"Quant Worker Manager: Failed to start - {e}")

    # Reminder: AI provider API keys are configured in the app (Models / Providers), stored in DB
    logger.info(
        "AI: Configure provider API keys in the app (Models / Providers) if you use AI features."
    )

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")

    # Stop worker managers
    if worker_manager:
        try:
            await worker_manager.stop()
            logger.info("Worker Manager: Stopped")
        except Exception as e:
            logger.error(f"Worker Manager: Error stopping - {e}")

    if quant_worker_manager:
        try:
            await quant_worker_manager.stop()
            logger.info("Quant Worker Manager: Stopped")
        except Exception as e:
            logger.error(f"Quant Worker Manager: Error stopping - {e}")

    # Close task queue connections if in distributed mode
    if settings.worker_distributed:
        try:
            from ..workers.queue import close_task_queue
            await close_task_queue()
            logger.info("Task Queue: Closed")
        except Exception as e:
            logger.error(f"Task Queue: Error closing - {e}")

    # Close exchange connection pool
    try:
        await ExchangePool.close_all()
        logger.info("ExchangePool: Closed all connections")
    except Exception as e:
        logger.error(f"ExchangePool: Error closing - {e}")

    await close_db()
    await close_redis()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-Powered Trading Agent with Prompt-Driven Strategies",
        lifespan=lifespan,
        docs_url="/api/v1/docs" if settings.is_debug else None,
        redoc_url="/api/v1/redoc" if settings.is_debug else None,
        openapi_url="/api/v1/openapi.json" if settings.is_debug else None,
    )

    # Security headers middleware (inner layer)
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if not settings.is_debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Prometheus metrics middleware (middle layer)
    setup_prometheus_middleware(app)

    # CORS middleware - added LAST = outermost = runs first
    # Must be outermost to avoid BaseHTTPMiddleware interfering with CORS headers
    cors_origins = settings.get_cors_origins()
    logger.info(f"CORS origins: {cors_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    )

    # ==================== API v1 Routes ====================
    # All versioned API routes use /api/v1 prefix
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(crypto.router, prefix="/api/v1")
    app.include_router(accounts.router, prefix="/api/v1")
    app.include_router(strategies.router, prefix="/api/v1")
    app.include_router(quant_strategies.router, prefix="/api/v1")
    app.include_router(decisions.router, prefix="/api/v1")
    app.include_router(backtest.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")
    app.include_router(data.router, prefix="/api/v1")
    app.include_router(models.router, prefix="/api/v1")
    app.include_router(providers.router, prefix="/api/v1")
    app.include_router(metrics.router, prefix="/api/v1")
    app.include_router(notifications.router, prefix="/api/v1")
    app.include_router(workers.router, prefix="/api/v1")
    app.include_router(ws.router, prefix="/api/v1")
    
    # ==================== Legacy Routes (backward compatibility) ====================
    # Legacy /api routes are only available in development/staging for migration.
    # In production, only /api/v1 is served to reduce attack surface.
    if settings.is_debug:
        app.include_router(auth.router, prefix="/api", include_in_schema=False)
        app.include_router(crypto.router, prefix="/api", include_in_schema=False)
        app.include_router(accounts.router, prefix="/api", include_in_schema=False)
        app.include_router(strategies.router, prefix="/api", include_in_schema=False)
        app.include_router(quant_strategies.router, prefix="/api", include_in_schema=False)
        app.include_router(decisions.router, prefix="/api", include_in_schema=False)
        app.include_router(backtest.router, prefix="/api", include_in_schema=False)
        app.include_router(dashboard.router, prefix="/api", include_in_schema=False)
        app.include_router(data.router, prefix="/api", include_in_schema=False)
        app.include_router(models.router, prefix="/api", include_in_schema=False)
        app.include_router(providers.router, prefix="/api", include_in_schema=False)
        app.include_router(metrics.router, prefix="/api", include_in_schema=False)
        app.include_router(notifications.router, prefix="/api", include_in_schema=False)
        app.include_router(workers.router, prefix="/api", include_in_schema=False)
        app.include_router(ws.router, prefix="/api", include_in_schema=False)

    # Health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
        }

    # API version info
    @app.get("/api")
    async def api_info():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "api_versions": ["v1"],
            "current_version": "v1",
            "docs": "/api/v1/docs" if settings.is_debug else None,
            "deprecation_notice": "Please use /api/v1 prefix for all API calls.",
        }

    # Root redirect
    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "api": "/api",
            "docs": "/api/v1/docs" if settings.is_debug else None,
        }

    return app


# Create app instance
app = create_app()
