"""
Quantitative Strategy Execution Engines.

Implements rule-based trading strategies:
- GridEngine: Grid trading with buy/sell order grids
- DCAEngine: Dollar-cost averaging with scheduled orders
- RSIEngine: RSI indicator-based buy/sell signals

Each engine implements run_cycle() which is called periodically
by the QuantExecutionWorker.
"""

import logging
import math
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Optional

from ..traders.base import BaseTrader, OrderResult, TradeError
from .position_service import (
    CapitalExceededError,
    PositionConflictError,
    PositionService,
)

logger = logging.getLogger(__name__)


class QuantEngineBase(ABC):
    """
    Base class for all quantitative strategy engines.

    Each engine receives the trader (exchange adapter) and strategy
    configuration, then executes trading logic in run_cycle().
    """

    def __init__(
        self,
        agent_id: str,
        trader: BaseTrader,
        symbol: str,
        config: dict,
        runtime_state: dict,
        account_id: Optional[str] = None,
        position_service: Optional[PositionService] = None,
        strategy: Optional[object] = None,
    ):
        # Note: agent_id is AgentDB.id (QuantStrategyDB is alias for AgentDB)
        self.agent_id = agent_id
        self.trader = trader
        self.symbol = symbol
        self.config = config
        self.runtime_state = runtime_state or {}
        self.account_id = account_id
        self.position_service = position_service
        self.strategy = strategy  # QuantStrategyDB instance for capital checks
        self._cached_account_equity: Optional[float] = None

    # ------------------------------------------------------------------
    # Position isolation helpers for subclasses
    # ------------------------------------------------------------------

    async def _open_with_isolation(
        self,
        size_usd: float,
        leverage: int = 1,
        side: str = "long",
    ) -> OrderResult:
        """
        Open (or add to) a position with strategy-level isolation.

        Returns the full OrderResult so callers have access to
        filled_size and filled_price for accurate state tracking.

        Handles position accumulation: if the strategy already owns an
        open position on this symbol, the order is placed and the
        existing DB record is updated (accumulated) rather than creating
        a new claim.
        """
        ps = self.position_service
        claim = None
        is_existing_position = False  # True when accumulating onto open record

        if ps and self.account_id:
            try:
                if self.strategy and hasattr(self.strategy, "get_effective_capital"):
                    # Use capital-checked claim when strategy object is
                    # available (enforces allocated_capital limits).
                    # Cache equity per engine instance (= per cycle) to
                    # avoid hitting the exchange API on every grid level.
                    if self._cached_account_equity is None:
                        account_state = await self.trader.get_account_state()
                        self._cached_account_equity = account_state.equity
                    claim = await ps.claim_position_with_capital_check(
                        strategy_id=uuid.UUID(self.agent_id),
                        strategy_type="quant",
                        account_id=uuid.UUID(self.account_id),
                        symbol=self.symbol,
                        side=side,
                        leverage=leverage,
                        account_equity=self._cached_account_equity,
                        requested_size_usd=size_usd,
                        strategy=self.strategy,
                    )
                else:
                    # Fallback: no capital check (backward compatible)
                    claim = await ps.claim_position(
                        strategy_id=uuid.UUID(self.agent_id),
                        strategy_type="quant",
                        account_id=uuid.UUID(self.account_id),
                        symbol=self.symbol,
                        side=side,
                        leverage=leverage,
                    )
                # If the returned record is already open, this is an
                # accumulation (e.g. DCA adding to position, Grid buying
                # another level).  We must NOT release/delete it on failure.
                is_existing_position = claim.status == "open"
            except CapitalExceededError as e:
                logger.warning(
                    f"Quant {self.agent_id}: capital exceeded for "
                    f"{self.symbol}: {e}"
                )
                return OrderResult(
                    success=False,
                    error=f"Capital exceeded: {e}",
                )
            except PositionConflictError as e:
                logger.warning(
                    f"Quant {self.agent_id}: symbol conflict for "
                    f"{self.symbol}: {e}"
                )
                return OrderResult(
                    success=False,
                    error=f"Symbol conflict: {e}",
                )

        try:
            if side == "long":
                result = await self.trader.open_long(
                    symbol=self.symbol,
                    size_usd=size_usd,
                    leverage=leverage,
                )
            else:
                result = await self.trader.open_short(
                    symbol=self.symbol,
                    size_usd=size_usd,
                    leverage=leverage,
                )
        except Exception:
            if ps and claim and not is_existing_position:
                should_release = True
                try:
                    pos = await self.trader.get_position(self.symbol)
                    if pos and pos.size > 0:
                        logger.warning(
                            f"Quant {self.agent_id}: exception during order "
                            f"for {self.symbol} but exchange shows position. "
                            "Confirming claim."
                        )
                        try:
                            await ps.confirm_position(
                                position_id=claim.id,
                                size=pos.size,
                                size_usd=pos.size_usd,
                                entry_price=pos.entry_price,
                            )
                        except Exception:
                            logger.critical(
                                f"Quant {self.agent_id}: failed to confirm "
                                f"claim {claim.id} for {self.symbol}."
                            )
                        should_release = False
                except Exception as inner_exc:
                    logger.warning(
                        f"Quant {self.agent_id}: failed to check position "
                        f"for {self.symbol} after order exception: {inner_exc}"
                    )
                if should_release:
                    await ps.release_claim(claim.id)
            # For existing positions, do NOT release on exception –
            # the position still exists on the exchange.
            raise

        if ps and claim:
            if result.success:
                estimated_size = result.filled_size or (
                    size_usd / (result.filled_price or 1.0)
                )
                fill_price = result.filled_price or 0.0

                try:
                    if is_existing_position:
                        # Accumulate: add to existing open record
                        await ps.accumulate_position(
                            position_id=claim.id,
                            additional_size=result.filled_size or estimated_size,
                            additional_size_usd=size_usd,
                            fill_price=fill_price,
                        )
                    else:
                        # First open: transition pending → open
                        await ps.confirm_position(
                            position_id=claim.id,
                            size=result.filled_size or estimated_size,
                            size_usd=size_usd,
                            entry_price=fill_price,
                        )
                except Exception as confirm_err:
                    logger.critical(
                        f"Quant {self.agent_id}: position DB update FAILED "
                        f"after successful order for {self.symbol} "
                        f"(claim {claim.id}): {confirm_err}. "
                        "Leaving for reconciliation."
                    )
            elif not is_existing_position:
                # Only release pending claims – never delete open records
                await ps.release_claim(claim.id)

        return result

    async def _close_with_isolation(self) -> OrderResult:
        """
        Close the strategy's position with isolation tracking.

        Returns the full OrderResult so callers have access to
        close price and other fill details.
        """
        ps = self.position_service
        pos_record = None

        if ps:
            pos_record = await ps.get_strategy_position_for_symbol(
                uuid.UUID(self.agent_id), self.symbol
            )

        result = await self.trader.close_position(symbol=self.symbol)

        if ps and pos_record and result.success:
            await ps.close_position_record(
                position_id=pos_record.id,
                close_price=result.filled_price or 0.0,
            )

        return result

    @abstractmethod
    async def run_cycle(self) -> dict:
        """
        Execute one cycle of the strategy.

        Returns:
            dict with keys:
                - success: bool
                - trades_executed: int
                - pnl_change: float
                - updated_state: dict (new runtime_state to persist)
                - message: str (human-readable summary)
        """
        pass

    async def _get_current_price(self) -> float:
        """Get the current market price for the symbol.

        Raises TradeError if the price is invalid (zero/negative/None).
        """
        market_data = await self.trader.get_market_data(self.symbol)
        price = market_data.mid_price
        if not price or price <= 0:
            raise TradeError(
                f"Invalid market price for {self.symbol}: {price}",
                code="INVALID_PRICE",
            )
        return price


