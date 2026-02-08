"""Quant strategy routes for traditional quantitative trading strategies"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.repositories.account import AccountRepository
from ...db.repositories.quant_strategy import QuantStrategyRepository
from ...models.quant_strategy import (
    QUANT_CONFIG_MODELS,
    QuantStrategyCreate,
    QuantStrategyResponse,
    QuantStrategyStatusUpdate,
    QuantStrategyType,
    QuantStrategyUpdate,
)

router = APIRouter(prefix="/quant-strategies", tags=["Quant Strategies"])
logger = logging.getLogger(__name__)


# ==================== Helper Functions ====================

def _to_response(strategy) -> QuantStrategyResponse:
    """Convert quant strategy DB model to response"""
    return QuantStrategyResponse(
        id=str(strategy.id),
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type,
        symbol=strategy.symbol,
        config=strategy.config,
        runtime_state=strategy.runtime_state or {},
        status=strategy.status,
        error_message=strategy.error_message,
        account_id=str(strategy.account_id) if strategy.account_id else None,
        allocated_capital=strategy.allocated_capital,
        allocated_capital_percent=strategy.allocated_capital_percent,
        total_pnl=strategy.total_pnl,
        total_trades=strategy.total_trades,
        winning_trades=strategy.winning_trades,
        losing_trades=strategy.losing_trades,
        win_rate=strategy.win_rate,
        max_drawdown=strategy.max_drawdown,
        created_at=strategy.created_at.isoformat(),
        updated_at=strategy.updated_at.isoformat(),
        last_run_at=strategy.last_run_at.isoformat() if strategy.last_run_at else None,
    )


def _validate_config(strategy_type: str, config: dict) -> None:
    """Validate config against the strategy-specific Pydantic model."""
    config_model = QUANT_CONFIG_MODELS.get(strategy_type)
    if config_model:
        try:
            config_model(**config)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid config for {strategy_type} strategy: {e}",
            )


# ==================== Routes ====================

@router.post("", response_model=QuantStrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_quant_strategy(
    data: QuantStrategyCreate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Create a new quantitative trading strategy.

    Supports: grid, dca, rsi strategy types.
    The strategy starts in 'draft' status.
    """
    # Validate strategy_type
    valid_types = {t.value for t in QuantStrategyType}
    strategy_type_str = data.strategy_type.value if isinstance(data.strategy_type, QuantStrategyType) else data.strategy_type
    if strategy_type_str not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy type. Must be one of: {', '.join(valid_types)}",
        )

    # Validate config structure against strategy-specific schema
    _validate_config(strategy_type_str, data.config)

    # Validate account ownership
    account_uuid = None
    if data.account_id:
        account_repo = AccountRepository(db)
        account = await account_repo.get_by_id(uuid.UUID(data.account_id))
        if not account or str(account.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found or does not belong to you.",
            )
        account_uuid = uuid.UUID(data.account_id)

    repo = QuantStrategyRepository(db)

    strategy = await repo.create(
        user_id=uuid.UUID(user_id),
        name=data.name,
        description=data.description,
        strategy_type=strategy_type_str,
        symbol=data.symbol.upper(),
        config=data.config,
        account_id=account_uuid,
        allocated_capital=data.allocated_capital,
        allocated_capital_percent=data.allocated_capital_percent,
    )

    return _to_response(strategy)


@router.get("", response_model=list[QuantStrategyResponse])
async def list_quant_strategies(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    status_filter: Optional[str] = None,
    strategy_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List all quant strategies for the current user.

    Optionally filter by status and/or strategy type.
    """
    repo = QuantStrategyRepository(db)
    strategies = await repo.get_by_user(
        uuid.UUID(user_id),
        status=status_filter,
        strategy_type=strategy_type,
        limit=limit,
        offset=offset,
    )

    return [_to_response(s) for s in strategies]


@router.get("/{strategy_id}", response_model=QuantStrategyResponse)
async def get_quant_strategy(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get a specific quant strategy"""
    repo = QuantStrategyRepository(db)
    strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quant strategy not found",
        )

    return _to_response(strategy)


