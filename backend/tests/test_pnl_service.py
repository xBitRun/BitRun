"""
Tests for P&L Service - Profit and Loss tracking and analytics.

Covers:
- record_pnl_from_position: Creating P&L records from closed positions
- get_agent_pnl_summary: Agent-level P&L statistics
- get_account_pnl_summary: Account-level P&L statistics with periods
- get_account_equity_curve: Equity curve data generation
- create_account_snapshot: Daily account snapshots
- create_agent_snapshot: Daily agent snapshots
- get_agent_trade_history: Paginated trade history
- get_account_agents_performance: Multi-agent performance metrics
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pnl_service import PnLService


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def pnl_service(mock_db):
    """Create a PnLService instance with mock db."""
    return PnLService(mock_db)


@pytest.fixture
def mock_position():
    """Create a mock closed position."""
    position = MagicMock()
    position.id = uuid.uuid4()
    position.agent_id = uuid.uuid4()
    position.account_id = uuid.uuid4()
    position.symbol = "BTC/USDT"
    position.side = "long"
    position.entry_price = 50000.0
    position.size = 0.1
    position.size_usd = 5000.0
    position.leverage = 5
    position.opened_at = datetime.now(UTC) - timedelta(hours=2)
    position.closed_at = datetime.now(UTC)
    return position


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.user_id = uuid.uuid4()
    agent.account_id = uuid.uuid4()
    agent.name = "Test Agent"
    agent.execution_mode = "mock"
    agent.mock_initial_balance = 10000.0
    agent.total_pnl = 500.0
    agent.total_trades = 10
    agent.winning_trades = 7
    agent.losing_trades = 3
    agent.max_drawdown = 5.0
    agent.status = "active"
    agent.win_rate = 70.0
    agent.strategy = MagicMock()
    agent.strategy.name = "Test Strategy"
    agent.strategy.type = "ai"
    return agent


@pytest.fixture
def mock_account():
    """Create a mock exchange account."""
    account = MagicMock()
    account.id = uuid.uuid4()
    account.user_id = uuid.uuid4()
    return account


@pytest.fixture
def mock_pnl_record():
    """Create a mock P&L record."""
    record = MagicMock()
    record.id = uuid.uuid4()
    record.agent_id = uuid.uuid4()
    record.account_id = uuid.uuid4()
    record.symbol = "BTC/USDT"
    record.side = "long"
    record.realized_pnl = 100.0
    record.fees = 5.0
    record.entry_price = 50000.0
    record.exit_price = 51000.0
    record.size = 0.1
    record.size_usd = 5000.0
    record.leverage = 5
    record.opened_at = datetime.now(UTC) - timedelta(hours=2)
    record.closed_at = datetime.now(UTC)
    record.duration_minutes = 120
    record.exit_reason = "take_profit"
    return record


# ── Test record_pnl_from_position ───────────────────────────────────────


@pytest.mark.unit
class TestRecordPnlFromPosition:
    """Tests for record_pnl_from_position method."""

    @pytest.mark.asyncio
    async def test_record_pnl_success(
        self, pnl_service, mock_db, mock_position, mock_agent
    ):
        """Should create P&L record from closed position."""
        # Mock agent query
        agent_result = MagicMock()
        agent_result.scalars().first.return_value = mock_agent
        mock_db.execute.return_value = agent_result

        # Mock db.add and flush
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        record = await pnl_service.record_pnl_from_position(
            position=mock_position,
            close_price=51000.0,
            realized_pnl=100.0,
            fees=5.0,
            exit_reason="take_profit",
        )

        assert record is not None
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_pnl_agent_not_found(
        self, pnl_service, mock_db, mock_position
    ):
        """Should raise ValueError if agent not found."""
        agent_result = MagicMock()
        agent_result.scalars().first.return_value = None
        mock_db.execute.return_value = agent_result

        with pytest.raises(ValueError, match="Agent not found"):
            await pnl_service.record_pnl_from_position(
                position=mock_position,
                close_price=51000.0,
                realized_pnl=100.0,
            )

    @pytest.mark.asyncio
    async def test_record_pnl_calculates_duration(
        self, pnl_service, mock_db, mock_position, mock_agent
    ):
        """Should calculate duration correctly from opened_at to closed_at."""
        agent_result = MagicMock()
        agent_result.scalars().first.return_value = mock_agent
        mock_db.execute.return_value = agent_result
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        # Position opened 2 hours ago
        mock_position.opened_at = datetime.now(UTC) - timedelta(hours=2)
        mock_position.closed_at = datetime.now(UTC)

        await pnl_service.record_pnl_from_position(
            position=mock_position,
            close_price=51000.0,
            realized_pnl=100.0,
        )

        # Verify the record was created (duration should be ~120 minutes)
        added_record = mock_db.add.call_args[0][0]
        assert added_record.duration_minutes == 120


# ── Test get_agent_pnl_summary ───────────────────────────────────────────


@pytest.mark.unit
class TestGetAgentPnlSummary:
    """Tests for get_agent_pnl_summary method."""

    @pytest.mark.asyncio
    async def test_summary_with_no_records(self, pnl_service, mock_db):
        """Should return zero values when no records exist."""
        result = MagicMock()
        result.scalars().all.return_value = []
        mock_db.execute.return_value = result

        summary = await pnl_service.get_agent_pnl_summary(
            agent_id=uuid.uuid4()
        )

        assert summary["total_pnl"] == 0.0
        assert summary["total_trades"] == 0
        assert summary["winning_trades"] == 0
        assert summary["losing_trades"] == 0
        assert summary["win_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_summary_with_mixed_trades(self, pnl_service, mock_db):
        """Should calculate correct statistics with wins and losses."""
        # Create mock records: 3 wins, 2 losses
        records = []
        for pnl in [100.0, 50.0, 25.0, -30.0, -20.0]:
            r = MagicMock()
            r.realized_pnl = pnl
            r.fees = 5.0
            records.append(r)

        result = MagicMock()
        result.scalars().all.return_value = records
        mock_db.execute.return_value = result

        summary = await pnl_service.get_agent_pnl_summary(
            agent_id=uuid.uuid4()
        )

        assert summary["total_pnl"] == 125.0  # 100+50+25-30-20
        assert summary["total_trades"] == 5
        assert summary["winning_trades"] == 3
        assert summary["losing_trades"] == 2
        assert summary["win_rate"] == 60.0  # 3/5 * 100

    @pytest.mark.asyncio
    async def test_summary_with_date_filter(self, pnl_service, mock_db):
        """Should filter records by date range."""
        result = MagicMock()
        result.scalars().all.return_value = []
        mock_db.execute.return_value = result

        start = date.today() - timedelta(days=7)
        end = date.today()

        await pnl_service.get_agent_pnl_summary(
            agent_id=uuid.uuid4(),
            start_date=start,
            end_date=end,
        )

        # Verify query was executed
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_summary_profit_factor_infinite(self, pnl_service, mock_db):
        """Should return infinite profit factor when no losses."""
        records = []
        for pnl in [100.0, 50.0, 25.0]:
            r = MagicMock()
            r.realized_pnl = pnl
            r.fees = 5.0
            records.append(r)

        result = MagicMock()
        result.scalars().all.return_value = records
        mock_db.execute.return_value = result

        summary = await pnl_service.get_agent_pnl_summary(
            agent_id=uuid.uuid4()
        )

        assert summary["profit_factor"] == float("inf")


# ── Test get_account_pnl_summary ─────────────────────────────────────────


@pytest.mark.unit
class TestGetAccountPnlSummary:
    """Tests for get_account_pnl_summary method."""

    @pytest.mark.asyncio
    async def test_summary_all_period(self, pnl_service, mock_db):
        """Should return all records when period is 'all'."""
        records = []
        for pnl in [200.0, -50.0]:
            r = MagicMock()
            r.realized_pnl = pnl
            records.append(r)

        result = MagicMock()
        result.scalars().all.return_value = records
        mock_db.execute.return_value = result

        summary = await pnl_service.get_account_pnl_summary(
            account_id=uuid.uuid4(),
            period="all",
        )

        assert summary["total_pnl"] == 150.0
        assert summary["total_trades"] == 2

    @pytest.mark.asyncio
    async def test_summary_day_period(self, pnl_service, mock_db):
        """Should filter by today's date for 'day' period."""
        result = MagicMock()
        result.scalars().all.return_value = []
        mock_db.execute.return_value = result

        await pnl_service.get_account_pnl_summary(
            account_id=uuid.uuid4(),
            period="day",
        )

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_summary_week_period(self, pnl_service, mock_db):
        """Should filter by week start for 'week' period."""
        result = MagicMock()
        result.scalars().all.return_value = []
        mock_db.execute.return_value = result

        await pnl_service.get_account_pnl_summary(
            account_id=uuid.uuid4(),
            period="week",
        )

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_summary_month_period(self, pnl_service, mock_db):
        """Should filter by month start for 'month' period."""
        result = MagicMock()
        result.scalars().all.return_value = []
        mock_db.execute.return_value = result

        await pnl_service.get_account_pnl_summary(
            account_id=uuid.uuid4(),
            period="month",
        )

        mock_db.execute.assert_called_once()