class GridEngine(QuantEngineBase):
    """
    Grid Trading Engine.

    Creates a grid of buy and sell orders within a price range.
    Profits from price oscillation within the range.

    Config:
        upper_price: float - Upper boundary
        lower_price: float - Lower boundary
        grid_count: int - Number of grid levels
        total_investment: float - Total investment amount (USD)
        leverage: float - Leverage multiplier (default 1.0)
    """

    async def run_cycle(self) -> dict:
        trades_executed = 0
        pnl_change = 0.0
        total_size_usd = 0.0  # Track total position size for this cycle

        try:
            upper_price = self.config["upper_price"]
            lower_price = self.config["lower_price"]
            grid_count = self.config["grid_count"]
            total_investment = self.config["total_investment"]
            leverage = self.config.get("leverage", 1.0)

            # Config safety checks
            if upper_price <= lower_price:
                return {
                    "success": False, "trades_executed": 0, "pnl_change": 0.0,
                    "updated_state": self.runtime_state,
                    "message": "Error: upper_price must be > lower_price",
                }
            if grid_count < 1:
                return {
                    "success": False, "trades_executed": 0, "pnl_change": 0.0,
                    "updated_state": self.runtime_state,
                    "message": "Error: grid_count must be >= 1",
                }

            # Calculate grid spacing
            grid_step = (upper_price - lower_price) / grid_count
            amount_per_grid = total_investment / grid_count

            # Get current price
            current_price = await self._get_current_price()

            # Initialize state on first run or when config changes
            config_hash = f"{upper_price}:{lower_price}:{grid_count}"
            if (
                not self.runtime_state.get("initialized")
                or self.runtime_state.get("config_hash") != config_hash
            ):
                self.runtime_state = {
                    "initialized": True,
                    "config_hash": config_hash,
                    "grid_levels": [],
                    "filled_buys": [],
                    "filled_sells": [],
                    "total_invested": 0.0,
                    "total_returned": 0.0,
                }

                # Calculate grid levels
                for i in range(grid_count + 1):
                    price = lower_price + i * grid_step
                    self.runtime_state["grid_levels"].append(round(price, 2))

            grid_levels = self.runtime_state["grid_levels"]
            filled_buys = set(self.runtime_state.get("filled_buys", []))
            filled_sells = set(self.runtime_state.get("filled_sells", []))

            # Check each grid level
            for i, level in enumerate(grid_levels):
                level_key = str(i)

                # Buy signal: price dropped below this grid level and not yet bought
                if current_price <= level and level_key not in filled_buys:
                    try:
                        size_usd = amount_per_grid
                        open_result = await self._open_with_isolation(
                            size_usd=size_usd,
                            leverage=int(leverage),
                            side="long",
                        )
                        if open_result.success:
                            filled_buys.add(level_key)
                            trades_executed += 1
                            total_size_usd += size_usd  # Track total size
                            self.runtime_state["total_invested"] += size_usd
                            logger.info(
                                f"Grid {self.agent_id}: BUY at grid level {level} "
                                f"(current: {current_price}, "
                                f"filled@{open_result.filled_price or current_price:.2f}, "
                                f"size: ${size_usd:.2f})"
                            )
                    except TradeError as e:
                        logger.warning(f"Grid trade error at level {level}: {e}")

                # Sell signal: price rose above this grid level + one step, and was bought
                elif current_price >= level + grid_step and level_key in filled_buys and level_key not in filled_sells:
                    try:
                        size_usd = amount_per_grid
                        close_result = await self._close_with_isolation()
                        if close_result.success:
                            filled_sells.add(level_key)
                            trades_executed += 1
                            total_size_usd += size_usd  # Track total size
                            profit = size_usd * (grid_step / level) if level > 0 else 0
                            pnl_change += profit
                            self.runtime_state["total_returned"] += size_usd + profit
                            logger.info(
                                f"Grid {self.agent_id}: SELL at grid level {level} "
                                f"(current: {current_price}, profit: ${profit:.2f})"
                            )
                    except TradeError as e:
                        logger.warning(f"Grid sell error at level {level}: {e}")

            # Update runtime state
            self.runtime_state["filled_buys"] = list(filled_buys)
            self.runtime_state["filled_sells"] = list(filled_sells)
            self.runtime_state["last_price"] = current_price
            self.runtime_state["last_check"] = datetime.now(UTC).isoformat()

            return {
                "success": True,
                "trades_executed": trades_executed,
                "pnl_change": pnl_change,
                "total_size_usd": total_size_usd,
                "updated_state": self.runtime_state,
                "message": f"Grid check: price={current_price:.2f}, trades={trades_executed}",
            }

        except Exception as e:
            logger.error(f"Grid engine error for {self.agent_id}: {e}")
            return {
                "success": False,
                "trades_executed": 0,
                "pnl_change": 0.0,
                "total_size_usd": 0.0,
                "updated_state": self.runtime_state,
                "message": f"Error: {str(e)}",
            }


