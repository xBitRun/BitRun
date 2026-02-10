"""
Tests for the Debate Engine service.

Covers:
- DebateEngine initialization
- run_debate() with all consensus modes
- Parallel model execution
- Model failure / parse error / timeout handling
- Vote aggregation, agreement score, consensus algorithms
- validate_debate_models() function
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.debate_engine import DebateEngine, validate_debate_models
from app.models.debate import (
    ConsensusMode,
    DebateConfig,
    DebateParticipant,
    DebateResult,
    DebateVote,
)
from app.models.decision import (
    ActionType,
    DecisionResponse,
    RiskControls,
    TradingDecision,
)
from app.services.ai.base import AIClientError, AIResponse, AIProvider
from app.services.decision_parser import DecisionParseError


# ── Helpers ──────────────────────────────────────────────────────────


def _decision(
    symbol="BTC",
    action=ActionType.OPEN_LONG,
    confidence=80,
    reasoning="Strong technical setup with bullish divergence",
):
    """Create a TradingDecision for testing."""
    return TradingDecision(
        symbol=symbol,
        action=action,
        confidence=confidence,
        reasoning=reasoning,
        leverage=5,
        position_size_usd=1000,
        risk_usd=100,
    )


def _participant(
    model_id="model-a",
    decisions=None,
    overall_confidence=80,
    error=None,
    chain_of_thought="Analysis reasoning",
    market_assessment="Bullish trend",
    latency_ms=500,
    tokens_used=100,
):
    """Create a DebateParticipant for testing."""
    return DebateParticipant(
        model_id=model_id,
        raw_response="raw response",
        chain_of_thought=chain_of_thought,
        market_assessment=market_assessment,
        decisions=decisions if decisions is not None else [],
        overall_confidence=overall_confidence,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        error=error,
    )


def _ai_response(content="test"):
    """Create an AIResponse for testing."""
    return AIResponse(
        content=content,
        model="test-model",
        provider=AIProvider.DEEPSEEK,
        tokens_used=100,
        input_tokens=50,
        output_tokens=50,
    )


def _decision_response(decisions=None, overall_confidence=80):
    """Create a DecisionResponse for testing."""
    return DecisionResponse(
        chain_of_thought="Test chain of thought",
        market_assessment="Test market assessment",
        decisions=decisions if decisions is not None else [],
        overall_confidence=overall_confidence,
    )


def _client_factory(model_content_map: dict):
    """Return a side_effect function for get_ai_client that maps model_id -> content."""

    def factory(model_id, **kwargs):
        c = AsyncMock()
        content = model_content_map[model_id]
        c.generate = AsyncMock(return_value=_ai_response(content))
        return c

    return factory


# ── Init ─────────────────────────────────────────────────────────────


class TestDebateEngineInit:
    """Tests for DebateEngine initialization."""

    def test_default_config(self):
        engine = DebateEngine()
        assert isinstance(engine.config, DebateConfig)
        assert isinstance(engine.risk_controls, RiskControls)
        assert engine.decision_parser is not None

    def test_custom_config(self):
        config = DebateConfig(
            model_ids=["a:b", "c:d"],
            consensus_mode=ConsensusMode.UNANIMOUS,
            min_participants=2,
            timeout_seconds=60,
        )
        risk = RiskControls(max_leverage=10, min_confidence=70)
        engine = DebateEngine(config=config, risk_controls=risk)

        assert engine.config.consensus_mode == ConsensusMode.UNANIMOUS
        assert engine.config.timeout_seconds == 60
        assert engine.risk_controls.max_leverage == 10
        assert engine.risk_controls.min_confidence == 70


# ── run_debate() ─────────────────────────────────────────────────────


class TestRunDebate:
    """Tests for DebateEngine.run_debate()."""

    @pytest.mark.asyncio
    async def test_rejects_single_model(self):
        engine = DebateEngine()
        with pytest.raises(ValueError, match="At least 2 models required"):
            await engine.run_debate("sys", "user", model_ids=["only:one"])

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_majority_vote(self, mock_get_client):
        """2/3 models vote OPEN_LONG → majority wins."""
        mock_get_client.side_effect = _client_factory(
            {"a:m1": "long", "a:m2": "long", "a:m3": "short"}
        )

        parsed = {
            "long": _decision_response(
                [_decision("BTC", ActionType.OPEN_LONG, 80)], 80
            ),
            "short": _decision_response(
                [_decision("BTC", ActionType.OPEN_SHORT, 70)], 70
            ),
        }

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(side_effect=lambda c: parsed[c])

        result = await engine.run_debate(
            "sys", "user",
            model_ids=["a:m1", "a:m2", "a:m3"],
            consensus_mode=ConsensusMode.MAJORITY_VOTE,
        )

        assert isinstance(result, DebateResult)
        assert result.successful_participants == 3
        assert result.consensus_mode == ConsensusMode.MAJORITY_VOTE
        assert len(result.final_decisions) >= 1
        assert result.final_decisions[0].action == ActionType.OPEN_LONG

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_highest_confidence(self, mock_get_client):
        """Model with highest overall_confidence wins."""
        mock_get_client.side_effect = _client_factory(
            {"a:m1": "a:m1", "a:m2": "a:m2"}
        )

        parsed = {
            "a:m1": _decision_response(
                [_decision("BTC", ActionType.OPEN_LONG, 60)], 60
            ),
            "a:m2": _decision_response(
                [_decision("BTC", ActionType.OPEN_SHORT, 95)], 95
            ),
        }

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(side_effect=lambda c: parsed[c])

        result = await engine.run_debate(
            "sys", "user",
            model_ids=["a:m1", "a:m2"],
            consensus_mode=ConsensusMode.HIGHEST_CONFIDENCE,
        )

        assert result.final_decisions[0].action == ActionType.OPEN_SHORT
        assert result.final_confidence == 95

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_weighted_average(self, mock_get_client):
        """Both models agree on OPEN_LONG via weighted consensus."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value=_ai_response("resp"))
        mock_get_client.return_value = mock_client

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(
            return_value=_decision_response(
                [_decision("BTC", ActionType.OPEN_LONG, 85)], 85
            )
        )

        result = await engine.run_debate(
            "sys", "user",
            model_ids=["a:m1", "a:m2"],
            consensus_mode=ConsensusMode.WEIGHTED_AVERAGE,
        )

        assert len(result.final_decisions) >= 1
        assert result.final_decisions[0].action == ActionType.OPEN_LONG

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_unanimous_all_agree(self, mock_get_client):
        """All models agree → unanimous decision."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value=_ai_response("resp"))
        mock_get_client.return_value = mock_client

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(
            return_value=_decision_response(
                [_decision("BTC", ActionType.OPEN_LONG, 85)], 85
            )
        )

        result = await engine.run_debate(
            "sys", "user",
            model_ids=["a:m1", "a:m2"],
            consensus_mode=ConsensusMode.UNANIMOUS,
        )

        assert len(result.final_decisions) >= 1
        assert result.final_decisions[0].action == ActionType.OPEN_LONG

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_unanimous_no_agreement(self, mock_get_client):
        """Models disagree → unanimous yields no decisions."""
        mock_get_client.side_effect = _client_factory(
            {"a:m1": "a:m1", "a:m2": "a:m2"}
        )

        parsed = {
            "a:m1": _decision_response(
                [_decision("BTC", ActionType.OPEN_LONG, 80)], 80
            ),
            "a:m2": _decision_response(
                [_decision("BTC", ActionType.OPEN_SHORT, 80)], 80
            ),
        }

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(side_effect=lambda c: parsed[c])

        result = await engine.run_debate(
            "sys", "user",
            model_ids=["a:m1", "a:m2"],
            consensus_mode=ConsensusMode.UNANIMOUS,
        )

        assert len(result.final_decisions) == 0

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_not_enough_successful_participants(self, mock_get_client):
        """All models fail → insufficient participants."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(
            side_effect=AIClientError("Connection failed")
        )
        mock_get_client.return_value = mock_client

        engine = DebateEngine(config=DebateConfig(min_participants=2))

        result = await engine.run_debate(
            "sys", "user", model_ids=["a:m1", "a:m2"]
        )

        assert result.successful_participants == 0
        assert result.failed_participants == 2
        assert len(result.final_decisions) == 0
        assert "Not enough" in result.consensus_reasoning

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_parse_error_marks_participant_failed(self, mock_get_client):
        """DecisionParseError → participant recorded with error."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value=_ai_response("bad"))
        mock_get_client.return_value = mock_client

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(
            side_effect=DecisionParseError("Invalid JSON")
        )

        result = await engine.run_debate(
            "sys", "user", model_ids=["a:m1", "a:m2"]
        )

        assert result.successful_participants == 0
        assert result.failed_participants == 2
        for p in result.participants:
            assert p.error is not None
            assert "Parse error" in p.error

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_timeout_handling(self, mock_get_client):
        """Timeout during generation → participant records timeout error."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_get_client.return_value = mock_client

        engine = DebateEngine()

        result = await engine.run_debate(
            "sys", "user", model_ids=["a:m1", "a:m2"]
        )

        assert result.failed_participants == 2
        for p in result.participants:
            assert "Timeout" in (p.error or "")

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_ai_client_error_handling(self, mock_get_client):
        """AIClientError → participant records AI error."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(
            side_effect=AIClientError("Rate limit exceeded")
        )
        mock_get_client.return_value = mock_client

        engine = DebateEngine()

        result = await engine.run_debate(
            "sys", "user", model_ids=["a:m1", "a:m2"]
        )

        assert result.failed_participants == 2
        for p in result.participants:
            assert "AI error" in (p.error or "")

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_unexpected_error_handling(self, mock_get_client):
        """Unexpected exception → participant records generic error."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(
            side_effect=RuntimeError("Something broke")
        )
        mock_get_client.return_value = mock_client

        engine = DebateEngine()

        result = await engine.run_debate(
            "sys", "user", model_ids=["a:m1", "a:m2"]
        )

        assert result.failed_participants == 2
        for p in result.participants:
            assert "Unexpected error" in (p.error or "")

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_all_models_called_in_parallel(self, mock_get_client):
        """All model IDs are invoked during a debate."""
        called_models = []

        def make_client(model_id, **kwargs):
            called_models.append(model_id)
            c = AsyncMock()
            c.generate = AsyncMock(return_value=_ai_response("resp"))
            return c

        mock_get_client.side_effect = make_client

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(
            return_value=_decision_response(
                [_decision("BTC", ActionType.HOLD, 50)], 50
            )
        )

        await engine.run_debate(
            "sys", "user", model_ids=["a:m1", "a:m2", "a:m3"]
        )

        assert sorted(called_models) == ["a:m1", "a:m2", "a:m3"]

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_credentials_resolver_used(self, mock_get_client):
        """credentials_resolver is called for each model."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value=_ai_response("resp"))
        mock_get_client.return_value = mock_client

        resolver = AsyncMock(return_value=("test-key", "https://api.example.com"))

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(
            return_value=_decision_response(
                [_decision("BTC", ActionType.HOLD, 50)], 50
            )
        )

        await engine.run_debate(
            "sys", "user",
            model_ids=["a:m1", "a:m2"],
            credentials_resolver=resolver,
        )

        assert resolver.call_count == 2

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_mixed_success_failure_below_threshold(self, mock_get_client):
        """1 success + 1 failure with min_participants=2 → invalid result."""

        def make_client(model_id, **kwargs):
            c = AsyncMock()
            if model_id == "a:m1":
                c.generate = AsyncMock(return_value=_ai_response("resp"))
            else:
                c.generate = AsyncMock(
                    side_effect=AIClientError("Failed")
                )
            return c

        mock_get_client.side_effect = make_client

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(
            return_value=_decision_response(
                [_decision("BTC", ActionType.OPEN_LONG, 80)], 80
            )
        )

        result = await engine.run_debate(
            "sys", "user", model_ids=["a:m1", "a:m2"]
        )

        assert result.successful_participants == 1
        assert result.failed_participants == 1
        assert "Not enough" in result.consensus_reasoning


# ── Vote Aggregation ─────────────────────────────────────────────────


class TestAggregateVotes:
    """Tests for DebateEngine._aggregate_votes()."""

    def test_basic_aggregation(self):
        engine = DebateEngine()
        p1 = _participant("m1", [_decision("BTC", ActionType.OPEN_LONG, 80)])
        p2 = _participant("m2", [_decision("BTC", ActionType.OPEN_LONG, 70)])

        votes = engine._aggregate_votes([p1, p2])

        assert len(votes) == 1
        assert votes[0].symbol == "BTC"
        assert votes[0].action == ActionType.OPEN_LONG
        assert votes[0].vote_count == 2
        assert votes[0].average_confidence == 75.0

    def test_multiple_symbols(self):
        engine = DebateEngine()
        p1 = _participant("m1", [
            _decision("BTC", ActionType.OPEN_LONG, 80),
            _decision("ETH", ActionType.OPEN_SHORT, 70),
        ])
        p2 = _participant("m2", [_decision("BTC", ActionType.OPEN_LONG, 90)])

        votes = engine._aggregate_votes([p1, p2])

        assert len(votes) == 2
        btc_vote = next(v for v in votes if v.symbol == "BTC")
        eth_vote = next(v for v in votes if v.symbol == "ETH")
        assert btc_vote.vote_count == 2
        assert eth_vote.vote_count == 1

    def test_sorted_by_count_then_confidence(self):
        engine = DebateEngine()
        p1 = _participant("m1", [_decision("BTC", ActionType.OPEN_LONG, 80)])
        p2 = _participant("m2", [_decision("BTC", ActionType.OPEN_LONG, 90)])
        p3 = _participant("m3", [_decision("ETH", ActionType.OPEN_SHORT, 95)])

        votes = engine._aggregate_votes([p1, p2, p3])

        assert votes[0].symbol == "BTC"
        assert votes[0].vote_count == 2
        assert votes[1].symbol == "ETH"
        assert votes[1].vote_count == 1


# ── Agreement Score ──────────────────────────────────────────────────


class TestCalculateAgreement:
    """Tests for DebateEngine._calculate_agreement()."""

    def test_perfect_agreement(self):
        engine = DebateEngine()
        p1 = _participant("m1", [_decision("BTC", ActionType.OPEN_LONG)])
        p2 = _participant("m2", [_decision("BTC", ActionType.OPEN_LONG)])

        assert engine._calculate_agreement([p1, p2]) == 1.0

    def test_complete_disagreement(self):
        engine = DebateEngine()
        p1 = _participant("m1", [_decision("BTC", ActionType.OPEN_LONG)])
        p2 = _participant("m2", [_decision("ETH", ActionType.OPEN_SHORT)])

        assert engine._calculate_agreement([p1, p2]) == 0.0

    def test_partial_agreement(self):
        engine = DebateEngine()
        p1 = _participant("m1", [
            _decision("BTC", ActionType.OPEN_LONG),
            _decision("ETH", ActionType.OPEN_SHORT),
        ])
        p2 = _participant("m2", [_decision("BTC", ActionType.OPEN_LONG)])

        # Jaccard: |{BTC_LONG}| / |{BTC_LONG, ETH_SHORT}| = 1/2
        assert engine._calculate_agreement([p1, p2]) == 0.5

    def test_all_hold_returns_perfect(self):
        """HOLD/WAIT filtered out → empty sets → 1.0."""
        engine = DebateEngine()
        p1 = _participant("m1", [_decision("BTC", ActionType.HOLD)])
        p2 = _participant("m2", [_decision("BTC", ActionType.WAIT)])

        assert engine._calculate_agreement([p1, p2]) == 1.0

    def test_single_participant(self):
        engine = DebateEngine()
        p1 = _participant("m1", [_decision("BTC", ActionType.OPEN_LONG)])

        assert engine._calculate_agreement([p1]) == 1.0


# ── Consensus Algorithms ─────────────────────────────────────────────


class TestConsensusAlgorithms:
    """Tests for individual consensus methods."""

    def test_majority_vote_picks_winner(self):
        engine = DebateEngine()
        p1 = _participant("m1", [_decision("BTC", ActionType.OPEN_LONG, 80)])
        p2 = _participant("m2", [_decision("BTC", ActionType.OPEN_LONG, 70)])
        p3 = _participant("m3", [_decision("BTC", ActionType.OPEN_SHORT, 60)])

        participants = [p1, p2, p3]
        votes = engine._aggregate_votes(participants)
        decisions, reasoning = engine._consensus_majority_vote(participants, votes)

        assert len(decisions) == 1
        assert decisions[0].action == ActionType.OPEN_LONG
        assert "majority" in reasoning.lower()

    def test_highest_confidence_picks_winner(self):
        engine = DebateEngine()
        p1 = _participant(
            "m1", [_decision("BTC", ActionType.OPEN_LONG, 60)],
            overall_confidence=60,
        )
        p2 = _participant(
            "m2", [_decision("BTC", ActionType.OPEN_SHORT, 95)],
            overall_confidence=95,
        )

        decisions, reasoning = engine._consensus_highest_confidence([p1, p2])

        assert decisions[0].action == ActionType.OPEN_SHORT
        assert "m2" in reasoning

    def test_unanimous_full_agreement(self):
        engine = DebateEngine()
        p1 = _participant("m1", [_decision("BTC", ActionType.OPEN_LONG, 80)])
        p2 = _participant("m2", [_decision("BTC", ActionType.OPEN_LONG, 70)])

        participants = [p1, p2]
        votes = engine._aggregate_votes(participants)
        decisions, reasoning = engine._consensus_unanimous(participants, votes)

        assert len(decisions) == 1
        assert decisions[0].action == ActionType.OPEN_LONG
        assert "unanimous" in reasoning.lower()


# ── Final Confidence ─────────────────────────────────────────────────


class TestFinalConfidence:
    """Tests for DebateEngine._calculate_final_confidence()."""

    def test_highest_confidence_mode_returns_max(self):
        engine = DebateEngine()
        p1 = _participant("m1", overall_confidence=60)
        p2 = _participant("m2", overall_confidence=90)

        conf = engine._calculate_final_confidence(
            [p1, p2], [_decision()], ConsensusMode.HIGHEST_CONFIDENCE
        )
        assert conf == 90

    def test_no_final_decisions_returns_min_participant_confidence(self):
        engine = DebateEngine()
        p1 = _participant("m1", overall_confidence=60)
        p2 = _participant("m2", overall_confidence=40)

        conf = engine._calculate_final_confidence(
            [p1, p2], [], ConsensusMode.MAJORITY_VOTE
        )
        assert conf == 40

    def test_averages_decision_confidences(self):
        engine = DebateEngine()
        p1 = _participant("m1", overall_confidence=80)
        decisions = [_decision(confidence=70), _decision(confidence=90)]

        conf = engine._calculate_final_confidence(
            [p1], decisions, ConsensusMode.MAJORITY_VOTE
        )
        assert conf == 80  # (70 + 90) / 2

    def test_no_participants_returns_zero(self):
        engine = DebateEngine()
        conf = engine._calculate_final_confidence(
            [], [], ConsensusMode.MAJORITY_VOTE
        )
        assert conf == 0


# ── validate_debate_models() ─────────────────────────────────────────


class TestValidateDebateModels:
    """Tests for the validate_debate_models() module function."""

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_all_valid(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_get_client.return_value = mock_client

        results = await validate_debate_models(["a:m1", "a:m2"])

        assert results["a:m1"]["valid"] is True
        assert results["a:m2"]["valid"] is True

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_some_invalid(self, mock_get_client):
        def make_client(model_id, **kwargs):
            c = AsyncMock()
            if model_id == "a:m1":
                c.test_connection = AsyncMock(return_value=True)
            else:
                c.test_connection = AsyncMock(
                    side_effect=AIClientError("Auth failed")
                )
            return c

        mock_get_client.side_effect = make_client

        results = await validate_debate_models(["a:m1", "a:m2"])

        assert results["a:m1"]["valid"] is True
        assert results["a:m2"]["valid"] is False
        assert "Auth failed" in results["a:m2"]["error"]

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_with_credentials_resolver(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_get_client.return_value = mock_client

        resolver = AsyncMock(return_value=("api-key", "https://api.example.com"))

        results = await validate_debate_models(
            ["a:m1", "a:m2"], credentials_resolver=resolver
        )

        assert resolver.call_count == 2
        assert all(r["valid"] for r in results.values())

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_non_ai_client_error(self, mock_get_client):
        """Non-AIClientError exception (e.g. RuntimeError) → valid=False with error string."""
        mock_get_client.side_effect = RuntimeError("Unexpected crash in factory")

        results = await validate_debate_models(["a:m1"])

        assert results["a:m1"]["valid"] is False
        assert "Unexpected crash" in results["a:m1"]["error"]


# ── Dirty Data: empty / malformed model responses ────────────────────


class TestDirtyDataScenarios:
    """Tests for AI returning empty or malformed data in debate."""

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_model_returns_empty_decisions(self, mock_get_client):
        """All models return valid JSON but with empty decisions array."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value=_ai_response("resp"))
        mock_get_client.return_value = mock_client

        engine = DebateEngine()
        engine.decision_parser.parse = MagicMock(
            return_value=_decision_response(decisions=[], overall_confidence=40)
        )

        result = await engine.run_debate(
            "sys", "user", model_ids=["a:m1", "a:m2"]
        )

        # Both models succeed (no error) but have empty decisions
        # → succeeded because parse succeeded and decisions list is present
        assert result.successful_participants == 0  # succeeded requires decisions
        assert len(result.final_decisions) == 0

    @pytest.mark.asyncio
    @patch("app.services.debate_engine.get_ai_client")
    async def test_model_returns_malformed_response(self, mock_get_client):
        """Model returns something that causes DecisionParseError."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(
            return_value=_ai_response("completely invalid garbage {{{{}")
        )
        mock_get_client.return_value = mock_client

        engine = DebateEngine()
        # Use real parser — it will fail on this garbage
        result = await engine.run_debate(
            "sys", "user", model_ids=["a:m1", "a:m2"]
        )

        assert result.successful_participants == 0
        assert result.failed_participants == 2
        for p in result.participants:
            assert p.error is not None
            assert "Parse error" in p.error
