"""
Tests for Backtest Repository.

Covers:
- create: Create backtest result
- get_by_id: Get result by ID
- get_by_user: Get user's results (paginated)
- count_by_user: Count user's results
- get_by_strategy: Get strategy's results
- delete: Delete backtest result
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.backtest import BacktestRepository


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def backtest_repo(mock_session):
    """Create a BacktestRepository instance."""
    return BacktestRepository(mock_session)


@pytest.fixture
def mock_backtest_result():
    """Create a mock backtest result."""
    result = MagicMock()
    result.id = uuid.uuid4()
    result.user_id = uuid.uuid4()
    result.strategy_id = uuid.uuid4()
    result.strategy_name = "Test Strategy"
    result.symbols = ["BTC/USDT"]
    result.exchange = "binance"
    result.initial_balance = 10000.0
    result.final_balance = 12000.0
    result.total_return_percent = 20.0
    result.total_trades = 50
    result.winning_trades = 30
    result.losing_trades = 20
    result.win_rate = 60.0
    result.profit_factor = 1.5
    result.max_drawdown_percent = 10.0
    result.sharpe_ratio = 1.2
    result.sortino_ratio = 1.5
    result.calmar_ratio = 2.0
    result.total_fees = 50.0
    result.equity_curve = []
    result.drawdown_curve = []
    result.trades = []
    result.monthly_returns = []
    result.trade_statistics = {}
    result.symbol_breakdown = []
    result.analysis = {}
    result.created_at = datetime.utcnow()
    return result


# ── Test create ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBacktestRepositoryCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_success(self, backtest_repo, mock_session):
        """Should create backtest result successfully."""
        user_id = uuid.uuid4()
        strategy_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await backtest_repo.create(
            user_id=user_id,
            strategy_id=strategy_id,
            strategy_name="Test Strategy",
            symbols=["BTC/USDT"],
            exchange="binance",
            initial_balance=10000.0,
            timeframe="1h",
            use_ai=True,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            final_balance=12000.0,
            total_return_percent=20.0,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            win_rate=60.0,
            profit_factor=1.5,
            max_drawdown_percent=10.0,
            sharpe_ratio=1.2,
            sortino_ratio=1.5,
            calmar_ratio=2.0,
            total_fees=50.0,
            equity_curve=[],
            drawdown_curve=[],
            trades=[],
            monthly_returns=[],
            trade_statistics={},
            symbol_breakdown=[],
            analysis={},
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_none_strategy(self, backtest_repo, mock_session):
        """Should create backtest result without strategy."""
        user_id = uuid.uuid4()

        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await backtest_repo.create(
            user_id=user_id,
            strategy_id=None,
            strategy_name="Standalone Backtest",
            symbols=["ETH/USDT"],
            exchange="hyperliquid",
            initial_balance=5000.0,
            timeframe="4h",
            use_ai=False,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            final_balance=5500.0,
            total_return_percent=10.0,
            total_trades=20,
            winning_trades=12,
            losing_trades=8,
            win_rate=60.0,
            profit_factor=1.3,
            max_drawdown_percent=5.0,
            sharpe_ratio=None,
            sortino_ratio=None,
            calmar_ratio=None,
            total_fees=25.0,
            equity_curve=[],
            drawdown_curve=[],
            trades=[],
            monthly_returns=[],
            trade_statistics=None,
            symbol_breakdown=[],
            analysis=None,
        )

        mock_session.add.assert_called_once()


# ── Test get_by_id ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBacktestRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, backtest_repo, mock_session, mock_backtest_result):
        """Should return backtest result when found."""
        backtest_id = mock_backtest_result.id
        user_id = mock_backtest_result.user_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_backtest_result
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await backtest_repo.get_by_id(backtest_id, user_id)

        assert result == mock_backtest_result

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, backtest_repo, mock_session):
        """Should return None when not found."""
        backtest_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await backtest_repo.get_by_id(backtest_id, user_id)

        assert result is None


# ── Test get_by_user ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestBacktestRepositoryGetByUser:
    """Tests for get_by_user method."""

    @pytest.mark.asyncio
    async def test_get_by_user_success(self, backtest_repo, mock_session, mock_backtest_result):
        """Should return user's backtest results."""
        user_id = mock_backtest_result.user_id

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_backtest_result]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        results = await backtest_repo.get_by_user(user_id)

        assert len(results) == 1
        assert results[0] == mock_backtest_result

    @pytest.mark.asyncio
    async def test_get_by_user_with_pagination(self, backtest_repo, mock_session):
        """Should apply pagination correctly."""
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        results = await backtest_repo.get_by_user(user_id, limit=10, offset=20)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_user_empty(self, backtest_repo, mock_session):
        """Should return empty list when no results."""
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        results = await backtest_repo.get_by_user(user_id)

        assert results == []


# ── Test count_by_user ────────────────────────────────────────────────────


@pytest.mark.unit
class TestBacktestRepositoryCountByUser:
    """Tests for count_by_user method."""

    @pytest.mark.asyncio
    async def test_count_by_user_success(self, backtest_repo, mock_session):
        """Should return correct count."""
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await backtest_repo.count_by_user(user_id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_by_user_zero(self, backtest_repo, mock_session):
        """Should return 0 when no results."""
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await backtest_repo.count_by_user(user_id)

        assert count == 0


# ── Test get_by_strategy ──────────────────────────────────────────────────


@pytest.mark.unit
class TestBacktestRepositoryGetByStrategy:
    """Tests for get_by_strategy method."""

    @pytest.mark.asyncio
    async def test_get_by_strategy_success(self, backtest_repo, mock_session, mock_backtest_result):
        """Should return strategy's backtest results."""
        strategy_id = mock_backtest_result.strategy_id
        user_id = mock_backtest_result.user_id

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_backtest_result]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        results = await backtest_repo.get_by_strategy(strategy_id, user_id)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_by_strategy_with_pagination(self, backtest_repo, mock_session):
        """Should apply pagination correctly."""
        strategy_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        results = await backtest_repo.get_by_strategy(
            strategy_id, user_id, limit=5, offset=10
        )

        assert results == []


# ── Test delete ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBacktestRepositoryDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, backtest_repo, mock_session, mock_backtest_result):
        """Should delete backtest result successfully."""
        backtest_id = mock_backtest_result.id
        user_id = mock_backtest_result.user_id

        # Mock get_by_id to return result
        with patch.object(
            backtest_repo, "get_by_id", new_callable=AsyncMock, return_value=mock_backtest_result
        ):
            mock_session.delete = AsyncMock()
            mock_session.flush = AsyncMock()

            result = await backtest_repo.delete(backtest_id, user_id)

            assert result is True
            mock_session.delete.assert_called_once_with(mock_backtest_result)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, backtest_repo, mock_session):
        """Should return False when not found."""
        backtest_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch.object(
            backtest_repo, "get_by_id", new_callable=AsyncMock, return_value=None
        ):
            result = await backtest_repo.delete(backtest_id, user_id)

            assert result is False
