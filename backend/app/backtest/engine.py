"""
Backtest engine for strategy simulation.

Runs strategies against historical data with simulated execution.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from ..core.config import get_settings
from ..db.models import StrategyDB
from ..models.decision import DecisionResponse
from ..models.strategy import StrategyConfig
from ..services.ai import BaseAIClient
from ..services.decision_parser import DecisionParser
from ..services.prompt_builder import PromptBuilder
from ..services.strategy_engine import StrategyEngine
from ..traders.base import MarketData
from .data_provider import DataProvider, MarketSnapshot
from .simulator import SimulatedTrader, Trade

settings = get_settings()


@dataclass
class BacktestResult:
    """Backtest result summary"""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_balance: float
    final_balance: float
    total_return_percent: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_percent: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    recovery_factor: Optional[float] = None
    total_fees: float = 0.0
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    drawdown_curve: List[Dict[str, Any]] = field(default_factory=list)
    monthly_returns: List[Dict[str, Any]] = field(default_factory=list)
    trade_statistics: Dict[str, Any] = field(default_factory=dict)
    symbol_breakdown: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "total_return_percent": self.total_return_percent,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown_percent": self.max_drawdown_percent,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "total_fees": self.total_fees,
            "equity_curve": self.equity_curve,
        }


class BacktestEngine:
    """
    Backtest engine for running strategies on historical data.

    Features:
    - Historical data simulation
    - AI decision generation (optional mock)
    - Position tracking and P&L calculation
    - Performance metrics calculation
    - Equity curve generation

    Usage:
        engine = BacktestEngine(
            strategy=my_strategy,
            initial_balance=10000,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )
        result = await engine.run()
    """

    def __init__(
        self,
        strategy: StrategyDB,
        initial_balance: float = 10000.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        data_provider: Optional[DataProvider] = None,
        use_ai: bool = False,
        ai_client: Optional[BaseAIClient] = None,
        decision_interval_candles: int = 1,  # Make decision every N candles
    ):
        """
        Initialize backtest engine.

        Args:
            strategy: Strategy to backtest
            initial_balance: Starting balance in USD
            start_date: Backtest start date
            end_date: Backtest end date
            data_provider: Historical data provider
            use_ai: If True, use AI for decisions (slow, expensive)
            ai_client: AI client for decision generation (if None, uses strategy's ai_model)
            decision_interval_candles: How often to make decisions
        """
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.start_date = start_date or datetime(2024, 1, 1)
        self.end_date = end_date or datetime.now(UTC)
        self.data_provider = data_provider
        self.use_ai = use_ai
        self.decision_interval = decision_interval_candles

        # AI client must be provided by caller when use_ai=True (resolve from DB in route)
        if use_ai and ai_client is None:
            raise ValueError(
                "use_ai=True requires ai_client. Resolve credentials from DB in the caller "
                "(e.g. resolve_provider_credentials) and pass ai_client."
            )
        self.ai_client = ai_client

        # Parse strategy config
        self.config = StrategyConfig(**strategy.config) if strategy.config else StrategyConfig()

        # Initialize components with configured fees and slippage
        self.trader = SimulatedTrader(
            initial_balance=initial_balance,
            maker_fee=settings.simulator_maker_fee,
            taker_fee=settings.simulator_taker_fee,
            default_slippage=settings.simulator_default_slippage,
        )
        self.prompt_builder = PromptBuilder(config=self.config)
        self.decision_parser = DecisionParser(risk_controls=self.config.risk_controls)

        # Results
        self._equity_curve: List[Dict[str, Any]] = []
        self._decisions: List[Dict[str, Any]] = []
        self._candles_processed = 0

    async def run(self) -> BacktestResult:
        """
        Run the backtest.

        Returns:
            BacktestResult with performance metrics
        """
        # Initialize data provider if needed
        if not self.data_provider:
            self.data_provider = DataProvider()
            await self.data_provider.initialize()
            await self.data_provider.load_data(
                symbols=self.config.symbols,
                start_date=self.start_date,
                end_date=self.end_date,
                timeframe="1h",
            )

        # Get snapshots
        snapshots = self.data_provider.iterate()
        if not snapshots:
            raise ValueError("No data to backtest")

        # Run simulation
        for i, snapshot in enumerate(snapshots):
            # Update trader with current prices
            self.trader.set_current_time(snapshot.timestamp)
            self.trader.set_prices(snapshot.prices)

            # Record equity
            account = await self.trader.get_account_state()
            self._equity_curve.append({
                "timestamp": snapshot.timestamp.isoformat(),
                "equity": account.equity,
                "balance": self.trader.balance,
                "positions": account.position_count,
            })

            # Make decision at intervals
            if i % self.decision_interval == 0:
                await self._make_decision(snapshot)

            self._candles_processed += 1

        # Close any remaining positions
        for symbol in list(self.trader._positions.keys()):
            await self.trader.close_position(symbol)

        # Calculate final results
        return await self._build_result()

    async def _make_decision(self, snapshot: MarketSnapshot) -> None:
        """Make trading decision for current snapshot"""
        if self.use_ai and self.ai_client:
            # Use AI for decision (expensive)
            await self._ai_decision(snapshot)
        else:
            # Use simple rule-based strategy
            await self._rule_based_decision(snapshot)

    async def _ai_decision(self, snapshot: MarketSnapshot) -> None:
        """Generate AI decision"""
        try:
            # Build prompts
            account = await self.trader.get_account_state()
            market_data = {
                symbol: MarketData(
                    symbol=symbol,
                    mid_price=price,
                    bid_price=price * 0.999,
                    ask_price=price * 1.001,
                    volume_24h=0,
                    timestamp=snapshot.timestamp,
                )
                for symbol, price in snapshot.prices.items()
            }

            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(
                account=account,
                market_data=market_data,
            )

            # Call AI
            response = await self.ai_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            # Parse decision
            decision = self.decision_parser.parse(response.content)

            # Execute decisions
            await self._execute_decisions(decision, account)

            # Record decision
            self._decisions.append({
                "timestamp": snapshot.timestamp.isoformat(),
                "decision": decision.model_dump() if hasattr(decision, "model_dump") else str(decision),
            })

        except Exception as e:
            # Log error but continue with backtest
            import logging
            logging.getLogger(__name__).warning(f"Decision generation error at {snapshot.timestamp}: {e}")

    async def _rule_based_decision(self, snapshot: MarketSnapshot) -> None:
        """
        Simple rule-based decision for quick backtesting.

        Uses basic momentum strategy:
        - Long when price > SMA(20)
        - Short when price < SMA(20)
        """
        account = await self.trader.get_account_state()

        for symbol in self.config.symbols:
            price = snapshot.prices.get(symbol)
            if not price:
                continue

            # Get historical prices for SMA
            candles = self.data_provider.get_data(symbol)
            if len(candles) < 20:
                continue

            # Find current candle index
            current_idx = -1
            for i, c in enumerate(candles):
                if c.timestamp >= snapshot.timestamp:
                    current_idx = i
                    break

            if current_idx < 20:
                continue

            # Calculate SMA(20)
            sma_20 = sum(c.close for c in candles[current_idx-20:current_idx]) / 20

            # Current position
            position = await self.trader.get_position(symbol)

            # Decision logic
            if price > sma_20 * 1.01:  # 1% above SMA
                if not position:
                    # Open long
                    size_usd = account.available_balance * self.config.risk_controls.max_position_ratio
                    if size_usd > 100:  # Minimum position size
                        await self.trader.open_long(
                            symbol=symbol,
                            size_usd=size_usd,
                            leverage=self.config.risk_controls.max_leverage,
                            stop_loss=price * 0.97,  # 3% stop loss
                            take_profit=price * 1.06,  # 6% take profit
                        )
                elif position and position.side == "short":
                    await self.trader.close_position(symbol)

            elif price < sma_20 * 0.99:  # 1% below SMA
                if not position:
                    # Open short
                    size_usd = account.available_balance * self.config.risk_controls.max_position_ratio
                    if size_usd > 100:
                        await self.trader.open_short(
                            symbol=symbol,
                            size_usd=size_usd,
                            leverage=self.config.risk_controls.max_leverage,
                            stop_loss=price * 1.03,
                            take_profit=price * 0.94,
                        )
                elif position and position.side == "long":
                    await self.trader.close_position(symbol)

    async def _execute_decisions(
        self,
        decision: DecisionResponse,
        account,
    ) -> None:
        """Execute parsed AI decisions"""
        from ..models.decision import ActionType

        for d in decision.decisions:
            should_exec, _ = self.decision_parser.should_execute(d)
            if not should_exec:
                continue

            try:
                if d.action == ActionType.OPEN_LONG:
                    await self.trader.open_long(
                        symbol=d.symbol,
                        size_usd=d.position_size_usd,
                        leverage=d.leverage,
                        stop_loss=d.stop_loss,
                        take_profit=d.take_profit,
                    )
                elif d.action == ActionType.OPEN_SHORT:
                    await self.trader.open_short(
                        symbol=d.symbol,
                        size_usd=d.position_size_usd,
                        leverage=d.leverage,
                        stop_loss=d.stop_loss,
                        take_profit=d.take_profit,
                    )
                elif d.action in (ActionType.CLOSE_LONG, ActionType.CLOSE_SHORT):
                    await self.trader.close_position(d.symbol)
            except Exception:
                continue

    async def _build_result(self) -> BacktestResult:
        """Build final backtest result"""
        import statistics as stats_mod
        from collections import defaultdict

        stats = self.trader.get_statistics()
        trades = self.trader.get_trades()

        # --- Periodic returns for ratio calculations ---
        returns = []
        if len(self._equity_curve) > 1:
            for i in range(1, len(self._equity_curve)):
                prev = self._equity_curve[i - 1]["equity"]
                curr = self._equity_curve[i]["equity"]
                if prev > 0:
                    returns.append((curr - prev) / prev)

        # --- Sharpe Ratio (annualised, assuming hourly data) ---
        sharpe = None
        if returns:
            mean_return = stats_mod.mean(returns)
            std_return = stats_mod.stdev(returns) if len(returns) > 1 else 0
            if std_return > 0:
                sharpe = (mean_return * 8760) / (std_return * (8760 ** 0.5))

        # --- Sortino Ratio (only downside deviation) ---
        sortino = None
        if returns:
            mean_return = stats_mod.mean(returns)
            downside = [r for r in returns if r < 0]
            if downside and len(downside) > 1:
                downside_std = stats_mod.stdev(downside)
                if downside_std > 0:
                    sortino = (mean_return * 8760) / (downside_std * (8760 ** 0.5))

        # --- Calmar Ratio (annualised return / max drawdown) ---
        calmar = None
        max_dd_pct = stats["max_drawdown"]  # already in %
        if max_dd_pct > 0 and len(self._equity_curve) > 1:
            # Compute annualised return
            total_hours = len(self._equity_curve)
            total_return_pct = stats["total_pnl_percent"]
            if total_hours > 0:
                annualised_return = total_return_pct * (8760 / total_hours)
                calmar = annualised_return / max_dd_pct

        # --- Recovery Factor (total return / max drawdown) ---
        recovery_factor = None
        if max_dd_pct > 0:
            recovery_factor = round(stats["total_pnl_percent"] / max_dd_pct, 2)

        # --- Drawdown curve ---
        drawdown_curve = []
        if self._equity_curve:
            peak = self._equity_curve[0]["equity"]
            for pt in self._equity_curve:
                eq = pt["equity"]
                if eq > peak:
                    peak = eq
                dd_pct = ((peak - eq) / peak * 100) if peak > 0 else 0
                drawdown_curve.append({
                    "timestamp": pt["timestamp"],
                    "drawdown_percent": round(dd_pct, 4),
                })

        # --- Monthly returns ---
        monthly_returns = []
        if len(self._equity_curve) > 1:
            monthly_buckets: dict = {}
            for pt in self._equity_curve:
                month_key = pt["timestamp"][:7]  # "YYYY-MM"
                if month_key not in monthly_buckets:
                    monthly_buckets[month_key] = {"first": pt["equity"], "last": pt["equity"]}
                monthly_buckets[month_key]["last"] = pt["equity"]

            for month_key, bucket in sorted(monthly_buckets.items()):
                first_eq = bucket["first"]
                last_eq = bucket["last"]
                ret_pct = ((last_eq - first_eq) / first_eq * 100) if first_eq > 0 else 0
                monthly_returns.append({
                    "month": month_key,
                    "return_percent": round(ret_pct, 2),
                })

        # --- Trade statistics (extended) ---
        trade_statistics = {
            "average_win": stats["average_win"],
            "average_loss": stats["average_loss"],
            "largest_win": stats["largest_win"],
            "largest_loss": stats["largest_loss"],
            "gross_profit": stats["gross_profit"],
            "gross_loss": stats["gross_loss"],
            "avg_holding_hours": stats["avg_holding_hours"],
            "max_consecutive_wins": stats["max_consecutive_wins"],
            "max_consecutive_losses": stats["max_consecutive_losses"],
            "expectancy": stats["expectancy"],
            "recovery_factor": recovery_factor,
            "sortino_ratio": round(sortino, 2) if sortino is not None else None,
            "calmar_ratio": round(calmar, 2) if calmar is not None else None,
            "long_stats": stats["long_stats"],
            "short_stats": stats["short_stats"],
        }

        return BacktestResult(
            strategy_name=self.strategy.name,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_balance=self.initial_balance,
            final_balance=self.trader.balance,
            total_return_percent=stats["total_pnl_percent"],
            total_trades=stats["total_trades"],
            winning_trades=stats["winning_trades"],
            losing_trades=stats["losing_trades"],
            win_rate=stats["win_rate"],
            profit_factor=stats["profit_factor"],
            max_drawdown_percent=stats["max_drawdown"],
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            recovery_factor=recovery_factor,
            total_fees=stats["total_fees"],
            trades=trades,
            equity_curve=self._equity_curve,
            drawdown_curve=drawdown_curve,
            monthly_returns=monthly_returns,
            trade_statistics=trade_statistics,
            symbol_breakdown=stats["symbol_breakdown"],
            decisions=self._decisions,
        )

    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.data_provider:
            await self.data_provider.close()
