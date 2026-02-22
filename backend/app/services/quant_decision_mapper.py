"""
Shared mapper for quant execution result -> decision record payload.
"""

from __future__ import annotations

from typing import Any


def build_quant_decision_record_payload(
    *,
    strategy_type: str,
    symbol: str,
    quant_result: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build normalized decision-record payload from a quant cycle result.

    Returns a dict with:
      - strategy_name
      - chain_of_thought
      - market_assessment
      - decisions
      - executed_results
      - has_actual_execution
    """
    trades_executed = quant_result.get("trades_executed", 0)
    pnl_change = quant_result.get("pnl_change", 0.0)
    total_size_usd = quant_result.get("total_size_usd", 0.0)
    message = quant_result.get("message", "")
    success = quant_result.get("success", False)
    executed_results = quant_result.get("executed") or []

    strategy_names = {
        "grid": "网格交易策略",
        "dca": "定投策略",
        "rsi": "RSI指标策略",
    }
    strategy_name = strategy_names.get(strategy_type, strategy_type.upper())

    chain_of_thought = f"[{strategy_name}] {message}"
    if trades_executed > 0:
        chain_of_thought += f"\n执行了 {trades_executed} 笔交易"
    if pnl_change != 0:
        chain_of_thought += f"\n盈亏变化: ${pnl_change:.2f}"

    market_assessment = f"交易对: {symbol}\n执行状态: {'成功' if success else '失败'}"
    default_leverage = (config or {}).get("leverage", 1)

    decisions = []
    for ex in executed_results:
        action = ex.get("action")
        if not action:
            continue

        size_usd = (
            ex.get("actual_size_usd")
            if ex.get("actual_size_usd") is not None
            else ex.get("requested_size_usd", total_size_usd)
        )
        decisions.append(
            {
                "action": action,
                "symbol": ex.get("symbol", symbol),
                "confidence": ex.get("confidence", 100),
                "reasoning": ex.get("reason", ""),
                "leverage": ex.get("position_leverage", default_leverage),
                "position_size_usd": size_usd,
                # Backward-compatible alias used by some old views.
                "size_usd": size_usd,
                "risk_usd": 0,
            }
        )

    if not decisions:
        if trades_executed > 0:
            action = "close_long" if pnl_change > 0 else "open_long"
            action_desc = "卖出平仓获利" if pnl_change > 0 else "买入开仓"
        else:
            action = "hold"
            action_desc = "持有/观望"

        decisions = [
            {
                "action": action,
                "symbol": symbol,
                "confidence": 100,
                "reasoning": action_desc,
                "leverage": default_leverage,
                "position_size_usd": total_size_usd,
                "size_usd": total_size_usd,
                "risk_usd": 0,
            }
        ]

    has_actual_execution = any(ex.get("executed", False) for ex in executed_results)

    return {
        "strategy_name": strategy_name,
        "chain_of_thought": chain_of_thought,
        "market_assessment": market_assessment,
        "decisions": decisions,
        "executed_results": executed_results,
        "has_actual_execution": has_actual_execution,
    }