# ── Test get_account_equity_curve ─────────────────────────────────────────


@pytest.mark.unit
class TestGetAccountEquityCurve:
    """Tests for get_account_equity_curve method."""

    @pytest.mark.asyncio
    async def test_equity_curve_empty(self, pnl_service, mock_db):
        """Should return empty list when no snapshots."""
        result = MagicMock()
        result.scalars().all.return_value = []
        mock_db.execute.return_value = result

        curve = await pnl_service.get_account_equity_curve(
            account_id=uuid.uuid4()
        )

        assert curve == []

    @pytest.mark.asyncio
    async def test_equity_curve_with_snapshots(self, pnl_service, mock_db):
        """Should transform snapshots to equity curve format."""
        today = date.today()

        # Create mock snapshots
        snapshots = []
        for i, (equity, daily_pnl) in enumerate([
            (10000.0, 100.0),
            (10100.0, 50.0),
            (10150.0, -25.0),
        ]):
            s = MagicMock()
            s.snapshot_date = today - timedelta(days=2 - i)
            s.equity = equity
            s.daily_pnl = daily_pnl
            s.daily_pnl_percent = (daily_pnl / 10000.0) * 100
            snapshots.append(s)

        result = MagicMock()
        result.scalars().all.return_value = snapshots
        mock_db.execute.return_value = result

        curve = await pnl_service.get_account_equity_curve(
            account_id=uuid.uuid4()
        )

        assert len(curve) == 3
        assert curve[0]["equity"] == 10000.0
        assert curve[0]["daily_pnl"] == 100.0


