"""Strategy repository for database operations"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import StrategyDB


class StrategyRepository:
    """Repository for Strategy CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        prompt: str,
        account_id: Optional[uuid.UUID] = None,
        description: str = "",
        trading_mode: str = "conservative",
        config: Optional[dict] = None,
        ai_model: Optional[str] = None,
        allocated_capital: Optional[float] = None,
        allocated_capital_percent: Optional[float] = None,
    ) -> StrategyDB:
        """Create a new strategy"""
        strategy = StrategyDB(
            user_id=user_id,
            account_id=account_id,
            name=name,
            description=description,
            prompt=prompt,
            trading_mode=trading_mode,
            config=config or {},
            ai_model=ai_model,
            allocated_capital=allocated_capital,
            allocated_capital_percent=allocated_capital_percent,
            status="draft",
        )
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def get_by_id(
        self,
        strategy_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        include_decisions: bool = False
    ) -> Optional[StrategyDB]:
        """
        Get strategy by ID.

        If user_id is provided, ensures the strategy belongs to that user.
        """
        query = select(StrategyDB).where(StrategyDB.id == strategy_id)
        if user_id:
            query = query.where(StrategyDB.user_id == user_id)
        if include_decisions:
            query = query.options(selectinload(StrategyDB.decisions))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[StrategyDB]:
        """
        Get all strategies for a user.

        Optionally filter by status.
        """
        query = select(StrategyDB).where(StrategyDB.user_id == user_id)
        if status:
            query = query.where(StrategyDB.status == status)

        query = query.order_by(StrategyDB.updated_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_strategies(self) -> list[StrategyDB]:
        """Get all active strategies (for worker scheduling)"""
        query = select(StrategyDB).where(
            StrategyDB.status == "active"
        ).options(
            selectinload(StrategyDB.account)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs
    ) -> Optional[StrategyDB]:
        """Update strategy fields"""
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return None

        allowed_fields = {
            "name", "description", "prompt", "trading_mode",
            "config", "account_id", "ai_model", "status", "error_message",
            "last_run_at", "next_run_at"
        }

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(strategy, key, value)

        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def update_status(
        self,
        strategy_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Update strategy status"""
        stmt = (
            update(StrategyDB)
            .where(StrategyDB.id == strategy_id)
            .values(
                status=status,
                error_message=error_message,
                updated_at=datetime.now(UTC)
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def update_performance(
        self,
        strategy_id: uuid.UUID,
        pnl_change: float,
        is_win: bool
    ) -> bool:
        """
        Update strategy performance metrics after a trade.

        Args:
            strategy_id: Strategy ID
            pnl_change: P/L change from this trade
            is_win: Whether this was a winning trade
        """
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return False

        strategy.total_pnl += pnl_change
        strategy.total_trades += 1
        if is_win:
            strategy.winning_trades += 1
        else:
            strategy.losing_trades += 1

        # Update max drawdown if applicable
        if pnl_change < 0 and abs(pnl_change) > strategy.max_drawdown:
            strategy.max_drawdown = abs(pnl_change)

        strategy.last_run_at = datetime.now(UTC)

        await self.session.flush()
        return True

    async def delete(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Delete strategy"""
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return False

        await self.session.delete(strategy)
        await self.session.flush()
        return True
