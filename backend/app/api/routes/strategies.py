"""Strategy routes"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from ...core.dependencies import CryptoDep, CurrentUserDep, DbSessionDep, RateLimitApiDep, RateLimitStrategyDep
from ...db.repositories.account import AccountRepository
from ...db.repositories.strategy import StrategyRepository
from ...models.strategy import StrategyConfig, TradingMode, PromptSections
from ...models.decision import RiskControls
from ...services.prompt_builder import PromptBuilder
from ...workers.execution_worker import get_worker_manager

router = APIRouter(prefix="/strategies", tags=["Strategies"])
logger = logging.getLogger(__name__)


# ==================== Request/Response Models ====================

class StrategyCreate(BaseModel):
    """Create strategy request"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    prompt: str = Field(..., min_length=10)
    trading_mode: TradingMode = Field(default=TradingMode.CONSERVATIVE)
    config: Optional[dict] = None
    account_id: Optional[str] = None
    ai_model: str = Field(
        ...,
        min_length=1,
        description="AI model in format 'provider:model_id', e.g. 'deepseek:deepseek-chat'."
    )
    # Capital allocation (pick one)
    allocated_capital: Optional[float] = Field(
        default=None, ge=0, description="Fixed capital in USD (e.g. 5000)"
    )
    allocated_capital_percent: Optional[float] = Field(
        default=None, ge=0, le=1.0,
        description="Capital as fraction of equity (e.g. 0.3 = 30%)"
    )

    @model_validator(mode="after")
    def validate_capital_allocation(self):
        if self.allocated_capital is not None and self.allocated_capital_percent is not None:
            raise ValueError(
                "Cannot set both allocated_capital and allocated_capital_percent. "
                "Choose one allocation mode."
            )
        return self