# ── Test create_account_snapshot ─────────────────────────────────────────


@pytest.mark.unit
class TestCreateAccountSnapshot:
    """Tests for create_account_snapshot method."""

    @pytest.mark.asyncio
    async def test_create_snapshot_new(self, pnl_service, mock_db, mock_account):
        """Should create new daily snapshot."""
        # Mock account query
        account_result = MagicMock()
        account_result.scalars().first.return_value = mock_account

        # Mock yesterday's snapshot (None = first snapshot)
        yesterday_result = MagicMock()
        yesterday_result.scalars().first.return_value = None

        # Mock existing today snapshot (None = create new)
        existing_result = MagicMock()
        existing_result.scalars().first.return_value = None

        mock_db.execute.side_effect = [
            account_result,
            yesterday_result,
            existing_result,
        ]
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        snapshot = await pnl_service.create_account_snapshot(
            account_id=mock_account.id,
            equity=10000.0,
            available_balance=9500.0,
            unrealized_pnl=500.0,
        )

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_snapshot_update_existing(
        self, pnl_service, mock_db, mock_account
    ):
        """Should update existing snapshot for same day."""
        # Mock account query
        account_result = MagicMock()
        account_result.scalars().first.return_value = mock_account

        # Mock yesterday's snapshot
        yesterday_snapshot = MagicMock()
        yesterday_snapshot.equity = 9900.0
        yesterday_result = MagicMock()
        yesterday_result.scalars().first.return_value = yesterday_snapshot

        # Mock existing today snapshot
        existing_snapshot = MagicMock()
        existing_snapshot.equity = 10000.0
        existing_result = MagicMock()
        existing_result.scalars().first.return_value = existing_snapshot

        mock_db.execute.side_effect = [
            account_result,
            yesterday_result,
            existing_result,
        ]
        mock_db.flush = AsyncMock()

        snapshot = await pnl_service.create_account_snapshot(
            account_id=mock_account.id,
            equity=10100.0,
            available_balance=9600.0,
        )

        # Should update existing, not create new
        assert snapshot is existing_snapshot

    @pytest.mark.asyncio
    async def test_create_snapshot_account_not_found(
        self, pnl_service, mock_db
    ):
        """Should raise ValueError if account not found."""
        account_result = MagicMock()
        account_result.scalars().first.return_value = None
        mock_db.execute.return_value = account_result

        with pytest.raises(ValueError, match="Account not found"):
            await pnl_service.create_account_snapshot(
                account_id=uuid.uuid4(),
                equity=10000.0,
                available_balance=9500.0,
            )


# ── Test create_agent_snapshot ───────────────────────────────────────────


