"""Exchange account routes"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...core.dependencies import CryptoDep, CurrentUserDep, DbSessionDep, RateLimitAccountDep
from ...core.errors import (
    exchange_api_error,
    exchange_connection_error,
    sanitize_error_message,
)
from ...db.repositories.account import AccountRepository
from ...services.redis_service import get_redis_service
from ...traders import BaseTrader, TradeError
from ...traders.ccxt_trader import CCXTTrader, EXCHANGE_ID_MAP, create_trader_from_account
from ...traders.hyperliquid import mnemonic_to_private_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["Exchange Accounts"])


# ==================== Helper Functions ====================


async def _close_strategy_positions(
    *,
    db,
    ps,
    account_repo: "AccountRepository",
    strategy_id: "uuid.UUID",
    account_id: "uuid.UUID",
    user_id: "uuid.UUID",
) -> None:
    """Close all open positions for a strategy and update DB records.

    Shared helper used by account deletion to avoid duplicating the
    close logic for AI and quant strategies.
    """
    open_positions = await ps.get_strategy_positions(strategy_id, "open")
    if not open_positions:
        return

    trader = None
    try:
        credentials = await account_repo.get_decrypted_credentials(
            account_id, user_id
        )
        if not credentials:
            logger.warning(
                f"Cannot close positions for strategy {strategy_id}: "
                "failed to decrypt credentials"
            )
            return
        account = await account_repo.get_by_id(account_id, user_id)
        if not account:
            return

        trader = create_trader_from_account(account, credentials)
        await trader.initialize()
        for pos_record in open_positions:
            try:
                close_result = await trader.close_position(
                    symbol=pos_record.symbol
                )
                if close_result.success:
                    await ps.close_position_record(
                        position_id=pos_record.id,
                        close_price=close_result.filled_price or 0.0,
                    )
            except Exception as close_err:
                logger.error(
                    f"Error closing position {pos_record.symbol}: {close_err}"
                )
    except Exception as e:
        logger.error(
            f"Error closing positions for strategy {strategy_id}: {e}"
        )
    finally:
        if trader:
            try:
                await trader.close()
            except Exception:
                pass


# ==================== Request/Response Models ====================

class AccountCreate(BaseModel):
    """Create exchange account request"""
    name: str = Field(..., min_length=1, max_length=100)
    exchange: str = Field(..., description="Exchange type: hyperliquid, binance, bybit, okx")
    is_testnet: bool = False
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    private_key: Optional[str] = None  # For DEX like Hyperliquid
    mnemonic: Optional[str] = None  # For Hyperliquid - alternative to private_key
    passphrase: Optional[str] = None  # For exchanges that require it


class AccountUpdate(BaseModel):
    """Update exchange account request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_testnet: Optional[bool] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    private_key: Optional[str] = None
    mnemonic: Optional[str] = None  # For Hyperliquid - alternative to private_key
    passphrase: Optional[str] = None


class AccountResponse(BaseModel):
    """Exchange account response (no credentials)"""
    id: str
    name: str
    exchange: str
    is_testnet: bool
    is_connected: bool
    connection_error: Optional[str] = None
    created_at: str

    # Indicate which credential types are set (not the values)
    has_api_key: bool = False
    has_api_secret: bool = False
    has_private_key: bool = False
    has_passphrase: bool = False


# ==================== Routes ====================

