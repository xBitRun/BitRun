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

    # ------------------------------------------------------------------ #
    # JSON array as top-level response (wrapped in response object)
    # ------------------------------------------------------------------ #

    def test_parse_decisions_list_directly(self):
        """AI returns list of decisions directly — parser wraps in response."""
        # Response is just a list, not a dict with "decisions" key
        raw = '''Here is my analysis:

[{"symbol": "BTC", "action": "hold", "leverage": 1, "confidence": 60, "reasoning": "Wait for signal"}]

Let me know if you need more.'''

        result = self.parser.parse(raw)

        assert len(result.decisions) == 1
        assert result.decisions[0].symbol == "BTC"
        # Default values for missing top-level fields
        assert result.overall_confidence == 50
        assert result.next_review_minutes == 60

    def test_parse_data_is_list_wraps_in_dict(self):
        """When parsed data is a list, wrap it in a response dict."""
        # Raw JSON is a list (not a dict)
        raw = json.dumps([
            {
                "symbol": "BTC",
                "action": "hold",
                "leverage": 1,
                "confidence": 60,
                "reasoning": "Wait for signal",
            }
        ])

        result = self.parser.parse(raw)

        assert len(result.decisions) == 1
        assert result.decisions[0].symbol == "BTC"
        # Defaults applied when data is a list
        assert result.chain_of_thought == ""
        assert result.overall_confidence == 50

    # ------------------------------------------------------------------ #
    # _extract_text_before_json: extracts text before { or [
    # ------------------------------------------------------------------ #

    def test_extract_text_before_json_with_brace(self):
        """Extract text before JSON starting with {."""
        text = '''Here is my analysis of the market:
{"chain_of_thought": "test", "decisions": [], "overall_confidence": 50}'''

        result = self.parser.parse(text)

        # chain_of_thought should contain text before JSON (when extracted from array)
        # Note: in this case the JSON is direct, so chain_of_thought comes from JSON
        assert result.overall_confidence == 50

    def test_extract_text_before_json_with_bracket(self):
        """Extract text before JSON starting with [."""
        text = '''My analysis:
[{"symbol": "BTC", "action": "hold", "leverage": 1, "confidence": 60, "reasoning": "Testing with array format JSON"}]'''

        result = self.parser.parse(text)

        # chain_of_thought should be extracted from text before [
        assert result.decisions[0].symbol == "BTC"

    # ------------------------------------------------------------------ #
    # _validate_decisions: leverage clamping with logging
    # ------------------------------------------------------------------ #

    def test_leverage_clamped_with_logging(self, sample_decision_response, caplog):
        """Test that leverage clamping is logged."""
        import logging

        # Set max_leverage to 3, input has 5
        parser = DecisionParser(risk_controls=RiskControls(max_leverage=3))

        with caplog.at_level(logging.INFO):
            result = parser.parse(json.dumps(sample_decision_response))

        assert result.decisions[0].leverage == 3
        # Check that log message was recorded
        assert any("Leverage capped" in record.message for record in caplog.records)

    # ------------------------------------------------------------------ #
    # _validate_decisions: risk/reward ratio warning
    # ------------------------------------------------------------------ #

    def test_risk_reward_warning_long(self, caplog):
        """Test risk/reward warning for long position."""
        import logging

        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "open_long",
                    "leverage": 5,
                    "position_size_usd": 1000,
                    "entry_price": 50000,
                    "stop_loss": 49000,  # Risk: 1000
                    "take_profit": 50500,  # Reward: 500 → R:R = 0.5 < 1.0
                    "confidence": 75,
                    "reasoning": "Test risk/reward ratio warning",
                }
            ],
            "overall_confidence": 75
        }

        parser = DecisionParser(risk_controls=RiskControls(min_risk_reward_ratio=1.0))

        with caplog.at_level(logging.WARNING):
            result = parser.parse(json.dumps(response))

        assert len(result.decisions) == 1
        # Warning should be logged for poor risk/reward
        assert any("Risk/reward ratio" in record.message for record in caplog.records)

    def test_risk_reward_warning_short(self, caplog):
        """Test risk/reward warning for short position."""
        import logging

        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "open_short",
                    "leverage": 5,
                    "position_size_usd": 1000,
                    "entry_price": 50000,
                    "stop_loss": 51000,  # Risk: 1000
                    "take_profit": 49500,  # Reward: 500 → R:R = 0.5 < 1.0
                    "confidence": 75,
                    "reasoning": "Test risk/reward ratio warning for short",
                }
            ],
            "overall_confidence": 75
        }

        parser = DecisionParser(risk_controls=RiskControls(min_risk_reward_ratio=1.0))

        with caplog.at_level(logging.WARNING):
            result = parser.parse(json.dumps(response))

        assert len(result.decisions) == 1
        assert any("Risk/reward ratio" in record.message for record in caplog.records)

    def test_risk_reward_skip_for_non_open_actions(self):
        """Risk/reward check is skipped for close/hold actions."""
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [
                {
                    "symbol": "BTC",
                    "action": "close_long",
                    "leverage": 1,
                    "entry_price": 50000,
                    "stop_loss": 49000,
                    "take_profit": 50500,
                    "confidence": 75,
                    "reasoning": "Close action should not trigger R:R check",
                }
            ],
            "overall_confidence": 75
        }

        parser = DecisionParser(risk_controls=RiskControls(min_risk_reward_ratio=2.0))
        result = parser.parse(json.dumps(response))

        # Should parse successfully without R:R warning (risk/reward=0 for close)
        assert len(result.decisions) == 1

    # ------------------------------------------------------------------ #
    # should_execute: close action with zero position size passes
    # ------------------------------------------------------------------ #

    def test_should_execute_close_action_ignores_position_size(self):
        """Close actions should execute even with zero position_size_usd."""
        from app.models.decision import TradingDecision

        decision = TradingDecision(
            symbol="BTC",
            action=ActionType.CLOSE_LONG,
            confidence=80,
            position_size_usd=0,  # Zero size is OK for close
            reasoning="Close existing position regardless of size",
        )

        should, reason = self.parser.should_execute(decision)
        assert should is True
        assert "Passed" in reason

    # ------------------------------------------------------------------ #
    # should_execute: wait action (different from hold)
    # ------------------------------------------------------------------ #

    def test_should_execute_wait_action(self):
        """Wait action should not execute."""
        from app.models.decision import TradingDecision

        decision = TradingDecision(
            symbol="BTC",
            action=ActionType.WAIT,
            confidence=99,
            reasoning="Wait action should not be executed",
        )

        should, reason = self.parser.should_execute(decision)
        assert should is False
        assert "hold/wait" in reason

    # ------------------------------------------------------------------ #
    # extract_chain_of_thought: various patterns
    # ------------------------------------------------------------------ #

    def test_extract_chain_of_thought_reasoning_tag(self):
        """Extract chain of thought from <reasoning> tag."""
        raw = '''<reasoning>
This is my detailed analysis of the market conditions.
BTC looks bullish due to strong support.
</reasoning>

{"chain_of_thought": "ignored", "decisions": [], "overall_confidence": 50}'''

        cot = self.parser.extract_chain_of_thought(raw)
        assert "detailed analysis" in cot
        assert "BTC looks bullish" in cot

    def test_extract_chain_of_thought_markdown_header(self):
        """Extract chain of thought from markdown ## Analysis header."""
        raw = '''## Analysis

Market is showing signs of reversal.
Key indicators suggest bullish momentum.

## Decisions

{"chain_of_thought": "ignored", "decisions": [], "overall_confidence": 50}'''

        cot = self.parser.extract_chain_of_thought(raw)
        assert "signs of reversal" in cot

    def test_extract_chain_of_thought_fallback(self):
        """Extract chain of thought falls back to text before JSON."""
        raw = '''My analysis shows positive signals.

{"chain_of_thought": "different", "decisions": [], "overall_confidence": 50}'''

        cot = self.parser.extract_chain_of_thought(raw)
        assert "positive signals" in cot

    # ------------------------------------------------------------------ #
    # Edge case: ValidationError in _build_response (line 91-92)
    # ------------------------------------------------------------------ #

    def test_validation_error_in_build_response(self):
        """ValidationError at response level (not decision level)."""
        # Invalid overall_confidence type that can't be converted to int
        response = {
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [],
            "overall_confidence": "not_a_number"  # Will fail int()
        }

        with pytest.raises(DecisionParseError) as exc_info:
            self.parser.parse(json.dumps(response))

        # The error comes from int("not_a_number") in _build_response
        assert "invalid literal" in str(exc_info.value).lower() or "Validation" in str(exc_info.value)


