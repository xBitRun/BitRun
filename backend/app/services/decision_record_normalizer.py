"""
Normalize decision record payloads for read APIs.

Keeps backward compatibility for historical records with mixed field names.
"""

from __future__ import annotations

from typing import Any


def normalize_decisions(decisions: Any) -> list[dict[str, Any]]:
    """Normalize decision entries to a stable schema."""
    if not isinstance(decisions, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in decisions:
        if not isinstance(item, dict):
            continue
        normalized.append(_normalize_decision_item(item))
    return normalized


def normalize_execution_results(execution_results: Any) -> list[dict[str, Any]]:
    """Normalize execution result entries with size aliases."""
    if not isinstance(execution_results, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in execution_results:
        if not isinstance(item, dict):
            continue
        normalized.append(_normalize_execution_item(item))
    return normalized


def _normalize_decision_item(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    size = out.get("position_size_usd")
    if size is None:
        size = out.get("size_usd")
    if size is None:
        size = out.get("requested_size_usd")
    if size is None:
        size = 0
    out["position_size_usd"] = size
    out["size_usd"] = size
    out.setdefault("risk_usd", 0)
    return out


def _normalize_execution_item(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    size = out.get("actual_size_usd")
    if size is None:
        size = out.get("position_size_usd")
    if size is None:
        size = out.get("requested_size_usd")
    if size is None:
        size = out.get("size_usd")
    if size is None:
        size = 0
    out["position_size_usd"] = size
    out["size_usd"] = size
    if "reason" not in out and "reasoning" in out:
        out["reason"] = out.get("reasoning")
    if "reasoning" not in out and "reason" in out:
        out["reasoning"] = out.get("reason")
    return out

