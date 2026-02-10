"""
Backtest API routes.

Endpoints for running strategy backtests.
"""

import logging
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...backtest import BacktestEngine, DataProvider
from ...backtest.data_provider import DataProvider as _DP  # for SUPPORTED_EXCHANGES
from ...core.config import get_settings
from ...services.ai import get_ai_client, resolve_provider_credentials
from ...core.dependencies import CryptoDep, CurrentUserDep, DbSessionDep, RateLimitApiDep
from ...core.errors import (
    ErrorCode,
    backtest_failed_error,
    create_http_exception,
    internal_error,
)
from ...db.repositories.strategy import StrategyRepository
from ...models.strategy import StrategyConfig

router = APIRouter(prefix="/backtest", tags=["backtest"])
logger = logging.getLogger(__name__)
settings = get_settings()

SUPPORTED_EXCHANGES = _DP.SUPPORTED_EXCHANGES
ExchangeLiteral = Literal["binance", "bybit", "okx", "hyperliquid"]


class BacktestRequest(BaseModel):
    """Backtest request parameters"""
    strategy_id: UUID
    start_date: datetime = Field(description="Backtest start date")
    end_date: datetime = Field(description="Backtest end date")
    initial_balance: float = Field(default=10000, ge=100)
    symbols: list[str] | None = Field(default=None, description="Override strategy symbols for backtest")
    use_ai: bool = Field(default=False, description="Use AI for decisions (slow)")
    timeframe: str = Field(default="1h", description="Candle timeframe")
    exchange: ExchangeLiteral = Field(default="hyperliquid", description="Exchange data source")


class TradeRecord(BaseModel):
    """Single closed trade"""
    symbol: str
    side: str
    size: float
    entry_price: float
    exit_price: float
    leverage: int
    pnl: float
    pnl_percent: float
    opened_at: datetime
    closed_at: datetime
    duration_minutes: float
    exit_reason: str


