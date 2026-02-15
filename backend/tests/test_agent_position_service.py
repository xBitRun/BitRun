"""
Tests for AgentPositionService – agent-level position isolation.

Covers:
- Agent-isolated account state (get_agent_account_state)
- Position lifecycle: claim → confirm → close
- Accumulate position with weighted-average entry price
- Capital allocation checks
- Reconciliation (zombie, orphan, size-sync, grace period)
- Stale pending cleanup
- Redis lock interactions
- Error paths: IntegrityError, PositionConflictError, CapitalExceededError
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentDB, AgentPositionDB
from app.services.agent_position_service import (
    AgentPositionService,
    CapitalExceededError,
    PositionConflictError,
    _ZOMBIE_GRACE_PERIOD_SECONDS,
)
from app.traders.base import Position


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_position_db(
    agent_id: uuid.UUID,
    account_id: uuid.UUID | None = None,
    symbol: str = "BTC",
    side: str = "long",
    size: float = 0.1,
    size_usd: float = 5000.0,
    entry_price: float = 50000.0,
    leverage: int = 5,
    status: str = "open",
    opened_at: datetime | None = None,
    realized_pnl: float = 0.0,
    close_price: float | None = None,
    closed_at: datetime | None = None,
) -> AgentPositionDB:
    """Create an AgentPositionDB row in the DB."""
    return AgentPositionDB(
        id=uuid.uuid4(),
        agent_id=agent_id,
        account_id=account_id,
        symbol=symbol,
        side=side,
        size=size,
        size_usd=size_usd,
        entry_price=entry_price,
        leverage=leverage,
        status=status,
        opened_at=opened_at or datetime.now(UTC),
        realized_pnl=realized_pnl,
        close_price=close_price,
        closed_at=closed_at,
    )


def _make_exchange_position(
    symbol: str,
    side: str = "long",
    size: float = 0.1,
) -> Position:
    """Create a Position dataclass for exchange reconciliation."""
    return Position(
        symbol=symbol,
        side=side,
        size=size,
        size_usd=size * 50000,
        entry_price=50000.0,
        mark_price=50500.0,
        leverage=5,
        unrealized_pnl=50.0,
        unrealized_pnl_percent=1.0,
    )


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def agent_pos_service(db_session: AsyncSession, mock_redis) -> AgentPositionService:
    """Create an AgentPositionService with real DB and mocked Redis."""
    # Mock lock that always acquires
    lock = AsyncMock()
    lock.acquire = AsyncMock(return_value=True)
    lock.release = AsyncMock()
    mock_redis.redis.lock = MagicMock(return_value=lock)
    return AgentPositionService(db=db_session, redis=mock_redis)


@pytest_asyncio.fixture
async def agent_pos_service_no_redis(db_session: AsyncSession) -> AgentPositionService:
    """Create an AgentPositionService without Redis."""
    return AgentPositionService(db=db_session, redis=None)


# ─── Exception Classes ───────────────────────────────────────────────────────

class TestPositionConflictError:
    def test_message(self):
        agent_id = uuid.uuid4()
        err = PositionConflictError("BTC", agent_id)
        assert "BTC" in str(err)
        assert str(agent_id) in str(err)
        assert err.symbol == "BTC"
        assert err.agent_id == agent_id

    def test_is_exception(self):
        err = PositionConflictError("ETH", uuid.uuid4())
        assert isinstance(err, Exception)


class TestCapitalExceededError:
    def test_message(self):
        err = CapitalExceededError("Limit exceeded")
        assert str(err) == "Limit exceeded"

    def test_is_exception(self):
        err = CapitalExceededError("test")
        assert isinstance(err, Exception)


# ─── get_agent_account_state ──────────────────────────────────────────────────

class TestGetAgentAccountState:
    """Tests for building agent-isolated virtual account state."""

    async def test_empty_positions(
        self, agent_pos_service: AgentPositionService, test_agent: AgentDB
    ):
        """Agent with no positions should return base capital and zero PnL."""
        state = await agent_pos_service.get_agent_account_state(
            agent_id=test_agent.id,
            agent=test_agent,
            current_prices={},
        )
        assert state.agent_id == str(test_agent.id)
        assert state.positions == []
        assert state.total_unrealized_pnl == 0.0
        # mock mode: base_capital = mock_initial_balance = 10000.0
        assert state.equity == 10000.0
        assert state.available_balance == 10000.0

    async def test_long_position_with_profit(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Long position with price above entry -> positive unrealized PnL."""
        pos = _make_position_db(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="BTC",
            side="long",
            size=0.1,
            size_usd=5000.0,
            entry_price=50000.0,
            leverage=5,
        )
        db_session.add(pos)
        await db_session.flush()

        state = await agent_pos_service.get_agent_account_state(
            agent_id=test_agent.id,
            agent=test_agent,
            current_prices={"BTC": 51000.0},
        )
        assert len(state.positions) == 1
        # unrealized = (51000 - 50000) * 0.1 = 100
        assert state.total_unrealized_pnl == pytest.approx(100.0)
        # margin = 5000 / 5 = 1000
        # equity = 10000 + 100 + 0 (total_pnl) = 10100
        assert state.equity == pytest.approx(10100.0)
        # available = 10100 - 1000 = 9100
        assert state.available_balance == pytest.approx(9100.0)

    async def test_short_position_with_profit(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Short position with price below entry -> positive unrealized PnL."""
        pos = _make_position_db(
            agent_id=test_agent.id,
            symbol="ETH",
            side="short",
            size=1.0,
            size_usd=3000.0,
            entry_price=3000.0,
            leverage=3,
        )
        db_session.add(pos)
        await db_session.flush()

        state = await agent_pos_service.get_agent_account_state(
            agent_id=test_agent.id,
            agent=test_agent,
            current_prices={"ETH": 2800.0},
        )
        # unrealized = (3000 - 2800) * 1.0 = 200
        assert state.total_unrealized_pnl == pytest.approx(200.0)

    async def test_no_current_prices(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """When no current prices, unrealized PnL should be 0."""
        pos = _make_position_db(agent_id=test_agent.id, symbol="BTC")
        db_session.add(pos)
        await db_session.flush()

        state = await agent_pos_service.get_agent_account_state(
            agent_id=test_agent.id,
            agent=test_agent,
            current_prices=None,
        )
        assert state.total_unrealized_pnl == 0.0
        assert len(state.positions) == 1

    async def test_live_mode_allocated_capital(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Live mode agent with allocated_capital uses that as base."""
        test_agent.execution_mode = "live"
        test_agent.allocated_capital = 5000.0

        state = await agent_pos_service.get_agent_account_state(
            agent_id=test_agent.id,
            agent=test_agent,
        )
        assert state.equity == pytest.approx(5000.0)

    async def test_live_mode_percent_allocation_with_equity(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Live mode with percent allocation uses provided account_equity."""
        test_agent.execution_mode = "live"
        test_agent.allocated_capital = None
        test_agent.allocated_capital_percent = 0.5  # 50%

        state = await agent_pos_service.get_agent_account_state(
            agent_id=test_agent.id,
            agent=test_agent,
            account_equity=20000.0,  # Real account equity
        )
        # 50% of 20000 = 10000
        assert state.equity == pytest.approx(10000.0)

    async def test_live_mode_percent_allocation_fallback(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Live mode with percent allocation but no account_equity uses fallback."""
        test_agent.execution_mode = "live"
        test_agent.allocated_capital = None
        test_agent.allocated_capital_percent = 0.5  # 50%

        state = await agent_pos_service.get_agent_account_state(
            agent_id=test_agent.id,
            agent=test_agent,
        )
        # Fallback: 50% of 10000 = 5000
        assert state.equity == pytest.approx(5000.0)

    async def test_live_mode_no_allocation(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Live mode with no allocation configured uses default 10000."""
        test_agent.execution_mode = "live"
        test_agent.allocated_capital = None
        test_agent.allocated_capital_percent = None

        state = await agent_pos_service.get_agent_account_state(
            agent_id=test_agent.id,
            agent=test_agent,
        )
        assert state.equity == pytest.approx(10000.0)

    async def test_available_balance_clamped_to_zero(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Available balance cannot go negative."""
        # Create a very large position that uses more margin than equity
        pos = _make_position_db(
            agent_id=test_agent.id,
            size_usd=50000.0,
            leverage=1,  # margin = 50000
        )
        db_session.add(pos)
        await db_session.flush()

        state = await agent_pos_service.get_agent_account_state(
            agent_id=test_agent.id,
            agent=test_agent,
            current_prices={},
        )
        assert state.available_balance == 0.0


# ─── claim_position ──────────────────────────────────────────────────────────

class TestClaimPosition:
    """Tests for claiming a symbol slot before order execution."""

    async def test_claim_new_position(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Claiming a new symbol creates a pending record."""
        result = await agent_pos_service.claim_position(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="BTC",
            side="long",
            leverage=5,
        )
        assert result.symbol == "BTC"
        assert result.side == "long"
        assert result.status == "pending"
        assert result.leverage == 5
        assert result.agent_id == test_agent.id

    async def test_claim_normalizes_symbol_uppercase(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Symbol should be uppercased."""
        result = await agent_pos_service.claim_position(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="eth",
            side="short",
        )
        assert result.symbol == "ETH"

    async def test_claim_returns_existing_position(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """If agent already has open position on symbol, return it."""
        existing = _make_position_db(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="BTC",
            status="open",
        )
        db_session.add(existing)
        await db_session.flush()

        result = await agent_pos_service.claim_position(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="BTC",
            side="long",
        )
        assert result.id == existing.id

    async def test_claim_without_redis(
        self,
        agent_pos_service_no_redis: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Claiming works without Redis (no lock)."""
        result = await agent_pos_service_no_redis.claim_position(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="SOL",
            side="long",
        )
        assert result.symbol == "SOL"
        assert result.status == "pending"

    async def test_claim_lock_not_acquired(
        self,
        db_session: AsyncSession,
        mock_redis,
        test_agent: AgentDB,
    ):
        """If Redis lock cannot be acquired, raise PositionConflictError."""
        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=False)
        mock_redis.redis.lock = MagicMock(return_value=lock)
        svc = AgentPositionService(db=db_session, redis=mock_redis)

        with pytest.raises(PositionConflictError):
            await svc.claim_position(
                agent_id=test_agent.id,
                account_id=test_agent.account_id,
                symbol="BTC",
                side="long",
            )

    async def test_claim_lock_release_on_error(
        self,
        db_session: AsyncSession,
        mock_redis,
        test_agent: AgentDB,
    ):
        """Lock is released even if an error occurs inside the try block."""
        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=True)
        lock.release = AsyncMock()
        mock_redis.redis.lock = MagicMock(return_value=lock)
        svc = AgentPositionService(db=db_session, redis=mock_redis)

        # Force an error during flush by patching
        with patch.object(svc.db, "flush", side_effect=RuntimeError("db error")):
            with pytest.raises(RuntimeError):
                # Need a situation where get_agent_position_for_symbol returns None
                # but the nested begin raises an error
                with patch.object(
                    svc, "get_agent_position_for_symbol", return_value=None
                ):
                    with patch.object(
                        svc.db, "begin_nested", side_effect=RuntimeError("db error")
                    ):
                        await svc.claim_position(
                            agent_id=test_agent.id,
                            account_id=test_agent.account_id,
                            symbol="AVAX",
                            side="long",
                        )

        lock.release.assert_awaited()


# ─── claim_position_with_capital_check ────────────────────────────────────────

class TestClaimPositionWithCapitalCheck:
    """Tests for atomic capital check + claim."""

    async def test_claim_with_capital_ok(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Capital within limit allows claim."""
        test_agent.allocated_capital = 10000.0

        result = await agent_pos_service.claim_position_with_capital_check(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="BTC",
            side="long",
            leverage=5,
            account_equity=20000.0,
            requested_size_usd=5000.0,
            agent=test_agent,
        )
        assert result.symbol == "BTC"
        assert result.status == "pending"

    async def test_claim_capital_exceeded(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Capital exceeding limit raises CapitalExceededError."""
        test_agent.allocated_capital = 1000.0

        with pytest.raises(CapitalExceededError):
            await agent_pos_service.claim_position_with_capital_check(
                agent_id=test_agent.id,
                account_id=test_agent.account_id,
                symbol="BTC",
                side="long",
                leverage=1,
                account_equity=20000.0,
                requested_size_usd=2000.0,
                agent=test_agent,
            )

    async def test_claim_capital_no_agent_skips_check(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Without agent param, capital check is skipped."""
        result = await agent_pos_service.claim_position_with_capital_check(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="DOGE",
            side="long",
            agent=None,
        )
        assert result.symbol == "DOGE"

    async def test_claim_capital_zero_equity_skips_check(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Zero account equity skips capital check."""
        test_agent.allocated_capital = 100.0

        result = await agent_pos_service.claim_position_with_capital_check(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="XRP",
            side="short",
            account_equity=0.0,
            requested_size_usd=99999.0,
            agent=test_agent,
        )
        assert result.symbol == "XRP"

    async def test_claim_capital_lock_not_acquired(
        self,
        db_session: AsyncSession,
        mock_redis,
        test_agent: AgentDB,
    ):
        """If capital lock cannot be acquired, raise CapitalExceededError."""
        lock = AsyncMock()
        lock.acquire = AsyncMock(return_value=False)
        mock_redis.redis.lock = MagicMock(return_value=lock)
        svc = AgentPositionService(db=db_session, redis=mock_redis)

        with pytest.raises(CapitalExceededError, match="Could not acquire"):
            await svc.claim_position_with_capital_check(
                agent_id=test_agent.id,
                account_id=test_agent.account_id,
                symbol="BTC",
                side="long",
                agent=test_agent,
            )

    async def test_claim_capital_without_redis(
        self,
        agent_pos_service_no_redis: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Works without Redis (no capital lock)."""
        result = await agent_pos_service_no_redis.claim_position_with_capital_check(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="LINK",
            side="long",
        )
        assert result.symbol == "LINK"


# ─── confirm_position / release_claim ─────────────────────────────────────────

class TestConfirmAndRelease:
    """Tests for transitioning pending → open or deleting pending claims."""

    async def test_confirm_position(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Confirming a pending claim transitions it to open."""
        claim = await agent_pos_service.claim_position(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="BTC",
            side="long",
        )
        assert claim.status == "pending"

        await agent_pos_service.confirm_position(
            position_id=claim.id,
            size=0.05,
            size_usd=2500.0,
            entry_price=50000.0,
        )

        # Refresh from DB
        await db_session.refresh(claim)
        assert claim.status == "open"
        assert claim.size == 0.05
        assert claim.size_usd == 2500.0
        assert claim.entry_price == 50000.0

    async def test_release_claim(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Releasing a pending claim deletes it from DB."""
        claim = await agent_pos_service.claim_position(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="BTC",
            side="long",
        )

        await agent_pos_service.release_claim(claim.id)

        # Should not find it anymore
        result = await agent_pos_service.get_agent_position_for_symbol(
            test_agent.id, "BTC"
        )
        assert result is None

    async def test_release_only_deletes_pending(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Release does NOT delete open positions."""
        pos = _make_position_db(
            agent_id=test_agent.id,
            account_id=test_agent.account_id,
            symbol="ETH",
            status="open",
        )
        db_session.add(pos)
        await db_session.flush()

        await agent_pos_service.release_claim(pos.id)

        # Should still exist
        result = await agent_pos_service.get_agent_position_for_symbol(
            test_agent.id, "ETH"
        )
        assert result is not None
        assert result.status == "open"


# ─── accumulate_position ──────────────────────────────────────────────────────

class TestAccumulatePosition:
    """Tests for adding size to an existing open position (DCA/Grid)."""

    async def test_accumulate_weighted_avg_entry(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Accumulation recalculates weighted-average entry price."""
        pos = _make_position_db(
            agent_id=test_agent.id,
            symbol="BTC",
            size=0.1,
            size_usd=5000.0,
            entry_price=50000.0,
            status="open",
        )
        db_session.add(pos)
        await db_session.flush()

        await agent_pos_service.accumulate_position(
            position_id=pos.id,
            additional_size=0.1,
            additional_size_usd=4800.0,
            fill_price=48000.0,
        )

        await db_session.refresh(pos)
        assert pos.size == pytest.approx(0.2)
        assert pos.size_usd == pytest.approx(9800.0)
        # weighted avg: (0.1*50000 + 0.1*48000) / 0.2 = 49000
        assert pos.entry_price == pytest.approx(49000.0)

    async def test_accumulate_not_found(
        self,
        agent_pos_service: AgentPositionService,
    ):
        """Accumulating a non-existent position does nothing (no error)."""
        fake_id = uuid.uuid4()
        # Should not raise
        await agent_pos_service.accumulate_position(
            position_id=fake_id,
            additional_size=0.1,
            additional_size_usd=1000.0,
            fill_price=10000.0,
        )

    async def test_accumulate_closed_position_ignored(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Accumulating a closed position does nothing."""
        pos = _make_position_db(
            agent_id=test_agent.id,
            symbol="ETH",
            status="closed",
        )
        db_session.add(pos)
        await db_session.flush()
        original_size = pos.size

        await agent_pos_service.accumulate_position(
            position_id=pos.id,
            additional_size=1.0,
            additional_size_usd=3000.0,
            fill_price=3000.0,
        )

        await db_session.refresh(pos)
        assert pos.size == original_size

    async def test_accumulate_zero_total_size_fallback(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """When total size is 0 or fill_price is 0, use fallback entry price."""
        pos = _make_position_db(
            agent_id=test_agent.id,
            symbol="SOL",
            size=0.0,
            size_usd=0.0,
            entry_price=100.0,
            status="open",
        )
        db_session.add(pos)
        await db_session.flush()

        # additional_size=0 => total_size=0 => fallback
        await agent_pos_service.accumulate_position(
            position_id=pos.id,
            additional_size=0.0,
            additional_size_usd=0.0,
            fill_price=0.0,
        )

        await db_session.refresh(pos)
        # Fallback: fill_price(0) or old_entry(100) => 100
        assert pos.entry_price == pytest.approx(100.0)


# ─── close_position_record ────────────────────────────────────────────────────

class TestClosePositionRecord:
    async def test_close_position(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Close sets status, close_price, realized_pnl, and closed_at."""
        pos = _make_position_db(
            agent_id=test_agent.id,
            symbol="BTC",
            status="open",
        )
        db_session.add(pos)
        await db_session.flush()

        await agent_pos_service.close_position_record(
            position_id=pos.id,
            close_price=52000.0,
            realized_pnl=200.0,
        )

        await db_session.refresh(pos)
        assert pos.status == "closed"
        assert pos.close_price == 52000.0
        assert pos.realized_pnl == 200.0
        assert pos.closed_at is not None


# ─── Query helpers ────────────────────────────────────────────────────────────

class TestQueryHelpers:
    async def test_get_agent_positions_all(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Get all positions for an agent regardless of status."""
        for status in ("open", "pending", "closed"):
            pos = _make_position_db(
                agent_id=test_agent.id,
                symbol=f"SYM_{status.upper()}",
                status=status,
            )
            db_session.add(pos)
        await db_session.flush()

        all_pos = await agent_pos_service.get_agent_positions(test_agent.id)
        assert len(all_pos) == 3

    async def test_get_agent_positions_filtered(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Filter positions by status."""
        for status in ("open", "pending", "closed"):
            pos = _make_position_db(
                agent_id=test_agent.id,
                symbol=f"SYM_{status.upper()}",
                status=status,
            )
            db_session.add(pos)
        await db_session.flush()

        open_pos = await agent_pos_service.get_agent_positions(
            test_agent.id, status_filter="open"
        )
        assert len(open_pos) == 1
        assert open_pos[0].status == "open"

    async def test_get_agent_position_for_symbol(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Find open/pending position for specific symbol."""
        pos = _make_position_db(
            agent_id=test_agent.id,
            symbol="BTC",
            status="open",
        )
        db_session.add(pos)
        await db_session.flush()

        result = await agent_pos_service.get_agent_position_for_symbol(
            test_agent.id, "btc"  # lowercase input
        )
        assert result is not None
        assert result.symbol == "BTC"

    async def test_get_agent_position_for_symbol_not_found(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Returns None when no position exists."""
        result = await agent_pos_service.get_agent_position_for_symbol(
            test_agent.id, "DOESNOTEXIST"
        )
        assert result is None

    async def test_get_account_open_positions(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Get all open/pending positions for an account."""
        account_id = test_agent.account_id
        for status in ("open", "pending", "closed"):
            pos = _make_position_db(
                agent_id=test_agent.id,
                account_id=account_id,
                symbol=f"SYM_{status.upper()}",
                status=status,
            )
            db_session.add(pos)
        await db_session.flush()

        positions = await agent_pos_service.get_account_open_positions(account_id)
        assert len(positions) == 2  # open + pending

    async def test_has_open_positions_true(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        pos = _make_position_db(
            agent_id=test_agent.id, symbol="BTC", status="open"
        )
        db_session.add(pos)
        await db_session.flush()

        assert await agent_pos_service.has_open_positions(test_agent.id) is True

    async def test_has_open_positions_false(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        assert await agent_pos_service.has_open_positions(test_agent.id) is False

    async def test_has_open_positions_pending_counts(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Pending positions also count as 'having open positions'."""
        pos = _make_position_db(
            agent_id=test_agent.id, symbol="ETH", status="pending"
        )
        db_session.add(pos)
        await db_session.flush()

        assert await agent_pos_service.has_open_positions(test_agent.id) is True


# ─── get_account_net_positions ────────────────────────────────────────────────

class TestAccountNetPositions:
    async def test_net_positions_aggregation(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        test_user,
        test_strategy,
        db_session: AsyncSession,
    ):
        """Aggregate long and short positions per symbol."""
        account_id = test_agent.account_id

        # Create a second agent on same account
        agent2 = AgentDB(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="Agent 2",
            strategy_id=test_strategy.id,
            execution_mode="mock",
            mock_initial_balance=10000.0,
            account_id=account_id,
            status="draft",
            created_at=datetime.now(UTC),
        )
        db_session.add(agent2)
        await db_session.flush()

        # Agent 1: long BTC 0.1
        pos1 = _make_position_db(
            agent_id=test_agent.id,
            account_id=account_id,
            symbol="BTC",
            side="long",
            size=0.1,
            status="open",
        )
        # Agent 2: short BTC 0.05
        pos2 = _make_position_db(
            agent_id=agent2.id,
            account_id=account_id,
            symbol="BTC",
            side="short",
            size=0.05,
            status="open",
        )
        db_session.add_all([pos1, pos2])
        await db_session.flush()

        net = await agent_pos_service.get_account_net_positions(account_id)
        assert "BTC" in net
        assert net["BTC"]["long_size"] == pytest.approx(0.1)
        assert net["BTC"]["short_size"] == pytest.approx(0.05)
        assert net["BTC"]["net_size"] == pytest.approx(0.05)
        assert len(net["BTC"]["agents"]) == 2

    async def test_net_positions_empty(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        account_id = test_agent.account_id
        net = await agent_pos_service.get_account_net_positions(account_id)
        assert net == {}


# ─── check_capital_allocation ─────────────────────────────────────────────────

class TestCheckCapitalAllocation:
    async def test_no_allocation_configured(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """No allocation = always allowed."""
        test_agent.allocated_capital = None
        test_agent.allocated_capital_percent = None

        can_trade, reason = await agent_pos_service.check_capital_allocation(
            agent_id=test_agent.id,
            account_equity=10000.0,
            requested_size_usd=99999.0,
            agent=test_agent,
        )
        assert can_trade is True
        assert "No allocation" in reason

    async def test_within_limit(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Trade within allocation limit is allowed."""
        test_agent.allocated_capital = 5000.0

        can_trade, reason = await agent_pos_service.check_capital_allocation(
            agent_id=test_agent.id,
            account_equity=10000.0,
            requested_size_usd=5000.0,
            agent=test_agent,
            leverage=5,
        )
        assert can_trade is True
        assert reason == "OK"

    async def test_exceeds_limit(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Trade that would exceed allocation is rejected."""
        test_agent.allocated_capital = 1000.0

        can_trade, reason = await agent_pos_service.check_capital_allocation(
            agent_id=test_agent.id,
            account_equity=10000.0,
            requested_size_usd=5000.0,
            agent=test_agent,
            leverage=1,
        )
        assert can_trade is False
        assert "exceed" in reason.lower()

    async def test_accounts_for_existing_positions(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Capital check considers margin already used by open positions."""
        test_agent.allocated_capital = 3000.0

        # Existing position: 5000 USD at 5x => 1000 margin
        pos = _make_position_db(
            agent_id=test_agent.id,
            symbol="ETH",
            size_usd=5000.0,
            leverage=5,
            status="open",
        )
        db_session.add(pos)
        await db_session.flush()

        # Request: 10000 USD at 5x => 2000 margin. Total = 3000 => exactly at limit
        can_trade, _ = await agent_pos_service.check_capital_allocation(
            agent_id=test_agent.id,
            account_equity=10000.0,
            requested_size_usd=10000.0,
            agent=test_agent,
            leverage=5,
        )
        assert can_trade is True

        # Request: 10001 USD at 5x => 2000.2 margin. Total = 3000.2 => over limit
        can_trade, reason = await agent_pos_service.check_capital_allocation(
            agent_id=test_agent.id,
            account_equity=10000.0,
            requested_size_usd=10001.0,
            agent=test_agent,
            leverage=5,
        )
        assert can_trade is False


# ─── reconcile ────────────────────────────────────────────────────────────────

class TestReconcile:
    async def test_zombie_detection(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """App position with no exchange match → zombie → closed."""
        account_id = test_agent.account_id
        pos = _make_position_db(
            agent_id=test_agent.id,
            account_id=account_id,
            symbol="BTC",
            status="open",
            opened_at=datetime.now(UTC) - timedelta(seconds=_ZOMBIE_GRACE_PERIOD_SECONDS + 60),
        )
        db_session.add(pos)
        await db_session.flush()

        summary = await agent_pos_service.reconcile(
            account_id=account_id,
            exchange_positions=[],
        )
        assert summary["zombies_closed"] == 1
        assert any("ZOMBIE" in d for d in summary["details"])

    async def test_zombie_grace_period(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Recently opened positions should NOT be closed as zombies."""
        account_id = test_agent.account_id
        pos = _make_position_db(
            agent_id=test_agent.id,
            account_id=account_id,
            symbol="ETH",
            status="open",
            opened_at=datetime.now(UTC) - timedelta(seconds=10),  # very recent
        )
        db_session.add(pos)
        await db_session.flush()

        summary = await agent_pos_service.reconcile(
            account_id=account_id,
            exchange_positions=[],
        )
        assert summary["zombies_closed"] == 0
        assert any("SKIP_ZOMBIE" in d for d in summary["details"])

    async def test_orphan_detection(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
    ):
        """Exchange position with no app tracking → orphan."""
        account_id = test_agent.account_id
        exchange_pos = _make_exchange_position("SOL")

        summary = await agent_pos_service.reconcile(
            account_id=account_id,
            exchange_positions=[exchange_pos],
        )
        assert summary["orphans_found"] == 1
        assert any("ORPHAN" in d for d in summary["details"])

    async def test_size_drift(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Size mismatch between app and exchange → drift."""
        account_id = test_agent.account_id
        pos = _make_position_db(
            agent_id=test_agent.id,
            account_id=account_id,
            symbol="BTC",
            side="long",
            size=0.1,
            status="open",
            opened_at=datetime.now(UTC) - timedelta(seconds=600),
        )
        db_session.add(pos)
        await db_session.flush()

        # Exchange shows different size
        exchange_pos = _make_exchange_position("BTC", side="long", size=0.15)

        summary = await agent_pos_service.reconcile(
            account_id=account_id,
            exchange_positions=[exchange_pos],
        )
        assert summary["size_synced"] == 1
        assert any("DRIFT" in d for d in summary["details"])

    async def test_reconcile_all_matching(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Everything matches → no issues."""
        account_id = test_agent.account_id
        pos = _make_position_db(
            agent_id=test_agent.id,
            account_id=account_id,
            symbol="BTC",
            side="long",
            size=0.1,
            status="open",
            opened_at=datetime.now(UTC) - timedelta(seconds=600),
        )
        db_session.add(pos)
        await db_session.flush()

        exchange_pos = _make_exchange_position("BTC", side="long", size=0.1)

        summary = await agent_pos_service.reconcile(
            account_id=account_id,
            exchange_positions=[exchange_pos],
        )
        assert summary["zombies_closed"] == 0
        assert summary["orphans_found"] == 0
        assert summary["size_synced"] == 0

    async def test_short_position_drift(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Short exchange position: ex_size should be negative."""
        account_id = test_agent.account_id
        pos = _make_position_db(
            agent_id=test_agent.id,
            account_id=account_id,
            symbol="ETH",
            side="short",
            size=1.0,
            status="open",
            opened_at=datetime.now(UTC) - timedelta(seconds=600),
        )
        db_session.add(pos)
        await db_session.flush()

        exchange_pos = _make_exchange_position("ETH", side="short", size=1.0)

        summary = await agent_pos_service.reconcile(
            account_id=account_id,
            exchange_positions=[exchange_pos],
        )
        # app net = 0 - 1.0 = -1.0, exchange = -1.0 => matches
        assert summary["size_synced"] == 0


# ─── cleanup_stale_pending ────────────────────────────────────────────────────

class TestCleanupStalePending:
    async def test_cleanup_old_pending(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Stale pending claims are deleted."""
        old_pos = _make_position_db(
            agent_id=test_agent.id,
            symbol="BTC",
            status="pending",
            opened_at=datetime.now(UTC) - timedelta(seconds=600),
        )
        db_session.add(old_pos)
        await db_session.flush()

        count = await agent_pos_service.cleanup_stale_pending(max_age_seconds=300)
        assert count == 1

    async def test_cleanup_skips_recent_pending(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Recent pending claims are not deleted."""
        recent = _make_position_db(
            agent_id=test_agent.id,
            symbol="ETH",
            status="pending",
            opened_at=datetime.now(UTC),
        )
        db_session.add(recent)
        await db_session.flush()

        count = await agent_pos_service.cleanup_stale_pending(max_age_seconds=300)
        assert count == 0

    async def test_cleanup_skips_open_positions(
        self,
        agent_pos_service: AgentPositionService,
        test_agent: AgentDB,
        db_session: AsyncSession,
    ):
        """Open positions are never deleted even if old."""
        old_open = _make_position_db(
            agent_id=test_agent.id,
            symbol="SOL",
            status="open",
            opened_at=datetime.now(UTC) - timedelta(seconds=9999),
        )
        db_session.add(old_open)
        await db_session.flush()

        count = await agent_pos_service.cleanup_stale_pending(max_age_seconds=300)
        assert count == 0

    async def test_cleanup_returns_zero_when_nothing_to_clean(
        self,
        agent_pos_service: AgentPositionService,
    ):
        count = await agent_pos_service.cleanup_stale_pending()
        assert count == 0
