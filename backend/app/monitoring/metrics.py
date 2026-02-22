"""
Prometheus metrics for BITRUN.

Exposes metrics for monitoring:
- HTTP request latency and counts
- AI decision latency and token usage
- Trading execution metrics
- System health metrics
"""

import time
from functools import wraps
from typing import Callable, Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)


class MetricsCollector:
    """
    Prometheus metrics collector.

    Provides metrics for:
    - HTTP requests
    - AI decisions
    - Trading operations
    - WebSocket connections
    - System resources
    """

    def __init__(self, app_name: str = "bitrun"):
        self.app_name = app_name

        # ==================== HTTP Metrics ====================

        self.http_requests_total = Counter(
            f"{app_name}_http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )

        self.http_request_duration_seconds = Histogram(
            f"{app_name}_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        # ==================== AI Decision Metrics ====================

        self.ai_decisions_total = Counter(
            f"{app_name}_ai_decisions_total",
            "Total AI decisions generated",
            ["strategy_id", "action"],
        )

        self.ai_decision_latency_seconds = Histogram(
            f"{app_name}_ai_decision_latency_seconds",
            "AI decision generation latency",
            ["model"],
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
        )

        self.ai_tokens_total = Counter(
            f"{app_name}_ai_tokens_total",
            "Total AI tokens used",
            ["model", "type"],  # type: input/output
        )

        self.ai_decision_confidence = Histogram(
            f"{app_name}_ai_decision_confidence",
            "AI decision confidence distribution",
            ["strategy_id"],
            buckets=(10, 20, 30, 40, 50, 60, 70, 80, 90, 100),
        )

        # ==================== Trading Metrics ====================

        self.trades_total = Counter(
            f"{app_name}_trades_total",
            "Total trades executed",
            ["exchange", "symbol", "side", "status"],
        )

        self.trade_volume_usd = Counter(
            f"{app_name}_trade_volume_usd_total",
            "Total trading volume in USD",
            ["exchange", "symbol"],
        )

        self.trade_pnl_usd = Counter(
            f"{app_name}_trade_pnl_usd_total",
            "Total realized P&L in USD",
            ["exchange", "strategy_id"],
        )

        self.open_positions = Gauge(
            f"{app_name}_open_positions",
            "Number of open positions",
            ["exchange", "symbol"],
        )

        self.position_value_usd = Gauge(
            f"{app_name}_position_value_usd",
            "Total position value in USD",
            ["exchange"],
        )

        self.account_equity_usd = Gauge(
            f"{app_name}_account_equity_usd",
            "Account equity in USD",
            ["exchange", "account_id"],
        )

        # ==================== Strategy Metrics ====================

        self.active_strategies = Gauge(
            f"{app_name}_active_strategies",
            "Number of active strategies",
        )

        self.strategy_cycles_total = Counter(
            f"{app_name}_strategy_cycles_total",
            "Total strategy execution cycles",
            ["strategy_id", "status"],  # status: success/error
        )

        self.strategy_win_rate = Gauge(
            f"{app_name}_strategy_win_rate",
            "Strategy win rate percentage",
            ["strategy_id"],
        )

        # ==================== WebSocket Metrics ====================

        self.websocket_connections = Gauge(
            f"{app_name}_websocket_connections",
            "Active WebSocket connections",
        )

        self.websocket_messages_total = Counter(
            f"{app_name}_websocket_messages_total",
            "Total WebSocket messages",
            ["direction", "type"],  # direction: sent/received
        )

        # ==================== System Metrics ====================

        self.worker_status = Gauge(
            f"{app_name}_worker_status",
            "Worker status (1=running, 0=stopped)",
            ["strategy_id"],
        )

        self.redis_connected = Gauge(
            f"{app_name}_redis_connected",
            "Redis connection status (1=connected, 0=disconnected)",
        )

        self.database_connected = Gauge(
            f"{app_name}_database_connected",
            "Database connection status (1=connected, 0=disconnected)",
        )

        # App info
        self.app_info = Info(
            f"{app_name}_app_info",
            "Application information",
        )

    def set_app_info(self, version: str, environment: str) -> None:
        """Set application info"""
        self.app_info.info(
            {
                "version": version,
                "environment": environment,
            }
        )

    # ==================== HTTP Tracking ====================

    def track_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float,
    ) -> None:
        """Track HTTP request"""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status),
        ).inc()

        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

    # ==================== AI Tracking ====================

    def track_decision(
        self,
        strategy_id: str,
        action: str,
        model: str,
        latency_seconds: float,
        input_tokens: int,
        output_tokens: int,
        confidence: int,
    ) -> None:
        """Track AI decision"""
        self.ai_decisions_total.labels(
            strategy_id=strategy_id,
            action=action,
        ).inc()

        self.ai_decision_latency_seconds.labels(model=model).observe(latency_seconds)

        self.ai_tokens_total.labels(model=model, type="input").inc(input_tokens)
        self.ai_tokens_total.labels(model=model, type="output").inc(output_tokens)

        self.ai_decision_confidence.labels(strategy_id=strategy_id).observe(confidence)

    # ==================== Trade Tracking ====================

    def track_trade(
        self,
        exchange: str,
        symbol: str,
        side: str,
        status: str,
        volume_usd: float,
        pnl_usd: Optional[float] = None,
        strategy_id: Optional[str] = None,
    ) -> None:
        """Track trade execution"""
        self.trades_total.labels(
            exchange=exchange,
            symbol=symbol,
            side=side,
            status=status,
        ).inc()

        if volume_usd > 0:
            self.trade_volume_usd.labels(
                exchange=exchange,
                symbol=symbol,
            ).inc(volume_usd)

        if pnl_usd is not None and strategy_id:
            self.trade_pnl_usd.labels(
                exchange=exchange,
                strategy_id=strategy_id,
            ).inc(pnl_usd)

    def update_positions(
        self,
        exchange: str,
        positions: dict,  # symbol -> count
        total_value: float,
    ) -> None:
        """Update position metrics"""
        for symbol, count in positions.items():
            self.open_positions.labels(
                exchange=exchange,
                symbol=symbol,
            ).set(count)

        self.position_value_usd.labels(exchange=exchange).set(total_value)

    def update_account_equity(
        self,
        exchange: str,
        account_id: str,
        equity: float,
    ) -> None:
        """Update account equity"""
        self.account_equity_usd.labels(
            exchange=exchange,
            account_id=account_id,
        ).set(equity)

    # ==================== Strategy Tracking ====================

    def track_strategy_cycle(
        self,
        strategy_id: str,
        success: bool,
    ) -> None:
        """Track strategy execution cycle"""
        self.strategy_cycles_total.labels(
            strategy_id=strategy_id,
            status="success" if success else "error",
        ).inc()

    def update_strategy_stats(
        self,
        strategy_id: str,
        win_rate: float,
    ) -> None:
        """Update strategy statistics"""
        self.strategy_win_rate.labels(strategy_id=strategy_id).set(win_rate)

    def set_active_strategies(self, count: int) -> None:
        """Set active strategy count"""
        self.active_strategies.set(count)

    # ==================== WebSocket Tracking ====================

    def set_websocket_connections(self, count: int) -> None:
        """Set WebSocket connection count"""
        self.websocket_connections.set(count)

    def track_websocket_message(
        self,
        direction: str,  # sent/received
        msg_type: str,
    ) -> None:
        """Track WebSocket message"""
        self.websocket_messages_total.labels(
            direction=direction,
            type=msg_type,
        ).inc()

    # ==================== System Tracking ====================

    def set_worker_status(self, strategy_id: str, running: bool) -> None:
        """Set worker status"""
        self.worker_status.labels(strategy_id=strategy_id).set(1 if running else 0)

    def set_redis_status(self, connected: bool) -> None:
        """Set Redis connection status"""
        self.redis_connected.set(1 if connected else 0)

    def set_database_status(self, connected: bool) -> None:
        """Set database connection status"""
        self.database_connected.set(1 if connected else 0)

    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics output"""
        return generate_latest()

    @property
    def content_type(self) -> str:
        """Prometheus content type"""
        return CONTENT_TYPE_LATEST


# Global metrics collector
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create metrics collector singleton"""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


