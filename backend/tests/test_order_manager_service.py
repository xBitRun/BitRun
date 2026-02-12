"""
Tests for OrderManager service.

Covers: place_order_with_tracking, cancel_order, get_pending_orders,
        cancel_all_orders, close(), persistence.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.order_manager import OrderCallback, OrderManager
from app.traders.base import (
    Order,
    OrderResult,
    OrderStatus,
    OrderType,
    TradeError,
)


# ==================== Helpers ====================


def _make_order(**kwargs) -> Order:
    """Create a test Order with sensible defaults."""
    defaults = dict(
        order_id="order_1",
        client_order_id="cl_test",
        symbol="BTC/USDT",
        side="buy",
        order_type=OrderType.MARKET,
        status=OrderStatus.SUBMITTED,
        size=0.1,
        filled_size=0.0,
        remaining_size=0.1,
    )
    defaults.update(kwargs)
    return Order(**defaults)


def _make_filled_order_result(**kwargs) -> OrderResult:
    """Create a successful filled OrderResult."""
    defaults = dict(
        success=True,
        order_id="order_1",
        filled_size=0.1,
        filled_price=50000.0,
        status="filled",
    )
    defaults.update(kwargs)
    return OrderResult(**defaults)


# ==================== TestOrderManager ====================


class TestOrderManager:
    """Tests for OrderManager."""

    @pytest.fixture
    def mock_trader(self):
        trader = AsyncMock()
        trader.exchange_name = "mock"
        trader.place_market_order = AsyncMock(
            return_value=_make_filled_order_result()
        )
        trader.place_limit_order = AsyncMock(
            return_value=OrderResult(
                success=True, order_id="limit_1", status="open"
            )
        )
        trader.place_stop_loss = AsyncMock(
            return_value=OrderResult(
                success=True, order_id="sl_1", status="open"
            )
        )
        trader.place_take_profit = AsyncMock(
            return_value=OrderResult(
                success=True, order_id="tp_1", status="open"
            )
        )
        trader.cancel_order = AsyncMock(return_value=True)
        trader.cancel_all_orders = AsyncMock(return_value=3)
        trader.get_order = AsyncMock(return_value=None)
        return trader

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.redis = AsyncMock()
        redis.redis.setex = AsyncMock()
        redis.redis.get = AsyncMock(return_value=None)
        redis.redis.sadd = AsyncMock()
        redis.redis.smembers = AsyncMock(return_value=set())
        redis.redis.delete = AsyncMock()
        return redis

    @pytest.fixture
    def manager(self, mock_trader, mock_redis):
        return OrderManager(
            trader=mock_trader,
            redis=mock_redis,
            strategy_id="strat_1",
        )

    # ---------- Initialisation ----------

    def test_init(self, mock_trader, mock_redis):
        mgr = OrderManager(
            trader=mock_trader,
            redis=mock_redis,
            strategy_id="s1",
        )
        assert mgr.trader is mock_trader
        assert mgr.redis is mock_redis
        assert mgr.strategy_id == "s1"
        assert mgr._orders == {}
        assert mgr._tracking_tasks == {}

    # ---------- Place Order ----------

    @pytest.mark.asyncio
    async def test_place_market_order_immediate_fill(self, manager, mock_trader):
        """Market order that fills immediately should have FILLED status."""
        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            order_type=OrderType.MARKET,
        )

        assert order.status == OrderStatus.FILLED
        assert order.filled_size == 0.1
        assert order.avg_fill_price == 50000.0
        mock_trader.place_market_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_place_limit_order(self, manager, mock_trader):
        """Limit order that stays open should be tracked."""
        order = await manager.place_order_with_tracking(
            symbol="ETH/USDT",
            side="sell",
            size=1.0,
            order_type=OrderType.LIMIT,
            price=4000.0,
        )

        assert order.order_id == "limit_1"
        assert order.status == OrderStatus.SUBMITTED
        mock_trader.place_limit_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_place_stop_loss_order(self, manager, mock_trader):
        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="sell",
            size=0.1,
            order_type=OrderType.STOP_LOSS,
            trigger_price=45000.0,
        )

        assert order.order_id == "sl_1"
        mock_trader.place_stop_loss.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_place_take_profit_order(self, manager, mock_trader):
        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="sell",
            size=0.1,
            order_type=OrderType.TAKE_PROFIT,
            trigger_price=60000.0,
        )

        assert order.order_id == "tp_1"
        mock_trader.place_take_profit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_place_order_failed(self, manager, mock_trader):
        """When exchange returns failure, order should be FAILED."""
        mock_trader.place_market_order.return_value = OrderResult(
            success=False, error="Insufficient margin"
        )

        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="buy",
            size=100.0,
            order_type=OrderType.MARKET,
        )

        assert order.status == OrderStatus.FAILED
        assert order.error_message == "Insufficient margin"

    @pytest.mark.asyncio
    async def test_place_order_trade_error(self, manager, mock_trader):
        """When trader raises TradeError, order should be FAILED."""
        mock_trader.place_market_order.side_effect = TradeError("API down")

        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            order_type=OrderType.MARKET,
        )

        assert order.status == OrderStatus.FAILED
        assert "API down" in order.error_message

    @pytest.mark.asyncio
    async def test_place_order_unexpected_error(self, manager, mock_trader):
        mock_trader.place_market_order.side_effect = RuntimeError("unexpected")

        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            order_type=OrderType.MARKET,
        )

        assert order.status == OrderStatus.FAILED
        assert "unexpected" in order.error_message

    @pytest.mark.asyncio
    async def test_limit_order_requires_price(self, manager, mock_trader):
        """Limit order without price should fail with TradeError."""
        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            order_type=OrderType.LIMIT,
            # No price provided
        )

        assert order.status == OrderStatus.FAILED
        assert "price" in order.error_message.lower()

    @pytest.mark.asyncio
    async def test_stop_loss_requires_trigger_price(self, manager, mock_trader):
        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="sell",
            size=0.1,
            order_type=OrderType.STOP_LOSS,
            # No trigger_price
        )

        assert order.status == OrderStatus.FAILED
        assert "trigger_price" in order.error_message.lower()

    @pytest.mark.asyncio
    async def test_take_profit_requires_trigger_price(self, manager, mock_trader):
        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="sell",
            size=0.1,
            order_type=OrderType.TAKE_PROFIT,
            # No trigger_price
        )

        assert order.status == OrderStatus.FAILED
        assert "trigger_price" in order.error_message.lower()

    @pytest.mark.asyncio
    async def test_place_order_partial_fill(self, manager, mock_trader):
        """Partial fill should set PARTIALLY_FILLED status."""
        mock_trader.place_market_order.return_value = OrderResult(
            success=True,
            order_id="partial_1",
            filled_size=0.05,
            filled_price=50000.0,
            status="partially_filled",
        )

        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            order_type=OrderType.MARKET,
        )

        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_size == 0.05
        assert order.remaining_size == 0.05

    # ---------- Cancel Order ----------

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, manager, mock_trader, mock_redis):
        """Cancel an open order."""
        order = _make_order(order_id="cancel_me", status=OrderStatus.SUBMITTED)
        manager._orders["cancel_me"] = order

        result = await manager.cancel_order("cancel_me")

        assert result.status == OrderStatus.CANCELLED
        assert result.cancelled_at is not None
        mock_trader.cancel_order.assert_awaited_once_with("BTC/USDT", "cancel_me")

    @pytest.mark.asyncio
    async def test_cancel_order_not_found(self, manager):
        with pytest.raises(TradeError) as exc_info:
            await manager.cancel_order("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_cancel_order_not_open(self, manager):
        """Cancelling a filled order should return it unchanged."""
        order = _make_order(order_id="filled_1", status=OrderStatus.FILLED)
        manager._orders["filled_1"] = order

        result = await manager.cancel_order("filled_1")

        assert result.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_cancel_order_with_callback(self, manager, mock_trader):
        callback_called = False

        async def on_cancel(order):
            nonlocal callback_called
            callback_called = True

        manager.callback = OrderCallback(on_cancel=on_cancel)

        order = _make_order(order_id="cb_cancel", status=OrderStatus.SUBMITTED)
        manager._orders["cb_cancel"] = order

        await manager.cancel_order("cb_cancel")
        assert callback_called is True

    # ---------- Cancel All Orders ----------

    @pytest.mark.asyncio
    async def test_cancel_all_orders(self, manager, mock_trader):
        count = await manager.cancel_all_orders(symbol="BTC/USDT")

        assert count == 3
        mock_trader.cancel_all_orders.assert_awaited_once_with("BTC/USDT")

    @pytest.mark.asyncio
    async def test_cancel_all_orders_no_symbol(self, manager, mock_trader):
        count = await manager.cancel_all_orders()

        assert count == 3
        mock_trader.cancel_all_orders.assert_awaited_once_with(None)

    # ---------- Get Orders ----------

    @pytest.mark.asyncio
    async def test_get_order_from_cache(self, manager):
        order = _make_order(order_id="cached_1")
        manager._orders["cached_1"] = order

        result = await manager.get_order("cached_1")
        assert result is order

    @pytest.mark.asyncio
    async def test_get_order_from_redis(self, manager, mock_redis):
        """Load order from Redis when not in local cache."""
        order_data = _make_order(order_id="redis_1").to_dict()
        mock_redis.redis.get.return_value = json.dumps(order_data).encode()

        result = await manager.get_order("redis_1")

        assert result is not None
        assert result.order_id == "redis_1"

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, manager, mock_redis):
        mock_redis.redis.get.return_value = None
        result = await manager.get_order("missing_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_pending_orders(self, manager, mock_redis):
        order1 = _make_order(order_id="pend_1", status=OrderStatus.SUBMITTED)
        order2 = _make_order(order_id="pend_2", status=OrderStatus.FILLED)
        manager._orders["pend_1"] = order1
        manager._orders["pend_2"] = order2

        mock_redis.redis.smembers.return_value = {b"pend_1", b"pend_2"}

        pending = await manager.get_pending_orders()

        # Only the open order should be returned
        assert len(pending) == 1
        assert pending[0].order_id == "pend_1"

    @pytest.mark.asyncio
    async def test_get_pending_orders_no_strategy(self, mock_trader, mock_redis):
        mgr = OrderManager(trader=mock_trader, redis=mock_redis, strategy_id=None)
        pending = await mgr.get_pending_orders()
        assert pending == []

    # ---------- Persistence ----------

    @pytest.mark.asyncio
    async def test_persist_order(self, manager, mock_redis):
        order = _make_order(order_id="persist_1")

        await manager._persist_order(order)

        mock_redis.redis.setex.assert_awaited_once()
        call_args = mock_redis.redis.setex.call_args
        assert call_args[0][0] == "order:persist_1"
        assert call_args[0][1] == 86400

        mock_redis.redis.sadd.assert_awaited_once_with(
            "orders:strategy:strat_1", "persist_1"
        )
        assert manager._orders["persist_1"] is order

    @pytest.mark.asyncio
    async def test_load_order_corrupt_data(self, manager, mock_redis):
        mock_redis.redis.get.return_value = b"not valid json"
        result = await manager._load_order("corrupt_1")
        assert result is None

    # ---------- Unsupported Order Type ----------

    @pytest.mark.asyncio
    async def test_unsupported_order_type(self, manager, mock_trader):
        """Unsupported order type should fail."""
        # Patch _submit_order to simulate the unsupported type path
        order = Order(
            order_id="",
            client_order_id="cl_test",
            symbol="BTC/USDT",
            side="buy",
            order_type=MagicMock(value="unsupported"),
            status=OrderStatus.PENDING,
            size=0.1,
            remaining_size=0.1,
        )
        # The code checks specific types; any other type falls through to else
        result = await manager._submit_order(order)
        assert result.status == OrderStatus.FAILED
        assert "Unsupported order type" in result.error_message

    # ---------- Wait for Fill ----------

    @pytest.mark.asyncio
    async def test_place_order_wait_for_fill(self, manager, mock_trader):
        """wait_for_fill=True on immediately filled order returns directly."""
        order = await manager.place_order_with_tracking(
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            order_type=OrderType.MARKET,
            wait_for_fill=True,
        )
        # Already filled, so wait_for_fill doesn't block
        assert order.status == OrderStatus.FILLED

    # ---------- Tracking ----------

    @pytest.mark.asyncio
    async def test_start_tracking_dedup(self, manager):
        """Starting tracking twice for same order does nothing."""
        import asyncio
        order = _make_order(order_id="track_1", status=OrderStatus.SUBMITTED)
        manager._orders["track_1"] = order

        task = asyncio.create_task(asyncio.sleep(100))
        manager._tracking_tasks["track_1"] = task

        manager._start_tracking(order)
        # Still the same task
        assert manager._tracking_tasks["track_1"] is task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_stop_tracking(self, manager):
        """_stop_tracking cancels and removes the task."""
        import asyncio
        task = asyncio.create_task(asyncio.sleep(100))
        manager._tracking_tasks["stop_me"] = task

        manager._stop_tracking("stop_me")
        assert "stop_me" not in manager._tracking_tasks
        # Allow event loop to process the cancellation
        await asyncio.sleep(0)
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_stop_tracking_nonexistent(self, manager):
        """_stop_tracking with no matching task does nothing."""
        manager._stop_tracking("nonexistent")
        assert "nonexistent" not in manager._tracking_tasks

    # ---------- Handle Status Change & Callbacks ----------

    @pytest.mark.asyncio
    async def test_handle_status_change_fill(self, manager):
        """Fill callback is triggered on FILLED status change."""
        fill_called = False

        async def on_fill(order):
            nonlocal fill_called
            fill_called = True

        manager.callback = OrderCallback(on_fill=on_fill)
        order = _make_order(order_id="fill_cb", status=OrderStatus.FILLED)

        await manager._handle_status_change(order, OrderStatus.SUBMITTED)
        assert fill_called is True

    @pytest.mark.asyncio
    async def test_handle_status_change_cancel(self, manager):
        """Cancel callback triggered on CANCELLED status."""
        cancel_called = False

        async def on_cancel(order):
            nonlocal cancel_called
            cancel_called = True

        manager.callback = OrderCallback(on_cancel=on_cancel)
        order = _make_order(order_id="cancel_cb", status=OrderStatus.CANCELLED)

        await manager._handle_status_change(order, OrderStatus.SUBMITTED)
        assert cancel_called is True

    @pytest.mark.asyncio
    async def test_handle_status_change_expired(self, manager):
        """Cancel callback also triggered on EXPIRED."""
        cancel_called = False

        async def on_cancel(order):
            nonlocal cancel_called
            cancel_called = True

        manager.callback = OrderCallback(on_cancel=on_cancel)
        order = _make_order(order_id="exp_cb", status=OrderStatus.EXPIRED)

        await manager._handle_status_change(order, OrderStatus.SUBMITTED)
        assert cancel_called is True

    @pytest.mark.asyncio
    async def test_handle_status_change_failed_with_retry(self, manager, mock_trader):
        """FAILED status with retries left should trigger retry."""
        mock_trader.place_market_order.return_value = OrderResult(
            success=False, error="Temp fail"
        )
        order = _make_order(
            order_id="retry_1",
            status=OrderStatus.FAILED,
        )
        order.retry_count = 0
        order.max_retries = 3
        manager._orders["retry_1"] = order

        # Patch sleep to avoid delay
        with patch("app.services.order_manager.asyncio.sleep", new_callable=AsyncMock):
            await manager._handle_status_change(order, OrderStatus.SUBMITTED)

        assert order.retry_count == 1

    @pytest.mark.asyncio
    async def test_handle_status_change_failed_no_retry_with_callback(self, manager):
        """FAILED with no retries left triggers error callback."""
        error_called = False

        async def on_error(order, msg):
            nonlocal error_called
            error_called = True

        manager.callback = OrderCallback(on_error=on_error)
        order = _make_order(order_id="fail_cb", status=OrderStatus.FAILED)
        order.retry_count = 3
        order.max_retries = 3
        order.error_message = "permanent"

        await manager._handle_status_change(order, OrderStatus.SUBMITTED)
        assert error_called is True

    @pytest.mark.asyncio
    async def test_handle_status_change_callback_exception(self, manager):
        """Callback exception should be caught, not propagated."""
        def on_fill(order):
            raise RuntimeError("callback boom")

        manager.callback = OrderCallback(on_fill=on_fill)
        order = _make_order(order_id="boom_cb", status=OrderStatus.FILLED)

        # Should not raise
        await manager._handle_status_change(order, OrderStatus.SUBMITTED)

    @pytest.mark.asyncio
    async def test_handle_status_change_partial_fill(self, manager):
        """Partial fill callback is triggered on PARTIALLY_FILLED status."""
        partial_called = False

        async def on_partial_fill(order):
            nonlocal partial_called
            partial_called = True

        manager.callback = OrderCallback(on_partial_fill=on_partial_fill)
        order = _make_order(
            order_id="partial_cb",
            status=OrderStatus.PARTIALLY_FILLED,
            filled_size=0.05,
            remaining_size=0.05,
        )

        await manager._handle_status_change(order, OrderStatus.SUBMITTED)
        assert partial_called is True

    @pytest.mark.asyncio
    async def test_cancel_order_callback_exception(self, manager, mock_trader):
        """Cancel callback exception should be caught."""
        def on_cancel(order):
            raise RuntimeError("cancel boom")

        manager.callback = OrderCallback(on_cancel=on_cancel)
        order = _make_order(order_id="cancel_boom", status=OrderStatus.SUBMITTED)
        manager._orders["cancel_boom"] = order

        # Should not raise
        result = await manager.cancel_order("cancel_boom")
        assert result.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_all_orders_stops_tracking(self, manager, mock_trader):
        """cancel_all_orders stops all tracking tasks."""
        import asyncio

        # Add tracking tasks
        task1 = asyncio.create_task(asyncio.sleep(100))
        task2 = asyncio.create_task(asyncio.sleep(100))
        manager._tracking_tasks["track_1"] = task1
        manager._tracking_tasks["track_2"] = task2

        await manager.cancel_all_orders(symbol="BTC/USDT")

        # All tracking tasks should be stopped
        assert len(manager._tracking_tasks) == 0

    @pytest.mark.asyncio
    async def test_retry_order_exponential_backoff(self, manager, mock_trader):
        """Retry uses exponential backoff delay."""
        # First retry should use BASE_RETRY_DELAY
        order = _make_order(order_id="backoff_1", status=OrderStatus.FAILED)
        order.retry_count = 0
        order.max_retries = 3
        manager._orders["backoff_1"] = order

        sleep_calls = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            sleep_calls.append(delay)
            # Don't actually sleep

        with patch("app.services.order_manager.asyncio.sleep", mock_sleep):
            await manager._retry_order(order)

        # Should have called sleep with base delay
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == manager.BASE_RETRY_DELAY

    @pytest.mark.asyncio
    async def test_retry_order_second_attempt(self, manager, mock_trader):
        """Second retry uses 2x base delay."""
        order = _make_order(order_id="backoff_2", status=OrderStatus.FAILED)
        order.retry_count = 1  # Already tried once
        order.max_retries = 3
        manager._orders["backoff_2"] = order

        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch("app.services.order_manager.asyncio.sleep", mock_sleep):
            await manager._retry_order(order)

        # 2^1 * BASE_RETRY_DELAY = 2.0
        assert sleep_calls[0] == manager.BASE_RETRY_DELAY * 2

    # ---------- Wait for Completion ----------

    @pytest.mark.asyncio
    async def test_wait_for_completion_already_complete(self, manager):
        """Returns immediately if order is already complete."""
        order = _make_order(order_id="done_1", status=OrderStatus.FILLED)
        manager._orders["done_1"] = order

        result = await manager.wait_for_completion("done_1", timeout=1.0)
        assert result.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_wait_for_completion_not_found(self, manager, mock_redis):
        """Raises TradeError if order not found."""
        mock_redis.redis.get.return_value = None

        with pytest.raises(TradeError, match="not found"):
            await manager.wait_for_completion("missing_1", timeout=1.0)

    @pytest.mark.asyncio
    async def test_wait_for_completion_timeout(self, manager):
        """Raises TradeError on timeout."""
        order = _make_order(order_id="timeout_1", status=OrderStatus.SUBMITTED)
        manager._orders["timeout_1"] = order

        with patch("app.services.order_manager.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(TradeError, match="Timeout"):
                await manager.wait_for_completion("timeout_1", timeout=0.001)

    # ---------- Maybe Await ----------

    @pytest.mark.asyncio
    async def test_maybe_await_coroutine(self):
        """_maybe_await properly awaits a coroutine."""
        async def coro():
            return 42

        result = await OrderManager._maybe_await(coro())
        assert result == 42

    @pytest.mark.asyncio
    async def test_maybe_await_non_coroutine(self):
        """_maybe_await returns non-coroutine directly."""
        result = await OrderManager._maybe_await("hello")
        assert result == "hello"

    # ---------- Persistence Edge Cases ----------

    @pytest.mark.asyncio
    async def test_persist_order_no_strategy_id(self, mock_trader, mock_redis):
        """No strategy_id -> sadd is not called."""
        mgr = OrderManager(trader=mock_trader, redis=mock_redis, strategy_id=None)
        order = _make_order(order_id="no_strat")

        await mgr._persist_order(order)

        mock_redis.redis.setex.assert_awaited_once()
        mock_redis.redis.sadd.assert_not_awaited()

    # ---------- Close ----------

    @pytest.mark.asyncio
    async def test_close(self, manager):
        order = _make_order(order_id="close_1")
        manager._orders["close_1"] = order

        await manager.close()

        assert manager._orders == {}
        assert manager._tracking_tasks == {}

    @pytest.mark.asyncio
    async def test_close_with_tracking_tasks(self, manager):
        """close() cancels tracking tasks."""
        import asyncio
        task = asyncio.create_task(asyncio.sleep(100))
        manager._tracking_tasks["task_1"] = task
        manager._orders["task_1"] = _make_order(order_id="task_1")

        await manager.close()
        assert len(manager._tracking_tasks) == 0
        assert len(manager._orders) == 0


# ==================== Factory ====================


class TestCreateOrderManager:
    @pytest.mark.asyncio
    async def test_create_order_manager(self):
        """Factory function should create OrderManager."""
        from app.services.order_manager import create_order_manager

        mock_trader = AsyncMock()
        mock_callback = OrderCallback()

        with patch(
            "app.services.order_manager.get_redis_service",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ):
            mgr = await create_order_manager(
                trader=mock_trader,
                strategy_id="test_strat",
                callback=mock_callback,
            )

        assert mgr.trader is mock_trader
        assert mgr.strategy_id == "test_strat"
        assert mgr.callback is mock_callback
