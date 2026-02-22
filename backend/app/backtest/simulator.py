"""
Simulated trading for backtesting.

Implements BaseTrader interface with simulated execution.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Dict, List, Literal, Optional

from ..traders.base import (
    AccountState,
    BaseTrader,
    MarketData,
    OrderResult,
    Position,
    TradeError,
    calculate_unrealized_pnl_percent,
)


@dataclass
class SimulatedPosition:
    """Simulated position with P&L tracking"""

    symbol: str
    side: Literal["long", "short"]
    size: float
    entry_price: float
    leverage: int
    opened_at: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def calculate_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        if self.side == "long":
            return (current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - current_price) * self.size

    def calculate_pnl_percent(self, current_price: float) -> float:
        """Calculate unrealized P&L percentage (margin ROI)."""
        if self.entry_price == 0:
            return 0
        pnl = self.calculate_pnl(current_price)
        margin_used = (self.size * self.entry_price) / max(self.leverage, 1)
        return calculate_unrealized_pnl_percent(
            pnl,
            margin_used=margin_used,
            size_usd=self.size * self.entry_price,
            leverage=self.leverage,
        )

    def check_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss triggered"""
        if not self.stop_loss:
            return False

        if self.side == "long":
            return current_price <= self.stop_loss
        else:
            return current_price >= self.stop_loss

    def check_take_profit(self, current_price: float) -> bool:
        """Check if take profit triggered"""
        if not self.take_profit:
            return False

        if self.side == "long":
            return current_price >= self.take_profit
        else:
            return current_price <= self.take_profit

    def to_position(self, current_price: float) -> Position:
        """Convert to Position object"""
        pnl = self.calculate_pnl(current_price)
        pnl_percent = self.calculate_pnl_percent(current_price)

        return Position(
            symbol=self.symbol,
            side=self.side,
            size=self.size,
            size_usd=self.size * current_price,
            entry_price=self.entry_price,
            mark_price=current_price,
            leverage=self.leverage,
            unrealized_pnl=pnl,
            unrealized_pnl_percent=pnl_percent,
            liquidation_price=self._calc_liquidation_price(),
            margin_used=self.size * self.entry_price / self.leverage,
        )

    def _calc_liquidation_price(self) -> Optional[float]:
        """Calculate approximate liquidation price"""
        # Simplified liquidation calculation (actual varies by exchange)
        liq_threshold = 0.9 / self.leverage  # ~90% loss of margin

        if self.side == "long":
            return self.entry_price * (1 - liq_threshold)
        else:
            return self.entry_price * (1 + liq_threshold)


@dataclass
class Trade:
    """Closed trade record"""

    symbol: str
    side: Literal["long", "short"]
    size: float
    entry_price: float
    exit_price: float
    leverage: int
    pnl: float
    pnl_percent: float
    opened_at: datetime
    closed_at: datetime
    exit_reason: str = (
        "manual"  # manual, stop_loss, take_profit, liquidation, signal, reverse
    )

    @property
    def duration_minutes(self) -> float:
        return (self.closed_at - self.opened_at).total_seconds() / 60


