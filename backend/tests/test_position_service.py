"""
Tests for PositionService – strategy-level position isolation.

⚠️  DEPRECATED: PositionService has been superseded by AgentPositionService
    as part of the Strategy-Agent decoupling. The underlying model
    (AgentPositionDB) no longer has strategy_id / strategy_type fields.
    These tests are skipped until the quant subsystem is migrated.
    See: AgentPositionService tests in test_repositories.py

Covers:
- Symbol exclusivity checks
- Position lifecycle: claim → confirm → close
- Accumulate position with weighted-average entry price
- Capital allocation checks
- Reconciliation (zombie, orphan, size-sync)
- Stale pending cleanup
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.skip(
    reason="PositionService is deprecated; AgentPositionDB no longer has strategy_id. "
           "Use AgentPositionService (tested in test_repositories.py)."
)

from app.services.position_service import (
    CapitalExceededError,
    PositionConflictError,
    PositionService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_position_record(**overrides):
    """Create a mock StrategyPositionDB record."""
    record = MagicMock()
    record.id = overrides.get("id", uuid.uuid4())
    record.strategy_id = overrides.get("strategy_id", uuid.uuid4())
    record.strategy_type = overrides.get("strategy_type", "ai")
    record.account_id = overrides.get("account_id", uuid.uuid4())
    record.symbol = overrides.get("symbol", "BTC")
    record.side = overrides.get("side", "long")
    record.leverage = overrides.get("leverage", 1)
    record.size = overrides.get("size", 0.1)
    record.size_usd = overrides.get("size_usd", 5000.0)
    record.entry_price = overrides.get("entry_price", 50000.0)
    record.status = overrides.get("status", "open")
    record.opened_at = overrides.get("opened_at", datetime.now(UTC))
    record.close_price = overrides.get("close_price", None)
    record.realized_pnl = overrides.get("realized_pnl", None)
    record.closed_at = overrides.get("closed_at", None)
    return record


def _make_exchange_position(symbol="BTC", size=0.1, size_usd=5000.0,
                            entry_price=50000.0, leverage=1, side="long"):
    """Create a mock exchange Position."""
    pos = MagicMock()
    pos.symbol = symbol
    pos.size = size
    pos.size_usd = size_usd
    pos.entry_price = entry_price
    pos.leverage = leverage
    pos.side = side
    return pos


@pytest.fixture
def mock_db():
    """Mock AsyncSession."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.begin_nested = MagicMock()
    return db


@pytest.fixture
def mock_redis():
    """Mock RedisService."""
    redis_svc = MagicMock()
    mock_lock = AsyncMock()
    mock_lock.acquire = AsyncMock(return_value=True)
    mock_lock.release = AsyncMock()
    redis_svc.redis = MagicMock()
    redis_svc.redis.lock = MagicMock(return_value=mock_lock)
    return redis_svc


@pytest.fixture
def service(mock_db, mock_redis):
    return PositionService(db=mock_db, redis=mock_redis)


@pytest.fixture
def service_no_redis(mock_db):
    return PositionService(db=mock_db, redis=None)


# ===================================================================
# PositionConflictError / CapitalExceededError
# ===================================================================


class TestExceptions:
    def test_position_conflict_error(self):
        sid = uuid.uuid4()
        err = PositionConflictError("BTC", sid)
        assert "BTC" in str(err)
        assert str(sid) in str(err)
        assert err.symbol == "BTC"
        assert err.owner_strategy_id == sid

    def test_capital_exceeded_error(self):
        err = CapitalExceededError("Over limit")
        assert "Over limit" in str(err)


# ===================================================================
# Symbol exclusivity
# ===================================================================