@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: AccountCreate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitAccountDep = None,
):
    """
    Create a new exchange account.

    Credentials are encrypted before storage.
    For Hyperliquid, supports both private key and mnemonic phrase import.
    """
    repo = AccountRepository(db)

    # Validate exchange type
    valid_exchanges = {"hyperliquid", "binance", "bybit", "okx"}
    if data.exchange.lower() not in valid_exchanges:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exchange. Must be one of: {', '.join(valid_exchanges)}"
        )

    # For Hyperliquid, convert mnemonic to private key if provided
    private_key = data.private_key
    # Security: Convert mnemonic to private key and discard the mnemonic.
    # We intentionally do NOT persist the original mnemonic because:
    # 1. A mnemonic can derive ALL keys for a wallet – storing it exposes
    #    more than needed for trading (principle of least privilege).
    # 2. The derived private key is sufficient for all exchange operations.
    # 3. Users are expected to keep their own mnemonic backups.
    if data.exchange.lower() == "hyperliquid" and data.mnemonic and not data.private_key:
        try:
            private_key = mnemonic_to_private_key(data.mnemonic)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    # Create account
    account = await repo.create(
        user_id=uuid.UUID(user_id),
        name=data.name,
        exchange=data.exchange,
        is_testnet=data.is_testnet,
        api_key=data.api_key,
        api_secret=data.api_secret,
        private_key=private_key,
        passphrase=data.passphrase,
    )

    return AccountResponse(
        id=str(account.id),
        name=account.name,
        exchange=account.exchange,
        is_testnet=account.is_testnet,
        is_connected=account.is_connected,
        connection_error=account.connection_error,
        created_at=account.created_at.isoformat(),
        has_api_key=account.encrypted_api_key is not None,
        has_api_secret=account.encrypted_api_secret is not None,
        has_private_key=account.encrypted_private_key is not None,
        has_passphrase=account.encrypted_passphrase is not None,
    )


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    exchange: Optional[str] = None,
):
    """
    List all exchange accounts for the current user.

    Optionally filter by exchange type.
    """
    repo = AccountRepository(db)
    accounts = await repo.get_by_user(uuid.UUID(user_id), exchange=exchange)

    return [
        AccountResponse(
            id=str(acc.id),
            name=acc.name,
            exchange=acc.exchange,
            is_testnet=acc.is_testnet,
            is_connected=acc.is_connected,
            connection_error=acc.connection_error,
            created_at=acc.created_at.isoformat(),
            has_api_key=acc.encrypted_api_key is not None,
            has_api_secret=acc.encrypted_api_secret is not None,
            has_private_key=acc.encrypted_private_key is not None,
            has_passphrase=acc.encrypted_passphrase is not None,
        )
        for acc in accounts
    ]


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get a specific exchange account"""
    repo = AccountRepository(db)
    account = await repo.get_by_id(uuid.UUID(account_id), uuid.UUID(user_id))

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return AccountResponse(
        id=str(account.id),
        name=account.name,
        exchange=account.exchange,
        is_testnet=account.is_testnet,
        is_connected=account.is_connected,
        connection_error=account.connection_error,
        created_at=account.created_at.isoformat(),
        has_api_key=account.encrypted_api_key is not None,
        has_api_secret=account.encrypted_api_secret is not None,
        has_private_key=account.encrypted_private_key is not None,
        has_passphrase=account.encrypted_passphrase is not None,
    )


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    data: AccountUpdate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Update an exchange account.

    New credentials will be encrypted before storage.
    For Hyperliquid, supports both private key and mnemonic phrase import.
    """
    repo = AccountRepository(db)

    # Get existing account to check exchange type
    existing_account = await repo.get_by_id(uuid.UUID(account_id), uuid.UUID(user_id))
    if not existing_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    # For Hyperliquid, convert mnemonic to private key if provided.
    # Same as creation: mnemonic is converted and discarded (see create_account comments).
    if existing_account.exchange.lower() == "hyperliquid" and "mnemonic" in update_data:
        mnemonic = update_data.pop("mnemonic")
        if mnemonic and "private_key" not in update_data:
            try:
                update_data["private_key"] = mnemonic_to_private_key(mnemonic)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )

    account = await repo.update(
        uuid.UUID(account_id),
        uuid.UUID(user_id),
        **update_data
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return AccountResponse(
        id=str(account.id),
        name=account.name,
        exchange=account.exchange,
        is_testnet=account.is_testnet,
        is_connected=account.is_connected,
        connection_error=account.connection_error,
        created_at=account.created_at.isoformat(),
        has_api_key=account.encrypted_api_key is not None,
        has_api_secret=account.encrypted_api_secret is not None,
        has_private_key=account.encrypted_private_key is not None,
        has_passphrase=account.encrypted_passphrase is not None,
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Delete an exchange account.

    Automatically stops all active/paused strategies bound to this
    account (both AI and quant), closes their open positions, and
    then deletes the account.  This prevents orphaned active
    strategies that would fail on their next execution cycle.
    """
    account_uuid = uuid.UUID(account_id)
    user_uuid = uuid.UUID(user_id)

    from sqlalchemy import select, and_
    from ...db.models import StrategyDB, QuantStrategyDB
    from ...db.repositories.strategy import StrategyRepository
    from ...db.repositories.quant_strategy import QuantStrategyRepository
    from ...services.position_service import PositionService

    account_repo = AccountRepository(db)
    ps = PositionService(db=db)

    # ── 1. Stop all bound AI strategies ──
    ai_repo = StrategyRepository(db)
    bound_ai_query = select(StrategyDB).where(
        and_(
            StrategyDB.account_id == account_uuid,
            StrategyDB.user_id == user_uuid,
            StrategyDB.status.in_(["active", "paused", "warning"]),
        )
    )
    ai_result = await db.execute(bound_ai_query)
    bound_ai = list(ai_result.scalars().all())

    for strategy in bound_ai:
        logger.info(
            f"Account delete: stopping AI strategy {strategy.id} "
            f"(status={strategy.status})"
        )
        try:
            from ...workers.queue import TaskQueueService
            queue = TaskQueueService()
            await queue.stop_strategy(str(strategy.id))
        except Exception as e:
            logger.warning(f"Failed to stop AI worker for {strategy.id}: {e}")

        await _close_strategy_positions(
            db=db, ps=ps, account_repo=account_repo,
            strategy_id=strategy.id,
            account_id=account_uuid, user_id=user_uuid,
        )
        await ai_repo.update_status(strategy.id, "stopped", "Account deleted")

    # ── 2. Stop all bound quant strategies ──
    quant_repo = QuantStrategyRepository(db)
    bound_quant_query = select(QuantStrategyDB).where(
        and_(
            QuantStrategyDB.account_id == account_uuid,
            QuantStrategyDB.user_id == user_uuid,
            QuantStrategyDB.status.in_(["active", "paused", "warning"]),
        )
    )
    quant_result = await db.execute(bound_quant_query)
    bound_quant = list(quant_result.scalars().all())

    for strategy in bound_quant:
        logger.info(
            f"Account delete: stopping quant strategy {strategy.id} "
            f"(status={strategy.status})"
        )
        try:
            from ...workers.quant_worker import get_quant_worker_manager
            worker_manager = await get_quant_worker_manager()
            await worker_manager.stop_strategy(str(strategy.id))
        except Exception as e:
            logger.warning(f"Failed to stop quant worker for {strategy.id}: {e}")

        await _close_strategy_positions(
            db=db, ps=ps, account_repo=account_repo,
            strategy_id=strategy.id,
            account_id=account_uuid, user_id=user_uuid,
        )
        await quant_repo.update_status(strategy.id, "stopped", "Account deleted")

    # ── 3. Commit strategy status changes before deleting account ──
    await db.flush()

    # ── 4. Delete the account ──
    repo = AccountRepository(db)
    deleted = await repo.delete(account_uuid, user_uuid)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )


@router.post("/{account_id}/test", response_model=dict)
async def test_connection(
    account_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitAccountDep = None,
):
    """
    Test connection to the exchange.

    Attempts to authenticate with stored credentials and
    updates the connection status.
    """
    repo = AccountRepository(db)

    # Get account with credentials
    account = await repo.get_by_id(uuid.UUID(account_id), uuid.UUID(user_id))
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Get decrypted credentials
    credentials = await repo.get_decrypted_credentials(
        uuid.UUID(account_id),
        uuid.UUID(user_id)
    )

    trader = None
    try:
        # Create trader instance
        trader = create_trader_from_account(account, credentials)

        # Initialize and test connection
        await trader.initialize()

        # Try to get account state to verify connection works
        await trader.get_account_state()

        # Update connection status - success
        await repo.update_connection_status(
            uuid.UUID(account_id),
            is_connected=True,
            error=None
        )

        return {
            "success": True,
            "message": f"Successfully connected to {account.exchange}",
        }

    except ValueError as e:
        # Missing credentials or unsupported exchange
        error_message = str(e)
        await repo.update_connection_status(
            uuid.UUID(account_id),
            is_connected=False,
            error=error_message
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message  # ValueError messages are safe to expose
        )

    except TradeError as e:
        # Exchange-specific error - log and sanitize
        error_code = getattr(e, 'code', None)
        error_message = getattr(e, 'message', str(e))
        
        logger.warning(
            f"Exchange error testing connection for account {account_id}: "
            f"code={error_code}, message={error_message}"
        )
        
        await repo.update_connection_status(
            uuid.UUID(account_id),
            is_connected=False,
            error=error_message
        )
        
        # exchange_api_error will handle the specific error code and provide appropriate message
        raise exchange_api_error(e, operation="connection test")

    except Exception as e:
        # General error - log and sanitize
        logger.error(f"Unexpected error testing connection for account {account_id}: {e}", exc_info=True)
        await repo.update_connection_status(
            uuid.UUID(account_id),
            is_connected=False,
            error=sanitize_error_message(e, "Connection test failed")
        )
        raise exchange_connection_error(e, exchange=account.exchange)

    finally:
        # Clean up trader connection
        if trader:
            try:
                await trader.close()
            except Exception:
                logger.debug(f"Error closing trader connection for account {account_id}")


# ==================== Balance & Position Endpoints ====================

class PositionResponse(BaseModel):
    """Position response"""
    symbol: str
    side: str  # 'long' or 'short'
    size: float
    size_usd: float
    entry_price: float
    mark_price: float
    leverage: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    liquidation_price: Optional[float] = None


class AccountBalanceResponse(BaseModel):
    """Account balance response"""
    account_id: str
    equity: float
    available_balance: float
    total_margin_used: float
    unrealized_pnl: float
    positions: list[PositionResponse]


@router.get("/{account_id}/balance", response_model=AccountBalanceResponse)
async def get_account_balance(
    account_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    crypto: CryptoDep,
    bypass_cache: bool = False,
):
    """
    Get account balance and positions from the exchange.

    Fetches real-time data from the exchange API.
    Results are cached for 10 seconds; pass bypass_cache=true to force a fresh fetch.
    """
    repo = AccountRepository(db)

    # Verify account ownership
    account = await repo.get_by_id(uuid.UUID(account_id), uuid.UUID(user_id))
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Try cache first (unless bypassed)
    if not bypass_cache:
        try:
            redis = await get_redis_service()
            cached = await redis.get_cached_account_balance(account_id)
            if cached:
                logger.debug(f"Returning cached balance for account {account_id}")
                return AccountBalanceResponse(**cached)
        except Exception as e:
            logger.debug(f"Cache lookup failed for account {account_id}: {e}")

    # Get decrypted credentials
    credentials = await repo.get_decrypted_credentials(
        uuid.UUID(account_id),
        uuid.UUID(user_id)
    )

    trader = None
    try:
        # Create trader instance
        trader = create_trader_from_account(account, credentials)

        # Initialize connection
        await trader.initialize()

        # Get account state from exchange
        account_state = await trader.get_account_state()

        # Convert positions to response format
        positions = [
            PositionResponse(
                symbol=pos.symbol,
                side=pos.side,
                size=pos.size,
                size_usd=pos.size_usd,
                entry_price=pos.entry_price,
                mark_price=pos.mark_price,
                leverage=float(pos.leverage),
                unrealized_pnl=pos.unrealized_pnl,
                unrealized_pnl_percent=pos.unrealized_pnl_percent,
                liquidation_price=pos.liquidation_price,
            )
            for pos in account_state.positions
        ]

        # Update connection status to connected
        await repo.update_connection_status(
            uuid.UUID(account_id),
            is_connected=True,
            error=None
        )

        response = AccountBalanceResponse(
            account_id=account_id,
            equity=account_state.equity,
            available_balance=account_state.available_balance,
            total_margin_used=account_state.total_margin_used,
            unrealized_pnl=account_state.unrealized_pnl,
            positions=positions,
        )

        # Cache the response
        try:
            redis = await get_redis_service()
            await redis.cache_account_balance(
                account_id,
                response.model_dump(),
                ttl=10,  # 10 seconds
            )
        except Exception as e:
            logger.debug(f"Failed to cache balance for account {account_id}: {e}")

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)  # ValueError messages are safe to expose
        )

    except TradeError as e:
        # Update connection status on error
        logger.warning(f"Exchange error fetching balance for account {account_id}: {e.message}")
        await repo.update_connection_status(
            uuid.UUID(account_id),
            is_connected=False,
            error=str(e.message)
        )
        raise exchange_api_error(e, operation="fetch balance")

    except Exception as e:
        # Update connection status on error
        logger.error(f"Unexpected error fetching balance for account {account_id}: {e}", exc_info=True)
        await repo.update_connection_status(
            uuid.UUID(account_id),
            is_connected=False,
            error=sanitize_error_message(e, "Balance fetch failed")
        )
        raise exchange_connection_error(e, exchange=account.exchange)

    finally:
        # Clean up trader connection
        if trader:
            try:
                await trader.close()
            except Exception:
                logger.debug(f"Error closing trader connection for account {account_id}")


@router.get("/{account_id}/positions", response_model=list[PositionResponse])
async def get_account_positions(
    account_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    crypto: CryptoDep,
):
    """
    Get open positions for an account.

    Fetches real-time position data from the exchange.
    """
    repo = AccountRepository(db)

    # Verify account ownership
    account = await repo.get_by_id(uuid.UUID(account_id), uuid.UUID(user_id))
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Get decrypted credentials
    credentials = await repo.get_decrypted_credentials(
        uuid.UUID(account_id),
        uuid.UUID(user_id)
    )

    trader = None
    try:
        # Create trader instance
        trader = create_trader_from_account(account, credentials)

        # Initialize connection
        await trader.initialize()

        # Get positions from exchange
        positions = await trader.get_positions()

        # Convert to response format
        return [
            PositionResponse(
                symbol=pos.symbol,
                side=pos.side,
                size=pos.size,
                size_usd=pos.size_usd,
                entry_price=pos.entry_price,
                mark_price=pos.mark_price,
                leverage=float(pos.leverage),
                unrealized_pnl=pos.unrealized_pnl,
                unrealized_pnl_percent=pos.unrealized_pnl_percent,
                liquidation_price=pos.liquidation_price,
            )
            for pos in positions
        ]

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)  # ValueError messages are safe to expose
        )

    except TradeError as e:
        logger.warning(f"Exchange error fetching positions for account {account_id}: {e.message}")
        raise exchange_api_error(e, operation="fetch positions")

    except Exception as e:
        logger.error(f"Unexpected error fetching positions for account {account_id}: {e}", exc_info=True)
        raise exchange_connection_error(e, exchange=account.exchange)

    finally:
        # Clean up trader connection
        if trader:
            try:
                await trader.close()
            except Exception:
                logger.debug(f"Error closing trader connection for account {account_id}")
