"""
Unified strategy routes.

Handles all strategy types (AI, Grid, DCA, RSI) through a single
set of endpoints. Strategy is a pure logic template - no runtime
bindings (account, model, status, performance live on Agent).
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from ...core.dependencies import (
    CryptoDep,
    CurrentUserDep,
    DbSessionDep,
    RateLimitApiDep,
)
from ...db.repositories.strategy import StrategyRepository
from ...models.strategy import (
    AIStrategyConfig,
    STRATEGY_CONFIG_MODELS,
    StrategyCreate,
    StrategyUpdate,
    PromptSections,
    TradingMode,
)
from ...models.decision import RiskControls
from ...services.prompt_builder import PromptBuilder

router = APIRouter(prefix="/strategies", tags=["Strategies"])
logger = logging.getLogger(__name__)


# ==================== Response Models ====================


class StrategyResponse(BaseModel):
    """Unified strategy response"""

    id: str
    user_id: str
    type: str  # ai, grid, dca, rsi
    name: str
    description: str
    symbols: list[str]
    config: dict

    # Marketplace
    visibility: str
    category: Optional[str] = None
    tags: list[str] = []
    forked_from: Optional[str] = None
    fork_count: int = 0
    author_name: Optional[str] = None

    # Statistics
    agent_count: int = 0

    # Pricing
    is_paid: bool = False
    price_monthly: Optional[float] = None
    pricing_model: str = "free"

    # Timestamps
    created_at: str
    updated_at: str


class MarketplaceResponse(BaseModel):
    """Paginated marketplace response"""

    items: list[StrategyResponse]
    total: int
    limit: int
    offset: int


# ==================== Routes ====================


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    data: StrategyCreate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Create a new trading strategy.

    Strategy is a pure logic template. To execute it, create an Agent
    that binds this strategy to a model and account.
    """
    repo = StrategyRepository(db)

    strategy = await repo.create(
        user_id=uuid.UUID(user_id),
        type=data.type.value,
        name=data.name,
        description=data.description,
        symbols=[s.upper() for s in data.symbols],
        config=data.config,
        visibility=data.visibility.value,
        category=data.category,
        tags=data.tags,
        is_paid=data.is_paid,
        price_monthly=data.price_monthly,
        pricing_model=data.pricing_model.value,
    )

    return _strategy_to_response(strategy)


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List all strategies for the current user.

    Optionally filter by type (ai, grid, dca, rsi).
    """
    repo = StrategyRepository(db)
    strategies = await repo.get_by_user(
        uuid.UUID(user_id),
        type_filter=type,
        limit=limit,
        offset=offset,
    )

    return [_strategy_to_response(s) for s in strategies]


@router.get("/marketplace", response_model=MarketplaceResponse)
async def browse_marketplace(
    db: DbSessionDep,
    user_id: CurrentUserDep,
    type: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "fork_count",
    limit: int = 50,
    offset: int = 0,
):
    """
    Browse public strategies in the marketplace.

    Filter by type, category, or search text.
    Sort by fork_count (popular), newest, or updated.
    """
    repo = StrategyRepository(db)
    strategies, total = await repo.get_public(
        type_filter=type,
        category=category,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )

    return MarketplaceResponse(
        items=[_strategy_to_response(s) for s in strategies],
        total=total,
        limit=limit,
        offset=offset,
    )


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
        )

    return _strategy_to_response(strategy)


@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    data: StrategyUpdate,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Update a strategy's logic (name, config, symbols, etc.)"""
    from ...services.name_check_service import NameCheckService
    from ...db.repositories.agent import AgentRepository

    repo = StrategyRepository(db)

    update_data = data.model_dump(exclude_unset=True)

    # Strategy config fields that require active agent check
    STRATEGY_CONFIG_FIELDS = {"name", "description", "symbols", "config"}
    has_config_changes = any(
        field in update_data and update_data[field] is not None
        for field in STRATEGY_CONFIG_FIELDS
    )

    # Check for active agents before modifying strategy config
    if has_config_changes:
        agent_repo = AgentRepository(db)
        active_agents = await agent_repo.get_active_agents_by_strategy(
            uuid.UUID(strategy_id)
        )

        if active_agents:
            agent_names = [a.name for a in active_agents[:3]]
            agent_count = len(active_agents)

            if agent_count == 1:
                detail = (
                    f"Cannot modify strategy config: "
                    f"Agent '{agent_names[0]}' is active. "
                    f"Pause the agent first."
                )
            else:
                detail = (
                    f"Cannot modify strategy config: "
                    f"{agent_count} agents are active "
                    f"({', '.join(agent_names)}"
                    f"{', ...' if agent_count > 3 else ''}). "
                    f"Pause all agents first."
                )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            )

    # Normalize symbols
    if "symbols" in update_data and update_data["symbols"]:
        update_data["symbols"] = [s.upper() for s in update_data["symbols"]]

    # Convert enums to strings
    if "visibility" in update_data and update_data["visibility"]:
        new_visibility = update_data["visibility"].value
        update_data["visibility"] = new_visibility

        # Check marketplace name conflict when publishing to public
        if new_visibility == "public":
            strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
            if strategy:
                name_check = NameCheckService(db)
                if await name_check.market_name_exists(
                    strategy.name,
                    exclude_strategy_id=uuid.UUID(strategy_id),
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Strategy name already exists in the marketplace. "
                        "Please rename your strategy before publishing.",
                    )

    # Validate config if being updated
    if "config" in update_data and update_data["config"]:
        strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
        if strategy:
            config_model = STRATEGY_CONFIG_MODELS.get(strategy.type)
            if config_model:
                try:
                    config_model(**update_data["config"])
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid config for {strategy.type} strategy: {e}",
                    )

    strategy = await repo.update(
        uuid.UUID(strategy_id), uuid.UUID(user_id), **update_data
    )

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
        )

    return _strategy_to_response(strategy)