class StrategyUpdate(BaseModel):
    """Update strategy request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    prompt: Optional[str] = Field(None, min_length=10)
    trading_mode: Optional[TradingMode] = None
    config: Optional[dict] = None
    account_id: Optional[str] = None
    ai_model: Optional[str] = Field(
        default=None,
        description="AI model in format 'provider:model_id'. Cannot be set to empty string."
    )
    allocated_capital: Optional[float] = Field(default=None, ge=0)
    allocated_capital_percent: Optional[float] = Field(default=None, ge=0, le=1.0)

    @model_validator(mode="after")
    def validate_capital_allocation(self):
        # Only validate mutual exclusivity if both are explicitly provided
        if self.allocated_capital is not None and self.allocated_capital_percent is not None:
            raise ValueError(
                "Cannot set both allocated_capital and allocated_capital_percent. "
                "Choose one allocation mode."
            )
        return self


class StrategyResponse(BaseModel):
    """Strategy response"""
    id: str
    name: str
    description: str
    prompt: str
    trading_mode: str
    config: dict
    status: str
    error_message: Optional[str] = None
    account_id: Optional[str] = None
    ai_model: Optional[str] = None  # AI model used by this strategy

    # Capital allocation
    allocated_capital: Optional[float] = None
    allocated_capital_percent: Optional[float] = None

    # Performance
    total_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float

    # Timestamps
    created_at: str
    updated_at: str
    last_run_at: Optional[str] = None


class StrategyStatusUpdate(BaseModel):
    """Update strategy status"""
    status: str = Field(..., description="New status: active, paused, stopped")
    # When stopping: what to do with open positions
    close_positions: bool = Field(
        default=False,
        description="If True, close all open positions when stopping"
    )


class PromptPreviewRequest(BaseModel):
    """Request for previewing generated prompt"""
    prompt: str = Field(default="", description="User's custom strategy prompt (deprecated in simple mode)")
    trading_mode: TradingMode = Field(default=TradingMode.CONSERVATIVE)
    symbols: list[str] = Field(default=["BTC", "ETH"])
    timeframes: list[str] = Field(default=["15m", "1h", "4h"])
    language: str = Field(default="en", description="Prompt language: 'en' or 'zh'")
    prompt_mode: str = Field(default="simple", description="Prompt editing mode: 'simple' or 'advanced'")
    advanced_prompt: str = Field(default="", description="Full custom prompt content for advanced mode")
    indicators: Optional[dict] = Field(
        default=None,
        description="Technical indicator settings"
    )
    risk_controls: Optional[dict] = Field(
        default=None,
        description="Risk control parameters"
    )
    prompt_sections: Optional[dict] = Field(
        default=None,
        description="Custom prompt sections (role_definition, entry_standards, etc.)"
    )


class PromptPreviewResponse(BaseModel):
    """Response with generated prompt preview"""
    system_prompt: str
    estimated_tokens: int
    sections: dict = Field(
        default_factory=dict,
        description="Individual prompt sections for display"
    )


# ==================== Routes ====================

@router.post("/preview-prompt", response_model=PromptPreviewResponse)
async def preview_prompt(
    data: PromptPreviewRequest,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Preview the generated system prompt based on configuration.

    This endpoint allows users to see how their strategy configuration
    will be translated into AI prompts without saving to database.
    Useful for the Strategy Studio preview feature.
    """
    # Build indicator config (dict format)
    indicators = {
        "ema_periods": data.indicators.get("ema_periods", [9, 21, 55]) if data.indicators else [9, 21, 55],
        "rsi_period": data.indicators.get("rsi_period", 14) if data.indicators else 14,
        "macd_fast": data.indicators.get("macd_fast", 12) if data.indicators else 12,
        "macd_slow": data.indicators.get("macd_slow", 26) if data.indicators else 26,
        "macd_signal": data.indicators.get("macd_signal", 9) if data.indicators else 9,
        "atr_period": data.indicators.get("atr_period", 14) if data.indicators else 14,
    }

    # Build risk controls
    risk_controls = RiskControls(
        max_leverage=data.risk_controls.get("max_leverage", 5) if data.risk_controls else 5,
        max_position_ratio=data.risk_controls.get("max_position_ratio", 0.2) if data.risk_controls else 0.2,
        max_total_exposure=data.risk_controls.get("max_total_exposure", 0.8) if data.risk_controls else 0.8,
        min_risk_reward_ratio=data.risk_controls.get("min_risk_reward_ratio", 2.0) if data.risk_controls else 2.0,
        max_drawdown_percent=data.risk_controls.get("max_drawdown_percent", 0.1) if data.risk_controls else 0.1,
        min_confidence=data.risk_controls.get("min_confidence", 60) if data.risk_controls else 60,
    )

    # Build prompt sections
    prompt_sections = PromptSections(
        role_definition=data.prompt_sections.get("role_definition", "") if data.prompt_sections else "",
        trading_frequency=data.prompt_sections.get("trading_frequency", "") if data.prompt_sections else "",
        entry_standards=data.prompt_sections.get("entry_standards", "") if data.prompt_sections else "",
        decision_process=data.prompt_sections.get("decision_process", "") if data.prompt_sections else "",
    )

    # Create strategy config
    config = StrategyConfig(
        language=data.language,
        symbols=data.symbols,
        indicators=indicators,
        timeframes=data.timeframes,
        risk_controls=risk_controls,
        prompt_mode=data.prompt_mode or "simple",
        prompt_sections=prompt_sections,
        custom_prompt=data.prompt,
        advanced_prompt=data.advanced_prompt or "",
        execution_interval_minutes=30,
        auto_execute=True,
    )

    # Build prompt
    builder = PromptBuilder(
        config=config,
        trading_mode=data.trading_mode,
        custom_prompt=data.prompt,
    )

    system_prompt = builder.build_system_prompt()

    # Estimate tokens (rough estimation: ~4 chars per token)
    estimated_tokens = len(system_prompt) // 4

    # Return sections breakdown for UI display (using localized defaults)
    from ...services.prompt_templates import get_system_templates
    sys_t = get_system_templates(data.language)

    mode_key = data.trading_mode.value
    sections = {
        "role_definition": prompt_sections.role_definition or sys_t["default_role"],
        "trading_mode": sys_t["trading_mode"].get(mode_key, ""),
        "trading_frequency": prompt_sections.trading_frequency or sys_t["default_trading_frequency"],
        "entry_standards": prompt_sections.entry_standards or sys_t["default_entry_standards"],
        "decision_process": prompt_sections.decision_process or sys_t["default_decision_process"],
        "custom_prompt": data.prompt,
    }

    return PromptPreviewResponse(
        system_prompt=system_prompt,
        estimated_tokens=estimated_tokens,
        sections=sections,
    )


