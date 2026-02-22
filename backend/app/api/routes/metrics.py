"""
Prometheus metrics endpoint.

Exposes /metrics endpoint for Prometheus scraping.
"""

from fastapi import APIRouter, Response

from ...monitoring.metrics import get_metrics_collector

router = APIRouter(tags=["monitoring"])


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    """
    collector = get_metrics_collector()

    return Response(
        content=collector.generate_metrics(),
        media_type=collector.content_type,
    )


@router.get("/metrics/json")
async def get_metrics_json():
    """
    Get metrics summary in JSON format.

    Useful for debugging and dashboard integration.
    """
    collector = get_metrics_collector()

    # Get current metric values (simplified)
    return {
        "active_strategies": collector.active_strategies._value.get(),
        "websocket_connections": collector.websocket_connections._value.get(),
        "redis_connected": collector.redis_connected._value.get() == 1,
        "database_connected": collector.database_connected._value.get() == 1,
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with component status.
    """
    from ...core.config import get_settings
    from ...core.circuit_breaker import get_circuit_breaker_health
    from ...services.redis_service import get_redis_service

    settings = get_settings()
    collector = get_metrics_collector()

    # Check Redis
    redis_ok = False
    try:
        redis = await get_redis_service()
        redis_ok = await redis.ping()
    except Exception:
        pass

    # Check Database
    db_ok = False
    try:
        from ...db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            db_ok = True
    except Exception:
        pass

    # Get circuit breaker health
    circuit_health = get_circuit_breaker_health()

    # Update metrics
    collector.set_redis_status(redis_ok)
    collector.set_database_status(db_ok)

    overall_healthy = redis_ok and db_ok and circuit_health["healthy"]

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "components": {
            "redis": {"status": "ok" if redis_ok else "error"},
            "database": {"status": "ok" if db_ok else "error"},
            "circuit_breakers": circuit_health,
        },
    }


@router.get("/health/circuit-breakers")
async def circuit_breaker_health():
    """
    Get circuit breaker status for all protected services.

    Returns detailed information about each circuit breaker including:
    - Current state (closed/open/half-open)
    - Failure counts and rates
    - Last failure/success times
    """
    from ...core.circuit_breaker import get_circuit_breaker_health

    return get_circuit_breaker_health()