class SimulatedTrader(BaseTrader):
    """
    Simulated trader for backtesting.

    Features:
    - Realistic order execution with slippage
    - Position tracking with P&L
    - Trade history recording
    - SL/TP automatic execution
    - Fee simulation

    Usage:
        trader = SimulatedTrader(initial_balance=10000)
        trader.set_current_time(datetime.now())
        trader.set_prices({"BTC": 50000, "ETH": 3000})

        result = await trader.open_long("BTC", 1000, leverage=10)
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        maker_fee: float = 0.0002,  # 0.02%
        taker_fee: float = 0.0005,  # 0.05%
        default_slippage: float = 0.001,  # 0.1%
    ):
        """
        Initialize simulated trader.

        Args:
            initial_balance: Starting balance in USD
            maker_fee: Maker fee rate
            taker_fee: Taker fee rate
            default_slippage: Default slippage for market orders
        """
        super().__init__(testnet=True, default_slippage=default_slippage)

        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee

        self._positions: Dict[str, SimulatedPosition] = {}
        self._trades: List[Trade] = []
        self._current_prices: Dict[str, float] = {}
        self._current_time: datetime = datetime.now(UTC)
        self._order_id_counter = 0
        self._initialized = True

        # Tracking
        self.total_fees_paid = 0.0
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0

    @property
    def exchange_name(self) -> str:
        return "simulator"

    async def initialize(self) -> bool:
        self._initialized = True
        return True

    async def close(self) -> None:
        pass

    def set_current_time(self, time: datetime) -> None:
        """Set current simulation time"""
        self._current_time = time

    def set_prices(self, prices: Dict[str, float]) -> None:
        """Update current market prices"""
        self._current_prices.update(prices)
        self._check_sl_tp_triggers()
        self._update_metrics()

    def _check_sl_tp_triggers(self) -> None:
        """Check and execute stop loss / take profit orders"""
        for symbol in list(self._positions.keys()):
            pos = self._positions.get(symbol)
            if not pos:
                continue

            price = self._current_prices.get(symbol)
            if not price:
                continue

            if pos.check_stop_loss(price):
                self._close_position_internal(symbol, price, "stop_loss")
            elif pos.check_take_profit(price):
                self._close_position_internal(symbol, price, "take_profit")

    def _update_metrics(self) -> None:
        """Update tracking metrics"""
        equity = self._calculate_equity()

        if equity > self.peak_balance:
            self.peak_balance = equity

        if self.peak_balance > 0:
            drawdown = (self.peak_balance - equity) / self.peak_balance
            self.max_drawdown = max(self.max_drawdown, drawdown)

    def _calculate_equity(self) -> float:
        """Calculate total equity (balance + unrealized P&L)"""
        unrealized_pnl = 0.0
        for symbol, pos in self._positions.items():
            price = self._current_prices.get(symbol, pos.entry_price)
            unrealized_pnl += pos.calculate_pnl(price)
        return self.balance + unrealized_pnl

    def _next_order_id(self) -> str:
        self._order_id_counter += 1
        return f"SIM-{self._order_id_counter}"

    # ==================== Account Operations ====================

    async def get_account_state(self) -> AccountState:
        """Get simulated account state"""
        positions = []
        total_margin = 0.0
        total_unrealized_pnl = 0.0

        for symbol, pos in self._positions.items():
            price = self._current_prices.get(symbol, pos.entry_price)
            position = pos.to_position(price)
            positions.append(position)
            total_margin += position.margin_used
            total_unrealized_pnl += position.unrealized_pnl

        equity = self.balance + total_unrealized_pnl

        return AccountState(
            equity=equity,
            available_balance=self.balance - total_margin,
            total_margin_used=total_margin,
            unrealized_pnl=total_unrealized_pnl,
            positions=positions,
        )

    async def get_positions(self) -> List[Position]:
        """Get all positions"""
        account = await self.get_account_state()
        return account.positions

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        symbol = self._validate_symbol(symbol)
        pos = self._positions.get(symbol)
        if not pos:
            return None

        price = self._current_prices.get(symbol, pos.entry_price)
        return pos.to_position(price)

    # ==================== Market Data ====================

    async def get_market_price(self, symbol: str) -> float:
        """Get current price"""
        symbol = self._validate_symbol(symbol)
        price = self._current_prices.get(symbol)
        if price is None:
            raise TradeError(f"No price for {symbol}")
        return price

    async def get_market_data(self, symbol: str) -> MarketData:
        """Get market data"""
        symbol = self._validate_symbol(symbol)
        price = await self.get_market_price(symbol)

        return MarketData(
            symbol=symbol,
            mid_price=price,
            bid_price=price * (1 - self.default_slippage),
            ask_price=price * (1 + self.default_slippage),
            volume_24h=0,
            timestamp=self._current_time,
        )

    # ==================== Order Operations ====================

    async def place_market_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        leverage: int = 1,
        reduce_only: bool = False,
        slippage: Optional[float] = None,
        price: Optional[float] = None,
    ) -> OrderResult:
        """Execute simulated market order"""
        symbol = self._validate_symbol(symbol)
        slippage = slippage or self.default_slippage

        try:
            price = await self.get_market_price(symbol)

            # Apply slippage
            if side == "buy":
                exec_price = price * (1 + slippage)
            else:
                exec_price = price * (1 - slippage)

            # Calculate fee
            fee = size * exec_price * self.taker_fee
            self.total_fees_paid += fee

            # Execute
            if reduce_only:
                return await self._reduce_position(symbol, size, exec_price)
            else:
                return await self._open_or_increase_position(
                    symbol, side, size, exec_price, leverage
                )

        except Exception as e:
            return OrderResult(success=False, error=str(e))

    async def _open_or_increase_position(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        price: float,
        leverage: int,
    ) -> OrderResult:
        """Open new position or increase existing"""
        position_side = "long" if side == "buy" else "short"

        existing = self._positions.get(symbol)

        if existing and existing.side != position_side:
            # Close existing position first
            self._close_position_internal(symbol, price, "reverse")

        if existing and existing.side == position_side:
            # Increase position (average entry)
            total_size = existing.size + size
            avg_price = (
                existing.entry_price * existing.size + price * size
            ) / total_size
            existing.size = total_size
            existing.entry_price = avg_price
        else:
            # Open new position
            required_margin = size * price / leverage
            if required_margin > self.balance:
                return OrderResult(success=False, error="Insufficient balance")

            self._positions[symbol] = SimulatedPosition(
                symbol=symbol,
                side=position_side,
                size=size,
                entry_price=price,
                leverage=leverage,
                opened_at=self._current_time,
            )

        return OrderResult(
            success=True,
            order_id=self._next_order_id(),
            filled_size=size,
            filled_price=price,
            status="filled",
            timestamp=self._current_time,
        )

    async def _reduce_position(
        self,
        symbol: str,
        size: float,
        price: float,
    ) -> OrderResult:
        """Reduce or close position"""
        pos = self._positions.get(symbol)
        if not pos:
            return OrderResult(success=False, error="No position to reduce")

        close_size = min(size, pos.size)
        self._close_position_internal(symbol, price, "signal", close_size)

        return OrderResult(
            success=True,
            order_id=self._next_order_id(),
            filled_size=close_size,
            filled_price=price,
            status="filled",
            timestamp=self._current_time,
        )

    def _close_position_internal(
        self,
        symbol: str,
        price: float,
        reason: str,
        size: Optional[float] = None,
    ) -> None:
        """Internal position close logic"""
        pos = self._positions.get(symbol)
        if not pos:
            return

        close_size = size or pos.size
        close_size = min(close_size, pos.size)

        # Calculate P&L
        if pos.side == "long":
            pnl = (price - pos.entry_price) * close_size
        else:
            pnl = (pos.entry_price - price) * close_size

        pnl_percent = calculate_unrealized_pnl_percent(
            pnl,
            margin_used=(close_size * pos.entry_price) / max(pos.leverage, 1),
            size_usd=close_size * pos.entry_price,
            leverage=pos.leverage,
        )

        # Record trade
        self._trades.append(
            Trade(
                symbol=symbol,
                side=pos.side,
                size=close_size,
                entry_price=pos.entry_price,
                exit_price=price,
                leverage=pos.leverage,
                pnl=pnl,
                pnl_percent=pnl_percent,
                opened_at=pos.opened_at,
                closed_at=self._current_time,
                exit_reason=reason,
            )
        )

        # Update balance
        self.balance += pnl

        # Update or remove position
        if close_size >= pos.size:
            del self._positions[symbol]
        else:
            pos.size -= close_size

    async def place_limit_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        price: float,
        leverage: int = 1,
        reduce_only: bool = False,
        post_only: bool = False,
    ) -> OrderResult:
        """Limit orders are executed immediately in backtesting"""
        # For simplicity, execute as market at limit price
        return await self.place_market_order(
            symbol, side, size, leverage, reduce_only, slippage=0
        )

    async def place_stop_loss(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        """Set stop loss on position"""
        symbol = self._validate_symbol(symbol)
        pos = self._positions.get(symbol)

        if not pos:
            return OrderResult(success=False, error="No position")

        pos.stop_loss = trigger_price

        return OrderResult(
            success=True,
            order_id=self._next_order_id(),
            status="pending",
            timestamp=self._current_time,
        )

    async def place_take_profit(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        """Set take profit on position"""
        symbol = self._validate_symbol(symbol)
        pos = self._positions.get(symbol)

        if not pos:
            return OrderResult(success=False, error="No position")

        pos.take_profit = trigger_price

        return OrderResult(
            success=True,
            order_id=self._next_order_id(),
            status="pending",
            timestamp=self._current_time,
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel order (no-op in simulation)"""
        return True

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all orders (no-op in simulation)"""
        return 0

    async def close_position(
        self,
        symbol: str,
        size: Optional[float] = None,
        slippage: Optional[float] = None,
    ) -> OrderResult:
        """Close position"""
        symbol = self._validate_symbol(symbol)
        pos = self._positions.get(symbol)

        if not pos:
            return OrderResult(success=True, status="no_position")

        close_side = "sell" if pos.side == "long" else "buy"

        return await self.place_market_order(
            symbol, close_side, size or pos.size, reduce_only=True, slippage=slippage
        )

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage (stored for next trade)"""
        return True

    # ==================== Backtest Results ====================

    def get_trades(self) -> List[Trade]:
        """Get all closed trades"""
        return self._trades

    def get_statistics(self) -> dict:
        """Calculate trading statistics"""
        total_pnl_percent = (
            (self.balance - self.initial_balance) / self.initial_balance * 100
            if self.initial_balance > 0
            else 0
        )

        empty_side_stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "gross_profit": 0,
            "gross_loss": 0,
            "average_win": 0,
            "average_loss": 0,
        }

        if not self._trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "total_pnl": 0,
                "total_pnl_percent": total_pnl_percent,
                "gross_profit": 0,
                "gross_loss": 0,
                "average_win": 0,
                "average_loss": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "max_drawdown": self.max_drawdown * 100,
                "total_fees": self.total_fees_paid,
                "final_balance": self.balance,
                # Extended statistics
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "avg_holding_hours": 0,
                "expectancy": 0,
                "long_stats": empty_side_stats,
                "short_stats": empty_side_stats,
                "symbol_breakdown": [],
            }

        wins = [t for t in self._trades if t.pnl > 0]
        losses = [t for t in self._trades if t.pnl < 0]

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        total_trades = len(self._trades)
        win_rate = len(wins) / total_trades * 100 if total_trades else 0
        average_win = gross_profit / len(wins) if wins else 0
        average_loss = gross_loss / len(losses) if losses else 0

        # --- Max consecutive wins / losses ---
        max_consec_wins = 0
        max_consec_losses = 0
        cur_wins = 0
        cur_losses = 0
        for t in self._trades:
            if t.pnl > 0:
                cur_wins += 1
                cur_losses = 0
                max_consec_wins = max(max_consec_wins, cur_wins)
            elif t.pnl < 0:
                cur_losses += 1
                cur_wins = 0
                max_consec_losses = max(max_consec_losses, cur_losses)
            else:
                cur_wins = 0
                cur_losses = 0

        # --- Average holding time (hours) ---
        avg_holding_hours = (
            sum(t.duration_minutes for t in self._trades) / total_trades / 60
            if total_trades
            else 0
        )

        # --- Expectancy ---
        loss_rate = len(losses) / total_trades if total_trades else 0
        expectancy = (average_win * (win_rate / 100)) - (average_loss * loss_rate)

        # --- Long / Short breakdown ---
        def _side_stats(trades_subset: List[Trade]) -> dict:
            if not trades_subset:
                return empty_side_stats.copy()
            sw = [t for t in trades_subset if t.pnl > 0]
            sl = [t for t in trades_subset if t.pnl < 0]
            sgp = sum(t.pnl for t in sw)
            sgl = abs(sum(t.pnl for t in sl))
            return {
                "total_trades": len(trades_subset),
                "winning_trades": len(sw),
                "losing_trades": len(sl),
                "win_rate": len(sw) / len(trades_subset) * 100,
                "total_pnl": sum(t.pnl for t in trades_subset),
                "gross_profit": sgp,
                "gross_loss": sgl,
                "average_win": sgp / len(sw) if sw else 0,
                "average_loss": sgl / len(sl) if sl else 0,
            }

        long_trades = [t for t in self._trades if t.side == "long"]
        short_trades = [t for t in self._trades if t.side == "short"]

        # --- Symbol breakdown ---
        symbols_map: Dict[str, List[Trade]] = {}
        for t in self._trades:
            symbols_map.setdefault(t.symbol, []).append(t)

        symbol_breakdown = []
        for sym, sym_trades in sorted(symbols_map.items()):
            sym_wins = [t for t in sym_trades if t.pnl > 0]
            sym_pnl = sum(t.pnl for t in sym_trades)
            symbol_breakdown.append(
                {
                    "symbol": sym,
                    "total_trades": len(sym_trades),
                    "winning_trades": len(sym_wins),
                    "losing_trades": len(sym_trades) - len(sym_wins),
                    "win_rate": (
                        len(sym_wins) / len(sym_trades) * 100 if sym_trades else 0
                    ),
                    "total_pnl": round(sym_pnl, 2),
                    "average_pnl": (
                        round(sym_pnl / len(sym_trades), 2) if sym_trades else 0
                    ),
                }
            )

        return {
            "total_trades": total_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": win_rate,
            "profit_factor": (
                gross_profit / gross_loss if gross_loss > 0 else float("inf")
            ),
            "total_pnl": sum(t.pnl for t in self._trades),
            "total_pnl_percent": total_pnl_percent,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "average_win": average_win,
            "average_loss": average_loss,
            "largest_win": max((t.pnl for t in wins), default=0),
            "largest_loss": min((t.pnl for t in losses), default=0),
            "max_drawdown": self.max_drawdown * 100,
            "total_fees": self.total_fees_paid,
            "final_balance": self.balance,
            # Extended statistics
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses,
            "avg_holding_hours": round(avg_holding_hours, 2),
            "expectancy": round(expectancy, 2),
            "long_stats": _side_stats(long_trades),
            "short_stats": _side_stats(short_trades),
            "symbol_breakdown": symbol_breakdown,
        }