@pytest.mark.unit
class TestCreateAgentSnapshot:
    """Tests for create_agent_snapshot method."""

    @pytest.mark.asyncio
    async def test_create_agent_snapshot_success(
        self, pnl_service, mock_db, mock_agent
    ):
        """Should create agent snapshot with correct metrics."""
        agent_result = MagicMock()
        agent_result.scalars().first.return_value = mock_agent

        yesterday_result = MagicMock()
        yesterday_result.scalars().first.return_value = None

        existing_result = MagicMock()
        existing_result.scalars().first.return_value = None

        mock_db.execute.side_effect = [
            agent_result,
            yesterday_result,
            existing_result,
        ]
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        snapshot = await pnl_service.create_agent_snapshot(
            agent_id=mock_agent.id
        )

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_snapshot_mock_mode(
        self, pnl_service, mock_db, mock_agent
    ):
        """Should calculate virtual equity for mock agents."""
        mock_agent.execution_mode = "mock"
        mock_agent.mock_initial_balance = 10000.0
        mock_agent.total_pnl = 500.0

        agent_result = MagicMock()
        agent_result.scalars().first.return_value = mock_agent

        yesterday_result = MagicMock()
        yesterday_result.scalars().first.return_value = None

        existing_result = MagicMock()
        existing_result.scalars().first.return_value = None

        mock_db.execute.side_effect = [
            agent_result,
            yesterday_result,
            existing_result,
        ]
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        await pnl_service.create_agent_snapshot(agent_id=mock_agent.id)

        added_snapshot = mock_db.add.call_args[0][0]
        assert added_snapshot.virtual_equity == 10500.0  # 10000 + 500

    @pytest.mark.asyncio
    async def test_create_agent_snapshot_agent_not_found(
        self, pnl_service, mock_db
    ):
        """Should raise ValueError if agent not found."""
        agent_result = MagicMock()
        agent_result.scalars().first.return_value = None
        mock_db.execute.return_value = agent_result

        with pytest.raises(ValueError, match="Agent not found"):
            await pnl_service.create_agent_snapshot(agent_id=uuid.uuid4())


# ── Test get_agent_trade_history ─────────────────────────────────────────


@pytest.mark.unit
class TestGetAgentTradeHistory:
    """Tests for get_agent_trade_history method."""

    @pytest.mark.asyncio
    async def test_trade_history_empty(self, pnl_service, mock_db):
        """Should return empty list when no trades."""
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        records_result = MagicMock()
        records_result.scalars().all.return_value = []

        mock_db.execute.side_effect = [count_result, records_result]

        records, total = await pnl_service.get_agent_trade_history(
            agent_id=uuid.uuid4()
        )

        assert records == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_trade_history_with_pagination(self, pnl_service, mock_db):
        """Should apply limit and offset correctly."""
        count_result = MagicMock()
        count_result.scalar.return_value = 100

        records_result = MagicMock()
        records_result.scalars().all.return_value = []

        mock_db.execute.side_effect = [count_result, records_result]

        records, total = await pnl_service.get_agent_trade_history(
            agent_id=uuid.uuid4(),
            limit=20,
            offset=40,
        )

        assert total == 100


# ── Test get_account_agents_performance ───────────────────────────────────


@pytest.mark.unit
class TestGetAccountAgentsPerformance:
    """Tests for get_account_agents_performance method."""

    @pytest.mark.asyncio
    async def test_performance_no_agents(self, pnl_service, mock_db):
        """Should return empty list when no agents."""
        agents_result = MagicMock()
        agents_result.scalars().all.return_value = []

        # Mock for positions count query
        positions_result = MagicMock()
        positions_result.scalar.return_value = 0

        mock_db.execute.side_effect = [agents_result]

        performances = await pnl_service.get_account_agents_performance(
            account_id=uuid.uuid4()
        )

        assert performances == []

    @pytest.mark.asyncio
    async def test_performance_with_agents(
        self, pnl_service, mock_db, mock_agent
    ):
        """Should return performance metrics for each agent."""
        agents_result = MagicMock()
        agents_result.scalars().all.return_value = [mock_agent]

        # Mock snapshot query
        snapshot_result = MagicMock()
        snapshot_result.scalars().first.return_value = None

        # Mock positions count query
        positions_result = MagicMock()
        positions_result.scalar.return_value = 2

        mock_db.execute.side_effect = [
            agents_result,
            snapshot_result,
            positions_result,
        ]

        performances = await pnl_service.get_account_agents_performance(
            account_id=uuid.uuid4()
        )

        assert len(performances) == 1
        assert performances[0]["agent_name"] == "Test Agent"
        assert performances[0]["total_pnl"] == 500.0
        assert performances[0]["open_positions"] == 2
