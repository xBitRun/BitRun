import pytest

from app.services.quant_decision_mapper import build_quant_decision_record_payload


@pytest.mark.unit
class TestQuantDecisionMapper:
    def test_prefers_executed_payload_and_sets_execution_flag(self):
        payload = build_quant_decision_record_payload(
            strategy_type="grid",
            symbol="BTC",
            config={"leverage": 3},
            quant_result={
                "success": True,
                "message": "ok",
                "trades_executed": 2,
                "pnl_change": 10.0,
                "total_size_usd": 200.0,
                "executed": [
                    {
                        "symbol": "BTC",
                        "action": "open_long",
                        "confidence": 90,
                        "reason": "grid_buy_signal",
                        "executed": True,
                        "requested_size_usd": 100.0,
                        "actual_size_usd": 95.0,
                    },
                    {
                        "symbol": "BTC",
                        "action": "close_long",
                        "confidence": 88,
                        "reason": "grid_sell_signal",
                        "executed": False,
                        "requested_size_usd": 100.0,
                    },
                ],
            },
        )

        assert payload["strategy_name"] == "网格交易策略"
        assert payload["has_actual_execution"] is True
        assert len(payload["decisions"]) == 2
        assert payload["decisions"][0]["action"] == "open_long"
        assert payload["decisions"][0]["position_size_usd"] == 95.0
        assert payload["decisions"][0]["size_usd"] == 95.0
        assert payload["decisions"][0]["leverage"] == 3

    def test_fallback_when_no_executed_entries(self):
        payload = build_quant_decision_record_payload(
            strategy_type="dca",
            symbol="ETH",
            config={"leverage": 2},
            quant_result={
                "success": True,
                "message": "no trade",
                "trades_executed": 0,
                "pnl_change": 0.0,
                "total_size_usd": 0.0,
                "executed": [],
            },
        )

        assert payload["has_actual_execution"] is False
        assert len(payload["decisions"]) == 1
        assert payload["decisions"][0]["action"] == "hold"
        assert payload["decisions"][0]["symbol"] == "ETH"