class DebateValidationRequest(BaseModel):
    """Request to validate debate model configuration"""
    model_ids: list[str] = Field(..., min_length=2, max_length=5)


class DebateModelValidation(BaseModel):
    """Validation result for a single model"""
    model_id: str
    valid: bool
    error: Optional[str] = None


class DebateValidationResponse(BaseModel):
    """Response with debate model validation results"""
    valid: bool
    models: list[DebateModelValidation]
    message: str


@router.post("/validate-debate-models", response_model=DebateValidationResponse)
async def validate_debate_models(
    data: DebateValidationRequest,
    user_id: CurrentUserDep,
    db: DbSessionDep,
    crypto: CryptoDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Validate debate model configuration.

    Checks if all specified models are accessible and properly configured.
    Useful for validating debate setup before saving strategy.
    """
    from ...services.ai import resolve_provider_credentials
    from ...services.debate_engine import validate_debate_models as validate_models

    async def cred_resolver(model_id: str):
        return await resolve_provider_credentials(db, crypto, uuid.UUID(user_id), model_id)

    validation_results = await validate_models(data.model_ids, credentials_resolver=cred_resolver)

    models = [
        DebateModelValidation(
            model_id=model_id,
            valid=result["valid"],
            error=result.get("error"),
        )
        for model_id, result in validation_results.items()
    ]

    all_valid = all(m.valid for m in models)
    valid_count = sum(1 for m in models if m.valid)

    if all_valid:
        message = f"All {len(models)} models are valid and accessible"
    elif valid_count >= 2:
        message = f"{valid_count}/{len(models)} models are valid (minimum 2 required)"
    else:
        message = f"Only {valid_count} model(s) valid. At least 2 models required for debate."

    return DebateValidationResponse(
        valid=valid_count >= 2,
        models=models,
        message=message,
    )


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    data: StrategyCreate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Create a new trading strategy.

    The strategy starts in 'draft' status.
    """
    repo = StrategyRepository(db)

    # Validate account ownership
    account_uuid = None
    if data.account_id:
        account_repo = AccountRepository(db)
        account = await account_repo.get_by_id(uuid.UUID(data.account_id))
        if not account or str(account.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found or does not belong to you."
            )
        account_uuid = uuid.UUID(data.account_id)

    strategy = await repo.create(
        user_id=uuid.UUID(user_id),
        name=data.name,
        description=data.description,
        prompt=data.prompt,
        trading_mode=data.trading_mode.value,
        config=data.config,
        account_id=account_uuid,
        ai_model=data.ai_model,
        allocated_capital=data.allocated_capital,
        allocated_capital_percent=data.allocated_capital_percent,
    )

    return _strategy_to_response(strategy)


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List all strategies for the current user.

    Optionally filter by status.
    """
    repo = StrategyRepository(db)
    strategies = await repo.get_by_user(
        uuid.UUID(user_id),
        status=status,
        limit=limit,
        offset=offset,
    )

    return [_strategy_to_response(s) for s in strategies]


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get a specific strategy"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    return _strategy_to_response(strategy)


@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    data: StrategyUpdate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Update a strategy"""
    repo = StrategyRepository(db)

    update_data = data.model_dump(exclude_unset=True)

    # ai_model must not be set to empty string
    if "ai_model" in update_data and not update_data["ai_model"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ai_model cannot be empty. Select an AI model for this strategy."
        )

    from ...services.position_service import PositionService
    ps = PositionService(db=db)

    # Protect account_id change when positions are open + validate ownership
    if "account_id" in update_data and update_data["account_id"]:
        has_positions = await ps.has_open_positions(uuid.UUID(strategy_id))
        if has_positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change account while strategy has open positions. "
                       "Close all positions first."
            )
        # Validate account belongs to current user
        account_repo = AccountRepository(db)
        account = await account_repo.get_by_id(uuid.UUID(update_data["account_id"]))
        if not account or str(account.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found or does not belong to you."
            )
        update_data["account_id"] = uuid.UUID(update_data["account_id"])

    # Protect capital allocation changes when positions are open
    capital_fields_changed = (
        "allocated_capital" in update_data or "allocated_capital_percent" in update_data
    )
    if capital_fields_changed:
        has_positions = await ps.has_open_positions(uuid.UUID(strategy_id))
        if has_positions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change capital allocation while strategy has open positions. "
                       "Close all positions first."
            )

    # Convert trading_mode enum to string
    if "trading_mode" in update_data and update_data["trading_mode"]:
        update_data["trading_mode"] = update_data["trading_mode"].value

    strategy = await repo.update(
        uuid.UUID(strategy_id),
        uuid.UUID(user_id),
        **update_data
    )

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    return _strategy_to_response(strategy)


