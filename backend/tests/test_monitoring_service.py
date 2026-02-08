"""
Tests for Monitoring Service.

Covers: MetricsCollector, PrometheusMiddleware path normalization,
Sentry initialization, _before_send filtering, and helper functions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# MetricsCollector Tests
# ============================================================================

class TestMetricsCollector:
    """Tests for MetricsCollector with mocked prometheus_client."""

    @pytest.fixture(autouse=True)
    def mock_prometheus(self):
        """Mock prometheus_client to avoid global registry conflicts.

        Using MagicMock() instances (not the class) so that
        Counter("name", "desc", ["label"]) returns a MagicMock
        with auto-created .labels()/.inc()/.set()/.info() etc.
        """
        _new_mock = lambda *a, **kw: MagicMock()  # noqa: E731

        with (
            patch("app.monitoring.metrics.Counter", side_effect=_new_mock) as _,
            patch("app.monitoring.metrics.Histogram", side_effect=_new_mock) as _,
            patch("app.monitoring.metrics.Gauge", side_effect=_new_mock) as _,
            patch("app.monitoring.metrics.Info", side_effect=_new_mock) as _,
            patch(
                "app.monitoring.metrics.generate_latest",
                return_value=b"# HELP test_metric\n",
            ) as _,
            patch(
                "app.monitoring.metrics.CONTENT_TYPE_LATEST",
                "text/plain; version=0.0.4; charset=utf-8",
            ) as _,
        ):
            from app.monitoring import metrics as _mod

            _mod._collector = None
            yield
            _mod._collector = None

    def test_collector_initialization(self):
        """Test MetricsCollector creates all metric instruments."""
        from app.monitoring.metrics import MetricsCollector

        collector = MetricsCollector(app_name="test_app")

        assert collector.app_name == "test_app"
        assert collector.http_requests_total is not None
        assert collector.ai_decisions_total is not None
        assert collector.trades_total is not None
        assert collector.websocket_connections is not None
        assert collector.redis_connected is not None
        assert collector.database_connected is not None

    def test_set_app_info(self):
        """Test set_app_info does not raise."""
        from app.monitoring.metrics import MetricsCollector

        collector = MetricsCollector(app_name="test_app")
        collector.set_app_info(version="1.0.0", environment="test")

    def test_track_request(self):
        """Test tracking HTTP request metrics."""
        from app.monitoring.metrics import MetricsCollector

        collector = MetricsCollector(app_name="test_app")
        collector.track_request(
            method="GET",
            endpoint="/api/test",
            status=200,
            duration=0.15,
        )

    def test_track_decision(self):
        """Test tracking AI decision metrics."""
        from app.monitoring.metrics import MetricsCollector

        collector = MetricsCollector(app_name="test_app")
        collector.track_decision(
            strategy_id="strat-1",
            action="open_long",
            model="gpt-4o",
            latency_seconds=2.5,
            input_tokens=100,
            output_tokens=200,
            confidence=75,
        )

    def test_track_trade_with_pnl(self):
        """Test tracking trade with volume and PnL."""
        from app.monitoring.metrics import MetricsCollector

        collector = MetricsCollector(app_name="test_app")
        collector.track_trade(
            exchange="binance",
            symbol="BTCUSDT",
            side="long",
            status="success",
            volume_usd=5000.0,
            pnl_usd=100.0,
            strategy_id="strat-1",
        )

    def test_generate_metrics_returns_bytes(self):
        """Test generate_metrics returns Prometheus text output."""
        from app.monitoring.metrics import MetricsCollector

        collector = MetricsCollector(app_name="test_app")
        output = collector.generate_metrics()
        assert isinstance(output, bytes)

    def test_content_type_property(self):
        """Test content_type returns expected media type string."""
        from app.monitoring.metrics import MetricsCollector

        collector = MetricsCollector(app_name="test_app")
        assert "text/plain" in collector.content_type

    def test_get_metrics_collector_singleton(self):
        """Test get_metrics_collector returns the same instance on repeat calls."""
        from app.monitoring.metrics import get_metrics_collector

        c1 = get_metrics_collector()
        c2 = get_metrics_collector()
        assert c1 is c2

    def test_system_status_tracking(self):
        """Test various system status setters work without error."""
        from app.monitoring.metrics import MetricsCollector

        collector = MetricsCollector(app_name="test_app")
        collector.set_redis_status(connected=True)
        collector.set_database_status(connected=True)
        collector.set_active_strategies(count=5)
        collector.set_websocket_connections(count=10)
        collector.set_worker_status(strategy_id="s1", running=True)


# ============================================================================
# PrometheusMiddleware Tests
# ============================================================================

class TestPrometheusMiddleware:
    """Tests for PrometheusMiddleware path normalization."""

    def _make_middleware(self):
        """Create a bare middleware instance without calling __init__."""
        from app.monitoring.middleware import PrometheusMiddleware

        mw = PrometheusMiddleware.__new__(PrometheusMiddleware)
        mw.exclude_paths = set()
        mw.collector = MagicMock()
        return mw

    def test_normalize_path_replaces_uuid(self):
        """Test UUID segments are normalized to {id}."""
        mw = self._make_middleware()
        result = mw._normalize_path(
            "/api/strategies/550e8400-e29b-41d4-a716-446655440000/execute"
        )
        assert "{id}" in result
        assert "550e8400" not in result

    def test_normalize_path_replaces_numeric_id(self):
        """Test numeric ID segments are normalized to {id}."""
        mw = self._make_middleware()
        result = mw._normalize_path("/api/users/12345/orders")
        assert "{id}" in result
        assert "12345" not in result

    def test_normalize_path_preserves_non_id_segments(self):
        """Test non-ID path segments are preserved."""
        mw = self._make_middleware()
        result = mw._normalize_path("/api/health")
        assert result == "/api/health"


# ============================================================================
# Sentry Integration Tests
# ============================================================================

class TestSentryIntegration:
    """Tests for Sentry initialization, capture helpers, and _before_send."""

    @patch("app.monitoring.sentry.SENTRY_AVAILABLE", False)
    def test_init_sentry_sdk_not_available(self):
        """Test init_sentry returns False when sentry_sdk is not installed."""
        from app.monitoring.sentry import init_sentry

        assert init_sentry() is False

    @patch("app.monitoring.sentry.SENTRY_AVAILABLE", True)
    @patch("app.monitoring.sentry.get_settings")
    def test_init_sentry_no_dsn_configured(self, mock_get_settings):
        """Test init_sentry returns False when DSN is empty."""
        mock_get_settings.return_value = MagicMock(sentry_dsn="")

        from app.monitoring.sentry import init_sentry

        assert init_sentry() is False

    @patch("app.monitoring.sentry.SENTRY_AVAILABLE", False)
    @patch("app.monitoring.sentry.sentry_sdk", None)
    def test_capture_exception_returns_none_when_disabled(self):
        """Test capture_exception returns None when Sentry is disabled."""
        from app.monitoring.sentry import capture_exception

        result = capture_exception(ValueError("test error"))
        assert result is None

    @patch("app.monitoring.sentry.SENTRY_AVAILABLE", False)
    @patch("app.monitoring.sentry.sentry_sdk", None)
    def test_capture_message_returns_none_when_disabled(self):
        """Test capture_message returns None when Sentry is disabled."""
        from app.monitoring.sentry import capture_message

        result = capture_message("test message")
        assert result is None

    def test_before_send_filters_connection_reset(self):
        """Test _before_send drops ConnectionResetError events."""
        from app.monitoring.sentry import _before_send

        event = {"event_id": "abc"}
        hint = {
            "exc_info": (
                ConnectionResetError,
                ConnectionResetError("Connection reset"),
                None,
            )
        }

        assert _before_send(event, hint) is None

    def test_before_send_passes_regular_error(self):
        """Test _before_send passes through non-filtered errors."""
        from app.monitoring.sentry import _before_send

        event = {"event_id": "abc"}
        hint = {
            "exc_info": (ValueError, ValueError("bad value"), None)
        }

        result = _before_send(event, hint)
        assert result is not None

    def test_before_send_filters_sensitive_headers(self):
        """Test _before_send redacts authorization and cookie headers."""
        from app.monitoring.sentry import _before_send

        event = {
            "event_id": "abc",
            "request": {
                "headers": {
                    "authorization": "Bearer secret-token",
                    "cookie": "session=xyz",
                    "content-type": "application/json",
                },
            },
        }
        hint = {}

        result = _before_send(event, hint)
        assert result["request"]["headers"]["authorization"] == "[Filtered]"
        assert result["request"]["headers"]["cookie"] == "[Filtered]"
        assert result["request"]["headers"]["content-type"] == "application/json"

    def test_before_send_filters_sensitive_body_fields(self):
        """Test _before_send redacts password/api_key in request body."""
        from app.monitoring.sentry import _before_send

        event = {
            "event_id": "abc",
            "request": {
                "data": {
                    "username": "user@example.com",
                    "password": "s3cret",
                    "api_key": "sk-123",
                },
            },
        }
        hint = {}

        result = _before_send(event, hint)
        assert result["request"]["data"]["password"] == "[Filtered]"
        assert result["request"]["data"]["api_key"] == "[Filtered]"
        assert result["request"]["data"]["username"] == "user@example.com"
