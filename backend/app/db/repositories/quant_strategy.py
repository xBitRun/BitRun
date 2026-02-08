"""Quant strategy repository for database operations"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import QuantStrategyDB


class QuantStrategyRepository:
    """Repository for QuantStrategy CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        strategy_type: str,
        symbol: str,
        config: dict,
        account_id: Optional[uuid.UUID] = None,
        description: str = "",
        allocated_capital: Optional[float] = None,
        allocated_capital_percent: Optional[float] = None,
    ) -> QuantStrategyDB:
        """Create a new quant strategy"""
        strategy = QuantStrategyDB(
            user_id=user_id,
            account_id=account_id,
            name=name,
            description=description,
            strategy_type=strategy_type,
            symbol=symbol,
            config=config,
            runtime_state={},
            status="draft",
            allocated_capital=allocated_capital,
            allocated_capital_percent=allocated_capital_percent,
        )
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def get_by_id(
        self,
        strategy_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[QuantStrategyDB]:
        """Get quant strategy by ID."""
        query = select(QuantStrategyDB).where(QuantStrategyDB.id == strategy_id)
        if user_id:
            query = query.where(QuantStrategyDB.user_id == user_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        strategy_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[QuantStrategyDB]:
        """Get all quant strategies for a user."""
        query = select(QuantStrategyDB).where(QuantStrategyDB.user_id == user_id)
        if status:
            query = query.where(QuantStrategyDB.status == status)
        if strategy_type:
            query = query.where(QuantStrategyDB.strategy_type == strategy_type)

        query = query.order_by(QuantStrategyDB.updated_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_strategies(self) -> list[QuantStrategyDB]:
        """Get all active quant strategies (for worker scheduling)"""
        query = select(QuantStrategyDB).where(
            QuantStrategyDB.status == "active"
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs,
    ) -> Optional[QuantStrategyDB]:
        """Update quant strategy fields"""
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return None

        allowed_fields = {
            "name", "description", "symbol", "config",
            "account_id", "status", "error_message",
            "runtime_state", "last_run_at", "next_run_at",
            "allocated_capital", "allocated_capital_percent",
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
        error_message: Optional[str] = None,
    ) -> bool:
        """Update quant strategy status"""
        stmt = (
            update(QuantStrategyDB)
            .where(QuantStrategyDB.id == strategy_id)
            .values(
                status=status,
                error_message=error_message,
                updated_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def update_runtime_state(
        self,
        strategy_id: uuid.UUID,
        runtime_state: dict,
    ) -> bool:
        """Update quant strategy runtime state"""
        stmt = (
            update(QuantStrategyDB)
            .where(QuantStrategyDB.id == strategy_id)
            .values(
                runtime_state=runtime_state,
                last_run_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def update_performance(
        self,
        strategy_id: uuid.UUID,
        pnl_change: float,
        is_win: bool,
        trade_count: int = 1,
    ) -> bool:
        """Update quant strategy performance metrics after trade(s)."""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return False

        strategy.total_pnl += pnl_change
        strategy.total_trades += trade_count
        if is_win:
            strategy.winning_trades += trade_count
        else:
            strategy.losing_trades += trade_count

        if pnl_change < 0 and abs(pnl_change) > strategy.max_drawdown:
            strategy.max_drawdown = abs(pnl_change)

        strategy.last_run_at = datetime.now(UTC)

        await self.session.flush()
        return True

    async def delete(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete quant strategy"""
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return False

        await self.session.delete(strategy)
        await self.session.flush()
        return True
