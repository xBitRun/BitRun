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


# ==================== Metrics Tracking Methods ====================


class TestMetricsTrackingMethods:
    """Tests for MetricsCollector tracking methods that were uncovered."""

    def test_update_positions(self):
        from app.monitoring.metrics import MetricsCollector
        collector = MetricsCollector("test_tracking")
        collector.update_positions("binance", {"BTC": 2, "ETH": 1}, 15000.0)
        # No exception means success

    def test_update_account_equity(self):
        from app.monitoring.metrics import MetricsCollector
        collector = MetricsCollector("test_equity")
        collector.update_account_equity("binance", "acc_1", 50000.0)

    def test_track_strategy_cycle(self):
        from app.monitoring.metrics import MetricsCollector
        collector = MetricsCollector("test_cycle")
        collector.track_strategy_cycle("strat_1", success=True)
        collector.track_strategy_cycle("strat_1", success=False)

    def test_update_strategy_stats(self):
        from app.monitoring.metrics import MetricsCollector
        collector = MetricsCollector("test_stats")
        collector.update_strategy_stats("strat_1", win_rate=0.65)

    def test_set_active_strategies(self):
        from app.monitoring.metrics import MetricsCollector
        collector = MetricsCollector("test_active")
        collector.set_active_strategies(5)

    def test_track_websocket_message(self):
        from app.monitoring.metrics import MetricsCollector
        collector = MetricsCollector("test_ws")
        collector.track_websocket_message("sent", "market_update")
        collector.set_websocket_connections(10)

    def test_set_worker_status(self):
        from app.monitoring.metrics import MetricsCollector
        collector = MetricsCollector("test_worker")
        collector.set_worker_status("strat_1", running=True)
        collector.set_worker_status("strat_1", running=False)

    def test_set_system_status(self):
        from app.monitoring.metrics import MetricsCollector
        collector = MetricsCollector("test_system")
        collector.set_redis_status(True)
        collector.set_database_status(True)
        collector.set_redis_status(False)
        collector.set_database_status(False)


# ==================== Metrics Decorators ====================


