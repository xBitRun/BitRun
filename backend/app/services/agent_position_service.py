"""
Agent Position Service – Agent-level position isolation.

Replaces the old PositionService with agent-scoped operations.
Each agent has its own virtual position ledger, isolated from other
agents even when sharing the same exchange account.

Key changes from PositionService:
- Unique constraint is (agent_id, symbol) not (account_id, symbol)
- Multiple agents CAN hold the same symbol on the same account
- AgentAccountState provides agent-isolated view for prompt building
- Reconciliation compares SUM(agent positions) vs exchange net position

Provides:
- Position ownership per agent (claim-then-execute pattern)
- Position accumulation for agents that add to same-symbol positions
- Capital allocation validation (atomic with claim)
- Agent-level virtual AccountState for prompt isolation
- Position reconciliation between app-level and exchange-level
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal, Optional

from sqlalchemy import and_, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AgentDB, AgentPositionDB
from ..models.agent import AgentAccountState, AgentPosition
from ..services.redis_service import RedisService
from ..traders.base import Position

# Import PnLService lazily to avoid circular import
# from ..services.pnl_service import PnLService

logger = logging.getLogger(__name__)

# Redis lock prefixes
_POSITION_LOCK_PREFIX = "agent_pos_lock:"
_CAPITAL_LOCK_PREFIX = "agent_capital_lock:"
_LOCK_TIMEOUT_SECONDS = 10
_CAPITAL_LOCK_TIMEOUT_SECONDS = 15

# Grace period for zombie detection
_ZOMBIE_GRACE_PERIOD_SECONDS = 300  # 5 minutes


class PositionConflictError(Exception):
    """Raised when a symbol is already occupied by this agent."""

    def __init__(self, symbol: str, agent_id: uuid.UUID):
        self.symbol = symbol
        self.agent_id = agent_id
        super().__init__(
            f"Symbol {symbol} already has an open/pending position for agent {agent_id}"
        )


class CapitalExceededError(Exception):
    """Raised when opening a position would exceed capital allocation."""

    def __init__(self, message: str):
        super().__init__(message)


class AgentPositionService:
    """
    Manages agent-level position isolation and capital allocation.

    Each agent sees and operates on ONLY its own positions. The exchange-
    level net position is the aggregate of all agent positions on that
    account for that symbol.

    Usage::

        svc = AgentPositionService(db_session, redis_service)

        # Before opening a position
        claim = await svc.claim_position(agent_id, account_id, "BTC", "long")

        # After order executes successfully
        await svc.confirm_position(claim.id, size=0.05, size_usd=5000, entry_price=100000)

        # If order fails – release the claim
        await svc.release_claim(claim.id)

        # When closing
        await svc.close_position_record(claim.id, close_price=101000, realized_pnl=50)

        # Get agent-isolated account state (for prompt building)
        state = await svc.get_agent_account_state(agent_id, account_id, trader)
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: Optional[RedisService] = None,
    ):
        self.db = db
        self.redis = redis

    # ------------------------------------------------------------------
    # Agent-Isolated Account State (for prompt building)
    # ------------------------------------------------------------------

    async def get_agent_account_state(
        self,
        agent_id: uuid.UUID,
        agent: AgentDB,
        current_prices: Optional[dict[str, float]] = None,
        account_equity: Optional[float] = None,
    ) -> AgentAccountState:
        """
        Build an agent-isolated virtual AccountState.

        The AI prompt receives ONLY this agent's positions and virtual
        equity, preventing it from seeing other agents' positions.

        Args:
            agent_id: The agent's ID
            agent: The AgentDB instance (for capital allocation)
            current_prices: Dict of symbol -> current price (for unrealized P&L calc)
            account_equity: Real account equity for percentage-based capital allocation.
                           Required when agent uses allocated_capital_percent.

        Returns:
            AgentAccountState with isolated positions and virtual balance
        """
        # Get this agent's open positions
        open_positions = await self.get_agent_positions(agent_id, status_filter="open")

        # Convert to Pydantic models and calculate unrealized P&L
        positions = []
        total_unrealized_pnl = 0.0
        total_margin_used = 0.0

        for pos in open_positions:
            pydantic_pos = AgentPosition(
                id=str(pos.id),
                agent_id=str(pos.agent_id),
                account_id=str(pos.account_id) if pos.account_id else None,
                symbol=pos.symbol,
                side=pos.side,
                size=pos.size,
                size_usd=pos.size_usd,
                entry_price=pos.entry_price,
                leverage=pos.leverage,
                status=pos.status,
                realized_pnl=pos.realized_pnl,
                close_price=pos.close_price,
                opened_at=pos.opened_at,
                closed_at=pos.closed_at,
            )
            positions.append(pydantic_pos)

            # Calculate unrealized P&L if current prices available
            if current_prices and pos.symbol in current_prices:
                current_price = current_prices[pos.symbol]
                if pos.side == "long":
                    unrealized = (current_price - pos.entry_price) * pos.size
                else:
                    unrealized = (pos.entry_price - current_price) * pos.size
                total_unrealized_pnl += unrealized

            # Calculate margin used
            margin = pos.size_usd / max(pos.leverage, 1)
            total_margin_used += margin

        # Calculate virtual equity based on agent's allocation
        if agent.execution_mode == "mock":
            base_capital = agent.mock_initial_balance or 10000.0
        elif agent.allocated_capital is not None:
            base_capital = agent.allocated_capital
        elif agent.allocated_capital_percent is not None:
            # Use provided account_equity for percentage-based allocation
            if account_equity is not None and account_equity > 0:
                base_capital = account_equity * agent.allocated_capital_percent
            else:
                # Fallback to default if account_equity not provided
                base_capital = 10000.0 * agent.allocated_capital_percent
        elif account_equity is not None and account_equity > 0:
            # Live mode without allocation config: use real exchange equity
            base_capital = account_equity
        else:
            base_capital = 10000.0

        equity = base_capital + total_unrealized_pnl + agent.total_pnl
        available_balance = equity - total_margin_used

        return AgentAccountState(
            agent_id=str(agent_id),
            positions=positions,
            equity=equity,
            available_balance=max(available_balance, 0.0),
            total_unrealized_pnl=total_unrealized_pnl,
        )

    # ------------------------------------------------------------------
    # Position lifecycle: claim → confirm → close
    # ------------------------------------------------------------------

    async def claim_position(
        self,
        agent_id: uuid.UUID,
        account_id: Optional[uuid.UUID],
        symbol: str,
        side: Literal["long", "short"],
        leverage: int = 1,
    ) -> AgentPositionDB:
        """
        Claim a symbol slot BEFORE placing the order (crash-safe pattern).

        Unlike the old PositionService, the unique constraint is
        (agent_id, symbol), so multiple agents CAN hold the same
        symbol on the same account.

        If this agent already owns the symbol (open or pending), returns
        the existing record for accumulation.
        """
        symbol = symbol.upper()
        lock_key = f"{_POSITION_LOCK_PREFIX}{agent_id}:{symbol}"

        lock = None
        if self.redis:
            lock = self.redis.redis.lock(lock_key, timeout=_LOCK_TIMEOUT_SECONDS)
            acquired = await lock.acquire(blocking=True, blocking_timeout=5)
            if not acquired:
                raise PositionConflictError(symbol, agent_id)

        try:
            # Check if this agent already has a position on this symbol
            existing = await self.get_agent_position_for_symbol(agent_id, symbol)
            if existing:
                return existing

            # Create pending record inside a savepoint
            record = AgentPositionDB(
                id=uuid.uuid4(),
                agent_id=agent_id,
                account_id=account_id,
                symbol=symbol,
                side=side,
                leverage=leverage,
                status="pending",
                opened_at=datetime.now(UTC),
            )

            try:
                async with self.db.begin_nested():
                    self.db.add(record)
                    await self.db.flush()
            except IntegrityError:
                raise PositionConflictError(symbol, agent_id)

            return record

        finally:
            if lock:
                try:
                    await lock.release()
                except Exception:
                    pass

    async def claim_position_with_capital_check(
        self,
        agent_id: uuid.UUID,
        account_id: uuid.UUID,
        symbol: str,
        side: Literal["long", "short"],
        leverage: int = 1,
        account_equity: float = 0.0,
        requested_size_usd: float = 0.0,
        agent: Optional[AgentDB] = None,
    ) -> AgentPositionDB:
        """
        Atomically check capital allocation AND claim the symbol slot.

        Uses an agent-level Redis lock to prevent TOCTOU races.
        """
        lock_key = f"{_CAPITAL_LOCK_PREFIX}{agent_id}"
        lock = None

        if self.redis:
            lock = self.redis.redis.lock(
                lock_key, timeout=_CAPITAL_LOCK_TIMEOUT_SECONDS
            )
            acquired = await lock.acquire(blocking=True, blocking_timeout=10)
            if not acquired:
                raise CapitalExceededError(
                    "Could not acquire capital allocation lock – "
                    "another trade may be in progress"
                )

        try:
            # 1. Capital check (inside the lock)
            if agent and account_equity > 0:
                can_trade, reason = await self.check_capital_allocation(
                    agent_id=agent_id,
                    account_equity=account_equity,
                    requested_size_usd=requested_size_usd,
                    agent=agent,
                    leverage=leverage,
                )
                if not can_trade:
                    raise CapitalExceededError(reason)

            # 2. Claim position (still inside the lock)
            return await self.claim_position(
                agent_id=agent_id,
                account_id=account_id,
                symbol=symbol,
                side=side,
                leverage=leverage,
            )
        finally:
            if lock:
                try:
                    await lock.release()
                except Exception:
                    pass

    async def confirm_position(
        self,
        position_id: uuid.UUID,
        size: float,
        size_usd: float,
        entry_price: float,
    ) -> None:
        """Transition a pending claim to 'open' after the order fills."""
        stmt = (
            update(AgentPositionDB)
            .where(
                and_(
                    AgentPositionDB.id == position_id,
                    AgentPositionDB.status == "pending",
                )
            )
            .values(
                status="open",
                size=size,
                size_usd=size_usd,
                entry_price=entry_price,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def release_claim(self, position_id: uuid.UUID) -> None:
        """Delete a pending claim if the order failed (rollback)."""
        stmt = delete(AgentPositionDB).where(
            and_(
                AgentPositionDB.id == position_id,
                AgentPositionDB.status == "pending",
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def accumulate_position(
        self,
        position_id: uuid.UUID,
        additional_size: float,
        additional_size_usd: float,
        fill_price: float,
    ) -> None:
        """
        Update an existing open position with additional size.

        Used by DCA / Grid agents that add to the same symbol.
        Recalculates weighted-average entry price.
        """
        stmt = (
            select(AgentPositionDB)
            .where(AgentPositionDB.id == position_id)
            .with_for_update()
        )
        result = await self.db.execute(stmt)
        record = result.scalars().first()
        if not record or record.status != "open":
            logger.warning(
                f"accumulate_position: record {position_id} not found or "
                f"not open (status={getattr(record, 'status', '?')})"
            )
            return

        old_size = record.size or 0.0
        old_entry = record.entry_price or 0.0
        old_usd = record.size_usd or 0.0

        total_size = old_size + additional_size
        if total_size > 0 and fill_price > 0:
            new_entry = (
                old_size * old_entry + additional_size * fill_price
            ) / total_size
        else:
            new_entry = fill_price or old_entry

        update_stmt = (
            update(AgentPositionDB)
            .where(AgentPositionDB.id == position_id)
            .values(
                size=total_size,
                size_usd=old_usd + additional_size_usd,
                entry_price=round(new_entry, 8),
            )
        )
        await self.db.execute(update_stmt)
        await self.db.flush()
        logger.debug(
            f"accumulate_position: {record.symbol} size {old_size}->{total_size} "
            f"entry {old_entry}->{new_entry:.8f}"
        )

    async def close_position_record(
        self,
        position_id: uuid.UUID,
        close_price: float = 0.0,
        realized_pnl: float = 0.0,
        fees: float = 0.0,
        exit_reason: str = None,
    ) -> None:
        """
        Mark a position record as closed and record P&L.

        Args:
            position_id: The position UUID
            close_price: Price at which position was closed
            realized_pnl: Realized P&L from the trade
            fees: Trading fees
            exit_reason: Reason for exit (take_profit, stop_loss, signal, manual)
        """
        # Get the position first
        stmt = select(AgentPositionDB).where(AgentPositionDB.id == position_id)
        result = await self.db.execute(stmt)
        position = result.scalars().first()

        if not position:
            logger.warning(f"Position {position_id} not found for closing")
            return

        # Update position status
        update_stmt = (
            update(AgentPositionDB)
            .where(AgentPositionDB.id == position_id)
            .values(
                status="closed",
                close_price=close_price,
                realized_pnl=realized_pnl,
                closed_at=datetime.now(UTC),
            )
        )
        await self.db.execute(update_stmt)
        await self.db.flush()

        # Record P&L (lazy import to avoid circular dependency)
        try:
            from ..services.pnl_service import PnLService

            pnl_service = PnLService(self.db)
            await pnl_service.record_pnl_from_position(
                position=position,
                close_price=close_price,
                realized_pnl=realized_pnl,
                fees=fees,
                exit_reason=exit_reason,
            )
            logger.debug(
                f"Recorded P&L for position {position_id}: "
                f"pnl={realized_pnl:.2f} fees={fees:.2f}"
            )
        except Exception as e:
            # Don't fail the close if P&L recording fails
            logger.error(f"Failed to record P&L for position {position_id}: {e}")

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_agent_positions(
        self,
        agent_id: uuid.UUID,
        status_filter: Optional[str] = None,
    ) -> list[AgentPositionDB]:
        """Get all position records for an agent."""
        stmt = select(AgentPositionDB).where(AgentPositionDB.agent_id == agent_id)
        if status_filter:
            stmt = stmt.where(AgentPositionDB.status == status_filter)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_agent_position_for_symbol(
        self,
        agent_id: uuid.UUID,
        symbol: str,
    ) -> Optional[AgentPositionDB]:
        """Get the open/pending position for a specific symbol owned by an agent."""
        stmt = select(AgentPositionDB).where(
            and_(
                AgentPositionDB.agent_id == agent_id,
                AgentPositionDB.symbol == symbol.upper(),
                AgentPositionDB.status.in_(["open", "pending"]),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_account_open_positions(
        self,
        account_id: uuid.UUID,
    ) -> list[AgentPositionDB]:
        """Get all open/pending positions for an account (all agents)."""
        stmt = select(AgentPositionDB).where(
            and_(
                AgentPositionDB.account_id == account_id,
                AgentPositionDB.status.in_(["open", "pending"]),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def has_open_positions(self, agent_id: uuid.UUID) -> bool:
        """Check if an agent has any open OR pending positions."""
        stmt = select(AgentPositionDB).where(
            and_(
                AgentPositionDB.agent_id == agent_id,
                AgentPositionDB.status.in_(["open", "pending"]),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def get_account_net_positions(
        self,
        account_id: uuid.UUID,
    ) -> dict[str, dict]:
        """
        Calculate net positions per symbol for an account.

        Aggregates all agent positions to determine what the exchange
        should show. Used for reconciliation.

        Returns: {symbol: {"net_size": float, "agents": [...]}}
        """
        positions = await self.get_account_open_positions(account_id)
        net: dict[str, dict] = {}
        for pos in positions:
            sym = pos.symbol.upper()
            if sym not in net:
                net[sym] = {"long_size": 0.0, "short_size": 0.0, "agents": []}
            if pos.side == "long":
                net[sym]["long_size"] += pos.size
            else:
                net[sym]["short_size"] += pos.size
            net[sym]["agents"].append(
                {
                    "agent_id": str(pos.agent_id),
                    "side": pos.side,
                    "size": pos.size,
                }
            )
        for sym in net:
            net[sym]["net_size"] = net[sym]["long_size"] - net[sym]["short_size"]
        return net

    # ------------------------------------------------------------------
    # Capital allocation checks
    # ------------------------------------------------------------------

    async def check_capital_allocation(
        self,
        agent_id: uuid.UUID,
        account_equity: float,
        requested_size_usd: float,
        agent: AgentDB,
        leverage: int = 1,
    ) -> tuple[bool, str]:
        """
        Validate that the trade doesn't violate the agent's capital allocation.

        Checks agent's own allocation limit against its current open positions.
        Returns (can_trade, reason).
        """
        effective_capital = agent.get_effective_capital(account_equity)

        # If no allocation configured, allow (backward compatible)
        if effective_capital is None:
            return True, "No allocation configured"

        # Convert requested size to margin
        requested_margin = requested_size_usd / max(leverage, 1)

        # Sum the margin used by this agent's open positions
        open_positions = await self.get_agent_positions(agent_id, "open")
        current_used = sum(p.size_usd / max(p.leverage, 1) for p in open_positions)
        new_total = current_used + requested_margin

        if new_total > effective_capital:
            return False, (
                f"Would exceed agent allocation: "
                f"${new_total:.2f} > ${effective_capital:.2f} "
                f"(currently using ${current_used:.2f})"
            )

        return True, "OK"

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------

    async def reconcile(
        self,
        account_id: uuid.UUID,
        exchange_positions: list[Position],
    ) -> dict:
        """
        Compare agent position aggregates with exchange positions.

        For agent-level isolation, we compare the SUM of agent positions
        per symbol against the exchange's net position. Individual agent
        positions are not directly reconciled with the exchange.

        Returns summary dict with:
        - zombies_closed: int
        - orphans_found: int
        - size_synced: int
        """
        summary = {
            "zombies_closed": 0,
            "orphans_found": 0,
            "size_synced": 0,
            "details": [],
        }

        net_positions = await self.get_account_net_positions(account_id)
        exchange_map = {p.symbol.upper(): p for p in exchange_positions}

        app_symbols = set(net_positions.keys())
        exchange_symbols = set(exchange_map.keys())

        now = datetime.now(UTC)

        # Case 1: App has positions but exchange doesn't → zombie
        all_positions = await self.get_account_open_positions(account_id)
        for sym in app_symbols - exchange_symbols:
            # Close all agent positions for this symbol
            for pos in all_positions:
                if pos.symbol.upper() == sym:
                    # Grace period check
                    if (
                        pos.opened_at
                        and (now - pos.opened_at).total_seconds()
                        < _ZOMBIE_GRACE_PERIOD_SECONDS
                    ):
                        summary["details"].append(
                            f"SKIP_ZOMBIE: {sym} (agent {pos.agent_id}) "
                            f"opened recently – within grace period"
                        )
                        continue
                    await self.close_position_record(pos.id, 0.0, 0.0)
                    summary["zombies_closed"] += 1
                    summary["details"].append(
                        f"ZOMBIE: {sym} (agent {pos.agent_id}) closed – "
                        "no matching exchange position"
                    )
                    logger.warning(
                        f"[Reconciliation] Zombie: {sym} agent={pos.agent_id}"
                    )

        # Case 2: Exchange has positions but app doesn't → orphan
        # Log as warning but don't create unowned positions in the new model
        for sym in exchange_symbols - app_symbols:
            summary["orphans_found"] += 1
            summary["details"].append(
                f"ORPHAN: {sym} exists on exchange but not tracked by any agent"
            )
            logger.warning(f"[Reconciliation] Orphan: {sym} on account {account_id}")

        # Case 3: Both exist - compare aggregate size
        for sym in app_symbols & exchange_symbols:
            app_net = net_positions[sym]["net_size"]
            ex_pos = exchange_map[sym]
            ex_size = ex_pos.size if ex_pos.side == "long" else -ex_pos.size

            if abs(app_net - ex_size) > 1e-8:
                summary["size_synced"] += 1
                summary["details"].append(
                    f"DRIFT: {sym} app_net={app_net:.8f} vs exchange={ex_size:.8f} "
                    f"(delta={abs(app_net - ex_size):.8f})"
                )
                logger.warning(
                    f"[Reconciliation] Size drift: {sym} "
                    f"app={app_net} exchange={ex_size}"
                )

        return summary

    async def cleanup_stale_pending(
        self,
        max_age_seconds: int = 300,
    ) -> int:
        """Delete pending claims older than max_age_seconds."""
        cutoff = datetime.now(UTC) - timedelta(seconds=max_age_seconds)
        stmt = delete(AgentPositionDB).where(
            and_(
                AgentPositionDB.status == "pending",
                AgentPositionDB.opened_at < cutoff,
            )
        )
        result = await self.db.execute(stmt)
        count = result.rowcount
        if count:
            await self.db.flush()
            logger.info(f"[Reconciliation] Cleaned up {count} stale pending claims")
        return count
