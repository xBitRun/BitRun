"""Tests for unified TradeExecutionService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.trade_execution_service import TradeExecutionService
from app.traders.base import OrderResult


def _build_trader():
    trader = AsyncMock()
    trader.open_long = AsyncMock(return_value=OrderResult(success=True, filled_size=0.01, filled_price=50000))
    trader.open_short = AsyncMock(return_value=OrderResult(success=True, filled_size=0.01, filled_price=50000))
    trader.close_position = AsyncMock(return_value=OrderResult(success=True, filled_price=51000))
    trader.get_position = AsyncMock(return_value=None)
    return trader


@pytest.mark.asyncio
async def test_open_position_mock_mode_claims_without_account_id():
    trader = _build_trader()
    ps = AsyncMock()
    claim = MagicMock()
    claim.status = "pending"
    claim.id = uuid.uuid4()
    ps.claim_position = AsyncMock(return_value=claim)

    service = TradeExecutionService(
        trader=trader,
        position_service=ps,
        agent_id=uuid.uuid4(),
        account_id=None,
        capital_agent=None,
    )

    result = await service.open_position(
        symbol="BTC",
        side="long",
        size_usd=100,
        leverage=2,
        allow_accumulate=False,
    )

    assert result.success is True
    ps.claim_position.assert_called_once()
    _, kwargs = ps.claim_position.call_args
    assert kwargs["account_id"] is None
    ps.confirm_position.assert_called_once()


@pytest.mark.asyncio
async def test_close_position_computes_realized_pnl_and_closes_record():
    trader = _build_trader()
    ps = AsyncMock()
    pos_record = MagicMock()
    pos_record.id = uuid.uuid4()
    pos_record.side = "long"
    pos_record.entry_price = 50000.0
    pos_record.size = 0.01
    ps.get_agent_position_for_symbol = AsyncMock(return_value=pos_record)

    service = TradeExecutionService(
        trader=trader,
        position_service=ps,
        agent_id=uuid.uuid4(),
        account_id=None,
        capital_agent=None,
    )

    result, realized_pnl, record = await service.close_position(symbol="BTC")

    assert result.success is True
    assert record is pos_record
    assert realized_pnl == pytest.approx(10.0)  # (51000 - 50000) * 0.01
    ps.close_position_record.assert_called_once()