class TestSymbolExclusivity:
    @pytest.mark.asyncio
    async def test_check_symbol_available_true(self, service, mock_db):
        """Symbol is available when no existing position."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        available = await service.check_symbol_available(uuid.uuid4(), "BTC")
        assert available is True

    @pytest.mark.asyncio
    async def test_check_symbol_available_false(self, service, mock_db):
        """Symbol is not available when another strategy holds it."""
        existing = _make_position_record(symbol="BTC")
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = existing
        mock_db.execute.return_value = result_mock

        available = await service.check_symbol_available(uuid.uuid4(), "BTC")
        assert available is False

    @pytest.mark.asyncio
    async def test_check_symbol_available_with_exclude(self, service, mock_db):
        """Excluding own strategy should still check correctly."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        sid = uuid.uuid4()
        available = await service.check_symbol_available(
            uuid.uuid4(), "BTC", exclude_strategy_id=sid
        )
        assert available is True

    @pytest.mark.asyncio
    async def test_get_symbol_owner(self, service, mock_db):
        """Returns the owning position record."""
        existing = _make_position_record(symbol="ETH")
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = existing
        mock_db.execute.return_value = result_mock

        owner = await service.get_symbol_owner(uuid.uuid4(), "ETH")
        assert owner is existing

    @pytest.mark.asyncio
    async def test_check_symbols_conflict(self, service, mock_db):
        """Returns list of conflicting symbols."""
        call_count = 0

        async def _side_effect(stmt):
            nonlocal call_count
            result_mock = MagicMock()
            # First call (BTC) -> conflict, second (ETH) -> available
            if call_count == 0:
                result_mock.scalars.return_value.first.return_value = _make_position_record()
            else:
                result_mock.scalars.return_value.first.return_value = None
            call_count += 1
            return result_mock

        mock_db.execute.side_effect = _side_effect

        conflicts = await service.check_symbols_conflict(
            uuid.uuid4(), ["BTC", "ETH"]
        )
        assert "BTC" in conflicts
        assert "ETH" not in conflicts


# ===================================================================
# Position lifecycle: claim → confirm → close
# ===================================================================