# ==================== Decorators ====================


def track_request(func: Callable) -> Callable:
    """Decorator to track HTTP request metrics"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        response = await func(*args, **kwargs)
        duration = time.time() - start

        # Extract request info from args (assuming FastAPI route)
        # This is simplified - in practice you'd use middleware
        collector = get_metrics_collector()
        collector.track_request(
            method="GET",  # Would need to extract from request
            endpoint=func.__name__,
            status=200,  # Would need to extract from response
            duration=duration,
        )

        return response

    return wrapper


def track_decision(func: Callable) -> Callable:
    """
    Decorator to track AI decision metrics.

    Expects the decorated function to return a dict with:
    - decision: DecisionResponse object with decisions list
    - tokens_used: int
    - latency_ms: int
    - success: bool

    Can also extract strategy_id from kwargs or first positional arg.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        latency = time.time() - start

        collector = get_metrics_collector()

        try:
            # Extract strategy_id from kwargs or self.strategy
            strategy_id = kwargs.get("strategy_id", "unknown")
            if strategy_id == "unknown" and args:
                # Try to get from self.strategy if this is a method
                self_obj = args[0]
                if hasattr(self_obj, "strategy") and hasattr(self_obj.strategy, "id"):
                    strategy_id = str(self_obj.strategy.id)

            # Extract decision details from result
            if isinstance(result, dict):
                decision = result.get("decision")
                tokens_used = result.get("tokens_used", 0)

                if decision and hasattr(decision, "decisions"):
                    for d in decision.decisions:
                        action = (
                            d.action.value
                            if hasattr(d.action, "value")
                            else str(d.action)
                        )
                        collector.track_decision(
                            strategy_id=str(strategy_id),
                            action=action,
                            model="claude-sonnet",  # Default model
                            latency_seconds=latency,
                            input_tokens=tokens_used // 2,  # Approximate split
                            output_tokens=tokens_used // 2,
                            confidence=d.confidence,
                        )
                elif decision and hasattr(decision, "overall_confidence"):
                    # Track overall decision if no individual decisions
                    collector.track_decision(
                        strategy_id=str(strategy_id),
                        action="analyze",
                        model="claude-sonnet",
                        latency_seconds=latency,
                        input_tokens=tokens_used // 2,
                        output_tokens=tokens_used // 2,
                        confidence=decision.overall_confidence,
                    )
        except Exception as e:
            # Don't let metrics tracking break the main flow
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to track decision metrics: {e}"
            )

        return result

    return wrapper


