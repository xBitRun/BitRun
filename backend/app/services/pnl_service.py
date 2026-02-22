"""
P&L Service - Profit and Loss tracking and analytics.

Provides services for:
- Recording P&L when positions are closed
- Calculating account-level P&L summaries
- Generating equity curve data
- Creating daily snapshots for historical tracking
"""

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db.models import (
    AgentDB,
    AgentPositionDB,
    DailyAccountSnapshotDB,
    DailyAgentSnapshotDB,
    ExchangeAccountDB,
    PnlRecordDB,
)

logger = logging.getLogger(__name__)


class PnLService:
    """Service for P&L calculations and analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # P&L Recording
    # =========================================================================

    async def record_pnl_from_position(
        self,
        position: AgentPositionDB,
        close_price: float,
        realized_pnl: float,
        fees: float = 0.0,
        exit_reason: Optional[str] = None,
    ) -> PnlRecordDB:
        """
        Create a P&L record when a position is closed.

        Args:
            position: The closed position record
            close_price: Price at which position was closed
            realized_pnl: Realized profit/loss from the trade
            fees: Trading fees
            exit_reason: Reason for exit (take_profit, stop_loss, signal, manual)

        Returns:
            The created PnlRecordDB instance
        """
        # Calculate duration
        duration_minutes = 0
        if position.opened_at and position.closed_at:
            duration = position.closed_at - position.opened_at
            duration_minutes = int(duration.total_seconds() / 60)

        # Get agent for user_id
        agent_result = await self.db.execute(
            select(AgentDB).where(AgentDB.id == position.agent_id)
        )
        agent = agent_result.scalars().first()
        if not agent:
            raise ValueError(f"Agent not found: {position.agent_id}")

        record = PnlRecordDB(
            user_id=agent.user_id,
            agent_id=position.agent_id,
            account_id=position.account_id,
            position_id=position.id,
            symbol=position.symbol,
            side=position.side,
            realized_pnl=realized_pnl,
            fees=fees,
            entry_price=position.entry_price,
            exit_price=close_price,
            size=position.size,
            size_usd=position.size_usd,
            leverage=position.leverage,
            opened_at=position.opened_at,
            closed_at=position.closed_at or datetime.now(UTC),
            duration_minutes=duration_minutes,
            exit_reason=exit_reason,
        )

        self.db.add(record)
        await self.db.flush()

        logger.info(
            f"Recorded P&L: {position.symbol} {position.side} "
            f"pnl={realized_pnl:.2f} fees={fees:.2f}"
        )

        return record

    # =========================================================================
    # P&L Summaries
    # =========================================================================

    async def get_agent_pnl_summary(
        self,
        agent_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """
        Calculate P&L summary for an agent.

        Args:
            agent_id: The agent's UUID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with P&L summary metrics
        """
        # Build query
        stmt = select(PnlRecordDB).where(PnlRecordDB.agent_id == agent_id)

        if start_date:
            stmt = stmt.where(PnlRecordDB.closed_at >= start_date)
        if end_date:
            stmt = stmt.where(PnlRecordDB.closed_at < end_date + timedelta(days=1))

        result = await self.db.execute(stmt)
        records = list(result.scalars().all())

        if not records:
            return {
                "total_pnl": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "total_fees": 0.0,
            }

        total_pnl = sum(r.realized_pnl for r in records)
        total_trades = len(records)
        winning_trades = [r for r in records if r.realized_pnl > 0]
        losing_trades = [r for r in records if r.realized_pnl < 0]
        total_wins = sum(r.realized_pnl for r in winning_trades)
        total_losses = abs(sum(r.realized_pnl for r in losing_trades))
        total_fees = sum(r.fees for r in records)

        return {
            "total_pnl": round(total_pnl, 2),
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": (
                round((len(winning_trades) / total_trades) * 100, 2)
                if total_trades > 0
                else 0.0
            ),
            "avg_win": (
                round(total_wins / len(winning_trades), 2) if winning_trades else 0.0
            ),
            "avg_loss": (
                round(total_losses / len(losing_trades), 2) if losing_trades else 0.0
            ),
            "profit_factor": (
                round(total_wins / total_losses, 2)
                if total_losses > 0
                else float("inf") if total_wins > 0 else 0.0
            ),
            "total_fees": round(total_fees, 2),
        }

    async def get_account_pnl_summary(
        self,
        account_id: uuid.UUID,
        period: str = "all",
    ) -> dict:
        """
        Calculate P&L summary for an account.

        Args:
            account_id: The account's UUID
            period: Time period ('all', 'day', 'week', 'month')

        Returns:
            Dictionary with P&L summary metrics
        """
        now = datetime.now(UTC)
        today = now.date()

        # Calculate start date based on period
        if period == "day":
            start_date = today
        elif period == "week":
            start_date = today - timedelta(days=today.weekday())
        elif period == "month":
            start_date = today.replace(day=1)
        else:
            start_date = None

        # Build query
        stmt = select(PnlRecordDB).where(PnlRecordDB.account_id == account_id)

        if start_date:
            stmt = stmt.where(PnlRecordDB.closed_at >= start_date)

        result = await self.db.execute(stmt)
        records = list(result.scalars().all())

        if not records:
            return {
                "total_pnl": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
            }

        total_pnl = sum(r.realized_pnl for r in records)
        total_trades = len(records)
        winning_trades = [r for r in records if r.realized_pnl > 0]
        losing_trades = [r for r in records if r.realized_pnl < 0]
        total_wins = sum(r.realized_pnl for r in winning_trades)
        total_losses = abs(sum(r.realized_pnl for r in losing_trades))

        return {
            "total_pnl": round(total_pnl, 2),
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": (
                round((len(winning_trades) / total_trades) * 100, 2)
                if total_trades > 0
                else 0.0
            ),
            "profit_factor": (
                round(total_wins / total_losses, 2)
                if total_losses > 0
                else float("inf") if total_wins > 0 else 0.0
            ),
        }

    # =========================================================================
    # Equity Curve
    # =========================================================================

    async def get_account_equity_curve(
        self,
        account_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        granularity: str = "day",
    ) -> list[dict]:
        """
        Get equity curve data points for an account.

        Args:
            account_id: The account's UUID
            start_date: Start date for the curve
            end_date: End date for the curve
            granularity: Data granularity ('day', 'week', 'month')

        Returns:
            List of equity data points
        """
        # Default to last 30 days if not specified
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Query daily snapshots
        stmt = (
            select(DailyAccountSnapshotDB)
            .where(
                and_(
                    DailyAccountSnapshotDB.account_id == account_id,
                    DailyAccountSnapshotDB.snapshot_date >= start_date,
                    DailyAccountSnapshotDB.snapshot_date <= end_date,
                )
            )
            .order_by(DailyAccountSnapshotDB.snapshot_date)
        )

        result = await self.db.execute(stmt)
        snapshots = list(result.scalars().all())

        # Transform to equity curve format
        data_points = []
        cumulative_pnl = 0.0
        initial_equity = None

        for snapshot in snapshots:
            if initial_equity is None:
                initial_equity = snapshot.equity - snapshot.daily_pnl

            cumulative_pnl += snapshot.daily_pnl
            cumulative_pnl_percent = (
                (cumulative_pnl / initial_equity) * 100
                if initial_equity and initial_equity > 0
                else 0.0
            )

            data_points.append(
                {
                    "date": snapshot.snapshot_date.isoformat(),
                    "equity": round(snapshot.equity, 2),
                    "daily_pnl": round(snapshot.daily_pnl, 2),
                    "daily_pnl_percent": round(snapshot.daily_pnl_percent, 2),
                    "cumulative_pnl": round(cumulative_pnl, 2),
                    "cumulative_pnl_percent": round(cumulative_pnl_percent, 2),
                }
            )

        return data_points

    # =========================================================================
    # Daily Snapshots
    # =========================================================================

    async def create_account_snapshot(
        self,
        account_id: uuid.UUID,
        equity: float,
        available_balance: float,
        unrealized_pnl: float = 0.0,
        margin_used: float = 0.0,
        open_positions: int = 0,
        position_summary: Optional[list] = None,
        source: str = "scheduled",
    ) -> DailyAccountSnapshotDB:
        """
        Create a daily snapshot for an account.

        Args:
            account_id: The account's UUID
            equity: Current equity
            available_balance: Available balance
            unrealized_pnl: Unrealized P&L
            margin_used: Total margin used
            open_positions: Number of open positions
            position_summary: Summary of open positions
            source: Snapshot source ('scheduled', 'manual', 'trade')

        Returns:
            The created snapshot
        """
        # Get account for user_id
        account_result = await self.db.execute(
            select(ExchangeAccountDB).where(ExchangeAccountDB.id == account_id)
        )
        account = account_result.scalars().first()
        if not account:
            raise ValueError(f"Account not found: {account_id}")

        today = date.today()

        # Get yesterday's snapshot for daily P&L calculation
        yesterday = today - timedelta(days=1)
        yesterday_stmt = select(DailyAccountSnapshotDB).where(
            and_(
                DailyAccountSnapshotDB.account_id == account_id,
                DailyAccountSnapshotDB.snapshot_date == yesterday,
            )
        )
        yesterday_result = await self.db.execute(yesterday_stmt)
        yesterday_snapshot = yesterday_result.scalars().first()

        # Calculate daily P&L
        if yesterday_snapshot:
            daily_pnl = equity - yesterday_snapshot.equity
            daily_pnl_percent = (
                (daily_pnl / yesterday_snapshot.equity) * 100
                if yesterday_snapshot.equity > 0
                else 0.0
            )
        else:
            daily_pnl = 0.0
            daily_pnl_percent = 0.0

        # Create or update today's snapshot
        existing_stmt = select(DailyAccountSnapshotDB).where(
            and_(
                DailyAccountSnapshotDB.account_id == account_id,
                DailyAccountSnapshotDB.snapshot_date == today,
            )
        )
        existing_result = await self.db.execute(existing_stmt)
        existing = existing_result.scalars().first()

        if existing:
            # Update existing snapshot
            existing.equity = equity
            existing.available_balance = available_balance
            existing.unrealized_pnl = unrealized_pnl
            existing.margin_used = margin_used
            existing.daily_pnl = daily_pnl
            existing.daily_pnl_percent = daily_pnl_percent
            existing.open_positions = open_positions
            existing.position_summary = position_summary or []
            existing.snapshot_source = source
            snapshot = existing
        else:
            # Create new snapshot
            snapshot = DailyAccountSnapshotDB(
                user_id=account.user_id,
                account_id=account_id,
                snapshot_date=today,
                equity=equity,
                available_balance=available_balance,
                unrealized_pnl=unrealized_pnl,
                margin_used=margin_used,
                daily_pnl=daily_pnl,
                daily_pnl_percent=daily_pnl_percent,
                open_positions=open_positions,
                position_summary=position_summary or [],
                snapshot_source=source,
            )
            self.db.add(snapshot)

        await self.db.flush()
        logger.debug(f"Created account snapshot: account={account_id} equity={equity}")

        return snapshot

    async def create_agent_snapshot(
        self,
        agent_id: uuid.UUID,
        source: str = "scheduled",
    ) -> DailyAgentSnapshotDB:
        """
        Create a daily snapshot for an agent.

        Args:
            agent_id: The agent's UUID
            source: Snapshot source

        Returns:
            The created snapshot
        """
        # Get agent
        agent_result = await self.db.execute(
            select(AgentDB).where(AgentDB.id == agent_id)
        )
        agent = agent_result.scalars().first()
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        today = date.today()

        # Get yesterday's snapshot for daily metrics calculation
        yesterday = today - timedelta(days=1)
        yesterday_stmt = select(DailyAgentSnapshotDB).where(
            and_(
                DailyAgentSnapshotDB.agent_id == agent_id,
                DailyAgentSnapshotDB.snapshot_date == yesterday,
            )
        )
        yesterday_result = await self.db.execute(yesterday_stmt)
        yesterday_snapshot = yesterday_result.scalars().first()

        # Calculate daily metrics
        if yesterday_snapshot:
            daily_pnl = agent.total_pnl - yesterday_snapshot.total_pnl
            daily_trades = agent.total_trades - yesterday_snapshot.total_trades
            daily_winning = agent.winning_trades - yesterday_snapshot.winning_trades
            daily_losing = agent.losing_trades - yesterday_snapshot.losing_trades
        else:
            daily_pnl = agent.total_pnl
            daily_trades = agent.total_trades
            daily_winning = agent.winning_trades
            daily_losing = agent.losing_trades

        # Calculate virtual equity for mock agents
        virtual_equity = None
        if agent.execution_mode == "mock":
            virtual_equity = (agent.mock_initial_balance or 10000.0) + agent.total_pnl

        # Create or update today's snapshot
        existing_stmt = select(DailyAgentSnapshotDB).where(
            and_(
                DailyAgentSnapshotDB.agent_id == agent_id,
                DailyAgentSnapshotDB.snapshot_date == today,
            )
        )
        existing_result = await self.db.execute(existing_stmt)
        existing = existing_result.scalars().first()

        if existing:
            # Update existing snapshot
            existing.total_pnl = agent.total_pnl
            existing.total_trades = agent.total_trades
            existing.winning_trades = agent.winning_trades
            existing.losing_trades = agent.losing_trades
            existing.max_drawdown = agent.max_drawdown
            existing.daily_pnl = daily_pnl
            existing.daily_trades = daily_trades
            existing.daily_winning = daily_winning
            existing.daily_losing = daily_losing
            existing.virtual_equity = virtual_equity
            snapshot = existing
        else:
            # Create new snapshot
            snapshot = DailyAgentSnapshotDB(
                user_id=agent.user_id,
                agent_id=agent_id,
                account_id=agent.account_id,
                snapshot_date=today,
                total_pnl=agent.total_pnl,
                total_trades=agent.total_trades,
                winning_trades=agent.winning_trades,
                losing_trades=agent.losing_trades,
                max_drawdown=agent.max_drawdown,
                daily_pnl=daily_pnl,
                daily_trades=daily_trades,
                daily_winning=daily_winning,
                daily_losing=daily_losing,
                virtual_equity=virtual_equity,
            )
            self.db.add(snapshot)

        await self.db.flush()
        logger.debug(
            f"Created agent snapshot: agent={agent_id} "
            f"total_pnl={agent.total_pnl} daily_pnl={daily_pnl}"
        )

        return snapshot

    # =========================================================================
    # Trade History
    # =========================================================================

    async def get_agent_trade_history(
        self,
        agent_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PnlRecordDB], int]:
        """
        Get trade history for an agent.

        Args:
            agent_id: The agent's UUID
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            Tuple of (records, total_count)
        """
        # Count total
        count_stmt = (
            select(func.count())
            .select_from(PnlRecordDB)
            .where(PnlRecordDB.agent_id == agent_id)
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get records
        stmt = (
            select(PnlRecordDB)
            .where(PnlRecordDB.agent_id == agent_id)
            .order_by(PnlRecordDB.closed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())

        return records, total

    async def get_account_agents_performance(
        self,
        account_id: uuid.UUID,
    ) -> list[dict]:
        """
        Get performance metrics for all agents on an account.

        Args:
            account_id: The account's UUID

        Returns:
            List of agent performance dictionaries
        """
        # Get all agents for this account with strategy relationship preloaded
        stmt = (
            select(AgentDB)
            .options(selectinload(AgentDB.strategy))
            .where(AgentDB.account_id == account_id)
            .order_by(AgentDB.total_pnl.desc())
        )
        result = await self.db.execute(stmt)
        agents = list(result.scalars().all())

        performances = []
        for agent in agents:
            # Get today's daily P&L from snapshot
            today = date.today()
            snapshot_stmt = select(DailyAgentSnapshotDB).where(
                and_(
                    DailyAgentSnapshotDB.agent_id == agent.id,
                    DailyAgentSnapshotDB.snapshot_date == today,
                )
            )
            snapshot_result = await self.db.execute(snapshot_stmt)
            snapshot = snapshot_result.scalars().first()

            daily_pnl = snapshot.daily_pnl if snapshot else 0.0

            # Get open positions count
            positions_stmt = (
                select(func.count())
                .select_from(AgentPositionDB)
                .where(
                    and_(
                        AgentPositionDB.agent_id == agent.id,
                        AgentPositionDB.status.in_(["open", "pending"]),
                    )
                )
            )
            positions_result = await self.db.execute(positions_stmt)
            open_positions = positions_result.scalar() or 0

            performances.append(
                {
                    "agent_id": str(agent.id),
                    "agent_name": agent.name,
                    "strategy_name": (
                        agent.strategy.name if agent.strategy else "Unknown"
                    ),
                    "strategy_type": (
                        agent.strategy.type if agent.strategy else "unknown"
                    ),
                    "status": agent.status,
                    "total_pnl": round(agent.total_pnl, 2),
                    "daily_pnl": round(daily_pnl, 2),
                    "win_rate": round(agent.win_rate, 2),
                    "total_trades": agent.total_trades,
                    "winning_trades": agent.winning_trades,
                    "losing_trades": agent.losing_trades,
                    "max_drawdown": round(agent.max_drawdown, 2),
                    "open_positions": open_positions,
                }
            )

        return performances
