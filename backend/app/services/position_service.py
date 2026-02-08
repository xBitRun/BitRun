"""
Position Service – Strategy-level position isolation.

Provides:
- Symbol exclusivity enforcement (one strategy per symbol per account)
- Position ownership registration (claim-then-execute pattern)
- Position accumulation for strategies that add to same-symbol positions (Grid/DCA)
- Capital allocation validation (atomic with claim to prevent TOCTOU races)
- Position reconciliation helpers

This service is the central coordination point that prevents
multiple strategies on the same account from interfering with
each other's positions.
"""

import logging
import uuid
from datetime import datetime, timedelta, UTC
from typing import Literal, Optional, Union

from sqlalchemy import and_, select, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    ExchangeAccountDB,
    QuantStrategyDB,
    StrategyDB,
    StrategyPositionDB,
)
from ..services.redis_service import RedisService
from ..traders.base import AccountState, Position

logger = logging.getLogger(__name__)

# Redis lock prefix for position operations
_POSITION_LOCK_PREFIX = "pos_lock:"
# Redis lock prefix for account-level capital allocation
_CAPITAL_LOCK_PREFIX = "capital_lock:"
_LOCK_TIMEOUT_SECONDS = 10
_CAPITAL_LOCK_TIMEOUT_SECONDS = 15

# Grace period for zombie detection – skip recently opened positions
_ZOMBIE_GRACE_PERIOD_SECONDS = 300  # 5 minutes


class PositionConflictError(Exception):
    """Raised when a symbol is already occupied by another strategy."""

    def __init__(self, symbol: str, owner_strategy_id: uuid.UUID):
        self.symbol = symbol
        self.owner_strategy_id = owner_strategy_id
        super().__init__(
            f"Symbol {symbol} is already occupied by strategy {owner_strategy_id}"
        )


class CapitalExceededError(Exception):
    """Raised when opening a position would exceed capital allocation."""

    def __init__(self, message: str):
        super().__init__(message)