@router.post("/{strategy_id}/fork", response_model=StrategyResponse)
async def fork_strategy(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    name: Optional[str] = None,
):
    """
    Fork a public strategy from the marketplace.

    Creates a private copy under the current user's account.
    Records forked_from relationship for marketplace tracking.
    """
    repo = StrategyRepository(db)
    forked = await repo.fork(
        source_id=uuid.UUID(strategy_id),
        user_id=uuid.UUID(user_id),
        name_override=name,
    )

    if not forked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found or not public",
        )

    return _strategy_to_response(forked)


@router.post("/{strategy_id}/duplicate", response_model=StrategyResponse)
async def duplicate_strategy(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    name: Optional[str] = None,
):
    """
    Duplicate a user's own strategy.

    Creates an independent copy without marketplace fork tracking.
    Default name format: "{original_name} (副本)".
    Useful when you want to modify a strategy while keeping the original.
    """
    repo = StrategyRepository(db)
    duplicated = await repo.duplicate(
        source_id=uuid.UUID(strategy_id),
        user_id=uuid.UUID(user_id),
        name_override=name,
    )

    if not duplicated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
        )

    return _strategy_to_response(duplicated)


# ==================== Subscription Endpoints ====================


class SubscriptionResponse(BaseModel):
    """Subscription status response"""

    strategy_id: str
    subscribed: bool
    status: Optional[str] = None
    expires_at: Optional[str] = None


