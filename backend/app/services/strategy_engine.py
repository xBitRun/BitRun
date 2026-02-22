"""
Strategy Engine - Core orchestration for AI trading decisions.

Coordinates:
- Prompt building with market context
- AI decision generation
- Decision parsing and validation
- Trade execution
- Logging and audit trail
"""

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..db.models import AgentDB, StrategyDB
from ..db.repositories.agent import AgentRepository
from ..db.repositories.decision import DecisionRepository
from ..models.decision import ActionType, DecisionResponse
from ..models.debate import ConsensusMode, DebateConfig, DebateResult
from ..models.market_context import MarketContext
from ..models.strategy import AIStrategyConfig, TradingMode
from ..traders.base import AccountState, BaseTrader, MarketData, OrderResult
from .ai import BaseAIClient, get_ai_client, resolve_provider_credentials
from ..core.security import get_crypto_service
from .data_access_layer import DataAccessLayer
from .debate_engine import DebateEngine
from .decision_parser import DecisionParser, DecisionParseError
from .agent_position_service import (
    AgentPositionService,
    PositionConflictError,
    CapitalExceededError,
)
from .prompt_builder import PromptBuilder
from .notifications import get_notification_service
from ..api.websocket import publish_decision, publish_position_update

logger = logging.getLogger(__name__)


class StrategyExecutionError(Exception):
    """Error during strategy execution"""

    pass


# Minimum position size in USD to avoid exchange rejections due to min order size
MIN_POSITION_SIZE_USD = 10.0