class TestPositionLifecycle:
    @pytest.mark.asyncio
    async def test_claim_new_position(self, service, mock_db):
        """Claims a new position when symbol is free."""
        # get_symbol_owner returns None
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        # Mock begin_nested context manager
        nested_ctx = AsyncMock()
        mock_db.begin_nested.return_value = nested_ctx
        nested_ctx.__aenter__ = AsyncMock()
        nested_ctx.__aexit__ = AsyncMock(return_value=False)

        sid = uuid.uuid4()
        aid = uuid.uuid4()
        record = await service.claim_position(
            strategy_id=sid,
            strategy_type="ai",
            account_id=aid,
            symbol="btc",
            side="long",
            leverage=3,
        )
        assert record is not None
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_claim_existing_same_strategy(self, service, mock_db):
        """Returns existing record when same strategy already owns."""
        sid = uuid.uuid4()
        existing = _make_position_record(strategy_id=sid, symbol="BTC", status="open")
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = existing
        mock_db.execute.return_value = result_mock

        record = await service.claim_position(
            strategy_id=sid,
            strategy_type="ai",
            account_id=uuid.uuid4(),
            symbol="BTC",
            side="long",
        )
        assert record is existing

    @pytest.mark.asyncio
    async def test_claim_conflict_different_strategy(self, service, mock_db):
        """Raises PositionConflictError when another strategy owns."""
        existing = _make_position_record(strategy_id=uuid.uuid4(), symbol="BTC")
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = existing
        mock_db.execute.return_value = result_mock

        with pytest.raises(PositionConflictError):
            await service.claim_position(
                strategy_id=uuid.uuid4(),
                strategy_type="ai",
                account_id=uuid.uuid4(),
                symbol="BTC",
                side="long",
            )

    @pytest.mark.asyncio
    async def test_claim_redis_lock_failure(self, service, mock_redis):
        """Raises PositionConflictError when Redis lock cannot be acquired."""
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=False)
        mock_redis.redis.lock.return_value = mock_lock

        with pytest.raises(PositionConflictError):
            await service.claim_position(
                strategy_id=uuid.uuid4(),
                strategy_type="ai",
                account_id=uuid.uuid4(),
                symbol="BTC",
                side="long",
            )

    @pytest.mark.asyncio
    async def test_claim_without_redis(self, service_no_redis, mock_db):
        """Can claim position without Redis (fallback to DB-only)."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        nested_ctx = AsyncMock()
        mock_db.begin_nested.return_value = nested_ctx
        nested_ctx.__aenter__ = AsyncMock()
        nested_ctx.__aexit__ = AsyncMock(return_value=False)

        record = await service_no_redis.claim_position(
            strategy_id=uuid.uuid4(),
            strategy_type="quant",
            account_id=uuid.uuid4(),
            symbol="ETH",
            side="short",
        )
        assert record is not None

    @pytest.mark.asyncio
    async def test_confirm_position(self, service, mock_db):
        """Confirms a pending position to open."""
        pid = uuid.uuid4()
        await service.confirm_position(pid, size=0.05, size_usd=5000, entry_price=100000)
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_claim(self, service, mock_db):
        """Releases a pending claim."""
        pid = uuid.uuid4()
        await service.release_claim(pid)
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_position_record(self, service, mock_db):
        """Closes a position record."""
        pid = uuid.uuid4()
        await service.close_position_record(pid, close_price=105000, realized_pnl=250)
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()


# ===================================================================
# Accumulate position
# ===================================================================


class TestAccumulatePosition:
    @pytest.mark.asyncio
    async def test_accumulate_normal(self, service, mock_db):
        """Accumulates additional size with weighted average entry."""
        record = _make_position_record(
            size=0.1, size_usd=5000, entry_price=50000, status="open"
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = record
        mock_db.execute.return_value = result_mock

        await service.accumulate_position(
            position_id=record.id,
            additional_size=0.05,
            additional_size_usd=3000,
            fill_price=60000,
        )
        # execute called twice: select + update
        assert mock_db.execute.call_count == 2
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_accumulate_not_found(self, service, mock_db):
        """Does nothing when position not found."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        await service.accumulate_position(
            position_id=uuid.uuid4(),
            additional_size=0.05,
            additional_size_usd=3000,
            fill_price=60000,
        )
        # Only the select, no update
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_accumulate_not_open(self, service, mock_db):
        """Does nothing when position is not open (e.g., pending)."""
        record = _make_position_record(status="pending")
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = record
        mock_db.execute.return_value = result_mock

        await service.accumulate_position(
            position_id=record.id,
            additional_size=0.05,
            additional_size_usd=3000,
            fill_price=60000,
        )
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_accumulate_zero_total_size(self, service, mock_db):
        """Handles edge case where total_size is 0."""
        record = _make_position_record(
            size=0.0, size_usd=0, entry_price=0, status="open"
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = record
        mock_db.execute.return_value = result_mock

        await service.accumulate_position(
            position_id=record.id,
            additional_size=0.0,
            additional_size_usd=0,
            fill_price=50000,
        )
        # update still called with fallback price
        assert mock_db.execute.call_count == 2


# ===================================================================
# Capital allocation checks
# ===================================================================


class TestCapitalAllocation:
    @pytest.mark.asyncio
    async def test_claim_with_capital_check_pass(self, service, mock_db, mock_redis):
        """Capital check passes and position is claimed."""
        strategy = MagicMock()
        strategy.get_effective_capital.return_value = 10000.0

        # First call: get_strategy_positions (open) -> empty
        # Second call: get_account_open_positions -> empty
        # Third call: _get_total_account_allocation AI -> empty
        # Fourth call: _get_total_account_allocation Quant -> empty
        # Fifth call: get_symbol_owner -> None
        # Sixth call: begin_nested + flush
        call_count = 0

        async def _side_effect(stmt):
            nonlocal call_count
            result_mock = MagicMock()
            result_mock.scalars.return_value.all.return_value = []
            result_mock.scalars.return_value.first.return_value = None
            result_mock.rowcount = 0
            call_count += 1
            return result_mock

        mock_db.execute.side_effect = _side_effect
        nested_ctx = AsyncMock()
        mock_db.begin_nested.return_value = nested_ctx
        nested_ctx.__aenter__ = AsyncMock()
        nested_ctx.__aexit__ = AsyncMock(return_value=False)

        record = await service.claim_position_with_capital_check(
            strategy_id=uuid.uuid4(),
            strategy_type="ai",
            account_id=uuid.uuid4(),
            symbol="BTC",
            side="long",
            leverage=3,
            account_equity=50000.0,
            requested_size_usd=3000.0,
            strategy=strategy,
        )
        assert record is not None

    @pytest.mark.asyncio
    async def test_claim_with_capital_check_exceeds(self, service, mock_db, mock_redis):
        """Raises CapitalExceededError when exceeding allocation."""
        strategy = MagicMock()
        strategy.get_effective_capital.return_value = 100.0  # very small

        # Open positions already using most capital
        existing = _make_position_record(size_usd=100, leverage=1)
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [existing]
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(CapitalExceededError):
            await service.claim_position_with_capital_check(
                strategy_id=uuid.uuid4(),
                strategy_type="ai",
                account_id=uuid.uuid4(),
                symbol="BTC",
                side="long",
                leverage=1,
                account_equity=50000.0,
                requested_size_usd=5000.0,
                strategy=strategy,
            )

    @pytest.mark.asyncio
    async def test_claim_with_capital_check_no_strategy(self, service, mock_db, mock_redis):
        """Skips capital check when no strategy provided."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        nested_ctx = AsyncMock()
        mock_db.begin_nested.return_value = nested_ctx
        nested_ctx.__aenter__ = AsyncMock()
        nested_ctx.__aexit__ = AsyncMock(return_value=False)

        record = await service.claim_position_with_capital_check(
            strategy_id=uuid.uuid4(),
            strategy_type="quant",
            account_id=uuid.uuid4(),
            symbol="ETH",
            side="long",
            strategy=None,
        )
        assert record is not None

    @pytest.mark.asyncio
    async def test_claim_with_capital_lock_failure(self, service, mock_redis):
        """Raises CapitalExceededError when capital lock not acquired."""
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=False)
        mock_redis.redis.lock.return_value = mock_lock

        with pytest.raises(CapitalExceededError, match="lock"):
            await service.claim_position_with_capital_check(
                strategy_id=uuid.uuid4(),
                strategy_type="ai",
                account_id=uuid.uuid4(),
                symbol="BTC",
                side="long",
            )

    @pytest.mark.asyncio
    async def test_check_capital_no_allocation(self, service, mock_db):
        """No allocation configured -> always allowed."""
        strategy = MagicMock()
        strategy.get_effective_capital.return_value = None

        can_trade, reason = await service.check_capital_allocation(
            account_id=uuid.uuid4(),
            account_equity=50000,
            requesting_strategy_id=uuid.uuid4(),
            requested_size_usd=5000,
            strategy=strategy,
        )
        assert can_trade is True
        assert "No allocation" in reason

    @pytest.mark.asyncio
    async def test_check_capital_over_allocated_account(self, service, mock_db):
        """Account over-allocated beyond 95% of equity."""
        strategy = MagicMock()
        strategy.get_effective_capital.return_value = 100000.0  # larger than equity

        # No open positions for the strategy
        call_count = 0

        async def _side_effect(stmt):
            nonlocal call_count
            result_mock = MagicMock()
            result_mock.scalars.return_value.all.return_value = []
            call_count += 1
            return result_mock

        mock_db.execute.side_effect = _side_effect

        # Mock _get_total_account_allocation to return over-allocated amount
        with patch.object(service, "_get_total_account_allocation", return_value=48000):
            can_trade, reason = await service.check_capital_allocation(
                account_id=uuid.uuid4(),
                account_equity=50000,
                requesting_strategy_id=uuid.uuid4(),
                requested_size_usd=1000,
                strategy=strategy,
            )
            assert can_trade is False
            assert "over-allocated" in reason.lower()


# ===================================================================
# Query helpers
# ===================================================================


class TestQueryHelpers:
    @pytest.mark.asyncio
    async def test_get_strategy_positions_no_filter(self, service, mock_db):
        positions = [_make_position_record(), _make_position_record()]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = positions
        mock_db.execute.return_value = result_mock

        result = await service.get_strategy_positions(uuid.uuid4())
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_strategy_positions_with_filter(self, service, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result_mock

        result = await service.get_strategy_positions(uuid.uuid4(), status_filter="open")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_strategy_position_for_symbol(self, service, mock_db):
        record = _make_position_record(symbol="BTC")
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = record
        mock_db.execute.return_value = result_mock

        result = await service.get_strategy_position_for_symbol(uuid.uuid4(), "btc")
        assert result is record

    @pytest.mark.asyncio
    async def test_get_account_open_positions(self, service, mock_db):
        positions = [_make_position_record()]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = positions
        mock_db.execute.return_value = result_mock

        result = await service.get_account_open_positions(uuid.uuid4())
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_has_open_positions_true(self, service, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = _make_position_record()
        mock_db.execute.return_value = result_mock

        assert await service.has_open_positions(uuid.uuid4()) is True

    @pytest.mark.asyncio
    async def test_has_open_positions_false(self, service, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        assert await service.has_open_positions(uuid.uuid4()) is False


# ===================================================================
# Reconciliation
# ===================================================================


class TestReconciliation:
    @pytest.mark.asyncio
    async def test_reconcile_zombie(self, service, mock_db):
        """DB has position, exchange doesn't -> zombie closed."""
        aid = uuid.uuid4()
        old_position = _make_position_record(
            symbol="BTC",
            opened_at=datetime.now(UTC) - timedelta(minutes=10),
        )

        call_count = 0

        async def _side_effect(stmt):
            nonlocal call_count
            result_mock = MagicMock()
            if call_count == 0:
                # get_account_open_positions
                result_mock.scalars.return_value.all.return_value = [old_position]
            else:
                # close_position_record
                result_mock.rowcount = 1
            call_count += 1
            return result_mock

        mock_db.execute.side_effect = _side_effect

        summary = await service.reconcile(aid, [])
        assert summary["zombies_closed"] == 1
        assert summary["orphans_found"] == 0

    @pytest.mark.asyncio
    async def test_reconcile_zombie_grace_period(self, service, mock_db):
        """Recently opened DB position skipped (within grace period)."""
        aid = uuid.uuid4()
        recent_position = _make_position_record(
            symbol="BTC",
            opened_at=datetime.now(UTC) - timedelta(seconds=60),
        )

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [recent_position]
        mock_db.execute.return_value = result_mock

        summary = await service.reconcile(aid, [])
        assert summary["zombies_closed"] == 0
        assert "SKIP_ZOMBIE" in str(summary["details"])

    @pytest.mark.asyncio
    async def test_reconcile_orphan(self, service, mock_db):
        """Exchange has position, DB doesn't -> orphan created."""
        aid = uuid.uuid4()
        ex_pos = _make_exchange_position(symbol="ETH", size=1.0, size_usd=3000)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result_mock

        summary = await service.reconcile(aid, [ex_pos])
        assert summary["orphans_found"] == 1
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconcile_size_sync(self, service, mock_db):
        """Both exist but size differs -> sync from exchange."""
        aid = uuid.uuid4()
        db_pos = _make_position_record(symbol="BTC", size=0.1, size_usd=5000)
        ex_pos = _make_exchange_position(symbol="BTC", size=0.15, size_usd=7500)

        call_count = 0

        async def _side_effect(stmt):
            nonlocal call_count
            result_mock = MagicMock()
            if call_count == 0:
                result_mock.scalars.return_value.all.return_value = [db_pos]
            else:
                result_mock.rowcount = 1
            call_count += 1
            return result_mock

        mock_db.execute.side_effect = _side_effect

        summary = await service.reconcile(aid, [ex_pos])
        assert summary["size_synced"] == 1

    @pytest.mark.asyncio
    async def test_reconcile_no_discrepancies(self, service, mock_db):
        """No discrepancies -> empty summary."""
        aid = uuid.uuid4()
        db_pos = _make_position_record(symbol="BTC", size=0.1)
        ex_pos = _make_exchange_position(symbol="BTC", size=0.1)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [db_pos]
        mock_db.execute.return_value = result_mock

        summary = await service.reconcile(aid, [ex_pos])
        assert summary["zombies_closed"] == 0
        assert summary["orphans_found"] == 0
        assert summary["size_synced"] == 0


# ===================================================================
# Stale pending cleanup
# ===================================================================


class TestCleanupStalePending:
    @pytest.mark.asyncio
    async def test_cleanup_stale_found(self, service, mock_db):
        """Deletes stale pending claims."""
        result_mock = MagicMock()
        result_mock.rowcount = 3
        mock_db.execute.return_value = result_mock

        count = await service.cleanup_stale_pending(max_age_seconds=300)
        assert count == 3
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup_stale_none(self, service, mock_db):
        """No stale claims to delete."""
        result_mock = MagicMock()
        result_mock.rowcount = 0
        mock_db.execute.return_value = result_mock

        count = await service.cleanup_stale_pending()
        assert count == 0
