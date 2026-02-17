"""Backtest result repository for database operations

Handles CRUD operations for persisted backtest results.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BacktestResultDB


class BacktestRepository:
    """Repository for backtest result CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        strategy_id: Optional[uuid.UUID],
        strategy_name: str,
        symbols: list[str],
        exchange: str,
        initial_balance: float,
        timeframe: str,
        use_ai: bool,
        start_date: datetime,
        end_date: datetime,
        final_balance: float,
        total_return_percent: float,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        win_rate: float,
        profit_factor: float,
        max_drawdown_percent: float,
        sharpe_ratio: Optional[float],
        sortino_ratio: Optional[float],
        calmar_ratio: Optional[float],
        total_fees: float,
        equity_curve: list,
        drawdown_curve: list,
        trades: list,
        monthly_returns: list,
        trade_statistics: Optional[dict],
        symbol_breakdown: list,
        analysis: Optional[dict],
    ) -> BacktestResultDB:
        """Create a new backtest result record"""
        result = BacktestResultDB(
            user_id=user_id,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbols=symbols,
            exchange=exchange,
            initial_balance=initial_balance,
            timeframe=timeframe,
            use_ai=use_ai,
            start_date=start_date,
            end_date=end_date,
            final_balance=final_balance,
            total_return_percent=total_return_percent,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_fees=total_fees,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            trades=trades,
            monthly_returns=monthly_returns,
            trade_statistics=trade_statistics,
            symbol_breakdown=symbol_breakdown,
            analysis=analysis,
        )
        self.session.add(result)
        await self.session.flush()
        await self.session.refresh(result)
        return result

    async def get_by_id(
        self,
        backtest_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[BacktestResultDB]:
        """Get a backtest result by ID"""
        query = select(BacktestResultDB).where(
            BacktestResultDB.id == backtest_id,
            BacktestResultDB.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[BacktestResultDB]:
        """Get backtest results for a user (paginated)"""
        query = (
            select(BacktestResultDB)
            .where(BacktestResultDB.user_id == user_id)
            .order_by(BacktestResultDB.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """Count total backtest results for a user"""
        query = select(func.count(BacktestResultDB.id)).where(
            BacktestResultDB.user_id == user_id
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_by_strategy(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[BacktestResultDB]:
        """Get backtest results for a specific strategy"""
        query = (
            select(BacktestResultDB)
            .where(
                BacktestResultDB.strategy_id == strategy_id,
                BacktestResultDB.user_id == user_id,
            )
            .order_by(BacktestResultDB.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(
        self,
        backtest_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a backtest result"""
        result = await self.get_by_id(backtest_id, user_id)
        if not result:
            return False
        await self.session.delete(result)
        await self.session.flush()
        return True
