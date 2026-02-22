"""
Prometheus metrics middleware for FastAPI.

Automatically tracks HTTP request metrics.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .metrics import get_metrics_collector


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for Prometheus metrics.

    Automatically tracks:
    - Request count by method, path, status
    - Request latency histogram
    """

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: set[str] = None,
    ):
        """
        Initialize middleware.

        Args:
            app: ASGI application
            exclude_paths: Paths to exclude from metrics (e.g., /health, /metrics)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or {"/health", "/metrics", "/api/metrics"}
        self.collector = get_metrics_collector()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track metrics"""
        path = request.url.path

        # Skip excluded paths
        if path in self.exclude_paths:
            return await call_next(request)

        # Normalize path (remove IDs to reduce cardinality)
        normalized_path = self._normalize_path(path)

        # Track request
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time

            self.collector.track_request(
                method=request.method,
                endpoint=normalized_path,
                status=status_code,
                duration=duration,
            )

        return response

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing dynamic segments.

        /api/strategies/123-abc -> /api/strategies/{id}
        /api/accounts/456-def/test -> /api/accounts/{id}/test
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)

        return path


def setup_prometheus_middleware(app, exclude_paths: set[str] = None) -> None:
    """Setup Prometheus middleware for FastAPI app"""
    app.add_middleware(
        PrometheusMiddleware,
        exclude_paths=exclude_paths or {"/health", "/metrics", "/api/metrics"},
    )
