"""
Debate Engine for multi-model AI trading decisions.

Coordinates multiple AI models to analyze market data in parallel,
then aggregates their decisions using various consensus mechanisms.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Awaitable, Callable, Optional

# Resolver: model_id -> (api_key, base_url) from DB
CredentialsResolver: type = Callable[[str], Awaitable[tuple[str | None, str | None]]]

from ..models.debate import (
    ConsensusMode,
    DebateConfig,
    DebateParticipant,
    DebateResult,
    DebateVote,
)
from ..models.decision import (
    ActionType,
    DecisionResponse,
    RiskControls,
    TradingDecision,
)
from .ai.factory import get_ai_client
from .ai.base import AIClientError, AIResponse
from .decision_parser import DecisionParser, DecisionParseError

logger = logging.getLogger(__name__)


class DebateEngine:
    """
    Engine for coordinating multi-model AI debates.

    Workflow:
    1. Send identical prompts to multiple AI models in parallel
    2. Parse each model's response into decisions
    3. Aggregate decisions using the configured consensus mode
    4. Return the final consensus decision

    Consensus Modes:
    - majority_vote: Most common action for each symbol wins
    - highest_confidence: Decision from model with highest confidence wins
    - weighted_average: Weight decisions by confidence scores
    - unanimous: All models must agree, else hold
    """

    def __init__(
        self,
        config: Optional[DebateConfig] = None,
        risk_controls: Optional[RiskControls] = None,
    ):
        """
        Initialize the debate engine.

        Args:
            config: Debate configuration
            risk_controls: Risk controls for decision validation
        """
        self.config = config or DebateConfig()
        self.risk_controls = risk_controls or RiskControls()
        self.decision_parser = DecisionParser(risk_controls=self.risk_controls)

    async def run_debate(
        self,
        system_prompt: str,
        user_prompt: str,
        model_ids: Optional[list[str]] = None,
        consensus_mode: Optional[ConsensusMode] = None,
        credentials_resolver: Optional[CredentialsResolver] = None,
    ) -> DebateResult:
        """
        Run a multi-model debate session.

        Args:
            system_prompt: System prompt for all models
            user_prompt: User prompt with market data
            model_ids: Override models (uses config.model_ids if not provided)
            consensus_mode: Override consensus mode
            credentials_resolver: Optional async resolver (model_id) -> (api_key, base_url) from DB

        Returns:
            DebateResult with aggregated decisions
        """
        models = model_ids or self.config.model_ids
        mode = consensus_mode or self.config.consensus_mode

        if len(models) < 2:
            raise ValueError("At least 2 models required for debate")

        logger.info(f"Starting debate with {len(models)} models: {models}")
        start_time = datetime.now(UTC)

        # 1. Generate responses from all models in parallel
        participants = await self._generate_parallel(
            models, system_prompt, user_prompt, credentials_resolver
        )

        # 2. Count successful/failed participants
        successful = [p for p in participants if p.succeeded]
        failed = [p for p in participants if not p.succeeded]

        logger.info(
            f"Debate responses: {len(successful)} successful, {len(failed)} failed"
        )

        # 3. Check minimum participants
        if len(successful) < self.config.min_participants:
            logger.warning(
                f"Not enough successful participants: {len(successful)} < {self.config.min_participants}"
            )
            return self._create_invalid_result(
                participants, mode, "Not enough successful model responses"
            )

        # 4. Aggregate votes
        votes = self._aggregate_votes(successful)

        # 5. Calculate agreement score
        agreement_score = self._calculate_agreement(successful)

        # 6. Determine final decisions based on consensus mode
        final_decisions, consensus_reasoning = self._apply_consensus(
            successful, votes, mode
        )

        # 7. Calculate final confidence
        final_confidence = self._calculate_final_confidence(
            successful, final_decisions, mode
        )

        # 8. Combine market assessments and reasoning
        combined_assessment = self._combine_market_assessments(successful)
        combined_reasoning = self._combine_chain_of_thought(
            successful, final_decisions, consensus_reasoning
        )

        total_latency = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

        result = DebateResult(
            participants=participants,
            successful_participants=len(successful),
            failed_participants=len(failed),
            consensus_mode=mode,
            min_participants=self.config.min_participants,
            votes=votes,
            agreement_score=agreement_score,
            final_decisions=final_decisions,
            final_confidence=final_confidence,
            consensus_reasoning=consensus_reasoning,
            combined_market_assessment=combined_assessment,
            combined_chain_of_thought=combined_reasoning,
            total_latency_ms=total_latency,
        )

        logger.info(
            f"Debate completed: agreement={agreement_score:.2f}, "
            f"decisions={len(final_decisions)}, confidence={final_confidence}"
        )

        return result

    async def _generate_parallel(
        self,
        model_ids: list[str],
        system_prompt: str,
        user_prompt: str,
        credentials_resolver: Optional[CredentialsResolver] = None,
    ) -> list[DebateParticipant]:
        """Generate responses from all models in parallel."""
        tasks = [
            self._generate_single(model_id, system_prompt, user_prompt, credentials_resolver)
            for model_id in model_ids
        ]

        participants = await asyncio.gather(*tasks, return_exceptions=False)
        return participants

    async def _generate_single(
        self,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        credentials_resolver: Optional[CredentialsResolver] = None,
    ) -> DebateParticipant:
        """Generate response from a single model."""
        start_time = datetime.now(UTC)

        try:
            # Get AI client (credentials from resolver when provided)
            if credentials_resolver:
                api_key, base_url = await credentials_resolver(model_id)
                kwargs = {"api_key": api_key or ""}
                if base_url:
                    kwargs["base_url"] = base_url
                client = get_ai_client(model_id, **kwargs)
            else:
                client = get_ai_client(model_id)

            # Generate response
            response: AIResponse = await asyncio.wait_for(
                client.generate(system_prompt, user_prompt),
                timeout=self.config.timeout_seconds
            )

            latency_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            # Parse response
            try:
                parsed: DecisionResponse = self.decision_parser.parse(response.content)
            except DecisionParseError as e:
                logger.warning(f"Failed to parse response from {model_id}: {e}")
                return DebateParticipant(
                    model_id=model_id,
                    raw_response=response.content,
                    latency_ms=latency_ms,
                    tokens_used=response.tokens_used,
                    error=f"Parse error: {e.message}"
                )

            return DebateParticipant(
                model_id=model_id,
                raw_response=response.content,
                chain_of_thought=parsed.chain_of_thought,
                market_assessment=parsed.market_assessment,
                decisions=parsed.decisions,
                overall_confidence=parsed.overall_confidence,
                latency_ms=latency_ms,
                tokens_used=response.tokens_used,
            )

        except asyncio.TimeoutError:
            latency_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            logger.warning(f"Timeout waiting for {model_id}")
            return DebateParticipant(
                model_id=model_id,
                latency_ms=latency_ms,
                error=f"Timeout after {self.config.timeout_seconds}s"
            )
        except AIClientError as e:
            latency_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            logger.warning(f"AI client error from {model_id}: {e}")
            return DebateParticipant(
                model_id=model_id,
                latency_ms=latency_ms,
                error=f"AI error: {e.message}"
            )
        except Exception as e:
            latency_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            logger.exception(f"Unexpected error from {model_id}")
            return DebateParticipant(
                model_id=model_id,
                latency_ms=latency_ms,
                error=f"Unexpected error: {str(e)}"
            )

    def _aggregate_votes(
        self,
        participants: list[DebateParticipant],
    ) -> list[DebateVote]:
        """Aggregate votes across all participants."""
        # Group by (symbol, action)
        vote_map: dict[tuple[str, ActionType], DebateVote] = {}

        for participant in participants:
            for decision in participant.decisions:
                key = (decision.symbol, decision.action)

                if key not in vote_map:
                    vote_map[key] = DebateVote(
                        symbol=decision.symbol,
                        action=decision.action,
                        vote_count=0,
                        total_confidence=0,
                        average_confidence=0,
                        voters=[],
                    )

                vote = vote_map[key]
                vote.vote_count += 1
                vote.total_confidence += decision.confidence
                vote.voters.append(participant.model_id)

        # Calculate averages
        votes = list(vote_map.values())
        for vote in votes:
            if vote.vote_count > 0:
                vote.average_confidence = vote.total_confidence / vote.vote_count

        # Sort by vote count, then confidence
        votes.sort(key=lambda v: (v.vote_count, v.average_confidence), reverse=True)

        return votes

    def _calculate_agreement(
        self,
        participants: list[DebateParticipant],
    ) -> float:
        """
        Calculate agreement score between participants.

        Returns a score from 0 to 1 indicating how much models agree.
        """
        if len(participants) < 2:
            return 1.0

        # Get all (symbol, action) pairs from each participant
        participant_votes: list[set[tuple[str, str]]] = []

        for p in participants:
            votes = set()
            for d in p.decisions:
                if d.action not in (ActionType.HOLD, ActionType.WAIT):
                    votes.add((d.symbol, d.action.value))
            participant_votes.append(votes)

        if not any(participant_votes):
            return 1.0  # All models said hold/wait

        # Calculate Jaccard similarity between all pairs
        similarities = []
        for i in range(len(participant_votes)):
            for j in range(i + 1, len(participant_votes)):
                set_a = participant_votes[i]
                set_b = participant_votes[j]

                if not set_a and not set_b:
                    similarity = 1.0
                elif not set_a or not set_b:
                    similarity = 0.0
                else:
                    intersection = len(set_a & set_b)
                    union = len(set_a | set_b)
                    similarity = intersection / union if union > 0 else 0.0

                similarities.append(similarity)

        return sum(similarities) / len(similarities) if similarities else 1.0

    def _apply_consensus(
        self,
        participants: list[DebateParticipant],
        votes: list[DebateVote],
        mode: ConsensusMode,
    ) -> tuple[list[TradingDecision], str]:
        """
        Apply consensus algorithm to determine final decisions.

        Returns:
            Tuple of (final_decisions, reasoning_explanation)
        """
        if mode == ConsensusMode.MAJORITY_VOTE:
            return self._consensus_majority_vote(participants, votes)
        elif mode == ConsensusMode.HIGHEST_CONFIDENCE:
            return self._consensus_highest_confidence(participants)
        elif mode == ConsensusMode.WEIGHTED_AVERAGE:
            return self._consensus_weighted_average(participants, votes)
        elif mode == ConsensusMode.UNANIMOUS:
            return self._consensus_unanimous(participants, votes)
        else:
            return self._consensus_majority_vote(participants, votes)

    def _consensus_majority_vote(
        self,
        participants: list[DebateParticipant],
        votes: list[DebateVote],
    ) -> tuple[list[TradingDecision], str]:
        """Majority vote: most common action for each symbol wins."""
        final_decisions = []
        reasoning_parts = ["Consensus by majority vote:"]

        # Group votes by symbol
        symbol_votes: dict[str, list[DebateVote]] = defaultdict(list)
        for vote in votes:
            symbol_votes[vote.symbol].append(vote)

        # For each symbol, pick the action with most votes
        for symbol, symbol_vote_list in symbol_votes.items():
            if not symbol_vote_list:
                continue

            # Get winning vote
            winning_vote = max(
                symbol_vote_list,
                key=lambda v: (v.vote_count, v.average_confidence)
            )

            # Only include if majority agrees (> 50%)
            total_votes = sum(v.vote_count for v in symbol_vote_list)
            if winning_vote.vote_count > total_votes / 2:
                # Find a representative decision from voters
                for p in participants:
                    for d in p.decisions:
                        if d.symbol == symbol and d.action == winning_vote.action:
                            # Clone decision with adjusted confidence
                            final_decision = d.model_copy()
                            final_decision.confidence = int(winning_vote.average_confidence)
                            final_decisions.append(final_decision)
                            reasoning_parts.append(
                                f"- {symbol} {winning_vote.action.value}: "
                                f"{winning_vote.vote_count}/{total_votes} votes "
                                f"(avg confidence: {winning_vote.average_confidence:.0f}%)"
                            )
                            break
                    else:
                        continue
                    break

        return final_decisions, "\n".join(reasoning_parts)

    def _consensus_highest_confidence(
        self,
        participants: list[DebateParticipant],
    ) -> tuple[list[TradingDecision], str]:
        """Highest confidence: participant with highest overall confidence wins."""
        if not participants:
            return [], "No participants"

        # Find participant with highest overall confidence
        winner = max(participants, key=lambda p: p.overall_confidence)

        reasoning = (
            f"Consensus by highest confidence: "
            f"{winner.model_id} with {winner.overall_confidence}% confidence"
        )

        return winner.decisions.copy(), reasoning

    def _consensus_weighted_average(
        self,
        participants: list[DebateParticipant],
        votes: list[DebateVote],
    ) -> tuple[list[TradingDecision], str]:
        """Weighted average: weight by confidence scores."""
        final_decisions = []
        reasoning_parts = ["Consensus by weighted confidence:"]

        # Group by symbol
        symbol_decisions: dict[str, list[tuple[TradingDecision, int]]] = defaultdict(list)

        for p in participants:
            weight = p.overall_confidence
            for d in p.decisions:
                symbol_decisions[d.symbol].append((d, weight))

        # For each symbol, pick action with highest weighted vote
        for symbol, decisions_weights in symbol_decisions.items():
            if not decisions_weights:
                continue

            # Group by action and sum weights
            action_weights: dict[ActionType, tuple[float, TradingDecision]] = {}
            for decision, weight in decisions_weights:
                if decision.action not in action_weights:
                    action_weights[decision.action] = (0, decision)

                current_weight, _ = action_weights[decision.action]
                weighted_conf = weight * decision.confidence / 100
                action_weights[decision.action] = (
                    current_weight + weighted_conf,
                    decision
                )

            # Pick highest weighted action
            if action_weights:
                best_action, (total_weight, best_decision) = max(
                    action_weights.items(),
                    key=lambda x: x[1][0]
                )

                if best_action not in (ActionType.HOLD, ActionType.WAIT):
                    final_decision = best_decision.model_copy()
                    final_decisions.append(final_decision)
                    reasoning_parts.append(
                        f"- {symbol} {best_action.value}: weighted score {total_weight:.1f}"
                    )

        return final_decisions, "\n".join(reasoning_parts)

    def _consensus_unanimous(
        self,
        participants: list[DebateParticipant],
        votes: list[DebateVote],
    ) -> tuple[list[TradingDecision], str]:
        """Unanimous: all models must agree, else hold."""
        final_decisions = []
        reasoning_parts = ["Consensus by unanimous agreement:"]

        num_participants = len(participants)

        for vote in votes:
            if vote.vote_count == num_participants:
                # All participants agree on this action
                for p in participants:
                    for d in p.decisions:
                        if d.symbol == vote.symbol and d.action == vote.action:
                            final_decision = d.model_copy()
                            final_decision.confidence = int(vote.average_confidence)
                            final_decisions.append(final_decision)
                            reasoning_parts.append(
                                f"- {vote.symbol} {vote.action.value}: "
                                f"unanimous ({num_participants}/{num_participants})"
                            )
                            break
                    else:
                        continue
                    break

        if not final_decisions:
            reasoning_parts.append("- No unanimous agreement reached, defaulting to hold")

        return final_decisions, "\n".join(reasoning_parts)

    def _calculate_final_confidence(
        self,
        participants: list[DebateParticipant],
        final_decisions: list[TradingDecision],
        mode: ConsensusMode,
    ) -> int:
        """Calculate final confidence for the consensus decision."""
        if not participants:
            return 0

        if mode == ConsensusMode.HIGHEST_CONFIDENCE:
            return max(p.overall_confidence for p in participants)

        if not final_decisions:
            return min(p.overall_confidence for p in participants)

        # Average confidence of final decisions
        decision_confs = [d.confidence for d in final_decisions]
        if decision_confs:
            return int(sum(decision_confs) / len(decision_confs))

        # Fallback to average of participant confidences
        return int(sum(p.overall_confidence for p in participants) / len(participants))

    def _combine_market_assessments(
        self,
        participants: list[DebateParticipant],
    ) -> str:
        """Combine market assessments from all participants."""
        parts = ["## Combined Market Assessment\n"]

        for p in participants:
            if p.market_assessment:
                parts.append(f"### {p.model_id}\n{p.market_assessment}\n")

        return "\n".join(parts)

    def _combine_chain_of_thought(
        self,
        participants: list[DebateParticipant],
        final_decisions: list[TradingDecision],
        consensus_reasoning: str,
    ) -> str:
        """Combine chain of thought with consensus explanation."""
        parts = [
            "## Multi-Model Debate Analysis\n",
            f"**Participants:** {', '.join(p.model_id for p in participants)}\n",
            f"**Successful:** {len([p for p in participants if p.succeeded])}\n\n",
            "### Consensus Result\n",
            consensus_reasoning,
            "\n\n### Individual Model Reasoning\n",
        ]

        for p in participants:
            if p.chain_of_thought:
                parts.append(f"#### {p.model_id} (confidence: {p.overall_confidence}%)\n")
                # Truncate if too long
                cot = p.chain_of_thought
                if len(cot) > 500:
                    cot = cot[:500] + "..."
                parts.append(f"{cot}\n\n")

        return "".join(parts)

    def _create_invalid_result(
        self,
        participants: list[DebateParticipant],
        mode: ConsensusMode,
        reason: str,
    ) -> DebateResult:
        """Create a result indicating debate failure."""
        return DebateResult(
            participants=participants,
            successful_participants=len([p for p in participants if p.succeeded]),
            failed_participants=len([p for p in participants if not p.succeeded]),
            consensus_mode=mode,
            min_participants=self.config.min_participants,
            votes=[],
            agreement_score=0.0,
            final_decisions=[],
            final_confidence=0,
            consensus_reasoning=f"Debate failed: {reason}",
            combined_market_assessment="",
            combined_chain_of_thought=f"Debate failed: {reason}",
            total_latency_ms=sum(p.latency_ms for p in participants),
        )


async def validate_debate_models(
    model_ids: list[str],
    credentials_resolver: Optional[CredentialsResolver] = None,
) -> dict[str, dict]:
    """
    Validate that all models in a debate configuration are accessible.

    Args:
        model_ids: List of full model IDs (provider:model_id)
        credentials_resolver: Optional async resolver (model_id) -> (api_key, base_url)

    Returns:
        Dict mapping model_id to validation result
    """
    results = {}

    for model_id in model_ids:
        try:
            if credentials_resolver:
                api_key, base_url = await credentials_resolver(model_id)
                kwargs = {"api_key": api_key or ""}
                if base_url:
                    kwargs["base_url"] = base_url
                client = get_ai_client(model_id, **kwargs)
            else:
                client = get_ai_client(model_id)
            success = await client.test_connection()
            results[model_id] = {
                "valid": success,
                "error": None if success else "Connection test failed"
            }
        except AIClientError as e:
            results[model_id] = {
                "valid": False,
                "error": e.message
            }
        except Exception as e:
            results[model_id] = {
                "valid": False,
                "error": str(e)
            }

    return results
