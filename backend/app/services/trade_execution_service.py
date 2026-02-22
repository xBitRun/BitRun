"""
Unified trade execution service for AI and Quant engines.

Provides a single claim -> execute -> confirm/release lifecycle with
agent-position isolation for both live and mock modes.
"""

import logging
import uuid
from typing import Optional

from ..db.models import AgentDB, AgentPositionDB
from ..traders.base import BaseTrader, OrderResult
from .agent_position_service import (
    AgentPositionService,
    CapitalExceededError,
    PositionConflictError,
)

logger = logging.getLogger(__name__)


class TradeExecutionService:
    """Shared trade execution with position-isolation lifecycle."""

    def __init__(
        self,
        trader: BaseTrader,
        position_service: Optional[AgentPositionService],
        agent_id: uuid.UUID | str,
        account_id: Optional[uuid.UUID | str] = None,
        capital_agent: Optional[AgentDB] = None,
    ):
        self.trader = trader
        self.position_service = position_service
        self.agent_id = self._coerce_id(agent_id)
        self.account_id = None if account_id is None else self._coerce_id(account_id)
        self.capital_agent = capital_agent

    @staticmethod
    def _coerce_id(value: uuid.UUID | str) -> uuid.UUID | str:
        """Best-effort UUID coercion while remaining test-double friendly."""
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return str(value)

    async def open_position(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        leverage: int = 1,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        account_equity: Optional[float] = None,
        allow_accumulate: bool = False,
    ) -> OrderResult:
        """
        Open (or optionally accumulate) a position with isolation tracking.

        - For live mode with account_id and capital_agent: runs capital check.
        - For mock mode (account_id=None): still claims for visibility consistency.
        """
        ps = self.position_service
        claim: Optional[AgentPositionDB] = None
        is_existing_position = False

        if ps:
            try:
                if (
                    self.account_id is not None
                    and self.capital_agent is not None
                ):
                    normalized_equity = (
                        account_equity
                        if isinstance(account_equity, (int, float))
                        else 0.0
                    )
                    claim = await ps.claim_position_with_capital_check(
                        agent_id=self.agent_id,
                        account_id=self.account_id,
                        symbol=symbol,
                        side=side,
                        leverage=leverage,
                        account_equity=normalized_equity,
                        requested_size_usd=size_usd,
                        agent=self.capital_agent,
                    )
                else:
                    claim = await ps.claim_position(
                        agent_id=self.agent_id,
                        account_id=self.account_id,
                        symbol=symbol,
                        side=side,
                        leverage=leverage,
                    )
                is_existing_position = claim.status == "open"
            except CapitalExceededError as e:
                return OrderResult(success=False, error=f"Capital exceeded: {e}")
            except PositionConflictError as e:
                return OrderResult(success=False, error=f"Symbol conflict: {e}")

        try:
            if side == "long":
                result = await self.trader.open_long(
                    symbol=symbol,
                    size_usd=size_usd,
                    leverage=leverage,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
            else:
                result = await self.trader.open_short(
                    symbol=symbol,
                    size_usd=size_usd,
                    leverage=leverage,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
        except Exception:
            if ps and claim and not is_existing_position:
                should_release = True
                try:
                    pos = await self.trader.get_position(symbol)
                    if pos and pos.size > 0:
                        await ps.confirm_position(
                            position_id=claim.id,
                            size=pos.size,
                            size_usd=pos.size_usd,
                            entry_price=pos.entry_price,
                        )
                        should_release = False
                except Exception:
                    pass
                if should_release:
                    await ps.release_claim(claim.id)
            raise

        if ps and claim:
            if result.success:
                estimated_size = result.filled_size or (size_usd / (result.filled_price or 1.0))
                fill_price = result.filled_price or 0.0
                try:
                    if allow_accumulate and is_existing_position:
                        await ps.accumulate_position(
                            position_id=claim.id,
                            additional_size=result.filled_size or estimated_size,
                            additional_size_usd=size_usd,
                            fill_price=fill_price,
                        )
                    else:
                        await ps.confirm_position(
                            position_id=claim.id,
                            size=result.filled_size or estimated_size,
                            size_usd=size_usd,
                            entry_price=fill_price,
                        )
                except Exception as e:
                    logger.critical(
                        "Position DB update failed after successful order "
                        f"for {symbol} (claim {claim.id}): {e}"
                    )
            elif not is_existing_position:
                await ps.release_claim(claim.id)

        return result

    async def close_position(
        self,
        symbol: str,
    ) -> tuple[OrderResult, Optional[float], Optional[AgentPositionDB]]:
        """
        Close a position with isolation tracking.

        Returns:
            (order_result, realized_pnl, position_record)
        """
        ps = self.position_service
        pos_record = None

        if ps:
            pos_record = await ps.get_agent_position_for_symbol(self.agent_id, symbol)

        result = await self.trader.close_position(symbol=symbol)
        realized_pnl: Optional[float] = None

        if ps and pos_record and result.success:
            close_price = result.filled_price or 0.0
            realized_pnl = 0.0
            if close_price > 0 and pos_record.entry_price > 0 and pos_record.size > 0:
                if pos_record.side == "long":
                    realized_pnl = (close_price - pos_record.entry_price) * pos_record.size
                else:
                    realized_pnl = (pos_record.entry_price - close_price) * pos_record.size

            await ps.close_position_record(
                position_id=pos_record.id,
                close_price=close_price,
                realized_pnl=realized_pnl,
            )

        return result, realized_pnl, pos_record