@router.post("/{strategy_id}/status", response_model=StrategyResponse)
async def update_strategy_status(
    strategy_id: str,
    data: StrategyStatusUpdate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitStrategyDep = None,
):
    """
    Update strategy status.

    Valid transitions:
    - draft -> active (start)
    - active -> paused (pause)
    - paused -> active (resume)
    - active/paused -> stopped (stop)
    """
    valid_statuses = {"active", "paused", "stopped"}
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    repo = StrategyRepository(db)

    # Get current strategy
    strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
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
        # Warning state: strategy is running but has issues (e.g. capital
        # over-allocation, repeated partial failures). Can resume, pause, or stop.
        ("warning", "active"),
        ("warning", "paused"),
        ("warning", "stopped"),
    }

    if (current, new) not in valid_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{current}' to '{new}'"
        )

    # Check if account is set for activation
    if new == "active" and not strategy.account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate strategy without an exchange account"
        )

    # When recovering from error state, verify exchange connection
    if new == "active" and current == "error":
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

    # Sync with worker manager
    try:
        worker_manager = await get_worker_manager()
        if new == "active":
            # Start worker for this strategy
            success = await worker_manager.start_strategy(strategy_id)
            if not success:
                logger.warning(f"Failed to start worker for strategy {strategy_id}")
        elif new in ("paused", "stopped"):
            # Stop worker for this strategy
            await worker_manager.stop_strategy(strategy_id)
    except Exception as e:
        logger.error(f"Error syncing worker for strategy {strategy_id}: {e}")

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
                account = strategy.account
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
                                        f"for stopped strategy {strategy_id}"
                                    )
                                else:
                                    logger.warning(
                                        f"Failed to close {pos_record.symbol} "
                                        f"for strategy {strategy_id}: {result.error}"
                                    )
                            except Exception as close_err:
                                logger.error(
                                    f"Error closing position {pos_record.symbol}: {close_err}"
                                )
                    finally:
                        await trader.close()
                    await db.commit()
        except Exception as e:
            logger.error(f"Error closing positions for strategy {strategy_id}: {e}")

    # Refresh strategy
    strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
    return _strategy_to_response(strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Delete a strategy. Must be stopped/draft and have no open positions."""
    repo = StrategyRepository(db)

    # Validate strategy exists and check status
    strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )

    if strategy.status not in ("draft", "stopped"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete strategy in '{strategy.status}' status. "
                   "Stop the strategy first."
        )

    # Check for open positions
    from ...services.position_service import PositionService
    ps = PositionService(db=db)
    has_positions = await ps.has_open_positions(uuid.UUID(strategy_id))
    if has_positions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete strategy with open positions. "
                   "Close all positions first."
        )

    deleted = await repo.delete(uuid.UUID(strategy_id), uuid.UUID(user_id))

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )


# ==================== Helper Functions ====================

def _strategy_to_response(strategy) -> StrategyResponse:
    """Convert strategy DB model to response"""
    return StrategyResponse(
        id=str(strategy.id),
        name=strategy.name,
        description=strategy.description,
        prompt=strategy.prompt,
        trading_mode=strategy.trading_mode,
        config=strategy.config,
        status=strategy.status,
        error_message=strategy.error_message,
        account_id=str(strategy.account_id) if strategy.account_id else None,
        ai_model=strategy.ai_model,
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
