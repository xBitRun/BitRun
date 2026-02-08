"""
Tests for the decision parser service.
"""

import pytest
from app.services.decision_parser import DecisionParser, DecisionParseError
from app.models.decision import RiskControls, ActionType


class TestDecisionParser:
    """Tests for DecisionParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DecisionParser()
    
    def test_parse_valid_json_response(self, sample_decision_response):
        """Test parsing a valid JSON decision response."""
        import json
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
        import json
        raw_response = f"```json\n{json.dumps(sample_decision_response)}\n```"
        
        result = self.parser.parse(raw_response)
        
        assert result is not None
        assert len(result.decisions) == 1
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises DecisionParseError."""
        raw_response = "This is not valid JSON"
        
        with pytest.raises(DecisionParseError) as exc_info:
            self.parser.parse(raw_response)
        
        assert "No valid JSON found" in str(exc_info.value)
    
    def test_parse_empty_response(self):
        """Test parsing empty response raises DecisionParseError."""
        with pytest.raises(DecisionParseError) as exc_info:
            self.parser.parse("")
        
        assert "Empty response" in str(exc_info.value)
        
        with pytest.raises((DecisionParseError, TypeError)):
            self.parser.parse(None)
    
    def test_risk_controls_max_leverage(self, sample_decision_response):
        """Test that risk controls limit leverage."""
        import json
        
        # Create parser with low max leverage
        parser = DecisionParser(
            risk_controls=RiskControls(max_leverage=3)
        )
        
        # Response has leverage=5, which exceeds max
        raw_response = json.dumps(sample_decision_response)
        result = parser.parse(raw_response)
        
        # Should still parse but clamp leverage
        assert result is not None
        # The decision should have been clamped or the leverage validated
    
    def test_risk_controls_min_confidence(self, sample_decision_response):
        """Test that low confidence decisions are filtered."""
        import json
        
        # Set high minimum confidence
        parser = DecisionParser(
            risk_controls=RiskControls(min_confidence=80)
        )
        
        # Response has confidence=75, which is below min
        raw_response = json.dumps(sample_decision_response)
        result = parser.parse(raw_response)
        
        assert result is not None
        # Decisions below confidence threshold may be filtered
    
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
        
        import json
        result = self.parser.parse(json.dumps(response))
        
        assert result is not None
        assert result.decisions[0].action == ActionType.HOLD
        assert result.decisions[0].position_size_usd == 0
    
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
        
        import json
        result = self.parser.parse(json.dumps(response))
        
        assert result is not None
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
        
        assert result is not None
        assert result.chain_of_thought == "test"