class DCAEngine(QuantEngineBase):
    """
    Dollar-Cost Averaging Engine.

    Places periodic buy orders at fixed intervals to average the entry price.
    Sells when take-profit target is reached.

    Config:
        order_amount: float - Amount per order (USD)
        interval_minutes: int - Time between orders
        take_profit_percent: float - Take profit percentage
        total_budget: float - Total budget limit (0 = unlimited)
        max_orders: int - Maximum number of orders (0 = unlimited)
    """

    async def run_cycle(self) -> dict:
        trades_executed = 0
        pnl_change = 0.0
        total_size_usd = 0.0  # Track total position size for this cycle

        try:
            order_amount = self.config["order_amount"]
            take_profit_pct = self.config.get("take_profit_percent", 5.0)
            total_budget = self.config.get("total_budget", 0)
            max_orders = self.config.get("max_orders", 0)

            current_price = await self._get_current_price()

            # Initialize state
            if not self.runtime_state.get("initialized"):
                self.runtime_state = {
                    "initialized": True,
                    "orders_placed": 0,
                    "total_invested": 0.0,
                    "total_quantity": 0.0,
                    "avg_cost": 0.0,
                    "last_order_time": None,
                }

            orders_placed = self.runtime_state.get("orders_placed", 0)
            total_invested = self.runtime_state.get("total_invested", 0.0)
            total_quantity = self.runtime_state.get("total_quantity", 0.0)
            avg_cost = self.runtime_state.get("avg_cost", 0.0)

            # Check if we should take profit
            if total_quantity > 0 and avg_cost > 0:
                current_pnl_pct = ((current_price - avg_cost) / avg_cost) * 100
                if current_pnl_pct >= take_profit_pct:
                    # Take profit - sell all
                    try:
                        sell_value = total_quantity * current_price
                        close_result = await self._close_with_isolation()
                        if not close_result.success:
                            raise TradeError("Close position failed")
                        pnl_change = sell_value - total_invested
                        trades_executed += 1
                        total_size_usd += sell_value  # Track total size
                        logger.info(
                            f"DCA {self.agent_id}: TAKE PROFIT at {current_price:.2f} "
                            f"(avg_cost: {avg_cost:.2f}, pnl: ${pnl_change:.2f}, "
                            f"+{current_pnl_pct:.1f}%)"
                        )
                        # Reset state
                        self.runtime_state["total_invested"] = 0.0
                        self.runtime_state["total_quantity"] = 0.0
                        self.runtime_state["avg_cost"] = 0.0
                        self.runtime_state["last_check"] = datetime.now(UTC).isoformat()
                        return {
                            "success": True,
                            "trades_executed": trades_executed,
                            "pnl_change": pnl_change,
                            "total_size_usd": total_size_usd,
                            "updated_state": self.runtime_state,
                            "message": f"Take profit: +{current_pnl_pct:.1f}%, P/L: ${pnl_change:.2f}",
                        }
                    except TradeError as e:
                        logger.warning(f"DCA take profit error: {e}")

            # Check budget and order limits
            if total_budget > 0 and total_invested >= total_budget:
                return {
                    "success": True,
                    "trades_executed": 0,
                    "pnl_change": 0.0,
                    "updated_state": self.runtime_state,
                    "message": "Budget limit reached, waiting for take profit",
                }

            if max_orders > 0 and orders_placed >= max_orders:
                return {
                    "success": True,
                    "trades_executed": 0,
                    "pnl_change": 0.0,
                    "updated_state": self.runtime_state,
                    "message": "Max orders reached, waiting for take profit",
                }

            # Enforce interval: skip if last order was too recent
            interval_minutes = self.config.get("interval_minutes", 60)
            last_order_time_str = self.runtime_state.get("last_order_time")
            if last_order_time_str:
                try:
                    last_order_time = datetime.fromisoformat(last_order_time_str)
                    elapsed = (datetime.now(UTC) - last_order_time.replace(tzinfo=UTC)).total_seconds()
                    if elapsed < interval_minutes * 60:
                        self.runtime_state["last_check"] = datetime.now(UTC).isoformat()
                        return {
                            "success": True,
                            "trades_executed": 0,
                            "pnl_change": 0.0,
                            "updated_state": self.runtime_state,
                            "message": f"Waiting for interval ({interval_minutes}min), "
                                       f"elapsed={elapsed/60:.1f}min",
                        }
                except (ValueError, TypeError):
                    pass  # Malformed timestamp, proceed with order

            # Place a buy order
            try:
                open_result = await self._open_with_isolation(
                    size_usd=order_amount,
                    leverage=1,
                    side="long",
                )
                if not open_result.success:
                    raise TradeError("Open position failed or symbol conflict")
                trades_executed += 1
                total_size_usd += order_amount  # Track total size

                # Use actual fill data when available
                actual_price = open_result.filled_price or current_price
                quantity = open_result.filled_size or (order_amount / actual_price)

                # Update running average
                new_total_invested = total_invested + order_amount
                new_total_quantity = total_quantity + quantity
                new_avg_cost = new_total_invested / new_total_quantity if new_total_quantity > 0 else actual_price

                self.runtime_state["orders_placed"] = orders_placed + 1
                self.runtime_state["total_invested"] = new_total_invested
                self.runtime_state["total_quantity"] = new_total_quantity
                self.runtime_state["avg_cost"] = new_avg_cost
                self.runtime_state["last_order_time"] = datetime.now(UTC).isoformat()

                logger.info(
                    f"DCA {self.agent_id}: BUY ${order_amount} at {current_price:.2f} "
                    f"(avg_cost: {new_avg_cost:.2f}, total: ${new_total_invested:.2f})"
                )

            except TradeError as e:
                logger.warning(f"DCA buy error: {e}")

            self.runtime_state["last_check"] = datetime.now(UTC).isoformat()

            return {
                "success": True,
                "trades_executed": trades_executed,
                "pnl_change": pnl_change,
                "total_size_usd": total_size_usd,
                "updated_state": self.runtime_state,
                "message": f"DCA cycle: price={current_price:.2f}, orders={orders_placed + trades_executed}",
            }

        except Exception as e:
            logger.error(f"DCA engine error for {self.agent_id}: {e}")
            return {
                "success": False,
                "trades_executed": 0,
                "pnl_change": 0.0,
                "total_size_usd": 0.0,
                "updated_state": self.runtime_state,
                "message": f"Error: {str(e)}",
            }