def track_trade(func: Callable) -> Callable:
    """
    Decorator to track trade execution metrics.

    Expects the decorated function to return an OrderResult or dict with:
    - success: bool
    - filled_size: float
    - filled_price: float
    - error: optional str

    Can extract symbol, side from kwargs.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)

        collector = get_metrics_collector()

        try:
            # Extract trade details from kwargs
            symbol = kwargs.get("symbol", "unknown")
            exchange = kwargs.get("exchange", "unknown")

            # Try to get exchange from self.trader
            if exchange == "unknown" and args:
                self_obj = args[0]
                if hasattr(self_obj, "trader") and hasattr(self_obj.trader, "exchange"):
                    exchange = self_obj.trader.exchange
                elif hasattr(self_obj, "exchange"):
                    exchange = self_obj.exchange

            # Determine side from function name or kwargs
            side = kwargs.get("side", "unknown")
            if side == "unknown":
                func_name = func.__name__.lower()
                if "long" in func_name or "buy" in func_name:
                    side = "long"
                elif "short" in func_name or "sell" in func_name:
                    side = "short"
                elif "close" in func_name:
                    side = "close"

            # Extract result details
            if hasattr(result, "success"):
                success = result.success
                filled_size = getattr(result, "filled_size", 0) or 0
                filled_price = getattr(result, "filled_price", 0) or 0
            elif isinstance(result, dict):
                success = result.get("success", False)
                filled_size = result.get("filled_size", 0) or 0
                filled_price = result.get("filled_price", 0) or 0
            else:
                success = bool(result)
                filled_size = 0
                filled_price = 0

            volume_usd = (
                filled_size * filled_price if filled_size and filled_price else 0
            )
            status = "success" if success else "failed"

            collector.track_trade(
                exchange=str(exchange),
                symbol=str(symbol),
                side=str(side),
                status=status,
                volume_usd=volume_usd,
            )
        except Exception as e:
            # Don't let metrics tracking break the main flow
            import logging

            logging.getLogger(__name__).warning(f"Failed to track trade metrics: {e}")

        return result

    return wrapper