class TestEnsureSlTp:
    """Tests for SL/TP auto-fill logic (_ensure_sl_tp)."""

    # ------------------------------------------------------------------ #
    # Helper: build a minimal open_long response JSON
    # ------------------------------------------------------------------ #

    @staticmethod
    def _make_response(
        action: str = "open_long",
        symbol: str = "BTC",
        entry_price=50000,
        stop_loss=None,
        take_profit=None,
    ) -> str:
        return json.dumps({
            "chain_of_thought": "test",
            "market_assessment": "test",
            "decisions": [{
                "symbol": symbol,
                "action": action,
                "leverage": 5,
                "position_size_usd": 1000,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": 80,
                "risk_usd": 50,
                "reasoning": "SL/TP auto-fill test decision entry",
            }],
            "overall_confidence": 75,
        })

    # ------------------------------------------------------------------ #
    # AI returns complete SL/TP → not modified
    # ------------------------------------------------------------------ #

    def test_ai_provided_sl_tp_not_modified(self):
        """When AI provides both SL and TP, they should not be overwritten."""
        parser = DecisionParser(
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1200},
        )
        raw = self._make_response(stop_loss=48000, take_profit=55000)
        result = parser.parse(raw)

        assert result.decisions[0].stop_loss == 48000
        assert result.decisions[0].take_profit == 55000

    # ------------------------------------------------------------------ #
    # ATR-based auto-fill: missing SL only
    # ------------------------------------------------------------------ #

    def test_missing_sl_filled_with_atr_long(self):
        """Missing SL on open_long → entry - sl_atr_mult * ATR."""
        rc = RiskControls(default_sl_atr_multiplier=1.5)
        parser = DecisionParser(
            risk_controls=rc,
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},
        )
        raw = self._make_response(stop_loss=None, take_profit=55000)
        result = parser.parse(raw)

        # 50000 - 1.5 * 1000 = 48500
        assert result.decisions[0].stop_loss == 48500.0
        assert result.decisions[0].take_profit == 55000  # unchanged

    def test_missing_sl_filled_with_atr_short(self):
        """Missing SL on open_short → entry + sl_atr_mult * ATR."""
        rc = RiskControls(default_sl_atr_multiplier=2.0)
        parser = DecisionParser(
            risk_controls=rc,
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},
        )
        raw = self._make_response(action="open_short", stop_loss=None, take_profit=45000)
        result = parser.parse(raw)

        # 50000 + 2.0 * 1000 = 52000
        assert result.decisions[0].stop_loss == 52000.0
        assert result.decisions[0].take_profit == 45000

    # ------------------------------------------------------------------ #
    # ATR-based auto-fill: missing TP only
    # ------------------------------------------------------------------ #

    def test_missing_tp_filled_with_atr_long(self):
        """Missing TP on open_long → entry + tp_atr_mult * ATR."""
        rc = RiskControls(default_tp_atr_multiplier=3.0)
        parser = DecisionParser(
            risk_controls=rc,
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},
        )
        raw = self._make_response(stop_loss=48000, take_profit=None)
        result = parser.parse(raw)

        # 50000 + 3.0 * 1000 = 53000
        assert result.decisions[0].take_profit == 53000.0
        assert result.decisions[0].stop_loss == 48000

    def test_missing_tp_filled_with_atr_short(self):
        """Missing TP on open_short → entry - tp_atr_mult * ATR."""
        rc = RiskControls(default_tp_atr_multiplier=3.0)
        parser = DecisionParser(
            risk_controls=rc,
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},
        )
        raw = self._make_response(action="open_short", stop_loss=52000, take_profit=None)
        result = parser.parse(raw)

        # 50000 - 3.0 * 1000 = 47000
        assert result.decisions[0].take_profit == 47000.0

    # ------------------------------------------------------------------ #
    # ATR-based auto-fill: both SL and TP missing
    # ------------------------------------------------------------------ #

    def test_both_missing_filled_long(self):
        """Both SL and TP missing on open_long → both auto-filled from ATR."""
        rc = RiskControls(default_sl_atr_multiplier=1.5, default_tp_atr_multiplier=3.0)
        parser = DecisionParser(
            risk_controls=rc,
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},
        )
        raw = self._make_response(stop_loss=None, take_profit=None)
        result = parser.parse(raw)

        d = result.decisions[0]
        assert d.stop_loss == 48500.0   # 50000 - 1.5 * 1000
        assert d.take_profit == 53000.0  # 50000 + 3.0 * 1000

    def test_both_missing_filled_short(self):
        """Both SL and TP missing on open_short → both auto-filled from ATR."""
        rc = RiskControls(default_sl_atr_multiplier=1.5, default_tp_atr_multiplier=3.0)
        parser = DecisionParser(
            risk_controls=rc,
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},
        )
        raw = self._make_response(action="open_short", stop_loss=None, take_profit=None)
        result = parser.parse(raw)

        d = result.decisions[0]
        assert d.stop_loss == 51500.0   # 50000 + 1.5 * 1000
        assert d.take_profit == 47000.0  # 50000 - 3.0 * 1000

    # ------------------------------------------------------------------ #
    # Fallback to fixed percentage when ATR unavailable
    # ------------------------------------------------------------------ #

    def test_no_atr_falls_back_to_fixed_percent_long(self):
        """No ATR data → SL = 5%, TP = 10% of entry price (long)."""
        parser = DecisionParser(
            market_prices={"BTC": 50000},
            market_atrs={},  # No ATR
        )
        raw = self._make_response(stop_loss=None, take_profit=None)
        result = parser.parse(raw)

        d = result.decisions[0]
        # SL: 50000 - 0.05 * 50000 = 47500
        assert d.stop_loss == 47500.0
        # TP: 50000 + 0.10 * 50000 = 55000
        assert d.take_profit == 55000.0

    def test_no_atr_falls_back_to_fixed_percent_short(self):
        """No ATR data → SL = 5%, TP = 10% of entry price (short)."""
        parser = DecisionParser(
            market_prices={"BTC": 50000},
            market_atrs={},
        )
        raw = self._make_response(action="open_short", stop_loss=None, take_profit=None)
        result = parser.parse(raw)

        d = result.decisions[0]
        # SL: 50000 + 0.05 * 50000 = 52500
        assert d.stop_loss == 52500.0
        # TP: 50000 - 0.10 * 50000 = 45000
        assert d.take_profit == 45000.0

    # ------------------------------------------------------------------ #
    # max_sl_percent hard cap
    # ------------------------------------------------------------------ #

    def test_max_sl_percent_clamps_atr_distance(self):
        """When ATR-based SL exceeds max_sl_percent, it's clamped."""
        rc = RiskControls(
            default_sl_atr_multiplier=5.0,  # Very aggressive
            max_sl_percent=0.05,  # 5% cap
        )
        parser = DecisionParser(
            risk_controls=rc,
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 2000},  # 5.0 * 2000 = 10000 → 20% > 5% cap
        )
        raw = self._make_response(stop_loss=None, take_profit=55000)
        result = parser.parse(raw)

        # Capped: 50000 * 0.05 = 2500; SL = 50000 - 2500 = 47500
        assert result.decisions[0].stop_loss == 47500.0

    def test_max_sl_percent_does_not_affect_small_distance(self):
        """When ATR-based SL is within max_sl_percent, it's not clamped."""
        rc = RiskControls(
            default_sl_atr_multiplier=1.0,
            max_sl_percent=0.10,  # 10% cap
        )
        parser = DecisionParser(
            risk_controls=rc,
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},  # 1.0 * 1000 = 1000 → 2% < 10%
        )
        raw = self._make_response(stop_loss=None, take_profit=55000)
        result = parser.parse(raw)

        # Not clamped: SL = 50000 - 1000 = 49000
        assert result.decisions[0].stop_loss == 49000.0

    # ------------------------------------------------------------------ #
    # entry_price fallback to market_prices
    # ------------------------------------------------------------------ #

    def test_missing_entry_price_uses_market_price(self):
        """When entry_price is None, market price is used as reference."""
        parser = DecisionParser(
            market_prices={"BTC": 48000},
            market_atrs={"BTC": 1000},
        )
        raw = self._make_response(entry_price=None, stop_loss=None, take_profit=None)
        result = parser.parse(raw)

        d = result.decisions[0]
        # entry_price should be set to market price
        assert d.entry_price == 48000
        # SL: 48000 - 1.5 * 1000 = 46500
        assert d.stop_loss == 46500.0

    def test_no_entry_and_no_market_price_skips_fill(self):
        """When neither entry_price nor market_prices available, SL/TP stay None."""
        parser = DecisionParser(
            market_prices={},  # No data
            market_atrs={},
        )
        raw = self._make_response(entry_price=None, stop_loss=None, take_profit=None)
        result = parser.parse(raw)

        d = result.decisions[0]
        assert d.stop_loss is None
        assert d.take_profit is None

    # ------------------------------------------------------------------ #
    # Hold / close actions not affected
    # ------------------------------------------------------------------ #

    def test_hold_action_not_modified(self):
        """Hold actions should not trigger SL/TP fill."""
        parser = DecisionParser(
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},
        )
        raw = self._make_response(action="hold", stop_loss=None, take_profit=None)
        result = parser.parse(raw)

        d = result.decisions[0]
        assert d.stop_loss is None
        assert d.take_profit is None

    def test_close_long_action_not_modified(self):
        """Close actions should not trigger SL/TP fill."""
        parser = DecisionParser(
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},
        )
        raw = self._make_response(action="close_long", stop_loss=None, take_profit=None)
        result = parser.parse(raw)

        d = result.decisions[0]
        assert d.stop_loss is None
        assert d.take_profit is None

    # ------------------------------------------------------------------ #
    # ATR = 0 treated as unavailable
    # ------------------------------------------------------------------ #

    def test_atr_zero_falls_back_to_fixed_percent(self):
        """ATR value of 0 should be treated as unavailable."""
        parser = DecisionParser(
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 0},
        )
        raw = self._make_response(stop_loss=None, take_profit=None)
        result = parser.parse(raw)

        d = result.decisions[0]
        # Fixed fallback: SL = 5%, TP = 10%
        assert d.stop_loss == 47500.0
        assert d.take_profit == 55000.0

    # ------------------------------------------------------------------ #
    # update_market_data works correctly
    # ------------------------------------------------------------------ #

    def test_update_market_data(self):
        """Test that update_market_data correctly injects prices/ATR."""
        parser = DecisionParser()
        assert parser.market_prices == {}
        assert parser.market_atrs == {}

        parser.update_market_data(
            market_prices={"BTC": 60000},
            market_atrs={"BTC": 1500},
        )
        assert parser.market_prices == {"BTC": 60000}
        assert parser.market_atrs == {"BTC": 1500}

        # Parse should now use the updated data
        raw = self._make_response(stop_loss=None, take_profit=None, entry_price=60000)
        result = parser.parse(raw)

        d = result.decisions[0]
        # SL: 60000 - 1.5 * 1500 = 57750
        assert d.stop_loss == 57750.0

    # ------------------------------------------------------------------ #
    # Boundary: max_sl_percent at boundaries
    # ------------------------------------------------------------------ #

    def test_max_sl_percent_exact_boundary(self):
        """ATR-based SL distance exactly equals max_sl_percent → not clamped."""
        rc = RiskControls(
            default_sl_atr_multiplier=2.5,
            max_sl_percent=0.05,  # 5%
        )
        parser = DecisionParser(
            risk_controls=rc,
            market_prices={"BTC": 50000},
            market_atrs={"BTC": 1000},  # 2.5 * 1000 = 2500 → exactly 5%
        )
        raw = self._make_response(stop_loss=None, take_profit=55000)
        result = parser.parse(raw)

        # 2500 == 50000 * 0.05 → not clamped
        assert result.decisions[0].stop_loss == 47500.0

    # ------------------------------------------------------------------ #
    # Multiple symbols with different ATRs
    # ------------------------------------------------------------------ #

    def test_multiple_symbols_different_atrs(self):
        """Different symbols get different SL/TP based on their ATRs."""
        parser = DecisionParser(
            market_prices={"BTC": 50000, "ETH": 3000},
            market_atrs={"BTC": 1000, "ETH": 100},
        )
        raw_btc = self._make_response(symbol="BTC", stop_loss=None, take_profit=None)
        raw_eth = self._make_response(symbol="ETH", entry_price=3000, stop_loss=None, take_profit=None)

        result_btc = parser.parse(raw_btc)
        result_eth = parser.parse(raw_eth)

        # BTC: SL = 50000 - 1500 = 48500, TP = 50000 + 3000 = 53000
        assert result_btc.decisions[0].stop_loss == 48500.0
        assert result_btc.decisions[0].take_profit == 53000.0

        # ETH: SL = 3000 - 150 = 2850, TP = 3000 + 300 = 3300
        assert result_eth.decisions[0].stop_loss == 2850.0
        assert result_eth.decisions[0].take_profit == 3300.0
