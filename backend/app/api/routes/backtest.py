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
from ...db.repositories.backtest import BacktestRepository
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
    ai_model: str | None = Field(default=None, description="AI model ID for AI strategies (e.g., 'deepseek:deepseek-chat')")
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


class BacktestAnalysis(BaseModel):
    """Backtest result analysis"""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


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
    analysis: Optional[BacktestAnalysis] = None


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
    trades_limit = settings.backtest_trades_limit

    # Limit trades to most recent ones (trades are in chronological order)
    # Keep the latest trades_limit trades to avoid large response size
    trades_to_return = result.trades[-trades_limit:] if len(result.trades) > trades_limit else result.trades

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
        for t in trades_to_return
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

    analysis = None
    if result.analysis:
        analysis = BacktestAnalysis(
            strengths=result.analysis.strengths,
            weaknesses=result.analysis.weaknesses,
            recommendations=result.analysis.recommendations,
        )

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
        analysis=analysis,
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

    # Resolve AI client from request.ai_model
    ai_client = None
    analysis_ai_client = None
    if request.use_ai:
        model_id = request.ai_model
        if not model_id:
            raise create_http_exception(
                ErrorCode.VALIDATION_ERROR,
                user_message="AI model is required when use_ai is enabled. Please select an AI model.",
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

    # Resolve AI client for analysis (use request's AI model if available)
    if request.ai_model:
        try:
            model_id = request.ai_model
            api_key, base_url = await resolve_provider_credentials(
                db, crypto, UUID(user_id), model_id
            )
            if api_key or "custom" in (model_id.split(":")[0] if ":" in model_id else "").lower():
                kwargs = {"api_key": api_key or ""}
                if base_url:
                    kwargs["base_url"] = base_url
                analysis_ai_client = get_ai_client(model_id, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to initialize analysis AI client: {e}")
            # Continue without analysis if AI client setup fails

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
            analysis_ai_client=analysis_ai_client,
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
    db: DbSessionDep = None,
    crypto: CryptoDep = None,
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

    # Quick backtest doesn't use AI for analysis (no strategy AI model)
    analysis_ai_client = None

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
            analysis_ai_client=analysis_ai_client,
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


# =============================================================================
# Persisted Backtest Records API
# =============================================================================

# Create a new router for /backtests (plural) to avoid conflict with /backtest
records_router = APIRouter(prefix="/backtests", tags=["backtest"])


class BacktestListItem(BaseModel):
    """List item for backtest results"""
    id: UUID
    strategy_name: str
    symbols: list[str]
    exchange: str
    start_date: datetime
    end_date: datetime
    initial_balance: float
    final_balance: float
    total_return_percent: float
    total_trades: int
    win_rate: float
    max_drawdown_percent: float
    sharpe_ratio: Optional[float] = None
    created_at: datetime


class BacktestListResponse(BaseModel):
    """Paginated backtest list"""
    items: list[BacktestListItem]
    total: int
    limit: int
    offset: int


class BacktestDetailResponse(BacktestResponse):
    """Full backtest result with id and timestamps"""
    id: UUID
    strategy_id: Optional[UUID] = None
    use_ai: bool = False
    timeframe: str = "1h"
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    created_at: datetime


def _build_list_item(record) -> BacktestListItem:
    """Convert BacktestResultDB to list item."""
    return BacktestListItem(
        id=record.id,
        strategy_name=record.strategy_name,
        symbols=record.symbols or [],
        exchange=record.exchange,
        start_date=record.start_date,
        end_date=record.end_date,
        initial_balance=record.initial_balance,
        final_balance=record.final_balance,
        total_return_percent=record.total_return_percent,
        total_trades=record.total_trades,
        win_rate=record.win_rate,
        max_drawdown_percent=record.max_drawdown_percent,
        sharpe_ratio=record.sharpe_ratio,
        created_at=record.created_at,
    )


def _build_detail_response(record) -> BacktestDetailResponse:
    """Convert BacktestResultDB to detail response."""
    limit = settings.backtest_equity_curve_limit
    trades_limit = settings.backtest_trades_limit

    # Build trades
    trades_data = record.trades or []
    trades_to_return = trades_data[-trades_limit:] if len(trades_data) > trades_limit else trades_data
    trade_records = [
        TradeRecord(
            symbol=t.get("symbol", ""),
            side=t.get("side", ""),
            size=t.get("size", 0),
            entry_price=t.get("entry_price", 0),
            exit_price=t.get("exit_price", 0),
            leverage=t.get("leverage", 1),
            pnl=round(t.get("pnl", 0), 2),
            pnl_percent=round(t.get("pnl_percent", 0), 2),
            opened_at=t.get("opened_at"),
            closed_at=t.get("closed_at"),
            duration_minutes=round(t.get("duration_minutes", 0), 1),
            exit_reason=t.get("exit_reason", ""),
        )
        for t in trades_to_return
    ]

    # Build trade statistics
    ts = record.trade_statistics or {}
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

    # Build monthly returns
    monthly_returns = [
        MonthlyReturn(**m) for m in (record.monthly_returns or [])
    ]

    # Build symbol breakdown
    symbol_breakdown = [
        SymbolBreakdown(**s) for s in (record.symbol_breakdown or [])
    ]

    # Build analysis
    analysis = None
    if record.analysis:
        analysis = BacktestAnalysis(
            strengths=record.analysis.get("strengths", []),
            weaknesses=record.analysis.get("weaknesses", []),
            recommendations=record.analysis.get("recommendations", []),
        )

    return BacktestDetailResponse(
        id=record.id,
        strategy_id=record.strategy_id,
        strategy_name=record.strategy_name,
        use_ai=record.use_ai,
        timeframe=record.timeframe,
        start_date=record.start_date,
        end_date=record.end_date,
        initial_balance=record.initial_balance,
        final_balance=record.final_balance,
        total_return_percent=record.total_return_percent,
        total_trades=record.total_trades,
        winning_trades=record.winning_trades,
        losing_trades=record.losing_trades,
        win_rate=record.win_rate,
        profit_factor=record.profit_factor,
        max_drawdown_percent=record.max_drawdown_percent,
        sharpe_ratio=record.sharpe_ratio,
        sortino_ratio=record.sortino_ratio,
        calmar_ratio=record.calmar_ratio,
        total_fees=record.total_fees,
        equity_curve=(record.equity_curve or [])[:limit],
        trades=trade_records,
        drawdown_curve=(record.drawdown_curve or [])[:limit],
        monthly_returns=monthly_returns,
        trade_statistics=trade_statistics,
        symbol_breakdown=symbol_breakdown,
        analysis=analysis,
        created_at=record.created_at,
    )


@records_router.get("", response_model=BacktestListResponse)
async def list_backtests(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _rate_limit: RateLimitApiDep = None,
):
    """
    List persisted backtest results for the current user.
    """
    repo = BacktestRepository(db)
    records = await repo.get_by_user(UUID(user_id), limit=limit, offset=offset)
    total = await repo.count_by_user(UUID(user_id))

    return BacktestListResponse(
        items=[_build_list_item(r) for r in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@records_router.post("", response_model=BacktestDetailResponse)
async def create_backtest(
    request: BacktestRequest,
    db: DbSessionDep,
    crypto: CryptoDep,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Run backtest and save the result.

    This runs the backtest and persists the result to the database.
    """
    # Get strategy
    strategy_repo = StrategyRepository(db)
    strategy = await strategy_repo.get_by_id(request.strategy_id, user_id)

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    # Resolve AI client from request.ai_model
    ai_client = None
    analysis_ai_client = None
    if request.use_ai:
        model_id = request.ai_model
        if not model_id:
            raise create_http_exception(
                ErrorCode.VALIDATION_ERROR,
                user_message="AI model is required when use_ai is enabled. Please select an AI model.",
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

    # Resolve AI client for analysis
    if request.ai_model:
        try:
            model_id = request.ai_model
            api_key, base_url = await resolve_provider_credentials(
                db, crypto, UUID(user_id), model_id
            )
            if api_key or "custom" in (model_id.split(":")[0] if ":" in model_id else "").lower():
                kwargs = {"api_key": api_key or ""}
                if base_url:
                    kwargs["base_url"] = base_url
                analysis_ai_client = get_ai_client(model_id, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to initialize analysis AI client: {e}")

    try:
        # Initialize data provider
        data_provider = DataProvider(exchange=request.exchange)
        await data_provider.initialize()

        # Load data
        config = StrategyConfig(**strategy.config) if strategy.config else StrategyConfig()
        symbols = request.symbols or config.symbols
        await data_provider.load_data(
            symbols=symbols,
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
            analysis_ai_client=analysis_ai_client,
        )

        result = await engine.run()
        await engine.cleanup()

        # Persist result
        backtest_repo = BacktestRepository(db)
        record = await backtest_repo.create(
            user_id=UUID(user_id),
            strategy_id=strategy.id,
            strategy_name=result.strategy_name,
            symbols=symbols,
            exchange=request.exchange,
            initial_balance=result.initial_balance,
            timeframe=request.timeframe,
            use_ai=request.use_ai,
            start_date=result.start_date,
            end_date=result.end_date,
            final_balance=result.final_balance,
            total_return_percent=result.total_return_percent,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            win_rate=result.win_rate,
            profit_factor=result.profit_factor,
            max_drawdown_percent=result.max_drawdown_percent,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=result.sortino_ratio,
            calmar_ratio=result.calmar_ratio,
            total_fees=result.total_fees,
            equity_curve=result.equity_curve,
            drawdown_curve=result.drawdown_curve,
            trades=[
                {
                    "symbol": t.symbol,
                    "side": t.side,
                    "size": t.size,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "leverage": t.leverage,
                    "pnl": t.pnl,
                    "pnl_percent": t.pnl_percent,
                    "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                    "closed_at": t.closed_at.isoformat() if t.closed_at else None,
                    "duration_minutes": t.duration_minutes,
                    "exit_reason": t.exit_reason,
                }
                for t in result.trades
            ],
            monthly_returns=result.monthly_returns or [],
            trade_statistics=result.trade_statistics,
            symbol_breakdown=result.symbol_breakdown or [],
            analysis={
                "strengths": result.analysis.strengths if result.analysis else [],
                "weaknesses": result.analysis.weaknesses if result.analysis else [],
                "recommendations": result.analysis.recommendations if result.analysis else [],
            } if result.analysis else None,
        )

        return _build_detail_response(record)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest failed for strategy {request.strategy_id}: {e}", exc_info=True)
        raise backtest_failed_error(e)


@records_router.get("/{backtest_id}", response_model=BacktestDetailResponse)
async def get_backtest(
    backtest_id: UUID,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Get a persisted backtest result by ID.
    """
    repo = BacktestRepository(db)
    record = await repo.get_by_id(backtest_id, UUID(user_id))

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest result not found"
        )

    return _build_detail_response(record)


@records_router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest(
    backtest_id: UUID,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Delete a persisted backtest result.
    """
    repo = BacktestRepository(db)
    deleted = await repo.delete(backtest_id, UUID(user_id))

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest result not found"
        )

    return None