@router.patch("/{strategy_id}", response_model=QuantStrategyResponse)
async def update_quant_strategy(
    strategy_id: str,
    data: QuantStrategyUpdate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Update a quant strategy"""
    repo = QuantStrategyRepository(db)

    update_data = data.model_dump(exclude_unset=True)

    from ...services.position_service import PositionService
    ps = PositionService(db=db)

    # Validate account ownership + protect account changes when positions exist
    if "account_id" in update_data and update_data["account_id"]:
        has_positions = await ps.has_open_positions(uuid.UUID(strategy_id))
        if has_positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change account while strategy has open positions. "
                       "Close all positions first.",
            )
        account_repo = AccountRepository(db)
        account = await account_repo.get_by_id(uuid.UUID(update_data["account_id"]))
        if not account or str(account.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found or does not belong to you.",
            )
        update_data["account_id"] = uuid.UUID(update_data["account_id"])

    # Protect symbol changes when positions exist
    if "symbol" in update_data:
        has_positions = await ps.has_open_positions(uuid.UUID(strategy_id))
        if has_positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change symbol while strategy has open positions. "
                       "Close all positions first.",
            )
        update_data["symbol"] = update_data["symbol"].upper()

    # Protect capital allocation changes when positions exist
    capital_changed = (
        "allocated_capital" in update_data or "allocated_capital_percent" in update_data
    )
    if capital_changed:
        has_positions = await ps.has_open_positions(uuid.UUID(strategy_id))
        if has_positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change capital allocation while strategy has open positions. "
                       "Close all positions first.",
            )

    # Validate config if being updated
    if "config" in update_data and update_data["config"]:
        strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
        if strategy:
            _validate_config(strategy.strategy_type, update_data["config"])

    strategy = await repo.update(
        uuid.UUID(strategy_id),
        uuid.UUID(user_id),
        **update_data,
    )

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quant strategy not found",
        )

    return _to_response(strategy)


@router.post("/{strategy_id}/status", response_model=QuantStrategyResponse)
async def update_quant_strategy_status(
    strategy_id: str,
    data: QuantStrategyStatusUpdate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Update quant strategy status.

    Valid transitions:
    - draft -> active (start)
    - active -> paused (pause)
    - paused -> active (resume)
    - active/paused -> stopped (stop)
    - warning -> active/paused/stopped
    """
    valid_statuses = {"active", "paused", "stopped"}
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    repo = QuantStrategyRepository(db)

    # Get current strategy
    strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quant strategy not found",
        )

    # Validate status transition
    current = strategy.status
    new = data.status

    valid_transitions = {
        ("draft", "active"),
        ("active", "paused"),
        ("active", "stopped"),
        ("paused", "active"),
        ("paused", "stopped"),
        ("error", "active"),
        ("error", "stopped"),
        # Warning state transitions
        ("warning", "active"),
        ("warning", "paused"),
        ("warning", "stopped"),
    }

    if (current, new) not in valid_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{current}' to '{new}'",
        )

    # Check if account is set for activation
    if new == "active" and not strategy.account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate strategy without an exchange account",
        )

    # Validate config before activation
    if new == "active":
        _validate_config(strategy.strategy_type, strategy.config)

        # When recovering from error state, verify that the exchange
        # connection is actually working before allowing reactivation.
        if current == "error":
            account_repo = AccountRepository(db)
            account = await account_repo.get_by_id(strategy.account_id)
            if not account:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Exchange account not found. Cannot reactivate.",
                )
            credentials = await account_repo.get_decrypted_credentials(
                strategy.account_id, strategy.user_id
            )
            if not credentials:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot decrypt exchange credentials. "
                           "Please update your API keys.",
                )
            trader = None
            try:
                from ...traders.ccxt_trader import create_trader_from_account
                trader = create_trader_from_account(account, credentials)
                await trader.initialize()
                # Quick connectivity check
                await trader.get_account_state()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Exchange connection failed: {e}. "
                           "Fix the issue before reactivating.",
                )
            finally:
                if trader:
                    try:
                        await trader.close()
                    except Exception:
                        pass

    # Update status
    await repo.update_status(uuid.UUID(strategy_id), new)

    # Sync with quant worker manager
    try:
        from ...workers.quant_worker import get_quant_worker_manager
        worker_manager = await get_quant_worker_manager()
        if new == "active":
            success = await worker_manager.start_strategy(strategy_id)
            if not success:
                logger.warning(f"Failed to start quant worker for strategy {strategy_id}")
        elif new in ("paused", "stopped"):
            await worker_manager.stop_strategy(strategy_id)
    except Exception as e:
        logger.error(f"Error syncing quant worker for strategy {strategy_id}: {e}")

    # Close open positions if requested when stopping
    if new == "stopped" and data.close_positions:
        try:
            from ...services.position_service import PositionService
            from ...traders.ccxt_trader import create_trader_from_account

            ps = PositionService(db=db)
            open_positions = await ps.get_strategy_positions(
                uuid.UUID(strategy_id), "open"
            )

            if open_positions and strategy.account_id:
                account_repo = AccountRepository(db)
                account = await account_repo.get_by_id(strategy.account_id)
                credentials = await account_repo.get_decrypted_credentials(
                    strategy.account_id, strategy.user_id
                )
                if account and credentials:
                    trader = create_trader_from_account(account, credentials)
                    await trader.initialize()
                    try:
                        for pos_record in open_positions:
                            try:
                                result = await trader.close_position(
                                    symbol=pos_record.symbol
                                )
                                if result.success:
                                    await ps.close_position_record(
                                        position_id=pos_record.id,
                                        close_price=result.filled_price or 0.0,
                                    )
                                    logger.info(
                                        f"Closed position {pos_record.symbol} "
                                        f"for stopped quant strategy {strategy_id}"
                                    )
                                else:
                                    logger.warning(
                                        f"Failed to close {pos_record.symbol}: {result.error}"
                                    )
                            except Exception as close_err:
                                logger.error(
                                    f"Error closing position {pos_record.symbol}: {close_err}"
                                )
                    finally:
                        await trader.close()
                    await db.commit()
        except Exception as e:
            logger.error(f"Error closing positions for quant strategy {strategy_id}: {e}")

    # Refresh strategy
    strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
    return _to_response(strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quant_strategy(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Delete a quant strategy. Must be stopped/draft and have no open positions."""
    repo = QuantStrategyRepository(db)

    # Validate strategy exists and check status
    strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quant strategy not found",
        )

    if strategy.status not in ("draft", "stopped"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete strategy in '{strategy.status}' status. "
                   "Stop the strategy first.",
        )

    # Check for open positions
    from ...services.position_service import PositionService
    ps = PositionService(db=db)
    has_positions = await ps.has_open_positions(uuid.UUID(strategy_id))
    if has_positions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete strategy with open positions. "
                   "Close all positions first.",
        )

    # Stop worker if running (safety)
    try:
        from ...workers.quant_worker import get_quant_worker_manager
        worker_manager = await get_quant_worker_manager()
        await worker_manager.stop_strategy(strategy_id)
    except Exception as e:
        logger.warning(f"Error stopping quant worker during delete: {e}")

    deleted = await repo.delete(uuid.UUID(strategy_id), uuid.UUID(user_id))

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quant strategy not found",
        )
