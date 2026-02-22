"""Agent repository for database operations

Handles CRUD for execution agents (Agent = Strategy + Model + Account/Mock).
"""

import uuid
from datetime import UTC, datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import AgentDB, StrategyDB

if TYPE_CHECKING:
    from ...services.name_check_service import NameCheckService


class AgentRepository:
    """Repository for Agent CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        strategy_id: uuid.UUID,
        execution_mode: str = "mock",
        ai_model: Optional[str] = None,
        account_id: Optional[uuid.UUID] = None,
        mock_initial_balance: Optional[float] = None,
        allocated_capital: Optional[float] = None,
        allocated_capital_percent: Optional[float] = None,
        execution_interval_minutes: int = 30,
        auto_execute: bool = True,
        trade_type: str = "crypto_perp",
        debate_enabled: bool = False,
        debate_models: Optional[list] = None,
        debate_consensus_mode: Optional[str] = None,
        debate_min_participants: int = 2,
    ) -> AgentDB:
        """Create a new agent.

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

        agent = AgentDB(
            user_id=user_id,
            name=unique_name,
            strategy_id=strategy_id,
            ai_model=ai_model,
            execution_mode=execution_mode,
            account_id=account_id,
            mock_initial_balance=mock_initial_balance,
            allocated_capital=allocated_capital,
            allocated_capital_percent=allocated_capital_percent,
            execution_interval_minutes=execution_interval_minutes,
            auto_execute=auto_execute,
            trade_type=trade_type,
            debate_enabled=debate_enabled,
            debate_models=debate_models,
            debate_consensus_mode=debate_consensus_mode,
            debate_min_participants=debate_min_participants,
            status="draft",
        )
        self.session.add(agent)
        await self.session.flush()
        await self.session.refresh(agent)
        return agent

    async def get_by_id(
        self,
        agent_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        include_strategy: bool = False,
        include_decisions: bool = False,
        include_account: bool = False,
    ) -> Optional[AgentDB]:
        """Get agent by ID with optional eager loading."""
        query = select(AgentDB).where(AgentDB.id == agent_id)
        if user_id:
            query = query.where(AgentDB.user_id == user_id)
        if include_strategy:
            query = query.options(selectinload(AgentDB.strategy))
        if include_decisions:
            query = query.options(selectinload(AgentDB.decisions))
        if include_account:
            query = query.options(selectinload(AgentDB.account))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        strategy_type: Optional[str] = None,
        execution_mode: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        include_account: bool = False,
    ) -> list[AgentDB]:
        """
        Get all agents for a user.

        Optionally filter by status, strategy type, or execution mode.
        """
        query = (
            select(AgentDB)
            .where(AgentDB.user_id == user_id)
            .options(selectinload(AgentDB.strategy))
        )
        if include_account:
            query = query.options(selectinload(AgentDB.account))
        if status:
            query = query.where(AgentDB.status == status)
        if execution_mode:
            query = query.where(AgentDB.execution_mode == execution_mode)
        if strategy_type:
            query = query.join(StrategyDB).where(StrategyDB.type == strategy_type)

        # Secondary sort by id for stable ordering when created_at is equal
        query = query.order_by(AgentDB.created_at.desc(), AgentDB.id.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_agents(self) -> list[AgentDB]:
        """Get all active agents (for worker scheduling)"""
        query = (
            select(AgentDB)
            .where(AgentDB.status == "active")
            .options(
                selectinload(AgentDB.strategy),
                selectinload(AgentDB.account),
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs,
    ) -> Optional[AgentDB]:
        """Update agent fields.

        If name is being updated, it's automatically deduplicated if
        a conflict exists with another strategy or agent for the same user.
        """
        agent = await self.get_by_id(agent_id, user_id)
        if not agent:
            return None

        allowed_fields = {
            "name", "ai_model",
            "execution_mode", "account_id", "mock_initial_balance",
            "allocated_capital", "allocated_capital_percent",
            "execution_interval_minutes", "auto_execute",
            "runtime_state",
            "trade_type",
            "debate_enabled", "debate_models", "debate_consensus_mode", "debate_min_participants",
        }

        # Handle name deduplication if name is being updated
        if "name" in kwargs and kwargs["name"] is not None:
            from ...services.name_check_service import NameCheckService
            name_check = NameCheckService(self.session)
            kwargs["name"] = await name_check.generate_unique_name(
                name=kwargs["name"],
                user_id=user_id,
                exclude_agent_id=agent_id,
            )

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(agent, key, value)

        await self.session.flush()
        await self.session.refresh(agent)
        return agent

    async def update_status(
        self,
        agent_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update agent status"""
        values: dict = {
            "status": status,
            "error_message": error_message,
            "updated_at": datetime.now(UTC),
        }
        stmt = (
            update(AgentDB)
            .where(AgentDB.id == agent_id)
            .values(**values)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def update_performance(
        self,
        agent_id: uuid.UUID,
        pnl_change: float,
        is_win: bool,
    ) -> bool:
        """Update agent performance metrics after a trade."""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return False

        agent.total_pnl += pnl_change
        agent.total_trades += 1
        if is_win:
            agent.winning_trades += 1
        else:
            agent.losing_trades += 1

        if pnl_change < 0 and abs(pnl_change) > agent.max_drawdown:
            agent.max_drawdown = abs(pnl_change)

        agent.last_run_at = datetime.now(UTC)

        await self.session.flush()
        return True

    async def update_runtime_state(
        self,
        agent_id: uuid.UUID,
        runtime_state: dict,
    ) -> bool:
        """Update quant agent runtime state."""
        stmt = (
            update(AgentDB)
            .where(AgentDB.id == agent_id)
            .values(
                runtime_state=runtime_state,
                updated_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def delete(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete agent"""
        agent = await self.get_by_id(agent_id, user_id)
        if not agent:
            return False

        await self.session.delete(agent)
        await self.session.flush()
        return True

    async def get_live_agent_by_account_id(
        self,
        account_id: uuid.UUID,
        exclude_agent_id: Optional[uuid.UUID] = None,
    ) -> Optional[AgentDB]:
        """
        Get active/live agent bound to a specific account.

        Used to prevent multiple agents from binding to the same exchange account.

        Args:
            account_id: The exchange account ID to check
            exclude_agent_id: Optional agent ID to exclude from the check (for updates)

        Returns:
            The agent bound to this account, or None if no binding exists
        """
        query = (
            select(AgentDB)
            .where(AgentDB.account_id == account_id)
            .where(AgentDB.execution_mode == "live")
            .where(AgentDB.status.in_(["active", "draft", "paused"]))
        )
        if exclude_agent_id:
            query = query.where(AgentDB.id != exclude_agent_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_bound_account_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        """
        Get all account IDs that are bound to active/live agents for a user.

        Used by frontend to show which accounts are already in use.
        """
        query = (
            select(AgentDB.account_id)
            .where(AgentDB.user_id == user_id)
            .where(AgentDB.account_id.isnot(None))
            .where(AgentDB.execution_mode == "live")
            .where(AgentDB.status.in_(["active", "draft", "paused"]))
        )
        result = await self.session.execute(query)
        return {row[0] for row in result.all()}

    async def get_account_allocated_percent(
        self,
        account_id: uuid.UUID,
        exclude_agent_id: Optional[uuid.UUID] = None,
    ) -> float:
        """
        Get the sum of allocated_capital_percent for all live agents on an account.

        Only considers agents with percentage allocation (not fixed amount).

        Args:
            account_id: The exchange account ID
            exclude_agent_id: Optional agent ID to exclude (for updates)

        Returns:
            Sum of allocated_capital_percent (0.0 to 1.0+)
        """
        query = (
            select(func.coalesce(func.sum(AgentDB.allocated_capital_percent), 0.0))
            .where(AgentDB.account_id == account_id)
            .where(AgentDB.execution_mode == "live")
            .where(AgentDB.status.in_(["active", "draft", "paused"]))
            .where(AgentDB.allocated_capital_percent.isnot(None))
        )
        if exclude_agent_id:
            query = query.where(AgentDB.id != exclude_agent_id)

        result = await self.session.execute(query)
        return float(result.scalar() or 0.0)

    async def get_account_allocation_summary(
        self,
        account_id: uuid.UUID,
    ) -> dict:
        """
        Get capital allocation summary for an account.

        Returns:
            {
                "total_percent": float,
                "allocation_mode": "percent" | "fixed" | None,
                "agents": [
                    {
                        "id": str,
                        "name": str,
                        "allocated_capital_percent": float | None,
                        "allocated_capital": float | None,
                    }
                ]
            }
        """
        query = (
            select(AgentDB)
            .where(AgentDB.account_id == account_id)
            .where(AgentDB.execution_mode == "live")
            .where(AgentDB.status.in_(["active", "draft", "paused"]))
        )
        result = await self.session.execute(query)
        agents = list(result.scalars().all())

        total_percent = sum(
            a.allocated_capital_percent or 0.0
            for a in agents
            if a.allocated_capital_percent is not None
        )

        # Determine allocation mode from existing agents
        has_percent = any(a.allocated_capital_percent is not None for a in agents)
        has_fixed = any(a.allocated_capital is not None for a in agents)

        if has_percent and not has_fixed:
            allocation_mode = "percent"
        elif has_fixed and not has_percent:
            allocation_mode = "fixed"
        else:
            allocation_mode = None  # Mixed or neither

        return {
            "total_percent": total_percent,
            "allocation_mode": allocation_mode,
            "agents": [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "allocated_capital_percent": a.allocated_capital_percent,
                    "allocated_capital": a.allocated_capital,
                }
                for a in agents
            ],
        }
