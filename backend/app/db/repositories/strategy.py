"""Strategy repository for database operations (unified model)

Handles all strategy types: ai, grid, dca, rsi.
Strategy is now a pure logic template - no runtime bindings,
no status, no performance metrics (those live on Agent).
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import StrategyDB, StrategyVersionDB


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
        is_paid: bool = False,
        price_monthly: Optional[float] = None,
        pricing_model: str = "free",
    ) -> StrategyDB:
        """Create a new unified strategy.

        Name is automatically deduplicated if a conflict exists with
        another strategy or agent for the same user.
        """
        # Ensure name is unique across strategies and agents
        from ...services.name_check_service import NameCheckService

        name_check = NameCheckService(self.session)
        unique_name = await name_check.generate_unique_name(
            name=name,
            user_id=user_id,
        )

        strategy = StrategyDB(
            user_id=user_id,
            type=type,
            name=unique_name,
            description=description,
            symbols=symbols,
            config=config,
            visibility=visibility,
            category=category,
            tags=tags or [],
            forked_from=forked_from,
            is_paid=is_paid,
            price_monthly=price_monthly,
            pricing_model=pricing_model,
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

        # Eager load agents to avoid lazy loading in async context
        query = query.options(selectinload(StrategyDB.agents))

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

        # Eager load agents to avoid lazy loading in async context
        query = query.options(selectinload(StrategyDB.agents))

        # Secondary sort by id for stable ordering when created_at is equal
        query = query.order_by(StrategyDB.created_at.desc(), StrategyDB.id.desc())
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
    ) -> tuple[list[StrategyDB], int]:
        """Get public strategies for the marketplace.

        Returns (strategies, total_count) tuple for pagination.
        """
        base_filter = StrategyDB.visibility == "public"
        filters = [base_filter]

        if type_filter:
            filters.append(StrategyDB.type == type_filter)
        if category:
            filters.append(StrategyDB.category == category)
        if search:
            filters.append(
                StrategyDB.name.ilike(f"%{search}%")
                | StrategyDB.description.ilike(f"%{search}%")
            )

        # Count total
        count_query = select(func.count(StrategyDB.id)).where(*filters)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Fetch page with user relationship eagerly loaded
        query = (
            select(StrategyDB).where(*filters).options(selectinload(StrategyDB.user))
        )

        # Secondary sort by id for stable ordering when primary sort field is equal
        if sort_by == "fork_count":
            query = query.order_by(StrategyDB.fork_count.desc(), StrategyDB.id.desc())
        elif sort_by == "newest":
            query = query.order_by(StrategyDB.created_at.desc(), StrategyDB.id.desc())
        else:
            query = query.order_by(StrategyDB.created_at.desc(), StrategyDB.id.desc())

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
        change_note: str = "",
        **kwargs,
    ) -> Optional[StrategyDB]:
        """Update strategy fields. Auto-snapshots config changes.

        If name is being updated, it's automatically deduplicated if
        a conflict exists with another strategy or agent for the same user.
        """
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return None

        # Determine if we need to snapshot (config, symbols, or description changed)
        versioned_fields = {"config", "symbols", "description", "name"}
        needs_snapshot = any(
            key in versioned_fields and kwargs.get(key) is not None for key in kwargs
        )

        if needs_snapshot:
            await self._create_version_snapshot(strategy, change_note)

        allowed_fields = {
            "name",
            "description",
            "symbols",
            "config",
            "visibility",
            "category",
            "tags",
            "is_paid",
            "price_monthly",
            "pricing_model",
        }

        # Handle name deduplication if name is being updated
        if "name" in kwargs and kwargs["name"] is not None:
            from ...services.name_check_service import NameCheckService

            name_check = NameCheckService(self.session)
            kwargs["name"] = await name_check.generate_unique_name(
                name=kwargs["name"],
                user_id=user_id,
                exclude_strategy_id=strategy_id,
            )

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
        """Fork a public strategy to the user's account.

        Name is automatically deduplicated if a conflict exists.
        Records forked_from relationship for marketplace tracking.
        """
        source = await self.get_by_id(source_id)
        if not source or source.visibility != "public":
            return None

        # Determine the name to use
        requested_name = name_override or source.name

        # Ensure name is unique across strategies and agents
        from ...services.name_check_service import NameCheckService

        name_check = NameCheckService(self.session)
        unique_name = await name_check.generate_unique_name(
            name=requested_name,
            user_id=user_id,
        )

        forked = StrategyDB(
            user_id=user_id,
            type=source.type,
            name=unique_name,
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

    async def duplicate(
        self,
        source_id: uuid.UUID,
        user_id: uuid.UUID,
        name_override: Optional[str] = None,
    ) -> Optional[StrategyDB]:
        """Duplicate a user's own strategy.

        Creates a completely independent copy without forked_from tracking.
        Name is automatically deduplicated if a conflict exists.
        Default name format: "{original_name} (副本)"
        """
        source = await self.get_by_id(source_id, user_id)
        if not source:
            return None

        # Determine the name to use (default to "{name} (副本)")
        requested_name = name_override or f"{source.name} (副本)"

        # Ensure name is unique across strategies and agents
        from ...services.name_check_service import NameCheckService

        name_check = NameCheckService(self.session)
        unique_name = await name_check.generate_unique_name(
            name=requested_name,
            user_id=user_id,
        )

        duplicated = StrategyDB(
            user_id=user_id,
            type=source.type,
            name=unique_name,
            description=source.description,
            symbols=source.symbols.copy() if source.symbols else [],
            config=source.config.copy() if source.config else {},
            visibility="private",  # Duplicates always start as private
            category=source.category,
            tags=source.tags.copy() if source.tags else [],
            # No forked_from - this is a pure duplicate, not a marketplace fork
        )
        self.session.add(duplicated)

        await self.session.flush()
        await self.session.refresh(duplicated)
        return duplicated

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

    # =========================================================================
    # Version management
    # =========================================================================

    async def _create_version_snapshot(
        self,
        strategy: StrategyDB,
        change_note: str = "",
    ) -> StrategyVersionDB:
        """Create a version snapshot of the current strategy state."""
        # Get next version number
        count_query = select(func.count(StrategyVersionDB.id)).where(
            StrategyVersionDB.strategy_id == strategy.id
        )
        result = await self.session.execute(count_query)
        current_count = result.scalar() or 0
        next_version = current_count + 1

        version = StrategyVersionDB(
            strategy_id=strategy.id,
            version=next_version,
            name=strategy.name,
            description=strategy.description or "",
            symbols=strategy.symbols.copy() if strategy.symbols else [],
            config=strategy.config.copy() if strategy.config else {},
            change_note=change_note,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_versions(
        self,
        strategy_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StrategyVersionDB]:
        """Get version history for a strategy."""
        # Verify ownership
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return []

        query = (
            select(StrategyVersionDB)
            .where(StrategyVersionDB.strategy_id == strategy_id)
            .order_by(StrategyVersionDB.version.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_version(
        self,
        strategy_id: uuid.UUID,
        version: int,
        user_id: uuid.UUID,
    ) -> Optional[StrategyVersionDB]:
        """Get a specific version snapshot."""
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return None

        query = select(StrategyVersionDB).where(
            StrategyVersionDB.strategy_id == strategy_id,
            StrategyVersionDB.version == version,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def restore_version(
        self,
        strategy_id: uuid.UUID,
        version: int,
        user_id: uuid.UUID,
    ) -> Optional[StrategyDB]:
        """Restore a strategy to a previous version.

        Creates a new version snapshot of current state, then applies
        the old version's config/symbols/description.
        """
        strategy = await self.get_by_id(strategy_id, user_id)
        if not strategy:
            return None

        version_snapshot = await self.get_version(strategy_id, version, user_id)
        if not version_snapshot:
            return None

        # Snapshot current state before restoring
        await self._create_version_snapshot(
            strategy,
            change_note=f"Auto-snapshot before restoring to v{version}",
        )

        # Apply old version's state
        strategy.name = version_snapshot.name
        strategy.description = version_snapshot.description
        strategy.symbols = (
            version_snapshot.symbols.copy() if version_snapshot.symbols else []
        )
        strategy.config = (
            version_snapshot.config.copy() if version_snapshot.config else {}
        )

        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy
