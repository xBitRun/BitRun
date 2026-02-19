"""
Agent routes - execution instance management.

Agent = Strategy + AI Model + Account/Mock.
Handles CRUD, status control, worker management, and position queries.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...core.dependencies import (
    CurrentUserDep,
    DbSessionDep,
    RateLimitStrategyDep,
)
from ...db.repositories.account import AccountRepository
from ...db.repositories.agent import AgentRepository
from ...db.repositories.decision import DecisionRepository
from ...db.repositories.strategy import StrategyRepository
from ...models.agent import (
    AgentCreate,
    AgentStatus,
    AgentStatusUpdate,
    AgentUpdate,
    ExecutionMode,
)
from ...traders.exchange_capabilities import supports_asset, AssetType

router = APIRouter(prefix="/agents", tags=["Agents"])
logger = logging.getLogger(__name__)


# ==================== Response Models ====================

class AgentResponse(BaseModel):
    """Agent response model"""
    id: str
    user_id: str
    name: str

    # Strategy
    strategy_id: str
    strategy_type: Optional[str] = None  # populated from strategy.type
    strategy_name: Optional[str] = None  # populated from strategy.name
    strategy_symbols: list[str] = []  # populated from strategy.symbols
    config: Optional[dict] = None  # populated from strategy.config

    # AI model
    ai_model: Optional[str] = None

    # Execution mode
    execution_mode: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None  # populated from exchange_account.name
    account_exchange: Optional[str] = None  # populated from exchange_account.exchange
    mock_initial_balance: Optional[float] = None

    # Capital allocation
    allocated_capital: Optional[float] = None
    allocated_capital_percent: Optional[float] = None

    # Execution config
    execution_interval_minutes: int = 30
    auto_execute: bool = True

    # Trade type configuration
    trade_type: str = "crypto_perp"

    # Multi-model debate configuration (for AI strategies)
    debate_enabled: bool = False
    debate_models: list[str] = []
    debate_consensus_mode: str = "majority_vote"
    debate_min_participants: int = 2

    # Runtime state (quant)
    runtime_state: Optional[dict] = None

    # Status
    status: str
    error_message: Optional[str] = None

    # Performance
    total_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    max_drawdown: float = 0.0

    # Timestamps
    created_at: str
    updated_at: str
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None


class AgentPositionResponse(BaseModel):
    """Agent position response"""
    id: str
    agent_id: str
    account_id: Optional[str] = None
    symbol: str
    side: str
    size: float
    size_usd: float
    entry_price: float
    leverage: int
    status: str
    realized_pnl: float = 0.0
    close_price: Optional[float] = None
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None
    # Real-time fields (populated in live mode from exchange)
    mark_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percent: Optional[float] = None


class AgentAccountStateResponse(BaseModel):
    """Agent account state response for positions tab"""
    equity: float = Field(description="Total account equity")
    available_balance: float = Field(description="Available balance for new positions")
    total_unrealized_pnl: float = Field(description="Total unrealized profit/loss")
    total_margin_used: float = Field(description="Total margin used by open positions")
    realized_pnl: float = 0.0
    close_price: Optional[float] = None
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None


class BoundAccountInfo(BaseModel):
    """Info about an account bound to agents"""
    account_id: str = Field(description="Exchange account ID")
    total_percent: float = Field(description="Total percentage allocated (0.0 to 1.0+)")
    agent_count: int = Field(description="Number of agents using this account")
    allocation_mode: Optional[str] = Field(
        default=None,
        description="Current allocation mode: 'percent', 'fixed', or None if no allocation set"
    )


# ==================== Routes ====================

@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Create a new execution agent.

    Binds a strategy to a model (for AI) and an account (for live) or
    mock configuration (for simulation).
    """
    strategy_repo = StrategyRepository(db)
    strategy = await strategy_repo.get_by_id(
        uuid.UUID(data.strategy_id), uuid.UUID(user_id)
    )
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy not found or does not belong to you."
        )

    # AI strategies require either ai_model or debate with 2+ models
    if strategy.type == "ai":
        has_single_model = data.ai_model is not None
        has_debate = data.debate_enabled and len(data.debate_models or []) >= 2
        if not has_single_model and not has_debate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI strategies require either ai_model or debate mode with 2+ models."
            )

    # Quant strategies don't need ai_model
    if strategy.type != "ai" and data.ai_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantitative strategies do not use an AI model."
        )

    # Validate account ownership for live mode
    account_uuid = None
    if data.execution_mode == ExecutionMode.LIVE:
        if not data.account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Live mode requires an exchange account."
            )
        account_repo = AccountRepository(db)
        account = await account_repo.get_by_id(uuid.UUID(data.account_id))
        if not account or str(account.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found or does not belong to you."
            )
        account_uuid = uuid.UUID(data.account_id)

        # Validate exchange supports the requested trade type
        if not supports_asset(account.exchange, AssetType(data.trade_type.value)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange {account.exchange} does not support {data.trade_type.value}"
            )

    agent_repo = AgentRepository(db)

    # Validate capital allocation for live mode
    if data.execution_mode == ExecutionMode.LIVE and account_uuid:
        if data.allocated_capital_percent is not None:
            total_percent = await agent_repo.get_account_allocated_percent(account_uuid)
            new_total = total_percent + data.allocated_capital_percent
            if new_total > 1.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Capital allocation exceeds 100%. "
                    f"Current: {total_percent*100:.1f}%, Requested: {data.allocated_capital_percent*100:.1f}%"
                )
    agent = await agent_repo.create(
        user_id=uuid.UUID(user_id),
        name=data.name,
        strategy_id=uuid.UUID(data.strategy_id),
        ai_model=data.ai_model,
        execution_mode=data.execution_mode.value,
        account_id=account_uuid,
        mock_initial_balance=data.mock_initial_balance,
        allocated_capital=data.allocated_capital,
        allocated_capital_percent=data.allocated_capital_percent,
        execution_interval_minutes=data.execution_interval_minutes,
        auto_execute=data.auto_execute,
        trade_type=data.trade_type.value,
        debate_enabled=data.debate_enabled,
        debate_models=data.debate_models,
        debate_consensus_mode=data.debate_consensus_mode,
        debate_min_participants=data.debate_min_participants,
    )

    # Eagerly load strategy for response
    agent = await agent_repo.get_by_id(
        agent.id, include_strategy=True, include_account=True
    )

    return _agent_to_response(agent)


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    status_filter: Optional[str] = None,
    strategy_type: Optional[str] = None,
    execution_mode: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List all agents for the current user.

    Optionally filter by status, strategy type, or execution mode.
    """
    agent_repo = AgentRepository(db)
    agents = await agent_repo.get_by_user(
        uuid.UUID(user_id),
        status=status_filter,
        strategy_type=strategy_type,
        execution_mode=execution_mode,
        limit=limit,
        offset=offset,
        include_account=True,
    )

    return [_agent_to_response(a) for a in agents]


@router.get("/bound-accounts", response_model=dict[str, BoundAccountInfo])
async def get_bound_accounts(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Get allocation info for all exchange accounts that have live agents.

    Returns account IDs mapped to their allocation summary (total percent, agent count, and allocation mode).
    """
    agent_repo = AgentRepository(db)
    bound_ids = await agent_repo.get_bound_account_ids(uuid.UUID(user_id))

    result = {}
    for account_id in bound_ids:
        summary = await agent_repo.get_account_allocation_summary(account_id)
        result[str(account_id)] = BoundAccountInfo(
            account_id=str(account_id),
            total_percent=summary["total_percent"],
            agent_count=len(summary["agents"]),
            allocation_mode=summary.get("allocation_mode"),
        )

    return result


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get a specific agent"""
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(
        uuid.UUID(agent_id),
        uuid.UUID(user_id),
        include_strategy=True,
        include_account=True,
    )

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    return _agent_to_response(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Update an agent's configuration"""
    agent_repo = AgentRepository(db)

    update_data = data.model_dump(exclude_unset=True)

    # Validate account ownership if changing
    if "account_id" in update_data and update_data["account_id"]:
        # Check for open positions
        from ...services.agent_position_service import AgentPositionService
        ps = AgentPositionService(db=db)
        has_positions = await ps.has_open_positions(uuid.UUID(agent_id))
        if has_positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change account while agent has open positions."
            )

        account_repo = AccountRepository(db)
        account = await account_repo.get_by_id(uuid.UUID(update_data["account_id"]))
        if not account or str(account.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found or does not belong to you."
            )
        update_data["account_id"] = uuid.UUID(update_data["account_id"])

    # Protect capital allocation changes when positions exist
    if "allocated_capital" in update_data or "allocated_capital_percent" in update_data:
        from ...services.agent_position_service import AgentPositionService
        ps = AgentPositionService(db=db)
        has_positions = await ps.has_open_positions(uuid.UUID(agent_id))
        if has_positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change capital allocation while agent has open positions."
            )

    # Validate capital allocation percentage doesn't exceed 100%
    if "allocated_capital_percent" in update_data and update_data["allocated_capital_percent"] is not None:
        # Get current agent to determine account_id
        current_agent = await agent_repo.get_by_id(uuid.UUID(agent_id), uuid.UUID(user_id))
        if current_agent and current_agent.account_id:
            total_percent = await agent_repo.get_account_allocated_percent(
                account_id=current_agent.account_id,
                exclude_agent_id=uuid.UUID(agent_id),
            )
            new_total = total_percent + update_data["allocated_capital_percent"]
            if new_total > 1.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Capital allocation would exceed 100%. "
                    f"Current (other agents): {total_percent*100:.1f}%, "
                    f"Requested: {update_data['allocated_capital_percent']*100:.1f}%"
                )

    # Convert enums
    if "execution_mode" in update_data and update_data["execution_mode"]:
        update_data["execution_mode"] = update_data["execution_mode"].value

    agent = await agent_repo.update(
        uuid.UUID(agent_id),
        uuid.UUID(user_id),
        **update_data,
    )

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    agent = await agent_repo.get_by_id(
        agent.id, include_strategy=True, include_account=True
    )
    return _agent_to_response(agent)


@router.post("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: str,
    data: AgentStatusUpdate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitStrategyDep = None,
):
    """
    Update agent status (start/pause/stop).

    Valid transitions:
    - draft -> active (start)
    - active -> paused (pause)
    - paused -> active (resume)
    - active/paused -> stopped (stop)
    - error/warning -> active/stopped
    """
    valid_statuses = {"active", "paused", "stopped"}
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(
        uuid.UUID(agent_id),
        uuid.UUID(user_id),
        include_strategy=True,
    )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Validate transition
    current = agent.status
    new = data.status

    valid_transitions = {
        ("draft", "active"),
        ("active", "paused"),
        ("active", "stopped"),
        ("paused", "active"),
        ("paused", "stopped"),
        ("error", "active"),
        ("error", "stopped"),
        ("warning", "active"),
        ("warning", "paused"),
        ("warning", "stopped"),
    }

    if (current, new) not in valid_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{current}' to '{new}'"
        )

    # Live mode activation requires an account
    if new == "active" and agent.execution_mode == "live" and not agent.account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate live agent without an exchange account"
        )

    # AI strategy activation requires ai_model
    if new == "active" and agent.strategy and agent.strategy.type == "ai":
        if not agent.ai_model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot activate AI agent without selecting a model"
            )

    # Exchange connection check for live mode error recovery
    if new == "active" and current == "error" and agent.execution_mode == "live":
        account_repo = AccountRepository(db)
        account = await account_repo.get_by_id(agent.account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exchange account not found. Cannot reactivate."
            )
        credentials = await account_repo.get_decrypted_credentials(
            agent.account_id, agent.user_id
        )
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot decrypt exchange credentials."
            )
        trader = None
        try:
            from ...traders.ccxt_trader import create_trader_from_account
            trader = create_trader_from_account(account, credentials)
            await trader.initialize()
            await trader.get_account_state()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange connection failed: {e}"
            )
        finally:
            if trader:
                try:
                    await trader.close()
                except Exception:
                    pass

    # Update status
    await agent_repo.update_status(uuid.UUID(agent_id), new)

    # TODO: Sync with unified worker manager
    # For now, use existing worker managers based on strategy type
    try:
        if agent.strategy and agent.strategy.type == "ai":
            # AI strategy: ExecutionWorker expects StrategyDB.id
            from ...workers.execution_worker import get_worker_manager
            worker_manager = await get_worker_manager()
            strategy_id = str(agent.strategy_id)  # StrategyDB.id
            if new == "active":
                await worker_manager.start_strategy(strategy_id)
            elif new in ("paused", "stopped"):
                await worker_manager.stop_strategy(strategy_id)
        else:
            # Quant strategy: QuantWorkerManager expects AgentDB.id
            # (because QuantStrategyDB = AgentDB)
            from ...workers.quant_worker import get_quant_worker_manager
            worker_manager = await get_quant_worker_manager()
            agent_id_str = str(agent.id)  # AgentDB.id
            if new == "active":
                await worker_manager.start_strategy(agent_id_str)
            elif new in ("paused", "stopped"):
                await worker_manager.stop_strategy(agent_id_str)
    except Exception as e:
        logger.error(f"Error syncing worker for agent {agent_id}: {e}")

    # Close positions if requested
    if new == "stopped" and data.close_positions:
        try:
            from ...services.agent_position_service import AgentPositionService
            ps = AgentPositionService(db=db)
            open_positions = await ps.get_agent_positions(
                uuid.UUID(agent_id), "open"
            )

            if open_positions and agent.account_id:
                account_repo = AccountRepository(db)
                account = await account_repo.get_by_id(agent.account_id)
                credentials = await account_repo.get_decrypted_credentials(
                    agent.account_id, agent.user_id
                )
                if account and credentials:
                    from ...traders.ccxt_trader import create_trader_from_account
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
                                        f"for agent {agent_id}"
                                    )
                            except Exception as close_err:
                                logger.error(
                                    f"Error closing position {pos_record.symbol}: {close_err}"
                                )
                    finally:
                        await trader.close()
                    await db.commit()
        except Exception as e:
            logger.error(f"Error closing positions for agent {agent_id}: {e}")

    agent = await agent_repo.get_by_id(
        uuid.UUID(agent_id),
        uuid.UUID(user_id),
        include_strategy=True,
        include_account=True,
    )
    return _agent_to_response(agent)


@router.get("/{agent_id}/positions", response_model=list[AgentPositionResponse])
async def get_agent_positions(
    agent_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    status_filter: Optional[str] = None,
):
    """Get positions for a specific agent (isolated from other agents).

    For live mode agents, fetches real-time position data from the exchange
    and merges with local position records.
    """
    # Verify ownership
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(uuid.UUID(agent_id), uuid.UUID(user_id))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    from ...services.agent_position_service import AgentPositionService
    ps = AgentPositionService(db=db)
    positions = await ps.get_agent_positions(
        uuid.UUID(agent_id),
        status_filter=status_filter,
    )

    # For live mode, fetch real-time data from exchange
    exchange_positions: dict[str, dict] = {}  # key: "{symbol}_{side}"
    if agent.account_id and agent.execution_mode == "live":
        try:
            from ...db.repositories.account import AccountRepository
            from ...traders.ccxt_trader import create_trader_from_account

            account_repo = AccountRepository(db)
            account = await account_repo.get_by_id(agent.account_id, uuid.UUID(user_id))
            if account:
                from ...core.config import get_settings
                from cryptography.fernet import Fernet

                settings = get_settings()
                cipher = Fernet(settings.data_encryption_key.encode())
                credentials = {
                    k: cipher.decrypt(v.encode()).decode()
                    for k, v in account.credentials.items()
                }
                trader = create_trader_from_account(account, credentials)
                await trader.initialize()
                try:
                    # Fetch positions from exchange
                    raw_positions = await trader.get_positions()
                    # Index by symbol+side for matching
                    for pos in raw_positions:
                        key = f"{pos.symbol}_{pos.side}"
                        exchange_positions[key] = {
                            "mark_price": pos.mark_price,
                            "unrealized_pnl": pos.unrealized_pnl,
                            "unrealized_pnl_percent": pos.unrealized_pnl_percent,
                            "size": pos.size,
                            "size_usd": pos.size_usd,
                        }
                finally:
                    await trader.close()
        except Exception as e:
            logger.warning(f"Failed to fetch exchange positions for agent {agent_id}: {e}")

    # Build response, merging exchange data for live mode
    result = []
    for p in positions:
        # Try to get real-time data from exchange
        key = f"{p.symbol}_{p.side}"
        exchange_data = exchange_positions.get(key, {})

        response = AgentPositionResponse(
            id=str(p.id),
            agent_id=str(p.agent_id),
            account_id=str(p.account_id) if p.account_id else None,
            symbol=p.symbol,
            side=p.side,
            size=exchange_data.get("size", p.size),
            size_usd=exchange_data.get("size_usd", p.size_usd),
            entry_price=p.entry_price,
            leverage=p.leverage,
            status=p.status,
            realized_pnl=p.realized_pnl,
            close_price=p.close_price,
            opened_at=p.opened_at.isoformat() if p.opened_at else None,
            closed_at=p.closed_at.isoformat() if p.closed_at else None,
            # Real-time fields from exchange (only in live mode)
            mark_price=exchange_data.get("mark_price"),
            unrealized_pnl=exchange_data.get("unrealized_pnl"),
            unrealized_pnl_percent=exchange_data.get("unrealized_pnl_percent"),
        )
        result.append(response)

    return result


@router.get("/{agent_id}/account-state", response_model=AgentAccountStateResponse)
async def get_agent_account_state(
    agent_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get agent's account state including equity and balance.

    For live mode: Returns real exchange account state (filtered to this agent's positions).
    For mock mode: Returns virtual account state based on mock balance.
    """
    # Get agent and verify ownership
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(uuid.UUID(agent_id), uuid.UUID(user_id))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    from ...services.agent_position_service import AgentPositionService
    ps = AgentPositionService(db=db)

    # For live mode with exchange account, get real data from exchange
    if agent.account_id and agent.execution_mode == "live":
        try:
            from ...db.repositories.account import AccountRepository
            from ...traders.ccxt_trader import create_trader_from_account

            account_repo = AccountRepository(db)
            credentials = await account_repo.get_decrypted_credentials(
                agent.account_id, uuid.UUID(user_id)
            )
            if credentials:
                account = await account_repo.get_by_id(agent.account_id, uuid.UUID(user_id))
                trader = create_trader_from_account(account, credentials)
                await trader.initialize()
                try:
                    # Get real account state from exchange
                    exchange_state = await trader.get_account_state()

                    # Get agent's open positions to calculate filtered metrics
                    agent_positions = await ps.get_agent_positions(
                        uuid.UUID(agent_id), status_filter="open"
                    )

                    # Build symbol+side set for this agent's positions
                    agent_position_keys = {
                        f"{p.symbol}_{p.side}" for p in agent_positions
                    }

                    # Get exchange positions and filter to this agent's
                    exchange_positions = await trader.get_positions()
                    filtered_positions = [
                        pos for pos in exchange_positions
                        if f"{pos.symbol}_{pos.side}" in agent_position_keys
                    ]

                    # Calculate totals from filtered positions
                    total_unrealized_pnl = sum(
                        pos.unrealized_pnl for pos in filtered_positions
                    )
                    total_margin_used = sum(
                        pos.size_usd / max(pos.leverage, 1)
                        for pos in filtered_positions
                    )

                    # Use real exchange equity
                    return AgentAccountStateResponse(
                        equity=exchange_state.equity,
                        available_balance=exchange_state.available_balance,
                        total_unrealized_pnl=total_unrealized_pnl,
                        total_margin_used=total_margin_used,
                    )
                finally:
                    await trader.close()
        except Exception as e:
            logger.warning(f"Failed to get real account state for agent {agent_id}: {e}")
            # Fall through to virtual calculation on error

    # Mock mode or live mode fallback: calculate virtual account state
    current_prices: Optional[dict[str, float]] = None
    account_equity: Optional[float] = None

    # Get current prices for unrealized P&L calculation (optional for mock)
    if agent.account_id and agent.execution_mode != "mock":
        try:
            from ...db.repositories.account import AccountRepository
            from ...traders.ccxt_trader import create_trader_from_account

            account_repo = AccountRepository(db)
            credentials = await account_repo.get_decrypted_credentials(
                agent.account_id, uuid.UUID(user_id)
            )
            if credentials:
                account = await account_repo.get_by_id(agent.account_id, uuid.UUID(user_id))
                trader = create_trader_from_account(account, credentials)
                await trader.initialize()
                try:
                    state = await trader.get_account_state()
                    account_equity = state.equity

                    # Get current prices for open positions
                    positions = await ps.get_agent_positions(uuid.UUID(agent_id), status_filter="open")
                    if positions:
                        symbols = list({p.symbol for p in positions})
                        tickers = await trader.fetch_tickers(symbols)
                        current_prices = {s: t.get("last") for s, t in tickers.items() if t.get("last")}
                finally:
                    await trader.close()
        except Exception as e:
            logger.warning(f"Failed to get prices for agent {agent_id}: {e}")

    # Get agent account state (virtual calculation)
    state = await ps.get_agent_account_state(
        agent_id=uuid.UUID(agent_id),
        agent=agent,
        current_prices=current_prices,
        account_equity=account_equity,
    )

    # Calculate total margin used
    total_margin_used = sum(
        pos.size_usd / max(pos.leverage, 1)
        for pos in state.positions
    )

    return AgentAccountStateResponse(
        equity=state.equity,
        available_balance=state.available_balance,
        total_unrealized_pnl=state.total_unrealized_pnl,
        total_margin_used=total_margin_used,
    )


@router.post("/{agent_id}/trigger")
async def trigger_agent_execution(
    agent_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Manually trigger an agent execution cycle (Run Now).
    """
    # Get agent and verify ownership
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(
        uuid.UUID(agent_id),
        uuid.UUID(user_id),
        include_strategy=True,
    )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Check if agent is active
    if agent.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot trigger execution for agent in '{agent.status}' status. Agent must be active."
        )

    # Route to appropriate worker based on strategy type
    strategy_type = agent.strategy.type if agent.strategy else None

    if strategy_type == "ai":
        # AI strategy: use ExecutionWorker
        from ...workers.execution_worker import get_worker_manager
        worker_manager = await get_worker_manager()
        result = await worker_manager.trigger_manual_execution(
            str(agent.strategy_id),
            user_id=user_id,
            agent_id=agent_id,
        )
    else:
        # Quant strategy (grid/dca/rsi): use QuantWorker
        from ...workers.quant_worker import get_quant_worker_manager
        worker_manager = await get_quant_worker_manager()

        # Trigger a single cycle execution
        result = await _trigger_quant_cycle(
            worker_manager,
            agent,
            db,
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to trigger execution"),
        )

    return {
        "message": f"Execution triggered for agent {agent_id}",
        "job_id": result.get("job_id"),
        "decision_id": result.get("decision_id"),
        "success": True,
    }


async def _save_quant_decision_record(
    db,
    agent,
    strategy_type: str,
    quant_result: dict,
    symbol: str,
) -> Optional[uuid.UUID]:
    """Save a Quant strategy execution as a decision record.

    This allows Quant strategies (grid/dca/rsi) to appear in the decision list
    alongside AI strategy decisions.
    """
    decision_repo = DecisionRepository(db)

    # Build chain of thought from quant result
    trades_executed = quant_result.get("trades_executed", 0)
    pnl_change = quant_result.get("pnl_change", 0.0)
    message = quant_result.get("message", "")
    success = quant_result.get("success", False)

    # Determine action based on strategy type and execution
    if trades_executed > 0:
        if pnl_change > 0:
            action = "close_long"
            action_desc = "卖出平仓获利"
        else:
            action = "open_long"
            action_desc = "买入开仓"
    else:
        action = "hold"
        action_desc = "持有/观望"

    # Build strategy-specific chain of thought
    strategy_names = {
        "grid": "网格交易策略",
        "dca": "定投策略",
        "rsi": "RSI指标策略",
    }
    strategy_name = strategy_names.get(strategy_type, strategy_type.upper())

    chain_of_thought = f"[{strategy_name}] {message}"
    if trades_executed > 0:
        chain_of_thought += f"\n执行了 {trades_executed} 笔交易"
    if pnl_change != 0:
        chain_of_thought += f"\n盈亏变化: ${pnl_change:.2f}"

    # Build market assessment
    market_assessment = f"交易对: {symbol}\n执行状态: {'成功' if success else '失败'}"

    # Build decisions list (rule-based, so confidence is 100)
    decisions = [{
        "action": action,
        "symbol": symbol,
        "confidence": 100,
        "reasoning": action_desc,
        "size_usd": 0,  # Quant doesn't track per-decision size
    }]

    record = await decision_repo.create(
        agent_id=agent.id,
        system_prompt=f"Quant Strategy: {strategy_name}",
        user_prompt=f"Symbol: {symbol}, Config: {agent.config}",
        raw_response=str(quant_result),
        chain_of_thought=chain_of_thought,
        market_assessment=market_assessment,
        decisions=decisions,
        overall_confidence=100,
        ai_model=f"quant:{strategy_type}",
        tokens_used=0,
        latency_ms=0,
    )

    logger.info(f"Saved quant decision record {record.id} for agent {agent.id}")
    return record.id


async def _trigger_quant_cycle(
    worker_manager,
    agent,
    db,
) -> dict:
    """Trigger a single execution cycle for a quant strategy."""
    from ...services.quant_engine import create_engine
    from ...services.position_service import PositionService
    from ...services.redis_service import get_redis_service
    from ...traders.mock_trader import MockTrader
    from ...traders.ccxt_trader import create_trader_from_account
    from ...db.repositories.account import AccountRepository

    # QuantEngine expects agent_id (not strategy_id)
    # because QuantStrategyDB = AgentDB
    agent_id_str = str(agent.id)

    try:
        # Create trader based on execution mode
        trader = None
        if agent.execution_mode == "mock":
            from ...workers.tasks import create_mock_trader
            symbols = [agent.symbol] if agent.symbol else ["BTC"]
            trader, error = await create_mock_trader(agent, db, symbols=symbols)
            if error:
                return {"success": False, "error": error}
        else:
            # Live mode
            if not agent.account_id:
                return {"success": False, "error": "No account configured for live trading"}

            account_repo = AccountRepository(db)
            account = await account_repo.get_by_id(agent.account_id)
            if not account:
                return {"success": False, "error": "Account not found"}

            credentials = await account_repo.get_decrypted_credentials(
                agent.account_id, agent.user_id,
            )
            if not credentials:
                return {"success": False, "error": "Failed to decrypt credentials"}

            trader = create_trader_from_account(account, credentials)
            await trader.initialize()

        # Create position service
        try:
            redis_service = await get_redis_service()
        except Exception:
            redis_service = None
        position_service = PositionService(db=db, redis=redis_service)

        # Create engine and run one cycle
        strategy_type = agent.strategy_type
        if not strategy_type or strategy_type not in ("grid", "dca", "rsi"):
            return {"success": False, "error": f"Unsupported strategy type: {strategy_type}"}

        engine = create_engine(
            strategy_type=strategy_type,
            agent_id=agent_id_str,  # Note: create_engine expects agent_id here
            trader=trader,
            symbol=agent.symbol,
            config=agent.config or {},
            runtime_state=agent.runtime_state or {},
            account_id=str(agent.account_id) if agent.account_id else None,
            position_service=position_service,
            strategy=agent,
        )

        result = await engine.run_cycle()

        # Save decision record for Quant strategies
        try:
            await _save_quant_decision_record(
                db=db,
                agent=agent,
                strategy_type=strategy_type,
                quant_result=result,
                symbol=agent.symbol,
            )
        except Exception as e:
            logger.warning(f"Failed to save quant decision record: {e}")

        # Update runtime state if changed
        if result.get("updated_state"):
            agent_repo = AgentRepository(db)
            await agent_repo.update(
                agent.id,
                agent.user_id,
                runtime_state=result["updated_state"],
                last_run_at=datetime.now(UTC),
                next_run_at=datetime.now(UTC) + timedelta(minutes=agent.execution_interval_minutes),
            )
            await db.commit()

        # Close trader connection
        if trader:
            try:
                await trader.close()
            except Exception:
                pass

        return {
            "success": True,
            "message": result.get("message", "Cycle completed"),
        }

    except Exception as e:
        logger.exception(f"Failed to trigger quant cycle for agent {agent_id_str}")
        return {"success": False, "error": str(e)}


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Delete an agent. Must be stopped/draft and have no open positions."""
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_by_id(uuid.UUID(agent_id), uuid.UUID(user_id))

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if agent.status not in ("draft", "stopped"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete agent in '{agent.status}' status. Stop it first."
        )

    from ...services.agent_position_service import AgentPositionService
    ps = AgentPositionService(db=db)
    has_positions = await ps.has_open_positions(uuid.UUID(agent_id))
    if has_positions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete agent with open positions. Close all positions first."
        )

    deleted = await agent_repo.delete(uuid.UUID(agent_id), uuid.UUID(user_id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )


# ==================== Helper Functions ====================

def _agent_to_response(agent) -> AgentResponse:
    """Convert agent DB model to response"""
    strategy = getattr(agent, "strategy", None)
    account = getattr(agent, "account", None)

    return AgentResponse(
        id=str(agent.id),
        user_id=str(agent.user_id),
        name=agent.name,
        strategy_id=str(agent.strategy_id),
        strategy_type=strategy.type if strategy else None,
        strategy_name=strategy.name if strategy else None,
        strategy_symbols=strategy.symbols if strategy else [],
        config=strategy.config if strategy else None,
        ai_model=agent.ai_model,
        execution_mode=agent.execution_mode,
        account_id=str(agent.account_id) if agent.account_id else None,
        account_name=account.name if account else None,
        account_exchange=account.exchange if account else None,
        mock_initial_balance=agent.mock_initial_balance,
        allocated_capital=agent.allocated_capital,
        allocated_capital_percent=agent.allocated_capital_percent,
        execution_interval_minutes=agent.execution_interval_minutes,
        auto_execute=agent.auto_execute,
        trade_type=agent.trade_type,
        debate_enabled=agent.debate_enabled,
        debate_models=agent.debate_models or [],
        debate_consensus_mode=agent.debate_consensus_mode or "majority_vote",
        debate_min_participants=agent.debate_min_participants,
        runtime_state=agent.runtime_state,
        status=agent.status,
        error_message=agent.error_message,
        total_pnl=agent.total_pnl,
        total_trades=agent.total_trades,
        winning_trades=agent.winning_trades,
        losing_trades=agent.losing_trades,
        win_rate=agent.win_rate,
        max_drawdown=agent.max_drawdown,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat(),
        last_run_at=agent.last_run_at.isoformat() if agent.last_run_at else None,
        next_run_at=agent.next_run_at.isoformat() if agent.next_run_at else None,
    )
