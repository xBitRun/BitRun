"""Quant strategy repository for database operations

Note: QuantStrategyDB is an alias for AgentDB. All 'agent_id' parameters
actually refer to AgentDB.id, not StrategyDB.id.

Architecture:
- StrategyDB stores the strategy logic (type, symbols, config)
- AgentDB (QuantStrategyDB) stores execution settings (account, capital, status)
- Each AgentDB has a strategy_id foreign key to StrategyDB
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import AgentDB, QuantStrategyDB, StrategyDB


class QuantStrategyRepository:
    """Repository for QuantStrategy (Agent) CRUD operations"""

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
        trade_type: str = "crypto_perp",
        execution_interval_minutes: int = 30,
    ) -> QuantStrategyDB:
        """Create a new quant strategy (agent).

        This creates both:
        1. StrategyDB - stores strategy logic (type, symbols, config)
        2. AgentDB - stores execution settings (account, capital, status)

        Name is automatically deduplicated across both strategies and agents
        for the same user.

        Args:
            user_id: Owner user ID
            name: Agent/strategy name
            strategy_type: Strategy type ("grid", "dca", "rsi")
            symbol: Trading symbol (e.g., "BTC")
            config: Strategy-specific configuration
            account_id: Optional exchange account for live trading
            description: Optional description
            allocated_capital: Optional fixed capital allocation
            allocated_capital_percent: Optional percentage-based allocation
            trade_type: Trade type (default: "crypto_perp")
            execution_interval_minutes: Execution interval in minutes

        Returns:
            The created AgentDB instance (QuantStrategyDB alias)
        """
        # Ensure name is unique across strategies and agents
        from ...services.name_check_service import NameCheckService

        name_check = NameCheckService(self.session)
        unique_name = await name_check.generate_unique_name(
            name=name,
            user_id=user_id,
        )

        # Step 1: Create StrategyDB with strategy logic
        strategy_db = StrategyDB(
            user_id=user_id,
            type=strategy_type,
            name=unique_name,
            description=description,
            symbols=[symbol],  # Quant strategies typically use single symbol
            config=config,
            visibility="private",
        )
        self.session.add(strategy_db)
        await self.session.flush()  # Get strategy_db.id

        # Step 2: Create AgentDB with execution settings
        # Note: Both strategy and agent share the same deduplicated name
        agent = AgentDB(
            user_id=user_id,
            name=unique_name,
            strategy_id=strategy_db.id,
            account_id=account_id,
            execution_mode="mock" if account_id is None else "live",
            allocated_capital=allocated_capital,
            allocated_capital_percent=allocated_capital_percent,
            trade_type=trade_type,
            execution_interval_minutes=execution_interval_minutes,
            runtime_state={},
            status="draft",
        )
        self.session.add(agent)
        await self.session.flush()
        await self.session.refresh(agent)

        # Also refresh the strategy relationship
        await self.session.refresh(agent, ["strategy"])

        return agent

    async def get_by_id(
        self,
        agent_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[QuantStrategyDB]:
        """Get quant agent by ID.

        Args:
            agent_id: AgentDB.id (not StrategyDB.id)
            user_id: Optional user filter
        """
        query = (
            select(QuantStrategyDB)
            .options(selectinload(QuantStrategyDB.strategy))
            .where(QuantStrategyDB.id == agent_id)
        )
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
        """Get all quant agents for a user.

        Note:
            strategy_type filter uses StrategyDB.type via JOIN,
            since strategy_type is a property on AgentDB.
        """
        query = (
            select(QuantStrategyDB)
            .options(selectinload(QuantStrategyDB.strategy))
            .where(QuantStrategyDB.user_id == user_id)
        )
        if status:
            query = query.where(QuantStrategyDB.status == status)
        if strategy_type:
            # Must JOIN with StrategyDB to filter by type
            query = query.join(StrategyDB, QuantStrategyDB.strategy_id == StrategyDB.id)
            query = query.where(StrategyDB.type == strategy_type)

        # Secondary sort by id for stable ordering when created_at is equal
        query = query.order_by(
            QuantStrategyDB.created_at.desc(), QuantStrategyDB.id.desc()
        )
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_strategies(self) -> list[QuantStrategyDB]:
        """Get all active quant agents (for worker scheduling).

        Only returns agents with strategy type 'grid', 'dca', or 'rsi'.
        AI strategies are handled by the separate ExecutionWorker system.
        """
        from ..models import StrategyDB

        query = (
            select(QuantStrategyDB)
            .options(selectinload(QuantStrategyDB.strategy))
            .join(StrategyDB, QuantStrategyDB.strategy_id == StrategyDB.id)
            .where(QuantStrategyDB.status == "active")
            .where(StrategyDB.type.in_(["grid", "dca", "rsi"]))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs,
    ) -> Optional[QuantStrategyDB]:
        """Update quant agent fields.

        If name is being updated, it's automatically deduplicated across
        both strategies and agents for the same user. The name is updated
        in both the AgentDB and StrategyDB to keep them in sync.

        Args:
            agent_id: AgentDB.id (not StrategyDB.id)

        Note:
            - "symbol" and "config" are stored in StrategyDB, not AgentDB
            - They are updated via the strategy relationship
        """
        agent = await self.get_by_id(agent_id, user_id)
        if not agent:
            return None

        # Agent-level fields (stored in AgentDB)
        agent_fields = {
            "name",
            "account_id",
            "status",
            "error_message",
            "runtime_state",
            "last_run_at",
            "next_run_at",
            "allocated_capital",
            "allocated_capital_percent",
            "execution_interval_minutes",
            "trade_type",
        }

        # Strategy-level fields (stored in StrategyDB via relationship)
        strategy_fields = {
            "symbol",
            "config",
            "description",
        }

        # Handle name deduplication if name is being updated
        if "name" in kwargs and kwargs["name"] is not None:
            from ...services.name_check_service import NameCheckService

            name_check = NameCheckService(self.session)
            kwargs["name"] = await name_check.generate_unique_name(
                name=kwargs["name"],
                user_id=user_id,
                exclude_agent_id=agent_id,
                exclude_strategy_id=agent.strategy_id,
            )

        for key, value in kwargs.items():
            if key in agent_fields:
                setattr(agent, key, value)
                # Also update strategy name if agent name is being updated
                if key == "name" and agent.strategy:
                    agent.strategy.name = value
            elif key in strategy_fields:
                # Update via strategy relationship
                if agent.strategy:
                    if key == "symbol":
                        # symbol -> symbols list
                        agent.strategy.symbols = [value] if value else []
                    else:
                        setattr(agent.strategy, key, value)

        await self.session.flush()
        await self.session.refresh(agent)
        return agent

    async def update_status(
        self,
        agent_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update quant agent status.

        Args:
            agent_id: AgentDB.id (not StrategyDB.id)
        """
        stmt = (
            update(QuantStrategyDB)
            .where(QuantStrategyDB.id == agent_id)
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
        agent_id: uuid.UUID,
        runtime_state: dict,
    ) -> bool:
        """Update quant agent runtime state.

        Args:
            agent_id: AgentDB.id (not StrategyDB.id)
        """
        stmt = (
            update(QuantStrategyDB)
            .where(QuantStrategyDB.id == agent_id)
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
        agent_id: uuid.UUID,
        pnl_change: float,
        is_win: bool,
        trade_count: int = 1,
    ) -> bool:
        """Update quant agent performance metrics after trade(s).

        Args:
            agent_id: AgentDB.id (not StrategyDB.id)
        """
        strategy = await self.get_by_id(agent_id)
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
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete quant agent.

        Args:
            agent_id: AgentDB.id (not StrategyDB.id)
        """
        strategy = await self.get_by_id(agent_id, user_id)
        if not strategy:
            return False

        await self.session.delete(strategy)
        await self.session.flush()
        return True
