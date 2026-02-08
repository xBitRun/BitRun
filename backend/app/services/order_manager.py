"""
Order Lifecycle Manager.

Provides comprehensive order management including:
- Order status tracking and polling
- Partial fill handling
- Failed order retry with exponential backoff
- Order persistence in Redis for recovery
- Notifications on order status changes
"""

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Literal, Optional

from ..core.config import get_settings
from ..services.redis_service import get_redis_service, RedisService
from ..traders.base import (
    BaseTrader,
    Order,
    OrderResult,
    OrderStatus,
    OrderType,
    TradeError,
)

logger = logging.getLogger(__name__)


class OrderCallback:
    """Callback for order status changes."""
    
    def __init__(
        self,
        on_fill: Optional[Callable[[Order], Any]] = None,
        on_partial_fill: Optional[Callable[[Order], Any]] = None,
        on_cancel: Optional[Callable[[Order], Any]] = None,
        on_error: Optional[Callable[[Order, str], Any]] = None,
    ):
        self.on_fill = on_fill
        self.on_partial_fill = on_partial_fill
        self.on_cancel = on_cancel
        self.on_error = on_error


class OrderManager:
    """
    Manages order lifecycle including tracking, retries, and persistence.
    
    Features:
    - Automatic order status polling
    - Retry failed orders with exponential backoff
    - Persist order state in Redis for recovery
    - Callbacks for order status changes
    - Partial fill handling
    
    Usage:
        manager = OrderManager(trader, redis)
        order = await manager.place_order_with_tracking(
            symbol="ETH",
            side="buy",
            size=0.1,
            order_type=OrderType.MARKET,
        )
        
        # Wait for completion
        final_order = await manager.wait_for_completion(order.order_id)
    """
    
    # Redis key prefixes
    PREFIX_ORDER = "order:"
    PREFIX_PENDING = "orders:pending:"
    PREFIX_STRATEGY = "orders:strategy:"
    
    # Retry settings
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 30.0  # seconds
    
    # Polling settings
    DEFAULT_POLL_INTERVAL = 2.0  # seconds
    DEFAULT_POLL_TIMEOUT = 60.0  # seconds
    
    def __init__(
        self,
        trader: BaseTrader,
        redis: RedisService,
        strategy_id: Optional[str] = None,
        callback: Optional[OrderCallback] = None,
    ):
        """
        Initialize OrderManager.
        
        Args:
            trader: Exchange trader instance
            redis: Redis service for persistence
            strategy_id: Optional strategy ID for grouping orders
            callback: Optional callback for order events
        """
        self.trader = trader
        self.redis = redis
        self.strategy_id = strategy_id
        self.callback = callback or OrderCallback()
        
        self._tracking_tasks: dict[str, asyncio.Task] = {}
        self._orders: dict[str, Order] = {}  # In-memory cache
    
    # ==================== Order Placement ====================
    
    async def place_order_with_tracking(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        leverage: int = 1,
        reduce_only: bool = False,
        post_only: bool = False,
        slippage: Optional[float] = None,
        auto_retry: bool = True,
        wait_for_fill: bool = False,
        fill_timeout: float = DEFAULT_POLL_TIMEOUT,
    ) -> Order:
        """
        Place an order with full lifecycle tracking.
        
        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            size: Order size
            order_type: Order type (market, limit, etc.)
            price: Limit price (required for limit orders)
            trigger_price: Trigger price for stop/TP orders
            leverage: Leverage multiplier
            reduce_only: If True, only reduces position
            post_only: If True, only posts to orderbook
            slippage: Slippage tolerance (for market orders)
            auto_retry: Automatically retry failed orders
            wait_for_fill: Block until order fills or fails
            fill_timeout: Timeout for waiting for fill
            
        Returns:
            Order object with current status
            
        Raises:
            TradeError: If order placement fails
        """
        # Generate client order ID for tracking
        client_order_id = f"cl_{uuid.uuid4().hex[:16]}"
        
        # Create initial order object
        order = Order(
            order_id="",  # Will be set after submission
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=OrderStatus.PENDING,
            size=size,
            remaining_size=size,
            price=price,
            trigger_price=trigger_price,
            leverage=leverage,
            reduce_only=reduce_only,
            post_only=post_only,
            max_retries=self.MAX_RETRIES if auto_retry else 0,
        )
        
        # Place the order
        order = await self._submit_order(order, slippage)
        
        # Persist order state
        await self._persist_order(order)
        
        # Start tracking if order is open
        if order.is_open:
            self._start_tracking(order)
        
        # Wait for fill if requested
        if wait_for_fill and order.is_open:
            order = await self.wait_for_completion(
                order.order_id,
                timeout=fill_timeout,
            )
        
        return order
    
    async def _submit_order(
        self,
        order: Order,
        slippage: Optional[float] = None,
    ) -> Order:
        """
        Submit order to exchange.
        
        Updates order object with result.
        """
        try:
            result: OrderResult
            
            if order.order_type == OrderType.MARKET:
                result = await self.trader.place_market_order(
                    symbol=order.symbol,
                    side=order.side,
                    size=order.size,
                    leverage=order.leverage,
                    reduce_only=order.reduce_only,
                    slippage=slippage,
                )
            elif order.order_type == OrderType.LIMIT:
                if order.price is None:
                    raise TradeError("Limit order requires price")
                result = await self.trader.place_limit_order(
                    symbol=order.symbol,
                    side=order.side,
                    size=order.size,
                    price=order.price,
                    leverage=order.leverage,
                    reduce_only=order.reduce_only,
                    post_only=order.post_only,
                )
            elif order.order_type == OrderType.STOP_LOSS:
                if order.trigger_price is None:
                    raise TradeError("Stop loss order requires trigger_price")
                result = await self.trader.place_stop_loss(
                    symbol=order.symbol,
                    side=order.side,
                    size=order.size,
                    trigger_price=order.trigger_price,
                    reduce_only=order.reduce_only,
                )
            elif order.order_type == OrderType.TAKE_PROFIT:
                if order.trigger_price is None:
                    raise TradeError("Take profit order requires trigger_price")
                result = await self.trader.place_take_profit(
                    symbol=order.symbol,
                    side=order.side,
                    size=order.size,
                    trigger_price=order.trigger_price,
                    reduce_only=order.reduce_only,
                )
            else:
                raise TradeError(f"Unsupported order type: {order.order_type}")
            
            # Update order with result
            order.updated_at = datetime.now(UTC)
            
            if result.success:
                order.order_id = result.order_id or order.client_order_id
                order.status = OrderStatus.SUBMITTED
                
                # Handle immediate fills (common for market orders)
                if result.filled_size and result.filled_size > 0:
                    order.filled_size = result.filled_size
                    order.remaining_size = order.size - result.filled_size
                    order.avg_fill_price = result.filled_price
                    
                    if order.remaining_size <= 0:
                        order.status = OrderStatus.FILLED
                        order.filled_at = datetime.now(UTC)
                    else:
                        order.status = OrderStatus.PARTIALLY_FILLED
                
                order.raw_data = result.raw_response
                
                logger.info(
                    f"Order submitted: {order.order_id} {order.symbol} "
                    f"{order.side} {order.size} @ {order.price or 'market'} "
                    f"-> {order.status.value}"
                )
            else:
                order.status = OrderStatus.FAILED
                order.error_message = result.error
                
                logger.warning(
                    f"Order failed: {order.symbol} {order.side} {order.size} "
                    f"-> {result.error}"
                )
            
            return order
            
        except TradeError as e:
            order.status = OrderStatus.FAILED
            order.error_message = e.message
            order.updated_at = datetime.now(UTC)
            
            logger.error(f"Order submission error: {e.message}")
            return order
        
        except Exception as e:
            order.status = OrderStatus.FAILED
            order.error_message = str(e)
            order.updated_at = datetime.now(UTC)
            
            logger.exception(f"Unexpected error submitting order: {e}")
            return order
    
    # ==================== Order Tracking ====================
    
    def _start_tracking(self, order: Order) -> None:
        """Start background task to track order status."""
        if order.order_id in self._tracking_tasks:
            return
        
        task = asyncio.create_task(self._track_order(order))
        self._tracking_tasks[order.order_id] = task
    
    def _stop_tracking(self, order_id: str) -> None:
        """Stop tracking an order."""
        task = self._tracking_tasks.pop(order_id, None)
        if task and not task.done():
            task.cancel()
    
    async def _track_order(self, order: Order) -> None:
        """
        Background task to poll order status.
        
        Updates order status and triggers callbacks on changes.
        """
        poll_interval = self.DEFAULT_POLL_INTERVAL
        last_status = order.status
        last_filled = order.filled_size
        
        try:
            while order.is_open:
                await asyncio.sleep(poll_interval)
                
                try:
                    # Get updated order from exchange
                    updated = await self.trader.get_order(order.symbol, order.order_id)
                    
                    if updated is None:
                        # Order not found, might be filled immediately
                        logger.warning(f"Order {order.order_id} not found, stopping tracking")
                        break
                    
                    # Update local order
                    order.status = updated.status
                    order.filled_size = updated.filled_size
                    order.remaining_size = updated.remaining_size
                    order.avg_fill_price = updated.avg_fill_price
                    order.fee = updated.fee
                    order.updated_at = datetime.now(UTC)
                    
                    if updated.filled_at:
                        order.filled_at = updated.filled_at
                    if updated.cancelled_at:
                        order.cancelled_at = updated.cancelled_at
                    
                    # Persist updated state
                    await self._persist_order(order)
                    
                    # Trigger callbacks on status change
                    if order.status != last_status:
                        await self._handle_status_change(order, last_status)
                        last_status = order.status
                    
                    # Trigger partial fill callback
                    if order.filled_size > last_filled and order.status == OrderStatus.PARTIALLY_FILLED:
                        if self.callback.on_partial_fill:
                            try:
                                await self._maybe_await(self.callback.on_partial_fill(order))
                            except Exception as e:
                                logger.error(f"Partial fill callback error: {e}")
                        last_filled = order.filled_size
                    
                except Exception as e:
                    logger.error(f"Error polling order {order.order_id}: {e}")
                    # Continue polling despite errors
        
        except asyncio.CancelledError:
            logger.debug(f"Order tracking cancelled: {order.order_id}")
        
        finally:
            self._tracking_tasks.pop(order.order_id, None)
    
    async def _handle_status_change(self, order: Order, old_status: OrderStatus) -> None:
        """Handle order status change and trigger callbacks."""
        logger.info(
            f"Order {order.order_id} status changed: "
            f"{old_status.value} -> {order.status.value}"
        )
        
        if order.status == OrderStatus.FILLED:
            if self.callback.on_fill:
                try:
                    await self._maybe_await(self.callback.on_fill(order))
                except Exception as e:
                    logger.error(f"Fill callback error: {e}")
        
        elif order.status in (OrderStatus.CANCELLED, OrderStatus.EXPIRED):
            if self.callback.on_cancel:
                try:
                    await self._maybe_await(self.callback.on_cancel(order))
                except Exception as e:
                    logger.error(f"Cancel callback error: {e}")
        
        elif order.status in (OrderStatus.FAILED, OrderStatus.REJECTED):
            # Handle retry
            if order.can_retry:
                logger.info(f"Retrying order {order.order_id} (attempt {order.retry_count + 1})")
                await self._retry_order(order)
            elif self.callback.on_error:
                try:
                    await self._maybe_await(
                        self.callback.on_error(order, order.error_message or "Unknown error")
                    )
                except Exception as e:
                    logger.error(f"Error callback error: {e}")
    
    async def _retry_order(self, order: Order) -> None:
        """
        Retry a failed order with exponential backoff.
        """
        order.retry_count += 1
        
        # Calculate delay with exponential backoff
        delay = min(
            self.BASE_RETRY_DELAY * (2 ** (order.retry_count - 1)),
            self.MAX_RETRY_DELAY,
        )
        
        logger.info(f"Waiting {delay}s before retry {order.retry_count}")
        await asyncio.sleep(delay)
        
        # Reset status and resubmit
        order.status = OrderStatus.PENDING
        order.error_message = None
        order = await self._submit_order(order)
        
        # Persist and track
        await self._persist_order(order)
        
        if order.is_open:
            self._start_tracking(order)
    
    # ==================== Order Waiting ====================
    
    async def wait_for_completion(
        self,
        order_id: str,
        timeout: float = DEFAULT_POLL_TIMEOUT,
    ) -> Order:
        """
        Wait for an order to reach a terminal state.
        
        Args:
            order_id: Order ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Final order state
            
        Raises:
            TradeError: If timeout exceeded
        """
        start = datetime.now(UTC)
        
        while True:
            order = await self.get_order(order_id)
            
            if order is None:
                raise TradeError(
                    f"Order {order_id} not found",
                    code="ORDER_NOT_FOUND",
                )
            
            if order.is_complete:
                return order
            
            elapsed = (datetime.now(UTC) - start).total_seconds()
            if elapsed >= timeout:
                raise TradeError(
                    f"Timeout waiting for order {order_id}",
                    code="ORDER_TIMEOUT",
                    details={"order": order.to_dict()},
                )
            
            await asyncio.sleep(self.DEFAULT_POLL_INTERVAL)
    
    # ==================== Order Retrieval ====================
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID.
        
        Checks local cache first, then Redis.
        """
        # Check local cache
        if order_id in self._orders:
            return self._orders[order_id]
        
        # Check Redis
        order = await self._load_order(order_id)
        if order:
            self._orders[order_id] = order
        
        return order
    
    async def get_pending_orders(self) -> list[Order]:
        """Get all pending orders for this strategy."""
        if not self.strategy_id:
            return []
        
        key = f"{self.PREFIX_STRATEGY}{self.strategy_id}"
        order_ids = await self.redis.redis.smembers(key)
        
        orders = []
        for oid in order_ids:
            order = await self.get_order(oid.decode() if isinstance(oid, bytes) else oid)
            if order and order.is_open:
                orders.append(order)
        
        return orders
    
    # ==================== Order Cancellation ====================
    
    async def cancel_order(self, order_id: str) -> Order:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Updated order with cancelled status
        """
        order = await self.get_order(order_id)
        
        if order is None:
            raise TradeError(f"Order {order_id} not found", code="ORDER_NOT_FOUND")
        
        if not order.is_open:
            logger.warning(f"Order {order_id} is not open (status: {order.status})")
            return order
        
        # Stop tracking
        self._stop_tracking(order_id)
        
        # Cancel on exchange
        success = await self.trader.cancel_order(order.symbol, order_id)
        
        if success:
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = datetime.now(UTC)
            order.updated_at = datetime.now(UTC)
            
            await self._persist_order(order)
            
            if self.callback.on_cancel:
                try:
                    await self._maybe_await(self.callback.on_cancel(order))
                except Exception as e:
                    logger.error(f"Cancel callback error: {e}")
        
        return order
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """
        Cancel all open orders.
        
        Args:
            symbol: If provided, only cancel orders for this symbol
            
        Returns:
            Number of orders cancelled
        """
        count = await self.trader.cancel_all_orders(symbol)
        
        # Stop all tracking tasks
        for order_id in list(self._tracking_tasks.keys()):
            self._stop_tracking(order_id)
        
        return count
    
    # ==================== Persistence ====================
    
    async def _persist_order(self, order: Order) -> None:
        """Persist order state to Redis."""
        key = f"{self.PREFIX_ORDER}{order.order_id}"
        
        data = order.to_dict()
        data["strategy_id"] = self.strategy_id
        
        await self.redis.redis.setex(
            key,
            86400,  # 24 hour TTL
            json.dumps(data),
        )
        
        # Add to strategy's order set
        if self.strategy_id:
            strategy_key = f"{self.PREFIX_STRATEGY}{self.strategy_id}"
            await self.redis.redis.sadd(strategy_key, order.order_id)
        
        # Update local cache
        self._orders[order.order_id] = order
    
    async def _load_order(self, order_id: str) -> Optional[Order]:
        """Load order from Redis."""
        key = f"{self.PREFIX_ORDER}{order_id}"
        
        data = await self.redis.redis.get(key)
        if not data:
            return None
        
        try:
            order_dict = json.loads(data.decode() if isinstance(data, bytes) else data)
            return Order.from_dict(order_dict)
        except Exception as e:
            logger.error(f"Failed to load order {order_id}: {e}")
            return None
    
    # ==================== Cleanup ====================
    
    async def close(self) -> None:
        """Stop all tracking and cleanup."""
        for order_id in list(self._tracking_tasks.keys()):
            self._stop_tracking(order_id)
        
        self._orders.clear()
    
    # ==================== Utilities ====================
    
    @staticmethod
    async def _maybe_await(result: Any) -> Any:
        """Await result if it's a coroutine."""
        if asyncio.iscoroutine(result):
            return await result
        return result


async def create_order_manager(
    trader: BaseTrader,
    strategy_id: Optional[str] = None,
    callback: Optional[OrderCallback] = None,
) -> OrderManager:
    """
    Factory function to create an OrderManager.
    
    Args:
        trader: Exchange trader instance
        strategy_id: Optional strategy ID for grouping orders
        callback: Optional callback for order events
        
    Returns:
        Configured OrderManager instance
    """
    redis = await get_redis_service()
    
    return OrderManager(
        trader=trader,
        redis=redis,
        strategy_id=strategy_id,
        callback=callback,
    )