class TestMetricsDecorators:
    """Tests for track_request, track_decision, and track_trade decorators."""

    @pytest.mark.asyncio
    async def test_track_request_decorator(self):
        from app.monitoring.metrics import track_request
        from unittest.mock import patch as _patch

        @track_request
        async def dummy_handler():
            return MagicMock()

        with _patch("app.monitoring.metrics.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector
            result = await dummy_handler()
            assert result is not None

    @pytest.mark.asyncio
    async def test_track_decision_decorator(self):
        from app.monitoring.metrics import track_decision
        from unittest.mock import patch as _patch

        @track_decision
        async def dummy_decision(**kwargs):
            return {
                "decision": MagicMock(decisions=[], overall_confidence=80),
                "tokens_used": 100,
                "latency_ms": 500,
            }

        with _patch("app.monitoring.metrics.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector
            result = await dummy_decision(strategy_id="strat_1")
            assert "decision" in result

    @pytest.mark.asyncio
    async def test_track_decision_decorator_with_individual_decisions(self):
        from app.monitoring.metrics import track_decision
        from unittest.mock import patch as _patch

        mock_decision = MagicMock()
        mock_decision.decisions = [
            MagicMock(action=MagicMock(value="buy"), confidence=85)
        ]

        @track_decision
        async def dummy_decision(**kwargs):
            return {
                "decision": mock_decision,
                "tokens_used": 200,
            }

        with _patch("app.monitoring.metrics.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector
            result = await dummy_decision(strategy_id="strat_2")
            assert result is not None

    @pytest.mark.asyncio
    async def test_track_decision_decorator_no_decision(self):
        from app.monitoring.metrics import track_decision
        from unittest.mock import patch as _patch

        @track_decision
        async def dummy_decision(**kwargs):
            return {"result": "no decision"}

        with _patch("app.monitoring.metrics.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector
            result = await dummy_decision()
            assert result is not None

    @pytest.mark.asyncio
    async def test_track_trade_decorator(self):
        from app.monitoring.metrics import track_trade
        from unittest.mock import patch as _patch

        @track_trade
        async def dummy_trade(**kwargs):
            return MagicMock(success=True, filled_size=0.1, filled_price=50000)

        with _patch("app.monitoring.metrics.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector
            result = await dummy_trade(symbol="BTC", side="buy")
            assert result is not None

    @pytest.mark.asyncio
    async def test_track_trade_decorator_dict_result(self):
        from app.monitoring.metrics import track_trade
        from unittest.mock import patch as _patch

        @track_trade
        async def dummy_trade(**kwargs):
            return {"success": True, "filled_size": 1.0, "filled_price": 3000}

        with _patch("app.monitoring.metrics.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector
            result = await dummy_trade(symbol="ETH")
            assert result is not None

    @pytest.mark.asyncio
    async def test_track_trade_decorator_bool_result(self):
        from app.monitoring.metrics import track_trade
        from unittest.mock import patch as _patch

        @track_trade
        async def dummy_trade(**kwargs):
            return True

        with _patch("app.monitoring.metrics.get_metrics_collector") as mock_get:
            mock_collector = MagicMock()
            mock_get.return_value = mock_collector
            result = await dummy_trade()
            assert result is True


# ==================== Sentry Success Paths ====================


class TestSentrySuccessPaths:
    """Tests for Sentry functions when SDK is available."""

    def test_before_send_filters_cancelled_error(self):
        from app.monitoring.sentry import _before_send
        import asyncio

        event = {"event_id": "123"}
        hint = {
            "exc_info": (
                type("asyncio.CancelledError", (Exception,), {"__name__": "asyncio.CancelledError"}),
                Exception("cancelled"),
                None,
            )
        }
        result = _before_send(event, hint)
        assert result is None

    def test_before_send_filters_connection_reset(self):
        from app.monitoring.sentry import _before_send

        event = {"event_id": "456"}
        hint = {"exc_info": (ConnectionResetError, ConnectionResetError(), None)}
        result = _before_send(event, hint)
        assert result is None

    def test_before_send_filters_status_code_404(self):
        from app.monitoring.sentry import _before_send

        exc = Exception("not found")
        exc.status_code = 404
        event = {"event_id": "789"}
        hint = {"exc_info": (type(exc), exc, None)}
        result = _before_send(event, hint)
        assert result is None

    def test_before_send_passes_normal_error(self):
        from app.monitoring.sentry import _before_send

        event = {"event_id": "abc"}
        hint = {"exc_info": (ValueError, ValueError("bad"), None)}
        result = _before_send(event, hint)
        assert result is not None

    def test_capture_exception_disabled(self):
        from app.monitoring.sentry import capture_exception
        # Sentry SDK may not be configured, should return None
        result = capture_exception(ValueError("test"), tags={"k": "v"})
        # Either None or a string event ID

    def test_capture_message_disabled(self):
        from app.monitoring.sentry import capture_message
        result = capture_message("test msg", level="warning", tags={"k": "v"})

    def test_set_user_disabled(self):
        from app.monitoring.sentry import set_user
        set_user("user_1", email="a@b.com", name="Test")

    def test_clear_user_disabled(self):
        from app.monitoring.sentry import clear_user
        clear_user()

    def test_add_breadcrumb_disabled(self):
        from app.monitoring.sentry import add_breadcrumb
        add_breadcrumb("test breadcrumb", category="test", data={"key": "val"})

    def test_start_transaction_disabled(self):
        from app.monitoring.sentry import start_transaction
        ctx = start_transaction("test_tx", op="task", description="test")
        # Should return nullcontext when disabled
        with ctx:
            pass

    def test_start_span_disabled(self):
        from app.monitoring.sentry import start_span
        ctx = start_span(op="db.query", description="SELECT")
        with ctx:
            pass

    @pytest.mark.asyncio
    async def test_sentry_trace_decorator_async(self):
        from app.monitoring.sentry import sentry_trace

        @sentry_trace("test_func", op="task")
        async def async_func():
            return 42

        result = await async_func()
        assert result == 42

    def test_sentry_trace_decorator_sync(self):
        from app.monitoring.sentry import sentry_trace

        @sentry_trace("test_sync")
        def sync_func():
            return "hello"

        result = sync_func()
        assert result == "hello"


class TestSentryEnabled:
    """Tests for Sentry functions when SDK is available."""

    def test_init_sentry_success(self):
        """Test successful Sentry initialization."""
        import app.monitoring.sentry as sentry_mod

        mock_sdk = MagicMock()
        mock_sdk.init = MagicMock()
        mock_sdk.set_tag = MagicMock()

        mock_settings = MagicMock()
        mock_settings.sentry_dsn = "https://key@sentry.io/1"
        mock_settings.environment = "test"
        mock_settings.app_version = "1.0.0"
        mock_settings.app_name = "bitrun"
        mock_settings.sentry_traces_sample_rate = 0.1
        mock_settings.sentry_profiles_sample_rate = 0.1

        original_available = sentry_mod.SENTRY_AVAILABLE
        original_sdk = sentry_mod.sentry_sdk

        try:
            sentry_mod.SENTRY_AVAILABLE = True
            sentry_mod.sentry_sdk = mock_sdk

            with patch("app.monitoring.sentry.get_settings", return_value=mock_settings):
                # Also need to mock the integration classes
                with patch.dict("sys.modules", {
                    "sentry_sdk": mock_sdk,
                    "sentry_sdk.integrations.asyncio": MagicMock(),
                    "sentry_sdk.integrations.fastapi": MagicMock(),
                    "sentry_sdk.integrations.logging": MagicMock(),
                    "sentry_sdk.integrations.sqlalchemy": MagicMock(),
                    "sentry_sdk.integrations.redis": MagicMock(),
                }):
                    result = sentry_mod.init_sentry()

            assert result is True
            mock_sdk.init.assert_called_once()
        finally:
            sentry_mod.SENTRY_AVAILABLE = original_available
            sentry_mod.sentry_sdk = original_sdk

    def test_init_sentry_exception(self):
        """Test Sentry initialization failure."""
        import app.monitoring.sentry as sentry_mod

        mock_sdk = MagicMock()
        mock_sdk.init = MagicMock(side_effect=RuntimeError("init failed"))

        mock_settings = MagicMock()
        mock_settings.sentry_dsn = "https://key@sentry.io/1"

        original_available = sentry_mod.SENTRY_AVAILABLE
        original_sdk = sentry_mod.sentry_sdk

        try:
            sentry_mod.SENTRY_AVAILABLE = True
            sentry_mod.sentry_sdk = mock_sdk

            with patch("app.monitoring.sentry.get_settings", return_value=mock_settings):
                result = sentry_mod.init_sentry()

            assert result is False
        finally:
            sentry_mod.SENTRY_AVAILABLE = original_available
            sentry_mod.sentry_sdk = original_sdk

    def test_capture_exception_enabled(self):
        """Test capture_exception when Sentry is available."""
        import app.monitoring.sentry as sentry_mod

        mock_sdk = MagicMock()
        mock_scope = MagicMock()
        mock_sdk.push_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sdk.push_scope.return_value.__exit__ = MagicMock(return_value=False)
        mock_sdk.capture_exception.return_value = "event-123"

        original_available = sentry_mod.SENTRY_AVAILABLE
        original_sdk = sentry_mod.sentry_sdk

        try:
            sentry_mod.SENTRY_AVAILABLE = True
            sentry_mod.sentry_sdk = mock_sdk

            result = sentry_mod.capture_exception(
                ValueError("test"),
                tags={"key": "val"},
                extra={"data": "info"},
                user={"id": "u1"},
            )

            assert result == "event-123"
            mock_scope.set_tag.assert_called()
            mock_scope.set_extra.assert_called()
            mock_scope.set_user.assert_called_with({"id": "u1"})
        finally:
            sentry_mod.SENTRY_AVAILABLE = original_available
            sentry_mod.sentry_sdk = original_sdk

    def test_capture_message_enabled(self):
        """Test capture_message when Sentry is available."""
        import app.monitoring.sentry as sentry_mod

        mock_sdk = MagicMock()
        mock_scope = MagicMock()
        mock_sdk.push_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sdk.push_scope.return_value.__exit__ = MagicMock(return_value=False)
        mock_sdk.capture_message.return_value = "msg-456"

        original_available = sentry_mod.SENTRY_AVAILABLE
        original_sdk = sentry_mod.sentry_sdk

        try:
            sentry_mod.SENTRY_AVAILABLE = True
            sentry_mod.sentry_sdk = mock_sdk

            result = sentry_mod.capture_message(
                "test message", level="warning",
                tags={"component": "test"},
                extra={"detail": "more"},
            )

            assert result == "msg-456"
            mock_scope.set_tag.assert_called()
            mock_scope.set_extra.assert_called()
        finally:
            sentry_mod.SENTRY_AVAILABLE = original_available
            sentry_mod.sentry_sdk = original_sdk

    def test_set_user_enabled(self):
        """Test set_user when Sentry is available."""
        import app.monitoring.sentry as sentry_mod

        mock_sdk = MagicMock()
        original_available = sentry_mod.SENTRY_AVAILABLE
        original_sdk = sentry_mod.sentry_sdk

        try:
            sentry_mod.SENTRY_AVAILABLE = True
            sentry_mod.sentry_sdk = mock_sdk

            sentry_mod.set_user("u1", email="a@b.com", name="Test")

            mock_sdk.set_user.assert_called_once_with({
                "id": "u1", "email": "a@b.com", "username": "Test",
            })
        finally:
            sentry_mod.SENTRY_AVAILABLE = original_available
            sentry_mod.sentry_sdk = original_sdk

    def test_clear_user_enabled(self):
        """Test clear_user when Sentry is available."""
        import app.monitoring.sentry as sentry_mod

        mock_sdk = MagicMock()
        original_available = sentry_mod.SENTRY_AVAILABLE
        original_sdk = sentry_mod.sentry_sdk

        try:
            sentry_mod.SENTRY_AVAILABLE = True
            sentry_mod.sentry_sdk = mock_sdk

            sentry_mod.clear_user()

            mock_sdk.set_user.assert_called_once_with(None)
        finally:
            sentry_mod.SENTRY_AVAILABLE = original_available
            sentry_mod.sentry_sdk = original_sdk

    def test_add_breadcrumb_enabled(self):
        """Test add_breadcrumb when Sentry is available."""
        import app.monitoring.sentry as sentry_mod

        mock_sdk = MagicMock()
        original_available = sentry_mod.SENTRY_AVAILABLE
        original_sdk = sentry_mod.sentry_sdk

        try:
            sentry_mod.SENTRY_AVAILABLE = True
            sentry_mod.sentry_sdk = mock_sdk

            sentry_mod.add_breadcrumb("test crumb", category="http", data={"url": "/api"})

            mock_sdk.add_breadcrumb.assert_called_once()
        finally:
            sentry_mod.SENTRY_AVAILABLE = original_available
            sentry_mod.sentry_sdk = original_sdk

    def test_start_transaction_enabled(self):
        """Test start_transaction when Sentry is available."""
        import app.monitoring.sentry as sentry_mod

        mock_sdk = MagicMock()
        mock_tx = MagicMock()
        mock_sdk.start_transaction.return_value = mock_tx
        original_available = sentry_mod.SENTRY_AVAILABLE
        original_sdk = sentry_mod.sentry_sdk

        try:
            sentry_mod.SENTRY_AVAILABLE = True
            sentry_mod.sentry_sdk = mock_sdk

            result = sentry_mod.start_transaction("test_op", op="task", description="desc")

            assert result == mock_tx
            mock_sdk.start_transaction.assert_called_once()
        finally:
            sentry_mod.SENTRY_AVAILABLE = original_available
            sentry_mod.sentry_sdk = original_sdk

    def test_start_span_enabled(self):
        """Test start_span when Sentry is available."""
        import app.monitoring.sentry as sentry_mod

        mock_sdk = MagicMock()
        mock_span = MagicMock()
        mock_sdk.start_span.return_value = mock_span
        original_available = sentry_mod.SENTRY_AVAILABLE
        original_sdk = sentry_mod.sentry_sdk

        try:
            sentry_mod.SENTRY_AVAILABLE = True
            sentry_mod.sentry_sdk = mock_sdk

            result = sentry_mod.start_span(op="db.query", description="SELECT")

            assert result == mock_span
            mock_sdk.start_span.assert_called_once()
        finally:
            sentry_mod.SENTRY_AVAILABLE = original_available
            sentry_mod.sentry_sdk = original_sdk
