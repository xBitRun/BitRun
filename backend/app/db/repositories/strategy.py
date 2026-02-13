"""Strategy repository for database operations (unified model)

Handles all strategy types: ai, grid, dca, rsi.
Strategy is now a pure logic template - no runtime bindings,
no status, no performance metrics (those live on Agent).
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import StrategyDB


class StrategyRepository:
    """Repository for unified Strategy CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        type: str,
        name: str,
        symbols: list[str],
        config: dict,
        description: str = "",
        visibility: str = "private",
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        forked_from: Optional[uuid.UUID] = None,
    ) -> StrategyDB:
        """Create a new unified strategy"""
        strategy = StrategyDB(
            user_id=user_id,
            type=type,
            name=name,
            description=description,
            symbols=symbols,
            config=config,
            visibility=visibility,
            category=category,
            tags=tags or [],
            forked_from=forked_from,
        )
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def get_by_id(
        self,
        strategy_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[StrategyDB]:
        """
        Get strategy by ID.

        If user_id is provided, ensures the strategy belongs to that user.
        """
        query = select(StrategyDB).where(StrategyDB.id == strategy_id)
        if user_id:
            query = query.where(StrategyDB.user_id == user_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        type_filter: Optional[str] = None,
        visibility: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StrategyDB]:
        """
        Get all strategies for a user.

        Optionally filter by type and visibility.
        """
        query = select(StrategyDB).where(StrategyDB.user_id == user_id)
        if type_filter:
            query = query.where(StrategyDB.type == type_filter)
        if visibility:
            query = query.where(StrategyDB.visibility == visibility)

        query = query.order_by(StrategyDB.updated_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_public(
        self,
        type_filter: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "fork_count",
        limit: int = 50,
        offset: int = 0,
    ) -> list[StrategyDB]:
        """Get public strategies for the marketplace."""
        query = select(StrategyDB).where(StrategyDB.visibility == "public")

        if type_filter:
            query = query.where(StrategyDB.type == type_filter)
        if category:
            query = query.where(StrategyDB.category == category)
        if search:
            query = query.where(
                StrategyDB.name.ilike(f"%{search}%")
                | StrategyDB.description.ilike(f"%{search}%")
            )

        if sort_by == "fork_count":
            query = query.order_by(StrategyDB.fork_count.desc())
        elif sort_by == "newest":
            query = query.order_by(StrategyDB.created_at.desc())
        else:
            query = query.order_by(StrategyDB.updated_at.desc())

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs,
    ) -> Optional[StrategyDB]:
        """Update strategy fields"""
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return None

        allowed_fields = {
            "name", "description", "symbols", "config",
            "visibility", "category", "tags",
        }

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(strategy, key, value)

        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def fork(
        self,
        source_id: uuid.UUID,
        user_id: uuid.UUID,
        name_override: Optional[str] = None,
    ) -> Optional[StrategyDB]:
        """Fork a public strategy to the user's account."""
        source = await self.get_by_id(source_id)
        if not source or source.visibility != "public":
            return None

        forked = StrategyDB(
            user_id=user_id,
            type=source.type,
            name=name_override or source.name,
            description=source.description,
            symbols=source.symbols.copy() if source.symbols else [],
            config=source.config.copy() if source.config else {},
            visibility="private",
            category=source.category,
            tags=source.tags.copy() if source.tags else [],
            forked_from=source.id,
        )
        self.session.add(forked)

        # Increment fork count on source
        source.fork_count = (source.fork_count or 0) + 1

        await self.session.flush()
        await self.session.refresh(forked)
        return forked

    async def delete(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete strategy (only if no agents reference it)"""
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return False

        await self.session.delete(strategy)
        await self.session.flush()
        return True