class StrategyEngine:
    """
    Core strategy execution engine.

    Lifecycle:
    1. Build prompts with market context
    2. Call AI for decision
    3. Parse and validate decisions
    4. Execute trades (if enabled)
    5. Log everything to database

    Usage:
        engine = StrategyEngine(strategy, trader, ai_client, db_session)
        result = await engine.run_cycle()
    """

    def __init__(
        self,
        agent: AgentDB,
        trader: BaseTrader,
        ai_client: Optional[BaseAIClient] = None,
        db_session: Optional[AsyncSession] = None,
        auto_execute: bool = True,
        use_enhanced_context: bool = True,
        position_service: Optional[AgentPositionService] = None,
        # Backward compat: accept strategy= kwarg, wrap in agent-like object
        strategy: Optional[StrategyDB] = None,
    ):
        """
        Initialize strategy engine.

        Args:
            agent: Agent execution instance (has .strategy loaded)
            trader: Exchange trading adapter
            ai_client: AI client for generating decisions
            db_session: Database session for persisting decisions
            auto_execute: If True, automatically execute decisions
            use_enhanced_context: If True, use DataAccessLayer for enhanced market context
            position_service: AgentPositionService for agent-level position isolation.
        """
        self.agent = agent
        self.strategy = agent.strategy if agent else strategy  # strategy from agent
        self.trader = trader
        self.db_session = db_session
        self.use_enhanced_context = use_enhanced_context
        self.position_service = position_service

        # Parse AI config from strategy.config
        self.config = (
            AIStrategyConfig(**self.strategy.config)
            if self.strategy.config
            else AIStrategyConfig()
        )

        # Respect both constructor param and config.auto_execute
        self.auto_execute = auto_execute and (agent.auto_execute if agent else True)
        self.risk_controls = self.config.risk_controls

        # Settings
        self._settings = get_settings()

        # AI client: use provided or resolve from DB in run_cycle when None
        self.ai_client = ai_client

        # Store the model ID used for this engine
        self._ai_model_id = self._get_effective_model_id()

        # Initialize components
        trading_mode = (
            TradingMode(self.config.trading_mode)
            if hasattr(self.config, "trading_mode")
            else TradingMode.CONSERVATIVE
        )
        self.prompt_builder = PromptBuilder(
            config=self.config,
            trading_mode=trading_mode,
            custom_prompt=self.config.custom_prompt,
            max_positions=self._settings.default_max_positions,
        )
        self.decision_parser = DecisionParser(risk_controls=self.risk_controls)

        # Initialize Data Access Layer for enhanced context
        self.data_access_layer: Optional[DataAccessLayer] = None
        if use_enhanced_context:
            try:
                self.data_access_layer = DataAccessLayer(
                    trader=trader,
                    config=self.config,
                )
                logger.info(f"Enhanced context enabled for strategy {self.strategy.id}")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize DataAccessLayer: {e}, falling back to basic context"
                )
                self.data_access_layer = None

        # Initialize debate engine if enabled (config from Agent, not Strategy)
        self.debate_engine: Optional[DebateEngine] = None
        if self.agent:
            debate_enabled = getattr(self.agent, "debate_enabled", False) or False
            debate_models = getattr(self.agent, "debate_models", None) or []
            debate_consensus_mode = (
                getattr(self.agent, "debate_consensus_mode", None) or "majority_vote"
            )
            debate_min_participants = (
                getattr(self.agent, "debate_min_participants", 2) or 2
            )

            if debate_enabled and len(debate_models) >= 2:
                debate_config = DebateConfig(
                    enabled=True,
                    model_ids=debate_models,
                    consensus_mode=ConsensusMode(debate_consensus_mode),
                    min_participants=debate_min_participants,
                )
                self.debate_engine = DebateEngine(
                    config=debate_config,
                    risk_controls=self.risk_controls,
                )
                logger.info(
                    f"Debate mode enabled for agent {self.agent.id} with "
                    f"{len(debate_models)} models"
                )

        # Execution state
        self._last_decision: Optional[DecisionResponse] = None
        self._last_account_state: Optional[AccountState] = None
        self._last_decision_record_id: Optional[uuid.UUID] = None
        self._last_debate_result: Optional[DebateResult] = None
        self._last_market_contexts: Optional[dict[str, MarketContext]] = None

    def _get_effective_model_id(self) -> str:
        """Get the effective model ID configured on the agent."""
        if self.agent and self.agent.ai_model:
            return self.agent.ai_model
        raise StrategyExecutionError(
            "No AI model configured for this agent. "
            "Edit the agent and select an AI model."
        )

    async def _resolve_and_set_ai_client(self) -> None:
        """Resolve API key from DB and set ai_client. Requires db_session."""
        if self.db_session is None:
            raise StrategyExecutionError(
                "Cannot resolve AI credentials without db_session. "
                "Pass ai_client or db_session when creating StrategyEngine."
            )
        model_id = self._get_effective_model_id()
        user_id = self.agent.user_id if self.agent else self.strategy.user_id
        api_key, base_url = await resolve_provider_credentials(
            self.db_session,
            get_crypto_service(),
            user_id,
            model_id,
        )
        if not api_key and "custom" not in model_id.lower().split(":")[0]:
            raise StrategyExecutionError(
                f"No API key configured for model {model_id}. "
                "Configure the provider in the app (Models / Providers)."
            )
        logger.info(f"Creating AI client for model: {model_id}")
        kwargs = {"api_key": api_key or ""}
        if base_url:
            kwargs["base_url"] = base_url
        self.ai_client = get_ai_client(model_id, **kwargs)

    async def run_cycle(self) -> dict:
        """
        Run one decision cycle.

        Returns:
            Dict with cycle results including:
            - decision: Parsed DecisionResponse
            - executed: List of execution results
            - error: Error message if any
            - decision_record_id: ID of saved decision record
        """
        result = {
            "success": False,
            "decision": None,
            "executed": [],
            "error": None,
            "latency_ms": 0,
            "tokens_used": 0,
            "decision_record_id": None,
        }

        start_time = time.time()
        system_prompt = ""
        user_prompt = ""
        raw_response = ""
        decision = None
        debate_result: Optional[DebateResult] = None

        # Resolve AI client from DB if not provided
        if self.ai_client is None:
            await self._resolve_and_set_ai_client()

        try:
            # 1. Get current account state (agent-isolated when possible)
            if self.position_service and self.agent:
                # Fetch current prices for unrealized P&L calculation
                current_prices: dict[str, float] = {}
                if self.strategy and self.strategy.symbols:
                    for sym in self.strategy.symbols:
                        try:
                            md = await self.trader.get_market_data(sym)
                            if md and md.mid_price > 0:
                                current_prices[sym] = md.mid_price
                        except Exception:
                            pass
                # Get real account equity for percentage-based capital allocation
                real_equity = None
                try:
                    real_account = await self.trader.get_account_state()
                    real_equity = real_account.equity
                except Exception:
                    pass
                agent_account = await self.position_service.get_agent_account_state(
                    agent_id=self.agent.id,
                    agent=self.agent,
                    current_prices=current_prices,
                    account_equity=real_equity,
                )
                account_state = agent_account.to_account_state(current_prices)
            else:
                account_state = await self.trader.get_account_state()
            self._last_account_state = account_state

            # 2. Check if we can trade (risk limits)
            can_trade, reason = await self._check_risk_limits(account_state)
            if not can_trade:
                result["error"] = f"Risk limit reached: {reason}"
                result["latency_ms"] = int((time.time() - start_time) * 1000)
                # Persist risk-limit skip as a decision record so user sees a record every cycle
                risk_limit_msg = result["error"]
                risk_decision = DecisionResponse(
                    chain_of_thought=risk_limit_msg,
                    market_assessment="",
                    decisions=[],
                )
                result["decision"] = risk_decision
                try:
                    decision_record_id = await self._save_decision_record(
                        system_prompt="Risk limit check.",
                        user_prompt="Account state checked; risk limit triggered.",
                        raw_response=risk_limit_msg,
                        decision=risk_decision,
                        execution_results=[],
                        tokens_used=0,
                        latency_ms=result["latency_ms"],
                        debate_result=None,
                    )
                    result["decision_record_id"] = (
                        str(decision_record_id) if decision_record_id else None
                    )
                    self._last_decision_record_id = decision_record_id
                except Exception as e:
                    logger.error(f"Failed to save risk-limit decision record: {e}")
                await self._publish_decision_update(result, risk_decision)
                return result

            # 3. Get market data (enhanced with K-lines/indicators or basic)
            # 4. Build prompts
            system_prompt = self.prompt_builder.build_system_prompt()
            market_contexts = None

            if self.data_access_layer is not None:
                # Use enhanced context with K-lines and technical indicators
                market_contexts = await self._get_market_contexts()
                self._last_market_contexts = market_contexts
                user_prompt = self.prompt_builder.build_user_prompt_with_context(
                    account=account_state,
                    market_contexts=market_contexts,
                )
                result["enhanced_context"] = True
            else:
                # Fallback to basic market data
                market_data = await self._get_market_data()
                user_prompt = self.prompt_builder.build_user_prompt(
                    account=account_state,
                    market_data=market_data,
                )
                result["enhanced_context"] = False

            # 5. Call AI for decision (single model or debate)
            debate_result: Optional[DebateResult] = None

            if self.debate_engine is not None:
                # Resolve credentials from DB for each debate model
                async def _debate_cred_resolver(model_id: str):
                    return await resolve_provider_credentials(
                        self.db_session,
                        get_crypto_service(),
                        self.strategy.user_id,
                        model_id,
                    )

                # Run multi-model debate
                debate_result = await self.debate_engine.run_debate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    credentials_resolver=_debate_cred_resolver,
                )
                self._last_debate_result = debate_result

                # Extract results from debate
                raw_response = debate_result.combined_chain_of_thought
                decision = debate_result.to_decision_response()
                result["tokens_used"] = sum(
                    p.tokens_used for p in debate_result.participants
                )
                result["debate"] = {
                    "models": [p.model_id for p in debate_result.participants],
                    "successful": debate_result.successful_participants,
                    "failed": debate_result.failed_participants,
                    "agreement_score": debate_result.agreement_score,
                    "consensus_mode": debate_result.consensus_mode.value,
                }

                # Debate bypasses parser.parse(), so run SL/TP fill + validation
                # explicitly on the consensus DecisionResponse.
                self._update_parser_market_data(market_contexts)
                self.decision_parser._validate_decisions(decision)
            else:
                # Single model decision
                ai_response = await self.ai_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                result["tokens_used"] = ai_response.tokens_used
                raw_response = ai_response.content

                # Inject market prices & ATR into parser so it can auto-fill
                # missing SL/TP on open decisions.
                self._update_parser_market_data(market_contexts)

                decision = self.decision_parser.parse(raw_response)

            self._last_decision = decision
            result["decision"] = decision

            # 7. Execute decisions (if enabled)
            if self.auto_execute:
                execution_results = await self._execute_decisions(
                    decision, account_state
                )
                result["executed"] = execution_results

            result["success"] = True

        except DecisionParseError as e:
            result["error"] = f"Failed to parse AI response: {e.message}"
            logger.warning(
                f"Decision parse error for strategy {self.strategy.id}: {e.message}"
            )
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Strategy cycle error for {self.strategy.id}: {e}")

        result["latency_ms"] = int((time.time() - start_time) * 1000)

        # When AI call failed (no raw_response / debate_result), persist error as a decision record
        if result.get("error") and not raw_response and debate_result is None:
            error_msg = result["error"]
            raw_response = error_msg
            decision = DecisionResponse(
                chain_of_thought=error_msg,
                market_assessment="",
                decisions=[],
            )
            result["decision"] = decision
            if not system_prompt:
                system_prompt = "AI invocation"
            if not user_prompt:
                user_prompt = "Error: " + error_msg

        # 8. Persist decision record to database
        try:
            decision_record_id = await self._save_decision_record(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                raw_response=raw_response,
                decision=decision,
                execution_results=result.get("executed", []),
                tokens_used=result["tokens_used"],
                latency_ms=result["latency_ms"],
                debate_result=debate_result,
                market_contexts=market_contexts,
                account_state=account_state,
            )
            result["decision_record_id"] = (
                str(decision_record_id) if decision_record_id else None
            )
            self._last_decision_record_id = decision_record_id

            # Update agent performance for executed closes (realized PnL)
            if self.db_session and result.get("executed") and self.agent:
                agent_repo = AgentRepository(self.db_session)
                for er in result["executed"]:
                    if er.get("executed") and er.get("realized_pnl") is not None:
                        pnl = float(er["realized_pnl"])
                        try:
                            await agent_repo.update_performance(
                                self.agent.id,
                                pnl_change=pnl,
                                is_win=pnl > 0,
                            )
                            logger.info(
                                f"Updated agent {self.agent.id} performance: "
                                f"realized_pnl={pnl:.2f} is_win={pnl > 0}"
                            )
                        except Exception as perf_e:
                            logger.warning(
                                f"Failed to update agent performance: {perf_e}"
                            )
                await self.db_session.flush()
        except Exception as e:
            logger.error(f"Failed to save decision record: {e}")
            # Don't fail the whole cycle if persistence fails

        # 9. Publish decision via WebSocket for real-time updates
        await self._publish_decision_update(result, decision)

        return result

    async def _publish_decision_update(
        self,
        result: dict,
        decision: Optional[DecisionResponse],
    ) -> None:
        """Publish decision to WebSocket for real-time client updates"""
        try:
            # Get user_id from agent
            user_id = (
                str(self.agent.user_id)
                if self.agent
                else (str(self.strategy.user_id) if self.strategy.user_id else None)
            )
            if not user_id:
                return

            agent_id = str(self.agent.id) if self.agent else str(self.strategy.id)

            # Build decision data for WebSocket
            decision_data = {
                "id": result.get("decision_record_id"),
                "agent_id": agent_id,
                "strategy_id": str(self.strategy.id) if self.strategy else None,
                "strategy_name": self.strategy.name if self.strategy else "",
                "timestamp": datetime.now(UTC).isoformat(),
                "success": result.get("success", False),
                "latency_ms": result.get("latency_ms", 0),
                "tokens_used": result.get("tokens_used", 0),
                "error": result.get("error"),
            }

            if decision:
                decision_data.update(
                    {
                        "overall_confidence": decision.overall_confidence,
                        "market_assessment": (
                            decision.market_assessment[:200]
                            if decision.market_assessment
                            else ""
                        ),
                        "decisions": [
                            {
                                "symbol": d.symbol,
                                "action": d.action.value,
                                "confidence": d.confidence,
                                "leverage": d.leverage,
                                "position_size_usd": d.position_size_usd,
                            }
                            for d in decision.decisions
                        ],
                    }
                )

            # Add execution results
            if result.get("executed"):
                decision_data["execution_results"] = result["executed"]

            await publish_decision(
                user_id=user_id,
                strategy_id=str(self.strategy.id),
                decision_data=decision_data,
            )

            # If trades were executed, also publish position update
            executed_trades = [
                e for e in result.get("executed", []) if e.get("executed")
            ]
            if executed_trades and self._last_account_state:
                # Re-fetch positions after execution (agent-isolated when possible)
                try:
                    if self.position_service and self.agent:
                        agent_state = (
                            await self.position_service.get_agent_account_state(
                                agent_id=self.agent.id,
                                agent=self.agent,
                                account_equity=self._last_account_state.equity,
                            )
                        )
                        positions_data = [
                            {
                                "symbol": p.symbol,
                                "side": p.side,
                                "size": p.size,
                                "entry_price": p.entry_price,
                                "unrealized_pnl": 0.0,
                            }
                            for p in agent_state.positions
                        ]
                    else:
                        new_account_state = await self.trader.get_account_state()
                        positions_data = [
                            {
                                "symbol": pos.get("symbol", ""),
                                "side": pos.get("side", ""),
                                "size": pos.get("size", 0),
                                "entry_price": pos.get("entry_price", 0),
                                "unrealized_pnl": pos.get("unrealized_pnl", 0),
                            }
                            for pos in getattr(new_account_state, "positions", [])
                        ]

                    # Get account_id from agent
                    ws_account_id = (
                        str(self.agent.account_id)
                        if self.agent and self.agent.account_id
                        else "unknown"
                    )

                    await publish_position_update(
                        user_id=user_id,
                        account_id=ws_account_id,
                        positions=positions_data,
                    )
                except Exception as e:
                    logger.warning(f"Failed to publish position update: {e}")

        except Exception as e:
            # Don't fail the cycle if WebSocket publishing fails
            logger.warning(f"Failed to publish decision to WebSocket: {e}")

        # Send notifications if configured
        await self._send_notifications(result, decision)

    async def _send_notifications(
        self,
        result: dict,
        decision: Optional[DecisionResponse],
    ) -> None:
        """Send notifications for the decision via configured channels"""
        try:
            notification_service = get_notification_service()
            if not notification_service.is_any_configured():
                return

            # Send decision notification
            agent_id = str(self.agent.id) if self.agent else str(self.strategy.id)
            decision_data = {
                "agent_id": agent_id,
                "overall_confidence": decision.overall_confidence if decision else 0,
                "decisions": [
                    {
                        "symbol": d.symbol,
                        "action": d.action.value,
                        "confidence": d.confidence,
                    }
                    for d in (decision.decisions if decision else [])
                ],
                "latency_ms": result.get("latency_ms", 0),
            }

            await notification_service.send_decision_notification(
                strategy_name=self.strategy.name,
                decision_data=decision_data,
            )

            # Send trade notifications for executed trades
            for execution in result.get("executed", []):
                if execution.get("executed"):
                    await notification_service.send_trade_notification(
                        strategy_name=self.strategy.name,
                        symbol=execution.get("symbol", "Unknown"),
                        action=execution.get("action", "unknown"),
                        size_usd=execution.get("size_usd", 0),
                        price=execution.get("price", 0),
                    )
        except Exception as e:
            # Don't fail the cycle if notifications fail
            logger.warning(f"Failed to send notifications: {e}")

    async def _save_decision_record(
        self,
        system_prompt: str,
        user_prompt: str,
        raw_response: str,
        decision: Optional[DecisionResponse],
        execution_results: list,
        tokens_used: int,
        latency_ms: int,
        debate_result: Optional[DebateResult] = None,
        market_contexts: Optional[dict] = None,
        account_state: Optional[AccountState] = None,
    ) -> Optional[uuid.UUID]:
        """
        Save decision record to database.

        Args:
            system_prompt: System prompt used
            user_prompt: User prompt with market data
            raw_response: Raw AI response
            decision: Parsed decision response
            execution_results: Results of trade execution
            tokens_used: Number of tokens used
            latency_ms: Latency in milliseconds
            debate_result: Optional debate result if debate mode was used
            market_contexts: Optional dict of symbol -> MarketContext used for this decision
            account_state: Optional account state at the time of the decision

        Returns:
            UUID of saved record, or None if no db_session
        """
        if not self.db_session:
            logger.debug("No database session provided, skipping decision persistence")
            return None

        if not raw_response and not debate_result:
            # Nothing to save if we didn't get a response
            return None

        repo = DecisionRepository(self.db_session)

        # Convert decisions to JSON-serializable format
        decisions_json = []
        if decision:
            for d in decision.decisions:
                decisions_json.append(
                    {
                        "symbol": d.symbol,
                        "action": d.action.value,
                        "leverage": d.leverage,
                        "position_size_usd": d.position_size_usd,
                        "entry_price": d.entry_price,
                        "stop_loss": d.stop_loss,
                        "take_profit": d.take_profit,
                        "confidence": d.confidence,
                        "risk_usd": d.risk_usd,
                        "reasoning": d.reasoning,
                    }
                )

        # Prepare debate-specific fields
        is_debate = debate_result is not None
        debate_models = None
        debate_responses = None
        debate_consensus_mode = None
        debate_agreement_score = None

        if debate_result:
            debate_models = [p.model_id for p in debate_result.participants]
            debate_responses = [
                {
                    "model_id": p.model_id,
                    "succeeded": p.succeeded,
                    "confidence": p.overall_confidence,
                    "latency_ms": p.latency_ms,
                    "tokens_used": p.tokens_used,
                    "error": p.error,
                    # 原始响应 - 用于调试和异常分析
                    "raw_response": p.raw_response,
                    # 思维链和市场评估（可选）
                    "chain_of_thought": p.chain_of_thought if p.succeeded else None,
                    "market_assessment": p.market_assessment if p.succeeded else None,
                    # 决策详情
                    "decisions": (
                        [
                            {
                                "symbol": d.symbol,
                                "action": d.action.value,
                                "confidence": d.confidence,
                            }
                            for d in p.decisions
                        ]
                        if p.succeeded
                        else []
                    ),
                }
                for p in debate_result.participants
            ]
            debate_consensus_mode = debate_result.consensus_mode.value
            debate_agreement_score = debate_result.agreement_score

        # Determine AI model label
        if is_debate:
            ai_model_label = f"debate:{len(debate_result.participants)}models"
        else:
            ai_model_label = self._ai_model_id

        # Serialize market contexts snapshot (limit K-lines to 5 per timeframe)
        market_snapshot = None
        if market_contexts:
            try:
                market_snapshot = [
                    ctx.to_dict(kline_limit=5) for ctx in market_contexts.values()
                ]
            except Exception as e:
                logger.warning(f"Failed to serialize market snapshot: {e}")

        # Serialize account state snapshot
        account_snapshot_data = None
        if account_state:
            try:
                account_snapshot_data = {
                    "equity": account_state.equity,
                    "available_balance": account_state.available_balance,
                    "total_margin_used": account_state.total_margin_used,
                    "unrealized_pnl": account_state.unrealized_pnl,
                    "margin_usage_percent": account_state.margin_usage_percent,
                    "position_count": account_state.position_count,
                    "positions": [
                        {
                            "symbol": pos.symbol,
                            "side": pos.side,
                            "size": pos.size,
                            "size_usd": pos.size_usd,
                            "entry_price": pos.entry_price,
                            "mark_price": pos.mark_price,
                            "leverage": pos.leverage,
                            "unrealized_pnl": pos.unrealized_pnl,
                            "unrealized_pnl_percent": pos.unrealized_pnl_percent,
                            "liquidation_price": pos.liquidation_price,
                        }
                        for pos in account_state.positions
                    ],
                }
            except Exception as e:
                logger.warning(f"Failed to serialize account snapshot: {e}")

        # Create the decision record
        agent_id = self.agent.id if self.agent else self.strategy.id
        record = await repo.create(
            agent_id=agent_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=raw_response
            or (debate_result.combined_chain_of_thought if debate_result else ""),
            chain_of_thought=decision.chain_of_thought if decision else "",
            market_assessment=decision.market_assessment if decision else "",
            decisions=decisions_json,
            overall_confidence=decision.overall_confidence if decision else 0,
            ai_model=ai_model_label,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            market_snapshot=market_snapshot,
            account_snapshot=account_snapshot_data,
            is_debate=is_debate,
            debate_models=debate_models,
            debate_responses=debate_responses,
            debate_consensus_mode=debate_consensus_mode,
            debate_agreement_score=debate_agreement_score,
        )

        # Save execution results and mark executed only if at least one order was actually placed
        if execution_results:
            has_actual_execution = any(
                er.get("executed", False) for er in execution_results
            )
            if has_actual_execution:
                await repo.mark_executed(record.id, execution_results)
            else:
                # Save execution results (with skip reasons) but don't mark as executed
                record.execution_results = execution_results
                await self.db_session.flush()

        await self.db_session.commit()

        logger.info(
            f"Saved decision record {record.id} for strategy {self.strategy.id}"
        )
        return record.id

    async def _check_risk_limits(self, account: AccountState) -> tuple[bool, str]:
        """
        Fatal pre-flight check — blocks the **entire** cycle.

        Only conditions that make it impossible (or dangerous) to call the
        AI at all should live here.  Everything that merely prevents
        *opening new positions* belongs in ``_check_can_open_position``
        so that close/hold decisions can still be generated and executed.

        Returns:
            Tuple of (can_trade, reason)
        """
        # Reject trading when equity is zero or negative
        if account.equity <= 0:
            return False, f"Equity is zero or negative (${account.equity:.2f})"

        return True, "OK"

    async def _check_can_open_position(self, account: AccountState) -> tuple[bool, str]:
        """
        Check whether the strategy is allowed to **open** a new position.

        These checks do NOT block the whole decision cycle — the AI is
        still called so it can produce close/hold decisions.  Only open
        actions are gated by this method.

        Uses strategy-level position count (via PositionService) instead
        of the account-wide count so that other strategies or manual
        trades on the same account don't block this strategy.

        Returns:
            Tuple of (can_open, reason)
        """
        rc = self.risk_controls
        max_positions = self._settings.default_max_positions

        # Agent-level position count (preferred)
        if self.position_service and self.agent:
            agent_positions = await self.position_service.get_agent_positions(
                self.agent.id, status_filter="open"
            )
            agent_position_count = len(agent_positions)
            if agent_position_count >= max_positions:
                return False, (
                    f"Agent max positions ({max_positions}) reached "
                    f"(agent has {agent_position_count})"
                )
        else:
            # Fallback: account-level check (backward compatible)
            if account.position_count >= max_positions:
                return False, f"Max positions ({max_positions}) reached"

        # Check margin usage at account level (still relevant as a
        # safety net – even if this strategy has room, the account
        # might be fully margined)
        if account.margin_usage_percent >= rc.max_total_exposure * 100:
            return (
                False,
                f"Margin usage {account.margin_usage_percent:.1f}% exceeds limit",
            )

        # Check drawdown - compare current unrealized PnL against equity
        # If we have significant unrealized losses, we might be in drawdown
        if account.equity > 0 and account.unrealized_pnl < 0:
            drawdown_percent = abs(account.unrealized_pnl) / account.equity
            if drawdown_percent >= rc.max_drawdown_percent:
                return (
                    False,
                    f"Drawdown {drawdown_percent*100:.1f}% exceeds max {rc.max_drawdown_percent*100:.1f}%",
                )

        return True, "OK"

    async def _get_market_data(self) -> dict[str, MarketData]:
        """Get basic market data for all configured symbols"""
        symbols = self.prompt_builder.get_symbols()
        market_data = {}

        for symbol in symbols:
            try:
                data = await self.trader.get_market_data(symbol)
                market_data[symbol] = data
            except Exception:
                # Skip symbols that fail
                continue

        return market_data

    async def _get_market_contexts(self) -> dict[str, MarketContext]:
        """
        Get enhanced market contexts with K-lines and technical indicators.

        Uses DataAccessLayer to fetch:
        - Real-time market data
        - K-lines for configured timeframes
        - Technical indicators (EMA, RSI, MACD, ATR, Bollinger Bands)
        - Funding rate history

        Returns:
            Dict mapping symbol to MarketContext
        """
        if self.data_access_layer is None:
            # Fallback: convert basic market data to minimal contexts
            market_data = await self._get_market_data()
            return {
                symbol: MarketContext(symbol=symbol, current=data)
                for symbol, data in market_data.items()
            }

        symbols = self.prompt_builder.get_symbols()

        try:
            return await self.data_access_layer.get_market_contexts(symbols)
        except Exception as e:
            logger.warning(
                f"Failed to get market contexts: {e}, falling back to basic data"
            )
            # Fallback to basic market data on failure
            market_data = await self._get_market_data()
            return {
                symbol: MarketContext(symbol=symbol, current=data)
                for symbol, data in market_data.items()
            }

    def get_last_market_contexts(self) -> Optional[dict[str, MarketContext]]:
        """Get the last fetched market contexts"""
        return self._last_market_contexts

    def _update_parser_market_data(
        self, market_contexts: Optional[dict[str, MarketContext]]
    ) -> None:
        """
        Extract current prices and ATR values from market contexts and
        inject them into the decision parser for SL/TP auto-fill.

        For ATR we prefer the 1h timeframe; if unavailable we try the
        first timeframe that has an ATR value.
        """
        market_prices: dict[str, float] = {}
        market_atrs: dict[str, float] = {}

        if market_contexts:
            for symbol, ctx in market_contexts.items():
                # Price: use mid_price from current market data
                if ctx.current and ctx.current.mid_price:
                    market_prices[symbol] = ctx.current.mid_price

                # ATR: prefer 1h, fallback to first available timeframe
                if ctx.indicators:
                    atr_value = None
                    for tf in ("1h", "4h", "15m", "30m", "1d"):
                        ind = ctx.indicators.get(tf)
                        if ind and ind.atr is not None:
                            atr_value = ind.atr
                            break
                    # If preferred timeframes not found, try any
                    if atr_value is None:
                        for ind in ctx.indicators.values():
                            if ind and ind.atr is not None:
                                atr_value = ind.atr
                                break
                    if atr_value is not None:
                        market_atrs[symbol] = atr_value

        self.decision_parser.update_market_data(market_prices, market_atrs)

    async def _execute_decisions(
        self,
        decision: DecisionResponse,
        account: AccountState,
    ) -> list[dict]:
        """
        Execute parsed decisions.

        Applies risk controls and executes in order:
        1. Close positions first
        2. Then open new positions

        Returns:
            List of execution results
        """
        results = []

        # Sort decisions: closes first, then opens, then holds
        sorted_decisions = sorted(
            decision.decisions,
            key=lambda d: (
                0
                if d.action in (ActionType.CLOSE_LONG, ActionType.CLOSE_SHORT)
                else (
                    1
                    if d.action in (ActionType.OPEN_LONG, ActionType.OPEN_SHORT)
                    else 2
                )
            ),
        )

        # Get configured watchlist for symbol validation
        configured_symbols = {s.upper() for s in self.prompt_builder.get_symbols()}

        for d in sorted_decisions:
            # Validate symbol is in strategy's configured watchlist
            if configured_symbols and d.symbol.upper() not in configured_symbols:
                results.append(
                    {
                        "symbol": d.symbol,
                        "action": d.action.value,
                        "confidence": d.confidence,
                        "executed": False,
                        "reason": (
                            f"Symbol {d.symbol} not in strategy watchlist "
                            f"({', '.join(sorted(configured_symbols))})"
                        ),
                        "requested_size_usd": d.position_size_usd,
                        "actual_size_usd": None,
                        "order_result": None,
                    }
                )
                logger.warning(
                    f"[Execution] SKIP {d.symbol} {d.action.value}: "
                    f"symbol not in watchlist"
                )
                continue

            # Check if should execute
            should_exec, reason = self.decision_parser.should_execute(d)

            exec_result = {
                "symbol": d.symbol,
                "action": d.action.value,
                "confidence": d.confidence,
                "executed": False,
                "reason": reason,
                "requested_size_usd": d.position_size_usd,
                "actual_size_usd": None,
                "order_result": None,
            }

            is_open_action = d.action in (ActionType.OPEN_LONG, ActionType.OPEN_SHORT)

            if not should_exec:
                logger.warning(
                    f"[Execution] SKIP {d.symbol} {d.action.value}: {reason} "
                    f"(confidence={d.confidence}, size_usd={d.position_size_usd})"
                )
                results.append(exec_result)
                continue

            # Refresh account state before open actions to get latest balance
            # and margin data (avoids stale state from AI analysis phase)
            if is_open_action:
                try:
                    account = await self.trader.get_account_state()
                    self._last_account_state = account
                except Exception as refresh_err:
                    logger.warning(
                        f"[Execution] Failed to refresh account state: {refresh_err}, "
                        "using stale state"
                    )

                # Gate new positions by risk limits (max_positions, margin, drawdown).
                # Close/hold decisions are never blocked here.
                can_open, open_reason = await self._check_can_open_position(account)
                if not can_open:
                    exec_result["reason"] = open_reason
                    logger.warning(
                        f"[Execution] SKIP OPEN {d.symbol} {d.action.value}: {open_reason}"
                    )
                    results.append(exec_result)
                    continue

            # Apply position size limits (margin-based)
            position_size = self._apply_position_limits(
                d.position_size_usd,
                account,
                leverage=d.leverage,
            )
            exec_result["actual_size_usd"] = position_size

            if d.position_size_usd != position_size:
                logger.info(
                    f"[Execution] Position size capped for {d.symbol}: "
                    f"${d.position_size_usd:.2f} -> ${position_size:.2f} "
                    f"(equity=${account.equity:.2f}, available=${account.available_balance:.2f}, "
                    f"leverage={d.leverage}x, max_ratio={self.risk_controls.max_position_ratio})"
                )

            # Check minimum position size to avoid exchange rejections
            if is_open_action and position_size < MIN_POSITION_SIZE_USD:
                reason = (
                    f"Position size ${position_size:.2f} below minimum "
                    f"${MIN_POSITION_SIZE_USD:.2f} after risk limits "
                    f"(requested ${d.position_size_usd:.2f})"
                )
                exec_result["reason"] = reason
                logger.warning(
                    f"[Execution] SKIP {d.symbol} {d.action.value}: {reason}"
                )
                results.append(exec_result)
                continue

            # For close actions, capture position metadata for later realized PnL calculation
            # We'll compute realized_pnl AFTER order execution using the actual fill price
            if d.action in (ActionType.CLOSE_LONG, ActionType.CLOSE_SHORT):
                pos = next((p for p in account.positions if p.symbol == d.symbol), None)
                position_leverage = pos.leverage if pos else d.leverage
                position_size_usd = pos.size_usd if pos else 0.0
                # Store position info for realized_pnl calculation after order fills
                exec_result["_position_entry_price"] = pos.entry_price if pos else 0.0
                exec_result["_position_size"] = pos.size if pos else 0.0
                exec_result["_position_side"] = pos.side if pos else "long"

            # Execute based on action type
            try:
                logger.info(
                    f"[Execution] Placing order: {d.symbol} {d.action.value} "
                    f"size_usd=${position_size:.2f} leverage={d.leverage}x "
                    f"sl={d.stop_loss} tp={d.take_profit}"
                )
                order_result = await self._execute_single_decision(
                    d, position_size, account
                )
                exec_result["executed"] = order_result.success
                exec_result["order_result"] = {
                    "order_id": order_result.order_id,
                    "filled_size": order_result.filled_size,
                    "filled_price": order_result.filled_price,
                    "status": order_result.status,
                    "error": order_result.error,
                }

                if order_result.success:
                    logger.info(
                        f"[Execution] ORDER SUCCESS: {d.symbol} {d.action.value} "
                        f"filled_size={order_result.filled_size} "
                        f"filled_price={order_result.filled_price} "
                        f"status={order_result.status}"
                    )

                    # Calculate realized_pnl using ACTUAL fill price (not cached current_prices)
                    # This ensures accuracy even when market data API is rate-limited
                    if d.action in (ActionType.CLOSE_LONG, ActionType.CLOSE_SHORT):
                        entry_price = exec_result.pop("_position_entry_price", 0.0)
                        pos_size = exec_result.pop("_position_size", 0.0)
                        pos_side = exec_result.pop("_position_side", "long")
                        close_price = order_result.filled_price or 0.0

                        if entry_price > 0 and pos_size > 0 and close_price > 0:
                            if pos_side == "long":
                                realized_pnl = (close_price - entry_price) * pos_size
                            else:
                                realized_pnl = (entry_price - close_price) * pos_size
                            logger.info(
                                f"[Execution] Calculated realized_pnl for {d.symbol}: "
                                f"${realized_pnl:.2f} (entry={entry_price:.2f}, "
                                f"close={close_price:.2f}, size={pos_size:.6f})"
                            )
                        else:
                            # Fallback: try to get from DB if available
                            realized_pnl = 0.0
                            if self.position_service and self.agent:
                                try:
                                    db_pos = await self.position_service.get_agent_position_for_symbol(
                                        self.agent.id, d.symbol
                                    )
                                    if db_pos and close_price > 0:
                                        if db_pos.side == "long":
                                            realized_pnl = (
                                                close_price - db_pos.entry_price
                                            ) * db_pos.size
                                        else:
                                            realized_pnl = (
                                                db_pos.entry_price - close_price
                                            ) * db_pos.size
                                        position_leverage = db_pos.leverage
                                        position_size_usd = db_pos.size_usd
                                        logger.info(
                                            f"[Execution] Fallback realized_pnl from DB: "
                                            f"${realized_pnl:.2f} (entry={db_pos.entry_price}, "
                                            f"close={close_price}, size={db_pos.size})"
                                        )
                                except Exception as calc_err:
                                    logger.warning(
                                        f"[Execution] Failed fallback realized_pnl calc for {d.symbol}: {calc_err}"
                                    )

                        exec_result["realized_pnl"] = realized_pnl
                        exec_result["position_leverage"] = position_leverage
                        exec_result["position_size_usd"] = position_size_usd
                else:
                    logger.warning(
                        f"[Execution] ORDER FAILED: {d.symbol} {d.action.value} "
                        f"error={order_result.error} status={order_result.status}"
                    )
                    # Clean up temp fields on failure
                    exec_result.pop("_position_entry_price", None)
                    exec_result.pop("_position_size", None)
                    exec_result.pop("_position_side", None)

            except Exception as e:
                exec_result["reason"] = str(e)
                logger.error(
                    f"[Execution] ORDER EXCEPTION: {d.symbol} {d.action.value} "
                    f"size_usd=${position_size:.2f}: {e}"
                )

            results.append(exec_result)

        return results

    def _apply_position_limits(
        self,
        requested_size: float,
        account: AccountState,
        leverage: int = 1,
    ) -> float:
        """
        Apply risk limits to position size, respecting capital allocation.

        All limits are margin-based: ``max_position_ratio`` caps the **margin**
        (i.e. position_value / leverage) as a fraction of equity, not the raw
        notional value.  This ensures that high-leverage positions can still
        utilise a meaningful share of the account.

        Args:
            requested_size: AI-requested position notional value (USD).
            account: Current account state.
            leverage: Leverage multiplier for this position (used to convert
                      between notional and margin).

        Returns:
            Final capped notional position size (USD).
        """
        rc = self.risk_controls
        lev = max(leverage, 1)

        # If agent has allocated capital, use it as the equity base
        effective_equity = account.equity
        capital_source = self.agent if self.agent else self.strategy
        effective_capital = capital_source.get_effective_capital(account.equity)
        if effective_capital is not None:
            effective_equity = effective_capital

        # max_position_ratio limits MARGIN (not notional).
        # Convert the margin cap back to a notional cap for comparison.
        max_margin_by_ratio = effective_equity * rc.max_position_ratio
        max_by_ratio = max_margin_by_ratio * lev

        # Available balance represents remaining margin capacity.
        # Keep a 5% safety buffer and convert to notional via leverage.
        max_margin_by_balance = account.available_balance * 0.95
        max_by_balance = max_margin_by_balance * lev

        # Take minimum
        max_size = min(max_by_ratio, max_by_balance)
        final_size = min(requested_size, max_size)

        logger.debug(
            f"[Position Limits] requested=${requested_size:.2f} "
            f"effective_equity=${effective_equity:.2f} leverage={lev}x "
            f"max_margin_by_ratio=${max_margin_by_ratio:.2f} "
            f"max_by_ratio=${max_by_ratio:.2f} "
            f"max_margin_by_balance=${max_margin_by_balance:.2f} "
            f"max_by_balance=${max_by_balance:.2f} "
            f"-> final=${final_size:.2f}"
        )

        return final_size

    async def _execute_single_decision(
        self,
        decision,
        position_size: float,
        account: AccountState,
    ) -> OrderResult:
        """
        Execute a single decision with position isolation.

        For OPEN actions:
          1. Claim the symbol slot (pending record in agent_positions)
          2. Check capital allocation
          3. Place the order
          4. On success → confirm the record; on failure → release the claim

        For CLOSE actions:
          1. Look up the agent's position record
          2. Close on exchange
          3. Mark the record as closed
        """
        symbol = decision.symbol
        ps = self.position_service  # may be None (backward compatible)

        # Get account_id from agent (None for mock agents)
        account_id = (
            self.agent.account_id
            if self.agent
            else getattr(self.strategy, "account_id", None)
        )
        agent_id = self.agent.id if self.agent else self.strategy.id

        # ------ OPEN LONG / SHORT ------
        if decision.action in (ActionType.OPEN_LONG, ActionType.OPEN_SHORT):
            side = "long" if decision.action == ActionType.OPEN_LONG else "short"
            claim = None

            # Step 1: Atomically check capital + claim symbol slot
            # For mock agents, account_id is None but we still track positions
            if ps:
                try:
                    claim = await ps.claim_position_with_capital_check(
                        agent_id=agent_id,
                        account_id=account_id,
                        symbol=symbol,
                        side=side,
                        leverage=decision.leverage,
                        account_equity=account.equity,
                        requested_size_usd=position_size,
                        agent=self.agent,
                    )
                except CapitalExceededError as e:
                    return OrderResult(
                        success=False,
                        error=f"Capital allocation rejected: {e}",
                    )
                except PositionConflictError as e:
                    return OrderResult(
                        success=False,
                        error=f"Symbol conflict: {e}",
                    )

            # Step 2: Place the order
            try:
                if decision.action == ActionType.OPEN_LONG:
                    result = await self.trader.open_long(
                        symbol=symbol,
                        size_usd=position_size,
                        leverage=decision.leverage,
                        stop_loss=decision.stop_loss,
                        take_profit=decision.take_profit,
                    )
                else:
                    result = await self.trader.open_short(
                        symbol=symbol,
                        size_usd=position_size,
                        leverage=decision.leverage,
                        stop_loss=decision.stop_loss,
                        take_profit=decision.take_profit,
                    )
            except Exception:
                # Before releasing the claim, check if the order might have
                # actually executed on the exchange (network timeout scenario).
                if ps and claim:
                    should_release = True
                    try:
                        pos = await self.trader.get_position(symbol)
                        if pos and pos.size > 0:
                            # Position exists on exchange – the order DID execute
                            # despite the exception. Confirm instead of releasing.
                            logger.warning(
                                f"[Execution] Exception during order for {symbol} "
                                f"but exchange shows position (size={pos.size}). "
                                "Confirming claim instead of releasing."
                            )
                            try:
                                await ps.confirm_position(
                                    position_id=claim.id,
                                    size=pos.size,
                                    size_usd=pos.size_usd,
                                    entry_price=pos.entry_price,
                                )
                            except Exception:
                                logger.critical(
                                    f"[Execution] Failed to confirm claim {claim.id} "
                                    f"for {symbol} after detecting exchange position."
                                )
                            should_release = False
                    except Exception:
                        pass  # Can't check – safer to release

                    if should_release:
                        await ps.release_claim(claim.id)
                raise

            # Step 3: Confirm or release
            if ps and claim:
                if result.success:
                    # If the exchange returned success, confirm the position even
                    # if filled_size is None (some exchanges report fills async).
                    # Use the estimated size as fallback so the claim isn't released
                    # for a position that actually exists on the exchange.
                    estimated_size = result.filled_size or (
                        position_size / (result.filled_price or 1.0)
                    )
                    try:
                        await ps.confirm_position(
                            position_id=claim.id,
                            size=result.filled_size or estimated_size,
                            size_usd=position_size,
                            entry_price=result.filled_price or 0.0,
                        )
                    except Exception as confirm_err:
                        # CRITICAL: Order succeeded on exchange but DB confirm
                        # failed. Do NOT release the claim – the reconciliation
                        # job will fix the pending record within 5 minutes.
                        logger.critical(
                            f"[Execution] confirm_position FAILED after successful "
                            f"order for {symbol} (claim {claim.id}): {confirm_err}. "
                            "Leaving claim as pending for reconciliation."
                        )
                else:
                    await ps.release_claim(claim.id)

            return result

        # ------ CLOSE LONG / SHORT ------
        elif decision.action in (ActionType.CLOSE_LONG, ActionType.CLOSE_SHORT):
            # Look up the agent's position record (if isolation is enabled)
            pos_record = None
            if ps:
                pos_record = await ps.get_agent_position_for_symbol(agent_id, symbol)
                if not pos_record:
                    logger.warning(
                        f"[Execution] No position record for {symbol} owned by "
                        f"agent {agent_id} – closing anyway"
                    )

            result = await self.trader.close_position(symbol=symbol)

            # Mark record as closed - ALWAYS use actual fill price for realized_pnl
            if ps and pos_record and result.success:
                # Calculate realized_pnl using the ACTUAL fill price from the close order
                # This ensures accuracy even when market data API is rate-limited
                close_price = result.filled_price or 0.0
                realized_pnl = 0.0

                if (
                    close_price > 0
                    and pos_record.entry_price > 0
                    and pos_record.size > 0
                ):
                    if pos_record.side == "long":
                        realized_pnl = (
                            close_price - pos_record.entry_price
                        ) * pos_record.size
                    else:
                        realized_pnl = (
                            pos_record.entry_price - close_price
                        ) * pos_record.size
                    logger.info(
                        f"[Execution] Calculated realized_pnl for {symbol}: "
                        f"${realized_pnl:.2f} (entry={pos_record.entry_price:.2f}, "
                        f"close={close_price:.2f}, size={pos_record.size:.6f})"
                    )
                else:
                    logger.warning(
                        f"[Execution] Cannot calculate realized_pnl for {symbol}: "
                        f"close_price={close_price}, entry_price={pos_record.entry_price}, "
                        f"size={pos_record.size}"
                    )

                await ps.close_position_record(
                    position_id=pos_record.id,
                    close_price=result.filled_price or 0.0,
                    realized_pnl=realized_pnl,
                )

            return result

        else:
            # HOLD or WAIT
            return OrderResult(success=True, status="no_action")

    def get_last_decision(self) -> Optional[DecisionResponse]:
        """Get the last parsed decision"""
        return self._last_decision

    def get_last_account_state(self) -> Optional[AccountState]:
        """Get the last account state"""
        return self._last_account_state

    def get_last_decision_record_id(self) -> Optional[uuid.UUID]:
        """Get the ID of the last saved decision record"""
        return self._last_decision_record_id
