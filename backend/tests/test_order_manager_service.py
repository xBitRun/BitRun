"""
Tests for OrderManager service.

Covers: place_order_with_tracking, cancel_order, get_pending_orders,
        cancel_all_orders, close(), persistence.
"""

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

    # ---------- Close ----------

    @pytest.mark.asyncio
    async def test_close(self, manager):
        order = _make_order(order_id="close_1")
        manager._orders["close_1"] = order

        await manager.close()

        assert manager._orders == {}
        assert manager._tracking_tasks == {}