class SideStats(BaseModel):
    """Statistics for one side (long or short)"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    total_pnl: float = 0
    gross_profit: float = 0
    gross_loss: float = 0
    average_win: float = 0
    average_loss: float = 0


class TradeStatistics(BaseModel):
    """Extended trade statistics"""
    average_win: float = 0
    average_loss: float = 0
    largest_win: float = 0
    largest_loss: float = 0
    gross_profit: float = 0
    gross_loss: float = 0
    avg_holding_hours: float = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    expectancy: float = 0
    recovery_factor: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    long_stats: SideStats = Field(default_factory=SideStats)
    short_stats: SideStats = Field(default_factory=SideStats)


class MonthlyReturn(BaseModel):
    """Monthly return data point"""
    month: str
    return_percent: float


class SymbolBreakdown(BaseModel):
    """Per-symbol performance"""
    symbol: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_pnl: float


class BacktestResponse(BaseModel):
    """Backtest result response"""
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
    total_fees: float = 0
    equity_curve: list[dict] = Field(default_factory=list)
    # New fields
    trades: list[TradeRecord] = Field(default_factory=list)
    drawdown_curve: list[dict] = Field(default_factory=list)
    monthly_returns: list[MonthlyReturn] = Field(default_factory=list)
    trade_statistics: Optional[TradeStatistics] = None
    symbol_breakdown: list[SymbolBreakdown] = Field(default_factory=list)


class QuickBacktestRequest(BaseModel):
    """Quick backtest with inline config"""
    symbols: list[str] = Field(default=["BTC", "ETH"])
    start_date: datetime
    end_date: datetime
    initial_balance: float = Field(default=10000, ge=100)
    max_leverage: int = Field(default=5, ge=1, le=100)
    max_position_ratio: float = Field(default=0.2, ge=0.01, le=1.0)
    timeframe: str = Field(default="1h")
    exchange: ExchangeLiteral = Field(default="hyperliquid", description="Exchange data source")


def _build_response(result) -> BacktestResponse:
    """Convert BacktestResult to API response."""
    limit = settings.backtest_equity_curve_limit

    trade_records = [
        TradeRecord(
            symbol=t.symbol,
            side=t.side,
            size=t.size,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            leverage=t.leverage,
            pnl=round(t.pnl, 2),
            pnl_percent=round(t.pnl_percent, 2),
            opened_at=t.opened_at,
            closed_at=t.closed_at,
            duration_minutes=round(t.duration_minutes, 1),
            exit_reason=t.exit_reason,
        )
        for t in result.trades
    ]

    ts = result.trade_statistics
    trade_statistics = TradeStatistics(
        average_win=round(ts.get("average_win", 0), 2),
        average_loss=round(ts.get("average_loss", 0), 2),
        largest_win=round(ts.get("largest_win", 0), 2),
        largest_loss=round(ts.get("largest_loss", 0), 2),
        gross_profit=round(ts.get("gross_profit", 0), 2),
        gross_loss=round(ts.get("gross_loss", 0), 2),
        avg_holding_hours=ts.get("avg_holding_hours", 0),
        max_consecutive_wins=ts.get("max_consecutive_wins", 0),
        max_consecutive_losses=ts.get("max_consecutive_losses", 0),
        expectancy=ts.get("expectancy", 0),
        recovery_factor=ts.get("recovery_factor"),
        sortino_ratio=ts.get("sortino_ratio"),
        calmar_ratio=ts.get("calmar_ratio"),
        long_stats=SideStats(**ts.get("long_stats", {})),
        short_stats=SideStats(**ts.get("short_stats", {})),
    ) if ts else None

    monthly_returns = [
        MonthlyReturn(**m) for m in (result.monthly_returns or [])
    ]

    symbol_breakdown = [
        SymbolBreakdown(**s) for s in (result.symbol_breakdown or [])
    ]

    return BacktestResponse(
        strategy_name=result.strategy_name,
        start_date=result.start_date,
        end_date=result.end_date,
        initial_balance=result.initial_balance,
        final_balance=result.final_balance,
        total_return_percent=result.total_return_percent,
        total_trades=result.total_trades,
        winning_trades=result.winning_trades,
        losing_trades=result.losing_trades,
        win_rate=result.win_rate,
        profit_factor=result.profit_factor,
        max_drawdown_percent=result.max_drawdown_percent,
        sharpe_ratio=result.sharpe_ratio,
        total_fees=result.total_fees,
        equity_curve=result.equity_curve[:limit],
        trades=trade_records,
        drawdown_curve=result.drawdown_curve[:limit],
        monthly_returns=monthly_returns,
        trade_statistics=trade_statistics,
        symbol_breakdown=symbol_breakdown,
    )


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    db: DbSessionDep,
    crypto: CryptoDep,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Run backtest for a saved strategy.

    Fetches historical data and simulates strategy execution.
    """
    # Get strategy
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(request.strategy_id, user_id)

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    # Resolve AI client from DB when use_ai
    ai_client = None
    if request.use_ai:
        model_id = strategy.ai_model
        if not model_id:
            raise create_http_exception(
                ErrorCode.VALIDATION_ERROR,
                user_message="Strategy has no AI model configured. Edit the strategy and select an AI model.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        api_key, base_url = await resolve_provider_credentials(
            db, crypto, UUID(user_id), model_id
        )
        if not api_key and "custom" not in (model_id.split(":")[0] if ":" in model_id else "").lower():
            raise create_http_exception(
                ErrorCode.VALIDATION_ERROR,
                user_message="No API key configured for the selected AI model. Configure the provider in Models / Providers.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        kwargs = {"api_key": api_key or ""}
        if base_url:
            kwargs["base_url"] = base_url
        ai_client = get_ai_client(model_id, **kwargs)

    try:
        # Initialize data provider with user-selected exchange
        data_provider = DataProvider(exchange=request.exchange)
        await data_provider.initialize()

        # Load data
        config = StrategyConfig(**strategy.config) if strategy.config else StrategyConfig()
        if request.symbols:
            config.symbols = request.symbols
        await data_provider.load_data(
            symbols=config.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            timeframe=request.timeframe,
        )

        # Run backtest
        engine = BacktestEngine(
            strategy=strategy,
            initial_balance=request.initial_balance,
            start_date=request.start_date,
            end_date=request.end_date,
            data_provider=data_provider,
            use_ai=request.use_ai,
            ai_client=ai_client,
        )

        result = await engine.run()
        await engine.cleanup()

        return _build_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest failed for strategy {request.strategy_id}: {e}", exc_info=True)
        raise backtest_failed_error(e)


@router.post("/quick", response_model=BacktestResponse)
async def quick_backtest(
    request: QuickBacktestRequest,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Run quick backtest with inline configuration.

    Uses default momentum strategy without AI.
    Good for quick market analysis.
    """
    from ...db.models import StrategyDB
    from ...models.decision import RiskControls

    # Create temporary strategy
    config = StrategyConfig(
        symbols=request.symbols,
        risk_controls=RiskControls(
            max_leverage=request.max_leverage,
            max_position_ratio=request.max_position_ratio,
        ),
    )

    strategy = StrategyDB(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        user_id=user_id,
        name="Quick Backtest",
        description="Temporary backtest",
        config=config.model_dump(),
        status="draft",
    )

    try:
        # Initialize data provider with user-selected exchange
        data_provider = DataProvider(exchange=request.exchange)
        await data_provider.initialize()

        # Load data
        await data_provider.load_data(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            timeframe=request.timeframe,
        )

        # Run backtest
        engine = BacktestEngine(
            strategy=strategy,
            initial_balance=request.initial_balance,
            start_date=request.start_date,
            end_date=request.end_date,
            data_provider=data_provider,
            use_ai=False,
        )

        result = await engine.run()
        await engine.cleanup()

        return _build_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick backtest failed: {e}", exc_info=True)
        raise backtest_failed_error(e)


@router.get("/symbols")
async def get_available_symbols(
    exchange: ExchangeLiteral = Query(default="hyperliquid"),
):
    """
    Get available trading symbols for backtesting.
    """
    try:
        data_provider = DataProvider(exchange=exchange)
        await data_provider.initialize()

        # Get popular futures symbols using the public method
        markets = await data_provider.get_available_markets()

        # Accept any stablecoin-quoted swap market (USDT, USDC, etc.)
        stablecoin_quotes = {"USDT", "USDC", "BUSD", "DAI", "TUSD"}
        symbols = []
        seen_bases: set[str] = set()
        for symbol, market in markets.items():
            if market.get("type") != "swap":
                continue
            if market.get("quote", "") not in stablecoin_quotes:
                continue
            base = market.get("base", "")
            if base and base not in seen_bases:
                seen_bases.add(base)
                symbols.append({
                    "symbol": base,
                    "full_symbol": symbol,
                })

        await data_provider.close()

        # Return all symbols sorted alphabetically
        symbols.sort(key=lambda x: x["symbol"])
        return {"symbols": symbols}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch symbols for {exchange}: {e}", exc_info=True)
        raise create_http_exception(
            code=ErrorCode.EXCHANGE_ERROR,
            user_message=f"Failed to fetch available symbols from {exchange}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            internal_error=e,
            log_error=False,  # Already logged above
        )