@router.get("/{strategy_id}/subscription", response_model=SubscriptionResponse)
async def get_subscription_status(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Check if the current user has an active subscription to a strategy."""
    from ...db.models import StrategySubscriptionDB

    query = select(StrategySubscriptionDB).where(
        StrategySubscriptionDB.strategy_id == uuid.UUID(strategy_id),
        StrategySubscriptionDB.user_id == uuid.UUID(user_id),
        StrategySubscriptionDB.status == "active",
    )
    result = await db.execute(query)
    sub = result.scalar_one_or_none()

    return SubscriptionResponse(
        strategy_id=strategy_id,
        subscribed=sub is not None,
        status=sub.status if sub else None,
        expires_at=sub.expires_at.isoformat() if sub and sub.expires_at else None,
    )


@router.post("/{strategy_id}/subscribe", response_model=SubscriptionResponse)
async def subscribe_to_strategy(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Subscribe to a paid strategy.

    For free strategies, this is a no-op (fork instead).
    For paid strategies, creates a subscription record.
    """
    from ...db.models import StrategySubscriptionDB
    from datetime import timedelta

    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(uuid.UUID(strategy_id))

    if not strategy or strategy.visibility != "public":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found or not public",
        )

    if not strategy.is_paid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is free. Use fork instead.",
        )

    # Check for existing active subscription
    existing_query = select(StrategySubscriptionDB).where(
        StrategySubscriptionDB.strategy_id == uuid.UUID(strategy_id),
        StrategySubscriptionDB.user_id == uuid.UUID(user_id),
        StrategySubscriptionDB.status == "active",
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        return SubscriptionResponse(
            strategy_id=strategy_id,
            subscribed=True,
            status=existing.status,
            expires_at=existing.expires_at.isoformat() if existing.expires_at else None,
        )

    # Create subscription
    from datetime import datetime, UTC

    now = datetime.now(UTC)
    expires_at = None
    if strategy.pricing_model == "monthly":
        expires_at = now + timedelta(days=30)

    sub = StrategySubscriptionDB(
        strategy_id=uuid.UUID(strategy_id),
        user_id=uuid.UUID(user_id),
        status="active",
        price_paid=strategy.price_monthly or 0.0,
        pricing_model=strategy.pricing_model,
        started_at=now,
        expires_at=expires_at,
    )
    db.add(sub)
    await db.flush()

    return SubscriptionResponse(
        strategy_id=strategy_id,
        subscribed=True,
        status="active",
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Delete a strategy.

    Will fail if any agents reference this strategy.
    Stop and delete all agents first.
    """
    repo = StrategyRepository(db)

    strategy = await repo.get_by_id(uuid.UUID(strategy_id), uuid.UUID(user_id))
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
        )

    # Check if any agents reference this strategy
    from ...db.repositories.agent import AgentRepository

    agent_repo = AgentRepository(db)
    agents = await agent_repo.get_by_user(uuid.UUID(user_id))
    refs = [a for a in agents if str(a.strategy_id) == strategy_id]
    if refs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete strategy: {len(refs)} agent(s) reference it. "
            "Delete all agents first.",
        )

    deleted = await repo.delete(uuid.UUID(strategy_id), uuid.UUID(user_id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
        )


# ==================== Version Management Endpoints ====================


class StrategyVersionResponse(BaseModel):
    """Strategy version snapshot response"""

    id: str
    strategy_id: str
    version: int
    name: str
    description: str
    symbols: list[str]
    config: dict
    change_note: str
    created_at: str


@router.get("/{strategy_id}/versions", response_model=list[StrategyVersionResponse])
async def list_versions(
    strategy_id: str,
    db: DbSessionDep,
    user_id: CurrentUserDep,
    limit: int = 50,
    offset: int = 0,
):
    """
    List version history for a strategy.

    Returns snapshots of previous configurations in reverse chronological order.
    """
    repo = StrategyRepository(db)
    versions = await repo.get_versions(
        uuid.UUID(strategy_id),
        uuid.UUID(user_id),
        limit=limit,
        offset=offset,
    )

    return [
        StrategyVersionResponse(
            id=str(v.id),
            strategy_id=str(v.strategy_id),
            version=v.version,
            name=v.name,
            description=v.description or "",
            symbols=v.symbols or [],
            config=v.config or {},
            change_note=v.change_note or "",
            created_at=v.created_at.isoformat(),
        )
        for v in versions
    ]


@router.get("/{strategy_id}/versions/{version}", response_model=StrategyVersionResponse)
async def get_version(
    strategy_id: str,
    version: int,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Get a specific version snapshot."""
    repo = StrategyRepository(db)
    v = await repo.get_version(
        uuid.UUID(strategy_id),
        version,
        uuid.UUID(user_id),
    )

    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
        )

    return StrategyVersionResponse(
        id=str(v.id),
        strategy_id=str(v.strategy_id),
        version=v.version,
        name=v.name,
        description=v.description or "",
        symbols=v.symbols or [],
        config=v.config or {},
        change_note=v.change_note or "",
        created_at=v.created_at.isoformat(),
    )


@router.post(
    "/{strategy_id}/versions/{version}/restore", response_model=StrategyResponse
)
async def restore_version(
    strategy_id: str,
    version: int,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Restore a strategy to a previous version.

    Creates a snapshot of the current state, then applies the
    selected version's config, symbols, and description.
    """
    from ...db.repositories.agent import AgentRepository

    # Check for active agents before restoring version
    agent_repo = AgentRepository(db)
    active_agents = await agent_repo.get_active_agents_by_strategy(
        uuid.UUID(strategy_id)
    )

    if active_agents:
        agent_names = [a.name for a in active_agents[:3]]
        agent_count = len(active_agents)

        if agent_count == 1:
            detail = (
                f"Cannot restore version: "
                f"Agent '{agent_names[0]}' is active. "
                f"Pause the agent first."
            )
        else:
            detail = (
                f"Cannot restore version: "
                f"{agent_count} agents are active "
                f"({', '.join(agent_names)}"
                f"{', ...' if agent_count > 3 else ''}). "
                f"Pause all agents first."
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    repo = StrategyRepository(db)
    strategy = await repo.restore_version(
        uuid.UUID(strategy_id),
        version,
        uuid.UUID(user_id),
    )

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy or version not found",
        )

    return _strategy_to_response(strategy)


# ==================== AI Strategy Specific Endpoints ====================


class PromptPreviewRequest(BaseModel):
    """Request for previewing generated prompt"""

    prompt: str = Field(default="", description="User's custom strategy prompt")
    trading_mode: TradingMode = Field(default=TradingMode.CONSERVATIVE)
    symbols: list[str] = Field(default=["BTC", "ETH"])
    timeframes: list[str] = Field(default=["15m", "1h", "4h"])
    language: str = Field(default="en", description="Prompt language: 'en' or 'zh'")
    prompt_mode: str = Field(default="simple")
    advanced_prompt: str = Field(default="")
    indicators: Optional[dict] = None
    risk_controls: Optional[dict] = None
    prompt_sections: Optional[dict] = None


class PromptPreviewResponse(BaseModel):
    """Response with generated prompt preview"""

    system_prompt: str
    estimated_tokens: int
    sections: dict = Field(default_factory=dict)


@router.post("/preview-prompt", response_model=PromptPreviewResponse)
async def preview_prompt(
    data: PromptPreviewRequest,
    user_id: CurrentUserDep,
    _rate_limit: RateLimitApiDep = None,
):
    """
    Preview the generated system prompt for an AI strategy.

    Useful for the Strategy Studio preview feature.
    """
    indicators = {
        "ema_periods": (
            data.indicators.get("ema_periods", [9, 21, 55])
            if data.indicators
            else [9, 21, 55]
        ),
        "rsi_period": data.indicators.get("rsi_period", 14) if data.indicators else 14,
        "macd_fast": data.indicators.get("macd_fast", 12) if data.indicators else 12,
        "macd_slow": data.indicators.get("macd_slow", 26) if data.indicators else 26,
        "macd_signal": data.indicators.get("macd_signal", 9) if data.indicators else 9,
        "atr_period": data.indicators.get("atr_period", 14) if data.indicators else 14,
    }

    risk_controls = RiskControls(
        max_leverage=(
            data.risk_controls.get("max_leverage", 5) if data.risk_controls else 5
        ),
        max_position_ratio=(
            data.risk_controls.get("max_position_ratio", 0.2)
            if data.risk_controls
            else 0.2
        ),
        max_total_exposure=(
            data.risk_controls.get("max_total_exposure", 0.8)
            if data.risk_controls
            else 0.8
        ),
        min_risk_reward_ratio=(
            data.risk_controls.get("min_risk_reward_ratio", 2.0)
            if data.risk_controls
            else 2.0
        ),
        max_drawdown_percent=(
            data.risk_controls.get("max_drawdown_percent", 0.1)
            if data.risk_controls
            else 0.1
        ),
        min_confidence=(
            data.risk_controls.get("min_confidence", 60) if data.risk_controls else 60
        ),
    )

    prompt_sections = PromptSections(
        role_definition=(
            data.prompt_sections.get("role_definition", "")
            if data.prompt_sections
            else ""
        ),
        trading_frequency=(
            data.prompt_sections.get("trading_frequency", "")
            if data.prompt_sections
            else ""
        ),
        entry_standards=(
            data.prompt_sections.get("entry_standards", "")
            if data.prompt_sections
            else ""
        ),
        decision_process=(
            data.prompt_sections.get("decision_process", "")
            if data.prompt_sections
            else ""
        ),
    )

    config = AIStrategyConfig(
        language=data.language,
        indicators=indicators,
        timeframes=data.timeframes,
        risk_controls=risk_controls,
        prompt_mode=data.prompt_mode or "simple",
        prompt_sections=prompt_sections,
        custom_prompt=data.prompt,
        advanced_prompt=data.advanced_prompt or "",
    )

    builder = PromptBuilder(
        config=config,
        trading_mode=data.trading_mode,
        custom_prompt=data.prompt,
    )

    system_prompt = builder.build_system_prompt()
    estimated_tokens = len(system_prompt) // 4

    from ...services.prompt_templates import get_system_templates

    sys_t = get_system_templates(data.language)

    mode_key = data.trading_mode.value
    sections = {
        "role_definition": prompt_sections.role_definition or sys_t["default_role"],
        "trading_mode": sys_t["trading_mode"].get(mode_key, ""),
        "trading_frequency": prompt_sections.trading_frequency
        or sys_t["default_trading_frequency"],
        "entry_standards": prompt_sections.entry_standards
        or sys_t["default_entry_standards"],
        "decision_process": prompt_sections.decision_process
        or sys_t["default_decision_process"],
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
    model_id: str
    valid: bool
    error: Optional[str] = None


class DebateValidationResponse(BaseModel):
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
    """Validate debate model configuration."""
    from ...services.ai import resolve_provider_credentials
    from ...services.debate_engine import validate_debate_models as validate_models

    async def cred_resolver(model_id: str):
        return await resolve_provider_credentials(
            db, crypto, uuid.UUID(user_id), model_id
        )

    validation_results = await validate_models(
        data.model_ids, credentials_resolver=cred_resolver
    )

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
        message = (
            f"Only {valid_count} model(s) valid. At least 2 models required for debate."
        )

    return DebateValidationResponse(
        valid=valid_count >= 2,
        models=models,
        message=message,
    )


# ==================== Helper Functions ====================


def _strategy_to_response(strategy) -> StrategyResponse:
    """Convert strategy DB model to response"""
    # Try to get author name from eagerly-loaded user relationship
    author_name = None
    try:
        if strategy.user:
            author_name = strategy.user.name
    except Exception:
        pass

    # Get agent count from eagerly-loaded agents relationship
    agent_count = 0
    try:
        if strategy.agents is not None:
            agent_count = len(strategy.agents)
    except Exception:
        pass

    return StrategyResponse(
        id=str(strategy.id),
        user_id=str(strategy.user_id),
        type=strategy.type,
        name=strategy.name,
        description=strategy.description,
        symbols=strategy.symbols or [],
        config=strategy.config or {},
        visibility=strategy.visibility,
        category=strategy.category,
        tags=strategy.tags or [],
        forked_from=str(strategy.forked_from) if strategy.forked_from else None,
        fork_count=strategy.fork_count or 0,
        author_name=author_name,
        agent_count=agent_count,
        is_paid=strategy.is_paid or False,
        price_monthly=strategy.price_monthly,
        pricing_model=strategy.pricing_model or "free",
        created_at=strategy.created_at.isoformat(),
        updated_at=strategy.updated_at.isoformat(),
    )
