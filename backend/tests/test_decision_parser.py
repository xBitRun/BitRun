"""
Tests for the decision parser service.

Covers:
- JSON extraction from various formats
- Weak assertion fixes (leverage clamping, confidence filtering)
- Exception path coverage (ValueError, KeyError, ValidationError)
- Dirty data scenarios (AI returns unexpected values)
- Integration layer validation (clamp, default, transform)
"""

import json

import pytest
from pydantic import ValidationError

from app.services.decision_parser import DecisionParser, DecisionParseError
from app.models.decision import RiskControls, ActionType


class TestDecisionParser:
    """Tests for DecisionParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DecisionParser()

    # ------------------------------------------------------------------ #
    # Happy-path parsing
    # ------------------------------------------------------------------ #

    def test_parse_valid_json_response(self, sample_decision_response):
        """Test parsing a valid JSON decision response."""
        raw_response = json.dumps(sample_decision_response)

        result = self.parser.parse(raw_response)

        assert result is not None
        assert result.chain_of_thought == "Market shows bullish momentum..."
        assert result.overall_confidence == 75
        assert len(result.decisions) == 1

        decision = result.decisions[0]
        assert decision.symbol == "BTC"
        assert decision.action == ActionType.OPEN_LONG
        assert decision.leverage == 5
        assert decision.confidence == 75

    def test_parse_response_with_code_block(self, sample_decision_response):
        """Test parsing response wrapped in markdown code block."""
        raw_response = f"```json\n{json.dumps(sample_decision_response)}\n```"

        result = self.parser.parse(raw_response)

        assert result is not None
        assert len(result.decisions) == 1
        assert result.decisions[0].symbol == "BTC"

    def test_parse_hold_decision(self):
        """Test parsing a hold decision."""
        response = {
            "chain_of_thought": "Market is uncertain",
            "market_assessment": "Sideways movement",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "hold",
                    "leverage": 1,
                    "position_size_usd": 0,
                    "confidence": 60,
                    "risk_usd": 0,
                    "reasoning": "Wait for clearer signal"
                }
            ],
            "overall_confidence": 60
        }

        result = self.parser.parse(json.dumps(response))

        assert result.decisions[0].action == ActionType.HOLD
        assert result.decisions[0].position_size_usd == 0
        assert result.decisions[0].leverage == 1

    def test_parse_multiple_decisions(self):
        """Test parsing multiple trading decisions."""
        response = {
            "chain_of_thought": "Diversified approach",
            "market_assessment": "Mixed signals",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "open_long",
                    "leverage": 3,
                    "position_size_usd": 500,
                    "confidence": 70,
                    "risk_usd": 50,
                    "reasoning": "Bullish on BTC"
                },
                {
                    "symbol": "ETH",
                    "action": "open_short",
                    "leverage": 2,
                    "position_size_usd": 300,
                    "confidence": 65,
                    "risk_usd": 30,
                    "reasoning": "Bearish on ETH"
                }
            ],
            "overall_confidence": 67
        }

        result = self.parser.parse(json.dumps(response))

        assert len(result.decisions) == 2
        assert result.decisions[0].symbol == "BTC"
        assert result.decisions[1].symbol == "ETH"
        assert result.decisions[0].action == ActionType.OPEN_LONG
        assert result.decisions[1].action == ActionType.OPEN_SHORT

    def test_extract_json_from_text(self):
        """Test extracting JSON from text with surrounding content."""
        text_with_json = '''
        Here is my analysis:

        ```json
        {"chain_of_thought": "test", "market_assessment": "test", "decisions": [], "overall_confidence": 50}
        ```

        Let me know if you need more details.
        '''

        result = self.parser.parse(text_with_json)

        assert result.chain_of_thought == "test"
        assert result.decisions == []

    # ------------------------------------------------------------------ #
    # Error handling: empty / invalid input
    # ------------------------------------------------------------------ #

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises DecisionParseError."""
        with pytest.raises(DecisionParseError) as exc_info:
            self.parser.parse("This is not valid JSON")
        assert "No valid JSON found" in str(exc_info.value)

    def test_parse_empty_response(self):
        """Test parsing empty response raises DecisionParseError."""
        with pytest.raises(DecisionParseError) as exc_info:
            self.parser.parse("")
        assert "Empty response" in str(exc_info.value)

        with pytest.raises((DecisionParseError, TypeError)):
            self.parser.parse(None)

    # ------------------------------------------------------------------ #
    # Risk controls: leverage clamping (weak assertion FIX)
    # ------------------------------------------------------------------ #

    def test_risk_controls_max_leverage(self, sample_decision_response):
        """Test that risk controls clamp leverage to max_leverage."""
        parser = DecisionParser(
            risk_controls=RiskControls(max_leverage=3)
        )
        raw_response = json.dumps(sample_decision_response)
        result = parser.parse(raw_response)

        assert result is not None
        assert len(result.decisions) == 1
        # Response has leverage=5, max_leverage=3 → must be clamped to 3
        assert result.decisions[0].leverage == 3

    # ------------------------------------------------------------------ #
    # Risk controls: confidence filtering (weak assertion FIX)
    # ------------------------------------------------------------------ #

    def test_risk_controls_min_confidence_filters(self, sample_decision_response):
        """Test that should_execute filters decisions below min_confidence."""
        parser = DecisionParser(
            risk_controls=RiskControls(min_confidence=80)
        )
        raw_response = json.dumps(sample_decision_response)
        result = parser.parse(raw_response)

        assert result is not None
        # Decision has confidence=75, min_confidence=80 → should NOT execute
        decision = result.decisions[0]
        should_exec, reason = parser.should_execute(decision)
        assert should_exec is False
        assert "below threshold" in reason

    # ------------------------------------------------------------------ #
    # Exception path: ValueError (invalid ActionType)
    # ------------------------------------------------------------------ #

    def test_invalid_action_type_skipped(self):
        """ValueError when ActionType('invalid') fails — decision is skipped."""
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "invalid_action",
                    "leverage": 5,
                    "confidence": 80,
                    "reasoning": "This should be skipped due to invalid action",
                }
            ],
            "overall_confidence": 50
        }

        result = self.parser.parse(json.dumps(response))
        # Invalid decision is silently skipped
        assert len(result.decisions) == 0

    # ------------------------------------------------------------------ #
    # Exception path: ValidationError (leverage > 50 passes int() but
    # fails Pydantic ge/le)
    # ------------------------------------------------------------------ #

    def test_validation_error_skipped(self):
        """ValidationError when leverage=100 exceeds le=50 — decision skipped."""
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "open_long",
                    "leverage": 100,
                    "confidence": 80,
                    "reasoning": "This should be skipped due to validation error",
                }
            ],
            "overall_confidence": 50
        }

        result = self.parser.parse(json.dumps(response))
        assert len(result.decisions) == 0

    # ------------------------------------------------------------------ #
    # Exception path: mixed valid and invalid decisions
    # ------------------------------------------------------------------ #

    def test_mixed_valid_invalid_decisions(self):
        """Valid decisions survive while invalid ones are skipped."""
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "open_long",
                    "leverage": 5,
                    "confidence": 80,
                    "reasoning": "Valid decision for testing purposes",
                },
                {
                    "symbol": "ETH",
                    "action": "bad_action",
                    "leverage": 5,
                    "confidence": 80,
                    "reasoning": "Invalid action will be skipped here",
                },
                {
                    "symbol": "SOL",
                    "action": "open_short",
                    "leverage": 200,
                    "confidence": 80,
                    "reasoning": "Leverage too high will be skipped here",
                },
            ],
            "overall_confidence": 50
        }

        result = self.parser.parse(json.dumps(response))
        assert len(result.decisions) == 1
        assert result.decisions[0].symbol == "BTC"

    # ------------------------------------------------------------------ #
    # Dirty data: leverage=0 for hold (REGRESSION TEST for the bug fix)
    # ------------------------------------------------------------------ #

    def test_hold_with_leverage_zero(self):
        """
        Regression test: AI returns leverage=0 for hold decisions.
        Parser must clamp leverage to 1 to satisfy ge=1 constraint.
        """
        response = {
            "chain_of_thought": "Market is uncertain",
            "market_assessment": "Sideways",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "hold",
                    "leverage": 0,
                    "position_size_usd": 0,
                    "confidence": 60,
                    "risk_usd": 0,
                    "reasoning": "Wait for clearer signal before entering",
                }
            ],
            "overall_confidence": 60
        }

        result = self.parser.parse(json.dumps(response))
        assert len(result.decisions) == 1
        assert result.decisions[0].action == ActionType.HOLD
        assert result.decisions[0].leverage == 1  # clamped from 0

    def test_wait_with_negative_leverage(self):
        """AI returns leverage=-1 for wait decisions — clamped to 1."""
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "ETH",
                    "action": "wait",
                    "leverage": -1,
                    "confidence": 50,
                    "reasoning": "Negative leverage should be clamped to one",
                }
            ],
            "overall_confidence": 50
        }

        result = self.parser.parse(json.dumps(response))
        assert len(result.decisions) == 1
        assert result.decisions[0].leverage == 1

    # ------------------------------------------------------------------ #
    # Dirty data: missing / wrong-type fields
    # ------------------------------------------------------------------ #

    def test_missing_confidence_uses_default(self):
        """AI omits confidence field — parser uses default 50."""
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "hold",
                    "reasoning": "No confidence field in this response",
                }
            ],
            "overall_confidence": 50
        }

        result = self.parser.parse(json.dumps(response))
        assert len(result.decisions) == 1
        assert result.decisions[0].confidence == 50

    def test_confidence_as_string_causes_skip(self):
        """AI returns confidence as non-numeric string — ValueError, decision skipped."""
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "hold",
                    "confidence": "high",
                    "reasoning": "String confidence should trigger ValueError",
                }
            ],
            "overall_confidence": 50
        }

        result = self.parser.parse(json.dumps(response))
        # int("high") raises ValueError → decision skipped
        assert len(result.decisions) == 0

    def test_null_symbol_crashes_unhandled(self):
        """
        AI returns symbol=null — d.get("symbol","").upper() receives None
        (because key exists with value None, so default "" is NOT used),
        causing AttributeError which is NOT caught by (ValueError, KeyError,
        ValidationError). This is a known gap.
        """
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": None,
                    "action": "hold",
                    "confidence": 50,
                    "reasoning": "Null symbol test for edge case handling",
                }
            ],
            "overall_confidence": 50
        }

        # This reveals a real bug: AttributeError is not caught
        with pytest.raises(AttributeError):
            self.parser.parse(json.dumps(response))

    def test_extra_unknown_fields_ignored(self):
        """AI returns extra fields — they are silently ignored."""
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "hold",
                    "leverage": 1,
                    "confidence": 60,
                    "reasoning": "Extra fields are ignored by the parser",
                    "moon_phase": "full",
                    "sentiment_score": 9.5,
                }
            ],
            "overall_confidence": 50
        }

        result = self.parser.parse(json.dumps(response))
        assert len(result.decisions) == 1
        assert result.decisions[0].symbol == "BTC"

    # ------------------------------------------------------------------ #
    # Integration layer: leverage clamp behavior
    # ------------------------------------------------------------------ #

    def test_parser_clamps_leverage_before_model_validation(self):
        """
        Parser clamps leverage < 1 to 1 BEFORE creating TradingDecision,
        so Pydantic's ge=1 never fires for this case.
        """
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "open_long",
                    "leverage": 0,
                    "confidence": 80,
                    "position_size_usd": 100,
                    "reasoning": "Leverage zero clamped to one by parser",
                }
            ],
            "overall_confidence": 50
        }

        result = self.parser.parse(json.dumps(response))
        assert len(result.decisions) == 1
        assert result.decisions[0].leverage == 1

    # ------------------------------------------------------------------ #
    # Integration layer: _extract_json malformed code block
    # ------------------------------------------------------------------ #

    def test_extract_json_malformed_code_block(self):
        """Malformed JSON inside code block — parse should fail gracefully."""
        text = '```json\n{"chain_of_thought": "test", "decisions": [INVALID\n```'

        with pytest.raises(DecisionParseError):
            self.parser.parse(text)

    # ------------------------------------------------------------------ #
    # should_execute validation
    # ------------------------------------------------------------------ #

    def test_should_execute_hold_action(self):
        """Hold/wait actions should never execute."""
        from app.models.decision import TradingDecision
        decision = TradingDecision(
            symbol="BTC", action=ActionType.HOLD, confidence=99,
            reasoning="Hold action should never execute regardless",
        )
        should, reason = self.parser.should_execute(decision)
        assert should is False
        assert "hold/wait" in reason

    def test_should_execute_zero_position_size(self):
        """Open action with zero position size should not execute."""
        from app.models.decision import TradingDecision
        decision = TradingDecision(
            symbol="BTC", action=ActionType.OPEN_LONG, confidence=99,
            position_size_usd=0,
            reasoning="Zero position size should not be executed",
        )
        should, reason = self.parser.should_execute(decision)
        assert should is False
        assert "zero" in reason.lower()

    def test_should_execute_passes(self):
        """Valid open action with sufficient confidence should execute."""
        from app.models.decision import TradingDecision
        decision = TradingDecision(
            symbol="BTC", action=ActionType.OPEN_LONG, confidence=80,
            position_size_usd=100,
            reasoning="Valid decision that should be executed normally",
        )
        should, reason = self.parser.should_execute(decision)
        assert should is True

    # ------------------------------------------------------------------ #
    # Empty decisions array
    # ------------------------------------------------------------------ #

    def test_empty_decisions_array(self):
        """AI returns valid JSON with empty decisions array."""
        response = {
            "chain_of_thought": "No opportunities",
            "market_assessment": "Flat market",
            "decisions": [],
            "overall_confidence": 30
        }

        result = self.parser.parse(json.dumps(response))
        assert result.decisions == []
        assert result.overall_confidence == 30

    # ------------------------------------------------------------------ #
    # Chinese encoding fixes
    # ------------------------------------------------------------------ #

    def test_chinese_encoding_fixes(self):
        """AI uses Chinese colons/commas — parser fixes encoding."""
        # Use Chinese full-width colon (\uff1a) and comma (\uff0c)
        raw = (
            '{"chain_of_thought"\uff1a "test"\uff0c '
            '"market_assessment": "ok"\uff0c '
            '"decisions": []\uff0c '
            '"overall_confidence": 50}'
        )

        result = self.parser.parse(raw)
        assert result.chain_of_thought == "test"
        assert result.overall_confidence == 50
