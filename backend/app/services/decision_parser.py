"""
Decision Parser for AI responses.

Parses and validates AI-generated trading decisions.
Handles various response formats and edge cases.
"""

import json
import logging
import re
from typing import Optional, Tuple

from pydantic import ValidationError

from ..models.decision import (
    ActionType,
    DecisionResponse,
    RiskControls,
    TradingDecision,
)

logger = logging.getLogger(__name__)


class DecisionParseError(Exception):
    """Error parsing AI decision response"""
    def __init__(self, message: str, raw_response: str = ""):
        self.message = message
        self.raw_response = raw_response
        super().__init__(message)


class DecisionParser:
    """
    Parses AI responses into structured trading decisions.

    Handles:
    - JSON extraction from various formats
    - Character encoding fixes (Chinese quotes, etc.)
    - Validation against schema
    - Chain of thought extraction
    """

    # Regex patterns for extracting content
    JSON_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', re.IGNORECASE)
    JSON_ARRAY_PATTERN = re.compile(r'\[\s*\{[\s\S]*?\}\s*\]')
    JSON_OBJECT_PATTERN = re.compile(r'\{[\s\S]*?"chain_of_thought"[\s\S]*?\}')

    def __init__(self, risk_controls: Optional[RiskControls] = None):
        """
        Initialize parser.

        Args:
            risk_controls: Risk controls for validation
        """
        self.risk_controls = risk_controls or RiskControls()

    def parse(self, raw_response: str) -> DecisionResponse:
        """
        Parse AI response into DecisionResponse.

        Args:
            raw_response: Raw AI response string

        Returns:
            Parsed and validated DecisionResponse

        Raises:
            DecisionParseError: If parsing fails
        """
        if not raw_response or not raw_response.strip():
            raise DecisionParseError("Empty response", raw_response)

        # Fix common encoding issues
        cleaned = self._fix_encoding(raw_response)

        # Extract JSON from response
        json_str = self._extract_json(cleaned)
        if not json_str:
            raise DecisionParseError("No valid JSON found in response", raw_response)

        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise DecisionParseError(f"Invalid JSON: {e}", raw_response)

        # Build response object
        try:
            response = self._build_response(data, raw_response)
        except ValidationError as e:
            raise DecisionParseError(f"Validation error: {e}", raw_response)
        except (ValueError, TypeError) as e:
            raise DecisionParseError(f"Data conversion error: {e}", raw_response)

        # Validate decisions
        self._validate_decisions(response)

        return response

    def _fix_encoding(self, text: str) -> str:
        """Fix common encoding issues in AI responses"""
        # Chinese quotes to ASCII
        replacements = {
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '【': '[',
            '】': ']',
            '（': '(',
            '）': ')',
            '：': ':',
            '，': ',',
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def _extract_json(self, text: str) -> Optional[str]:
        """
        Extract JSON from various response formats.

        Tries multiple strategies:
        1. Direct JSON parsing (if text is already valid JSON)
        2. JSON code block (```json ... ```)
        3. Raw JSON array
        """
        # First try: direct JSON parsing (most common case)
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # Try code block
        match = self.JSON_BLOCK_PATTERN.search(text)
        if match:
            return match.group(1).strip()

        # Try to find just the decisions array
        match = self.JSON_ARRAY_PATTERN.search(text)
        if match:
            # Wrap in response object
            return json.dumps({
                "chain_of_thought": self._extract_text_before_json(text),
                "market_assessment": "",
                "decisions": json.loads(match.group(0)),
                "overall_confidence": 50,
                "next_review_minutes": 60,
            })

        # Try to find JSON object with chain_of_thought (for text before JSON cases)
        match = self.JSON_OBJECT_PATTERN.search(text)
        if match:
            try:
                # Find the complete JSON object by matching braces
                json_start = text.find('{')
                if json_start >= 0:
                    brace_count = 0
                    for i, c in enumerate(text[json_start:]):
                        if c == '{':
                            brace_count += 1
                        elif c == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = text[json_start:json_start + i + 1]
                                json.loads(json_str)  # Validate
                                return json_str
            except json.JSONDecodeError:
                pass

        logger.warning(
            f"[DecisionParser] Failed to extract JSON from response. "
            f"Response length={len(text)}, preview: {text[:500]}"
        )
        return None

    def _extract_text_before_json(self, text: str) -> str:
        """Extract reasoning text before JSON block"""
        # Find where JSON starts
        json_start = text.find('{')
        if json_start == -1:
            json_start = text.find('[')

        if json_start > 0:
            return text[:json_start].strip()

        return ""

    def _build_response(self, data: dict, raw_response: str) -> DecisionResponse:
        """Build DecisionResponse from parsed data"""
        # Handle case where data is just a list of decisions
        if isinstance(data, list):
            data = {
                "chain_of_thought": "",
                "market_assessment": "",
                "decisions": data,
                "overall_confidence": 50,
                "next_review_minutes": 60,
            }

        # Parse decisions
        raw_decisions = data.get("decisions", [])
        if not raw_decisions:
            logger.warning(
                "[DecisionParser] AI returned empty decisions array. "
                f"chain_of_thought_length={len(data.get('chain_of_thought', ''))}"
            )

        decisions = []
        for d in raw_decisions:
            try:
                # Normalize action
                action_str = d.get("action", "hold").lower().replace("-", "_")
                action = ActionType(action_str)

                # For hold/wait, leverage is irrelevant; clamp to 1 to satisfy ge=1
                raw_leverage = int(d.get("leverage", 1))
                if raw_leverage < 1:
                    raw_leverage = 1

                decision = TradingDecision(
                    symbol=d.get("symbol", "").upper(),
                    action=action,
                    leverage=raw_leverage,
                    position_size_usd=float(d.get("position_size_usd", 0)),
                    entry_price=d.get("entry_price"),
                    stop_loss=d.get("stop_loss"),
                    take_profit=d.get("take_profit"),
                    confidence=int(d.get("confidence", 50)),
                    risk_usd=float(d.get("risk_usd", 0)),
                    reasoning=d.get("reasoning", "No reasoning provided"),
                )
                decisions.append(decision)
            except (ValueError, KeyError, ValidationError) as e:
                logger.warning(
                    f"[DecisionParser] Skipping invalid decision: {e} | "
                    f"raw={d}"
                )
                continue

        if raw_decisions and not decisions:
            logger.error(
                f"[DecisionParser] ALL {len(raw_decisions)} decisions failed validation! "
                f"raw_data={raw_decisions}"
            )
        elif len(decisions) < len(raw_decisions):
            logger.warning(
                f"[DecisionParser] {len(raw_decisions) - len(decisions)}/{len(raw_decisions)} "
                f"decisions were skipped during parsing"
            )

        return DecisionResponse(
            chain_of_thought=data.get("chain_of_thought", ""),
            market_assessment=data.get("market_assessment", ""),
            decisions=decisions,
            overall_confidence=int(data.get("overall_confidence", 50)),
            next_review_minutes=int(data.get("next_review_minutes", 60)),
        )

    def _validate_decisions(self, response: DecisionResponse) -> None:
        """
        Validate decisions against risk controls.

        Modifies decisions in place to enforce limits.
        """
        rc = self.risk_controls

        for decision in response.decisions:
            # Cap leverage
            if decision.leverage > rc.max_leverage:
                original = decision.leverage
                decision.leverage = rc.max_leverage
                logger.info(
                    f"[DecisionParser] Leverage capped for {decision.symbol}: "
                    f"{original}x -> {rc.max_leverage}x (max_leverage limit)"
                )

            # Validate risk/reward ratio for trades with SL/TP
            if decision.stop_loss and decision.take_profit and decision.entry_price:
                entry = decision.entry_price
                sl = decision.stop_loss
                tp = decision.take_profit

                if decision.action in (ActionType.OPEN_LONG,):
                    risk = entry - sl
                    reward = tp - entry
                elif decision.action in (ActionType.OPEN_SHORT,):
                    risk = sl - entry
                    reward = entry - tp
                else:
                    risk = reward = 0

                if risk > 0 and reward / risk < rc.min_risk_reward_ratio:
                    logger.warning(
                        f"[DecisionParser] Risk/reward ratio {reward/risk:.2f} "
                        f"below minimum {rc.min_risk_reward_ratio} for "
                        f"{decision.symbol} {decision.action.value}"
                    )

    def extract_chain_of_thought(self, raw_response: str) -> str:
        """Extract chain of thought from response"""
        # Look for explicit tags
        patterns = [
            (r'<reasoning>\s*([\s\S]*?)\s*</reasoning>', 1),
            (r'<chain_of_thought>\s*([\s\S]*?)\s*</chain_of_thought>', 1),
            (r'## Analysis\s*([\s\S]*?)(?=##|\{|\[|$)', 1),
            (r'## Market Analysis\s*([\s\S]*?)(?=##|\{|\[|$)', 1),
        ]

        for pattern, group in patterns:
            match = re.search(pattern, raw_response, re.IGNORECASE)
            if match:
                return match.group(group).strip()

        # Fallback: text before JSON
        return self._extract_text_before_json(raw_response)

    def should_execute(self, decision: TradingDecision) -> Tuple[bool, str]:
        """
        Check if a decision should be executed.

        Returns:
            Tuple of (should_execute, reason)
        """
        # Skip hold/wait actions
        if decision.action in (ActionType.HOLD, ActionType.WAIT):
            return False, "Action is hold/wait"

        # Check confidence threshold
        if decision.confidence < self.risk_controls.min_confidence:
            return False, f"Confidence {decision.confidence}% below threshold {self.risk_controls.min_confidence}%"

        # Check position size (only for open actions; close actions use existing position size)
        is_open = decision.action in (ActionType.OPEN_LONG, ActionType.OPEN_SHORT)
        if is_open and decision.position_size_usd <= 0:
            return False, "Position size is zero"

        return True, "Passed validation"
