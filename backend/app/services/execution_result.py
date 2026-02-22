"""Shared execution-result DTO helpers for AI/Quant engines."""

from typing import Optional

from ..traders.base import OrderResult


def order_result_to_dict(order_result: Optional[OrderResult]) -> Optional[dict]:
    """Convert OrderResult into a stable JSON-serializable shape."""
    if order_result is None:
        return None
    return {
        "order_id": order_result.order_id,
        "filled_size": order_result.filled_size,
        "filled_price": order_result.filled_price,
        "status": order_result.status,
        "error": order_result.error,
    }


def make_execution_result(
    *,
    symbol: str,
    action: str,
    confidence: int = 100,
    executed: bool = False,
    reason: str = "",
    requested_size_usd: Optional[float] = None,
    actual_size_usd: Optional[float] = None,
    order_result: Optional[OrderResult] = None,
    realized_pnl: Optional[float] = None,
    position_leverage: Optional[int] = None,
    position_size_usd: Optional[float] = None,
) -> dict:
    """Build a normalized execution result entry."""
    result = {
        "symbol": symbol,
        "action": action,
        "confidence": confidence,
        "executed": executed,
        "reason": reason,
        "requested_size_usd": requested_size_usd,
        "actual_size_usd": actual_size_usd,
        "order_result": order_result_to_dict(order_result),
    }
    if realized_pnl is not None:
        result["realized_pnl"] = realized_pnl
    if position_leverage is not None:
        result["position_leverage"] = position_leverage
    if position_size_usd is not None:
        result["position_size_usd"] = position_size_usd
    return result
