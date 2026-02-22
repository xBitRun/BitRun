import pytest

from app.services.decision_record_normalizer import (
    normalize_decisions,
    normalize_execution_results,
)


@pytest.mark.unit
class TestDecisionRecordNormalizer:
    def test_normalize_decisions_prefers_position_size(self):
        decisions = [
            {"action": "open_long", "symbol": "BTC", "position_size_usd": 120},
            {"action": "open_long", "symbol": "ETH", "size_usd": 80},
            {"action": "hold", "symbol": "SOL"},
        ]

        result = normalize_decisions(decisions)

        assert result[0]["position_size_usd"] == 120
        assert result[0]["size_usd"] == 120
        assert result[1]["position_size_usd"] == 80
        assert result[1]["size_usd"] == 80
        assert result[2]["position_size_usd"] == 0
        assert result[2]["size_usd"] == 0
        assert all("risk_usd" in d for d in result)

    def test_normalize_execution_results_adds_aliases(self):
        execution_results = [
            {
                "action": "close_long",
                "symbol": "BTC",
                "requested_size_usd": 100,
                "actual_size_usd": 90,
                "reason": "tp",
            },
            {
                "action": "open_long",
                "symbol": "ETH",
                "size_usd": 50,
                "reasoning": "signal",
            },
        ]

        result = normalize_execution_results(execution_results)

        assert result[0]["position_size_usd"] == 90
        assert result[0]["size_usd"] == 90
        assert result[0]["reasoning"] == "tp"
        assert result[1]["position_size_usd"] == 50
        assert result[1]["size_usd"] == 50
        assert result[1]["reason"] == "signal"

    def test_normalize_handles_non_list(self):
        assert normalize_decisions(None) == []
        assert normalize_decisions({}) == []
        assert normalize_execution_results(None) == []
        assert normalize_execution_results({}) == []