class PositionService:
    """
    Manages strategy-level position isolation and capital allocation.

    Usage::

        svc = PositionService(db_session, redis_service)

        # Before opening a position
        claim = await svc.claim_position(strategy_id, "ai", account_id, "BTC", "long")

        # After order executes successfully
        await svc.confirm_position(claim.id, size=0.05, size_usd=5000, entry_price=100000)

        # If order fails – release the claim
        await svc.release_claim(claim.id)

        # When closing
        await svc.close_position(claim.id, close_price=101000, realized_pnl=50)
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: Optional[RedisService] = None,
    ):
        self.db = db
        self.redis = redis

    # ------------------------------------------------------------------
    # Symbol exclusivity
    # ------------------------------------------------------------------

    async def check_symbol_available(
        self,
        account_id: uuid.UUID,
        symbol: str,
        exclude_strategy_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Check if a symbol is available for a new position on this account.

        Returns True if no other strategy holds an open/pending position
        for this symbol on the given account.
        """
        stmt = select(StrategyPositionDB).where(
            and_(
                StrategyPositionDB.account_id == account_id,
                StrategyPositionDB.symbol == symbol.upper(),
                StrategyPositionDB.status.in_(["open", "pending"]),
            )
        )
        if exclude_strategy_id:
            stmt = stmt.where(
                StrategyPositionDB.strategy_id != exclude_strategy_id
            )
        result = await self.db.execute(stmt)
        return result.scalars().first() is None

    async def get_symbol_owner(
        self,
        account_id: uuid.UUID,
        symbol: str,
    ) -> Optional[StrategyPositionDB]:
        """Get the strategy that currently owns a symbol on this account."""
        stmt = select(StrategyPositionDB).where(
            and_(
                StrategyPositionDB.account_id == account_id,
                StrategyPositionDB.symbol == symbol.upper(),
                StrategyPositionDB.status.in_(["open", "pending"]),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def check_symbols_conflict(
        self,
        account_id: uuid.UUID,
        symbols: list[str],
        exclude_strategy_id: Optional[uuid.UUID] = None,
    ) -> list[str]:
        """Check which symbols are already occupied. Returns list of conflicting symbols."""
        conflicts = []
        for symbol in symbols:
            if not await self.check_symbol_available(
                account_id, symbol, exclude_strategy_id
            ):
                conflicts.append(symbol.upper())
        return conflicts

    # ------------------------------------------------------------------
    # Position lifecycle: claim → confirm → close
    # ------------------------------------------------------------------

    async def claim_position(
        self,
        strategy_id: uuid.UUID,
        strategy_type: Literal["ai", "quant"],
        account_id: uuid.UUID,
        symbol: str,
        side: Literal["long", "short"],
        leverage: int = 1,
    ) -> StrategyPositionDB:
        """
        Claim a symbol slot BEFORE placing the order (crash-safe pattern).

        If the symbol is already taken by another strategy, raises
        PositionConflictError.  If the same strategy already owns the
        symbol (open or pending), returns the existing record so the
        caller can accumulate onto it.

        Uses Redis distributed lock + DB unique constraint as dual
        safety net.  DB conflicts are caught inside a **savepoint** so
        that the rest of the session is not rolled back.

        Returns the StrategyPositionDB record (pending for new, or
        open/pending for existing same-strategy positions).
        """
        symbol = symbol.upper()
        lock_key = f"{_POSITION_LOCK_PREFIX}{account_id}:{symbol}"

        # --- Acquire distributed lock (if Redis available) ---
        lock = None
        if self.redis:
            lock = self.redis.redis.lock(
                lock_key, timeout=_LOCK_TIMEOUT_SECONDS
            )
            acquired = await lock.acquire(blocking=True, blocking_timeout=5)
            if not acquired:
                raise PositionConflictError(symbol, uuid.UUID(int=0))

        try:
            # Check DB for existing claim
            existing = await self.get_symbol_owner(account_id, symbol)
            if existing and existing.strategy_id != strategy_id:
                raise PositionConflictError(symbol, existing.strategy_id)

            # If this strategy already has a pending/open record for this
            # symbol, return it instead of creating a duplicate.
            if existing and existing.strategy_id == strategy_id:
                return existing

            # Create pending record inside a savepoint so that an
            # IntegrityError (concurrent race hitting the partial unique
            # index) only rolls back this nested transaction, not the
            # entire session.
            record = StrategyPositionDB(
                id=uuid.uuid4(),
                strategy_id=strategy_id,
                strategy_type=strategy_type,
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
                # Savepoint is automatically rolled back; session stays usable.
                raise PositionConflictError(symbol, uuid.UUID(int=0))

            return record

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
            update(StrategyPositionDB)
            .where(
                and_(
                    StrategyPositionDB.id == position_id,
                    StrategyPositionDB.status == "pending",
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
        stmt = delete(StrategyPositionDB).where(
            and_(
                StrategyPositionDB.id == position_id,
                StrategyPositionDB.status == "pending",
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
        Update an existing *open* position with additional size.

        Used by DCA / Grid engines that add to the same symbol over
        multiple cycles.  Recalculates the weighted-average entry price.

        Uses ``FOR UPDATE`` to prevent stale reads if two callers ever
        accumulate the same position concurrently (defensive — the
        per-cycle execution lock should already prevent this).
        """
        stmt = (
            select(StrategyPositionDB)
            .where(StrategyPositionDB.id == position_id)
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
        # Weighted-average entry price
        if total_size > 0 and fill_price > 0:
            new_entry = (
                (old_size * old_entry + additional_size * fill_price) / total_size
            )
        else:
            new_entry = fill_price or old_entry

        update_stmt = (
            update(StrategyPositionDB)
            .where(StrategyPositionDB.id == position_id)
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

    async def claim_position_with_capital_check(
        self,
        strategy_id: uuid.UUID,
        strategy_type: Literal["ai", "quant"],
        account_id: uuid.UUID,
        symbol: str,
        side: Literal["long", "short"],
        leverage: int = 1,
        account_equity: float = 0.0,
        requested_size_usd: float = 0.0,
        strategy: Optional[Union[StrategyDB, QuantStrategyDB]] = None,
    ) -> StrategyPositionDB:
        """
        Atomically check capital allocation AND claim the symbol slot.

        Wraps both operations under an account-level Redis lock to
        prevent TOCTOU races where two strategies on different symbols
        both pass the capital check before either claims.

        Falls back to non-atomic behaviour when Redis is unavailable
        (DB unique constraint still prevents symbol-level conflicts).
        """
        lock_key = f"{_CAPITAL_LOCK_PREFIX}{account_id}"
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
            if strategy and account_equity > 0:
                can_trade, reason = await self.check_capital_allocation(
                    account_id=account_id,
                    account_equity=account_equity,
                    requesting_strategy_id=strategy_id,
                    requested_size_usd=requested_size_usd,
                    strategy=strategy,
                    leverage=leverage,
                )
                if not can_trade:
                    raise CapitalExceededError(reason)

            # 2. Claim position (still inside the lock)
            return await self.claim_position(
                strategy_id=strategy_id,
                strategy_type=strategy_type,
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

    async def close_position_record(
        self,
        position_id: uuid.UUID,
        close_price: float = 0.0,
        realized_pnl: float = 0.0,
    ) -> None:
        """Mark a position record as closed."""
        stmt = (
            update(StrategyPositionDB)
            .where(StrategyPositionDB.id == position_id)
            .values(
                status="closed",
                close_price=close_price,
                realized_pnl=realized_pnl,
                closed_at=datetime.now(UTC),
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_strategy_positions(
        self,
        strategy_id: uuid.UUID,
        status_filter: Optional[str] = None,
    ) -> list[StrategyPositionDB]:
        """Get all position records for a strategy."""
        stmt = select(StrategyPositionDB).where(
            StrategyPositionDB.strategy_id == strategy_id
        )
        if status_filter:
            stmt = stmt.where(StrategyPositionDB.status == status_filter)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_strategy_position_for_symbol(
        self,
        strategy_id: uuid.UUID,
        symbol: str,
    ) -> Optional[StrategyPositionDB]:
        """Get the open/pending position for a specific symbol owned by a strategy."""
        stmt = select(StrategyPositionDB).where(
            and_(
                StrategyPositionDB.strategy_id == strategy_id,
                StrategyPositionDB.symbol == symbol.upper(),
                StrategyPositionDB.status.in_(["open", "pending"]),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_account_open_positions(
        self,
        account_id: uuid.UUID,
    ) -> list[StrategyPositionDB]:
        """Get all open/pending positions for an account."""
        stmt = select(StrategyPositionDB).where(
            and_(
                StrategyPositionDB.account_id == account_id,
                StrategyPositionDB.status.in_(["open", "pending"]),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def has_open_positions(self, strategy_id: uuid.UUID) -> bool:
        """Check if a strategy has any open OR pending positions."""
        stmt = select(StrategyPositionDB).where(
            and_(
                StrategyPositionDB.strategy_id == strategy_id,
                StrategyPositionDB.status.in_(["open", "pending"]),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    # ------------------------------------------------------------------
    # Capital allocation checks
    # ------------------------------------------------------------------

    async def check_capital_allocation(
        self,
        account_id: uuid.UUID,
        account_equity: float,
        requesting_strategy_id: uuid.UUID,
        requested_size_usd: float,
        strategy: Union[StrategyDB, QuantStrategyDB],
        leverage: int = 1,
    ) -> tuple[bool, str]:
        """
        Validate that the trade doesn't violate capital allocation rules.

        Checks:
        1. Strategy's own allocation limit
        2. Total account allocation vs equity

        All comparisons use **margin** (size_usd / leverage) so that
        high-leverage positions are measured consistently.

        Returns (can_trade, reason).
        """
        effective_capital = strategy.get_effective_capital(account_equity)

        # If no allocation configured, allow (backward compatible)
        if effective_capital is None:
            return True, "No allocation configured"

        # Convert requested size to margin for consistent comparison
        requested_margin = requested_size_usd / max(leverage, 1)

        # Check 1: Strategy's own limit
        # Sum the margin used by this strategy's open positions
        open_positions = await self.get_strategy_positions(
            requesting_strategy_id, "open"
        )
        current_used = sum(p.size_usd / max(p.leverage, 1) for p in open_positions)
        new_total = current_used + requested_margin

        if new_total > effective_capital:
            return False, (
                f"Would exceed strategy allocation: "
                f"${new_total:.2f} > ${effective_capital:.2f} "
                f"(currently using ${current_used:.2f})"
            )

        # Check 2: Total account allocation
        all_open = await self.get_account_open_positions(account_id)
        total_used = sum(p.size_usd / max(p.leverage, 1) for p in all_open)
        total_with_new = total_used + requested_margin

        # Fetch all strategies on this account to calculate total allocation
        total_allocated = await self._get_total_account_allocation(
            account_id, account_equity
        )

        # Safety buffer: total allocated shouldn't exceed 95% of equity
        safe_equity = account_equity * 0.95
        if total_allocated > safe_equity:
            return False, (
                f"Account over-allocated: total allocated ${total_allocated:.2f} "
                f"> safe limit ${safe_equity:.2f} (equity ${account_equity:.2f})"
            )

        return True, "OK"

    async def _get_total_account_allocation(
        self,
        account_id: uuid.UUID,
        account_equity: float,
    ) -> float:
        """Calculate total allocated capital across all strategies on an account."""
        total = 0.0

        # AI strategies
        stmt = select(StrategyDB).where(
            and_(
                StrategyDB.account_id == account_id,
                StrategyDB.status.in_(["active", "paused", "warning"]),
            )
        )
        result = await self.db.execute(stmt)
        for s in result.scalars().all():
            cap = s.get_effective_capital(account_equity)
            if cap is not None:
                total += cap

        # Quant strategies
        stmt = select(QuantStrategyDB).where(
            and_(
                QuantStrategyDB.account_id == account_id,
                QuantStrategyDB.status.in_(["active", "paused", "warning"]),
            )
        )
        result = await self.db.execute(stmt)
        for s in result.scalars().all():
            cap = s.get_effective_capital(account_equity)
            if cap is not None:
                total += cap

        return total

    # ------------------------------------------------------------------
    # Reconciliation helpers
    # ------------------------------------------------------------------

    async def reconcile(
        self,
        account_id: uuid.UUID,
        exchange_positions: list[Position],
    ) -> dict:
        """
        Compare DB records with actual exchange positions and fix discrepancies.

        Returns a summary dict with:
        - zombies_closed: int (DB had open, exchange didn't)
        - orphans_found: int (exchange had position, DB didn't)
        - size_synced: int (size mismatch corrected)
        """
        summary = {
            "zombies_closed": 0,
            "orphans_found": 0,
            "size_synced": 0,
            "details": [],
        }

        db_positions = await self.get_account_open_positions(account_id)
        exchange_map = {p.symbol.upper(): p for p in exchange_positions}

        db_symbols = {p.symbol.upper() for p in db_positions}
        exchange_symbols = set(exchange_map.keys())

        # Case 1: DB has it, exchange doesn't → zombie (force-closed / liquidated)
        # Skip recently-opened positions to avoid false positives from
        # exchange propagation delay.
        now = datetime.now(UTC)
        for db_pos in db_positions:
            sym = db_pos.symbol.upper()
            if sym not in exchange_symbols:
                # Grace period: skip positions opened less than 5 minutes ago
                if db_pos.opened_at and (
                    now - db_pos.opened_at
                ).total_seconds() < _ZOMBIE_GRACE_PERIOD_SECONDS:
                    summary["details"].append(
                        f"SKIP_ZOMBIE: {sym} (strategy {db_pos.strategy_id}) "
                        f"opened recently – within grace period"
                    )
                    logger.debug(
                        f"[Reconciliation] Skipping recent position: {sym} "
                        f"strategy={db_pos.strategy_id} (opened {db_pos.opened_at})"
                    )
                    continue

                await self.close_position_record(
                    db_pos.id, close_price=0.0, realized_pnl=0.0
                )
                summary["zombies_closed"] += 1
                summary["details"].append(
                    f"ZOMBIE: {sym} (strategy {db_pos.strategy_id}) closed in DB – "
                    "no matching exchange position"
                )
                logger.warning(
                    f"[Reconciliation] Zombie position closed: {sym} "
                    f"strategy={db_pos.strategy_id} account={account_id}"
                )

        # Case 2: Exchange has it, DB doesn't → orphan (manual trade / crash)
        # Create an "unowned" record so the position is visible in the system.
        _UNOWNED_STRATEGY_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
        for sym in exchange_symbols - db_symbols:
            ex_pos = exchange_map[sym]
            try:
                record = StrategyPositionDB(
                    id=uuid.uuid4(),
                    strategy_id=_UNOWNED_STRATEGY_ID,
                    strategy_type="unknown",
                    account_id=account_id,
                    symbol=sym,
                    side=ex_pos.side if hasattr(ex_pos, "side") else "long",
                    size=ex_pos.size,
                    size_usd=ex_pos.size_usd,
                    entry_price=ex_pos.entry_price,
                    leverage=ex_pos.leverage if hasattr(ex_pos, "leverage") else 1,
                    status="open",
                    opened_at=datetime.now(UTC),
                )
                self.db.add(record)
            except Exception as e:
                logger.error(f"[Reconciliation] Failed to create orphan record for {sym}: {e}")

            summary["orphans_found"] += 1
            summary["details"].append(
                f"ORPHAN: {sym} exists on exchange but not tracked – created unowned record"
            )
            logger.warning(
                f"[Reconciliation] Orphan position found: {sym} "
                f"account={account_id} – created unowned tracking record"
            )

        # Case 3: Both exist but size differs → sync from exchange
        for db_pos in db_positions:
            sym = db_pos.symbol.upper()
            if sym in exchange_map:
                ex_pos = exchange_map[sym]
                if abs(db_pos.size - ex_pos.size) > 1e-8:
                    old_size = db_pos.size
                    stmt = (
                        update(StrategyPositionDB)
                        .where(StrategyPositionDB.id == db_pos.id)
                        .values(
                            size=ex_pos.size,
                            size_usd=ex_pos.size_usd,
                        )
                    )
                    await self.db.execute(stmt)
                    summary["size_synced"] += 1
                    summary["details"].append(
                        f"SYNC: {sym} size {old_size} -> {ex_pos.size}"
                    )

        if any(v for k, v in summary.items() if k != "details"):
            await self.db.flush()

        return summary

    # ------------------------------------------------------------------
    # Stale pending cleanup
    # ------------------------------------------------------------------

    async def cleanup_stale_pending(
        self,
        max_age_seconds: int = 300,
    ) -> int:
        """
        Delete pending claims older than *max_age_seconds*.

        These are leftovers from crashes between claim and order execution.
        Called by the reconciliation job.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=max_age_seconds)
        stmt = delete(StrategyPositionDB).where(
            and_(
                StrategyPositionDB.status == "pending",
                StrategyPositionDB.opened_at < cutoff,
            )
        )
        result = await self.db.execute(stmt)
        count = result.rowcount
        if count:
            await self.db.flush()
            logger.info(f"[Reconciliation] Cleaned up {count} stale pending claims")
        return count