class RSIEngine(QuantEngineBase):
    """
    RSI-Based Trading Engine.

    Buys when RSI drops below oversold threshold.
    Sells when RSI rises above overbought threshold.

    Config:
        rsi_period: int - RSI calculation period
        overbought_threshold: float - RSI overbought level (sell)
        oversold_threshold: float - RSI oversold level (buy)
        order_amount: float - Amount per order (USD)
        timeframe: str - Timeframe for RSI (e.g., "1h", "4h")
        leverage: float - Leverage multiplier
    """

    async def run_cycle(self) -> dict:
        trades_executed = 0
        pnl_change = 0.0
        total_size_usd = 0.0  # Track total position size for this cycle

        try:
            rsi_period = self.config.get("rsi_period", 14)
            overbought = self.config.get("overbought_threshold", 70.0)
            oversold = self.config.get("oversold_threshold", 30.0)
            order_amount = self.config["order_amount"]
            timeframe = self.config.get("timeframe", "1h")
            leverage = self.config.get("leverage", 1.0)

            # Initialize state
            if not self.runtime_state.get("initialized"):
                self.runtime_state = {
                    "initialized": True,
                    "has_position": False,
                    "entry_price": 0.0,
                    "position_size_usd": 0.0,
                    "last_rsi": None,
                    "last_signal": None,
                }

            # Get RSI value via klines and manual calculation
            current_price = await self._get_current_price()
            rsi_value = await self._calculate_rsi(timeframe, rsi_period)

            if rsi_value is None:
                self.runtime_state["last_check"] = datetime.now(UTC).isoformat()
                return {
                    "success": True,
                    "trades_executed": 0,
                    "pnl_change": 0.0,
                    "updated_state": self.runtime_state,
                    "message": "Insufficient data for RSI calculation",
                }

            has_position = self.runtime_state.get("has_position", False)

            # Reconcile has_position with actual exchange state to prevent drift
            # (e.g. manual close, liquidation, or close by another strategy)
            try:
                actual_pos = await self.trader.get_position(self.symbol)
                actual_has_position = actual_pos is not None and actual_pos.size > 0
                if has_position and not actual_has_position:
                    logger.warning(
                        f"RSI {self.agent_id}: state says has_position=True but "
                        f"exchange has no position for {self.symbol}. Resetting."
                    )
                    self.runtime_state["has_position"] = False
                    self.runtime_state["entry_price"] = 0.0
                    self.runtime_state["position_size_usd"] = 0.0
                    has_position = False
                elif not has_position and actual_has_position:
                    logger.warning(
                        f"RSI {self.agent_id}: state says has_position=False but "
                        f"exchange shows position for {self.symbol}. Syncing."
                    )
                    self.runtime_state["has_position"] = True
                    self.runtime_state["entry_price"] = actual_pos.entry_price
                    self.runtime_state["position_size_usd"] = actual_pos.size_usd
                    has_position = True
            except Exception as sync_err:
                logger.debug(f"RSI position sync check failed: {sync_err}")
            self.runtime_state["last_rsi"] = rsi_value

            # Buy signal: RSI below oversold and no position
            if rsi_value <= oversold and not has_position:
                try:
                    open_result = await self._open_with_isolation(
                        size_usd=order_amount,
                        leverage=int(leverage),
                        side="long",
                    )
                    if open_result.success:
                        trades_executed += 1
                        total_size_usd += order_amount  # Track total size
                        actual_entry = open_result.filled_price or current_price
                        self.runtime_state["has_position"] = True
                        self.runtime_state["entry_price"] = actual_entry
                        self.runtime_state["position_size_usd"] = order_amount
                        self.runtime_state["last_signal"] = "buy"

                        logger.info(
                            f"RSI {self.agent_id}: BUY signal (RSI={rsi_value:.1f} <= {oversold}) "
                            f"at {current_price:.2f} (filled@{actual_entry:.2f}), size=${order_amount}"
                        )
                except TradeError as e:
                    logger.warning(f"RSI buy error: {e}")

            # Sell signal: RSI above overbought and has position
            elif rsi_value >= overbought and has_position:
                try:
                    entry_price = self.runtime_state.get("entry_price", current_price)
                    position_size = self.runtime_state.get("position_size_usd", order_amount)

                    close_result = await self._close_with_isolation()
                    if close_result.success:
                        trades_executed += 1
                        total_size_usd += position_size  # Track total size
                        actual_close = close_result.filled_price or current_price

                        # Calculate P/L using actual fill prices
                        if entry_price > 0:
                            pnl_change = position_size * ((actual_close - entry_price) / entry_price)

                        self.runtime_state["has_position"] = False
                        self.runtime_state["entry_price"] = 0.0
                        self.runtime_state["position_size_usd"] = 0.0
                        self.runtime_state["last_signal"] = "sell"

                        logger.info(
                            f"RSI {self.agent_id}: SELL signal (RSI={rsi_value:.1f} >= {overbought}) "
                            f"at {current_price:.2f}, P/L=${pnl_change:.2f}"
                        )
                except TradeError as e:
                    logger.warning(f"RSI sell error: {e}")

            self.runtime_state["last_check"] = datetime.now(UTC).isoformat()
            self.runtime_state["last_price"] = current_price

            return {
                "success": True,
                "trades_executed": trades_executed,
                "pnl_change": pnl_change,
                "total_size_usd": total_size_usd,
                "updated_state": self.runtime_state,
                "message": f"RSI={rsi_value:.1f}, price={current_price:.2f}, trades={trades_executed}",
            }

        except Exception as e:
            logger.error(f"RSI engine error for {self.agent_id}: {e}")
            return {
                "success": False,
                "trades_executed": 0,
                "pnl_change": 0.0,
                "total_size_usd": 0.0,
                "updated_state": self.runtime_state,
                "message": f"Error: {str(e)}",
            }

    async def _calculate_rsi(self, timeframe: str, period: int) -> Optional[float]:
        """Calculate RSI from kline data"""
        try:
            # Need period + 1 candles for RSI calculation
            klines = await self.trader.get_klines(
                symbol=self.symbol,
                timeframe=timeframe,
                limit=period + 10,
            )

            if len(klines) < period + 1:
                return None

            # Extract closing prices
            closes = [k.close for k in klines]

            # Calculate price changes
            deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

            # Separate gains and losses
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]

            # Calculate average gain/loss using EMA method
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period

            for i in range(period, len(gains)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
            return round(rsi, 2)

        except Exception as e:
            logger.warning(f"RSI calculation failed: {e}")
            return None


def create_engine(
    strategy_type: str,
    agent_id: str,
    trader: BaseTrader,
    symbol: str,
    config: dict,
    runtime_state: dict,
    account_id: Optional[str] = None,
    position_service: Optional[PositionService] = None,
    strategy: Optional[object] = None,
) -> QuantEngineBase:
    """Factory function to create the appropriate engine for a strategy type.

    Args:
        strategy_type: Type of strategy (grid, dca, rsi)
        agent_id: AgentDB.id (not StrategyDB.id)
        ...
    """
    engines = {
        "grid": GridEngine,
        "dca": DCAEngine,
        "rsi": RSIEngine,
    }

    engine_class = engines.get(strategy_type)
    if not engine_class:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

    return engine_class(
        agent_id=agent_id,
        trader=trader,
        symbol=symbol,
        config=config,
        runtime_state=runtime_state,
        account_id=account_id,
        position_service=position_service,
        strategy=strategy,
    )
