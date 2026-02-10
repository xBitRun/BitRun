"""
Tests for app.services.prompt_builder.

Covers PromptBuilder: system prompt, user prompt, enhanced user prompt,
formatting helpers.
"""

from datetime import UTC, datetime

import pytest

from app.models.market_context import MarketContext, TechnicalIndicators
from app.models.strategy import StrategyConfig, TradingMode
from app.services.prompt_builder import PromptBuilder
from app.traders.base import AccountState, FundingRate, MarketData, OHLCV, Position


def _make_account(equity=10000, positions=None):
    return AccountState(
        equity=equity,
        available_balance=equity * 0.8,
        total_margin_used=equity * 0.2,
        unrealized_pnl=100,
        positions=positions or [],
    )


def _make_market_data(symbol="BTC"):
    return MarketData(
        symbol=symbol,
        mid_price=50000,
        bid_price=49990,
        ask_price=50010,
        volume_24h=1000000,
        funding_rate=0.0001,
    )


def _make_kline(close=50000):
    return OHLCV(
        timestamp=datetime(2024, 1, 15, 12, 0),
        open=close - 100,
        high=close + 200,
        low=close - 200,
        close=close,
        volume=500,
    )


class TestPromptBuilderInit:
    def test_default_language(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        assert pb.language == "en"

    def test_chinese_language(self):
        config = StrategyConfig(language="zh")
        pb = PromptBuilder(config)
        assert pb.language == "zh"

    def test_custom_prompt(self):
        config = StrategyConfig()
        pb = PromptBuilder(config, custom_prompt="Focus on BTC only")
        assert pb.custom_prompt == "Focus on BTC only"


class TestBuildSystemPrompt:
    def test_english_system_prompt(self):
        config = StrategyConfig()
        pb = PromptBuilder(config, TradingMode.CONSERVATIVE)
        prompt = pb.build_system_prompt()
        assert "Role Definition" in prompt
        assert "Trading Mode" in prompt
        assert "Hard Constraints" in prompt
        assert "Output Format" in prompt
        # Verify no section numbers in headers
        assert "## 1. Role Definition" not in prompt
        assert "## 3. Hard Constraints" not in prompt
        assert "## 7. Output Format" not in prompt

    def test_chinese_system_prompt(self):
        config = StrategyConfig(language="zh")
        pb = PromptBuilder(config, TradingMode.CONSERVATIVE)
        prompt = pb.build_system_prompt()
        assert "角色定义" in prompt
        assert "交易模式" in prompt

    def test_aggressive_mode(self):
        config = StrategyConfig()
        pb = PromptBuilder(config, TradingMode.AGGRESSIVE)
        prompt = pb.build_system_prompt()
        assert "AGGRESSIVE" in prompt

    def test_balanced_mode(self):
        config = StrategyConfig()
        pb = PromptBuilder(config, TradingMode.BALANCED)
        prompt = pb.build_system_prompt()
        assert "BALANCED" in prompt

    def test_includes_risk_controls(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        prompt = pb.build_system_prompt()
        assert "5x" in prompt  # default max_leverage
        assert "60%" in prompt  # default min_confidence

    def test_custom_prompt_deprecated_in_simple_mode(self):
        """Test that custom_prompt is ignored in simple mode (deprecated)."""
        config = StrategyConfig(prompt_mode="simple")
        pb = PromptBuilder(config, custom_prompt="Only trade BTC and ETH")
        prompt = pb.build_system_prompt()
        # In simple mode, custom_prompt is ignored
        assert "Only trade BTC and ETH" not in prompt
        assert "Additional Instructions" not in prompt

    def test_no_custom_prompt_section_when_empty(self):
        config = StrategyConfig()
        pb = PromptBuilder(config, custom_prompt="")
        prompt = pb.build_system_prompt()
        # Additional Instructions section should not appear when no custom prompt
        # (Note: custom_prompt is deprecated, this test verifies backward compatibility)
        assert "Additional Instructions" not in prompt

    def test_includes_json_schema(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        prompt = pb.build_system_prompt()
        assert "chain_of_thought" in prompt
        assert "json" in prompt.lower()

    def test_custom_prompt_sections(self):
        from app.models.strategy import PromptSections
        config = StrategyConfig(
            prompt_sections=PromptSections(
                role_definition="You are a DeFi expert.",
                trading_frequency="Trade every 15 minutes.",
            )
        )
        pb = PromptBuilder(config)
        prompt = pb.build_system_prompt()
        assert "DeFi expert" in prompt
        assert "every 15 minutes" in prompt

    def test_simple_mode_hard_constraints_at_end(self):
        """Test that in simple mode, hard constraints are placed at the end."""
        config = StrategyConfig(prompt_mode="simple")
        pb = PromptBuilder(config)
        prompt = pb.build_system_prompt()
        # Hard constraints should come after decision process
        role_idx = prompt.find("Role Definition")
        constraints_idx = prompt.find("Hard Constraints")
        output_idx = prompt.find("Output Format")
        assert role_idx < constraints_idx < output_idx

    def test_advanced_mode_uses_advanced_prompt(self):
        """Test that advanced mode uses advanced_prompt content."""
        config = StrategyConfig(
            prompt_mode="advanced",
            advanced_prompt="## Custom Role\nYou are a custom trader.\n\n## Custom Strategy\nFocus on altcoins.",
        )
        pb = PromptBuilder(config)
        prompt = pb.build_system_prompt()
        assert "Custom Role" in prompt
        assert "Custom Strategy" in prompt
        assert "custom trader" in prompt
        assert "altcoins" in prompt
        # Hard constraints and output format should still be appended
        assert "Hard Constraints" in prompt
        assert "Output Format" in prompt

    def test_advanced_mode_empty_fallback_to_defaults(self):
        """Test that advanced mode falls back to defaults when advanced_prompt is empty."""
        config = StrategyConfig(prompt_mode="advanced", advanced_prompt="")
        pb = PromptBuilder(config)
        prompt = pb.build_system_prompt()
        # Should still have role definition and other sections
        assert "Role Definition" in prompt or "角色定义" in prompt
        assert "Hard Constraints" in prompt
        assert "Output Format" in prompt


class TestBuildUserPrompt:
    def test_basic_user_prompt(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        account = _make_account()
        market = {"BTC": _make_market_data()}
        prompt = pb.build_user_prompt(account, market)
        assert "$10,000.00" in prompt
        assert "BTC" in prompt
        assert "$50,000.00" in prompt

    def test_with_positions(self):
        pos = Position(
            symbol="BTC",
            side="long",
            size=0.1,
            size_usd=5000,
            entry_price=49000,
            mark_price=50000,
            leverage=5,
            unrealized_pnl=100,
            unrealized_pnl_percent=2.0,
            liquidation_price=40000,
        )
        account = _make_account(positions=[pos])
        config = StrategyConfig()
        pb = PromptBuilder(config)
        prompt = pb.build_user_prompt(account, {})
        assert "BTC" in prompt
        assert "LONG" in prompt
        assert "$40,000.00" in prompt  # liquidation

    def test_no_positions(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        account = _make_account()
        prompt = pb.build_user_prompt(account, {})
        assert "No open positions" in prompt

    def test_with_recent_trades(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        account = _make_account()
        trades = [
            {"symbol": "BTC", "side": "long", "pnl": 150, "timestamp": "2024-01-15"},
            {"symbol": "ETH", "side": "short", "pnl": -50, "timestamp": "2024-01-14"},
        ]
        prompt = pb.build_user_prompt(account, {}, recent_trades=trades)
        assert "$+150.00" in prompt
        assert "$-50.00" in prompt

    def test_chinese_user_prompt(self):
        config = StrategyConfig(language="zh")
        pb = PromptBuilder(config)
        account = _make_account()
        prompt = pb.build_user_prompt(account, {})
        assert "账户状态" in prompt
        assert "你的任务" in prompt

    def test_empty_market_data(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        account = _make_account()
        prompt = pb.build_user_prompt(account, {})
        assert "Your Task" in prompt  # should still have task section


class TestBuildUserPromptWithContext:
    def test_enhanced_prompt(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        account = _make_account()

        indicators = TechnicalIndicators(
            rsi=55,
            ema={9: 50100, 21: 49800},
            macd={"macd": 0.5, "signal": 0.3, "histogram": 0.2},
            atr=500,
            bollinger={"upper": 51000, "middle": 50000, "lower": 49000},
        )
        ctx = MarketContext(
            symbol="BTC",
            current=_make_market_data(),
            exchange_name="binance",
            klines={"1h": [_make_kline() for _ in range(5)]},
            indicators={"1h": indicators},
            funding_history=[
                FundingRate(timestamp=datetime.now(UTC), rate=0.0002),
                FundingRate(timestamp=datetime.now(UTC), rate=0.0001),
                FundingRate(timestamp=datetime.now(UTC), rate=0.0003),
            ],
        )
        prompt = pb.build_user_prompt_with_context(account, {"BTC": ctx})
        assert "BTC" in prompt
        assert "Binance" in prompt
        assert "RSI" in prompt
        assert "EMA" in prompt
        assert "MACD" in prompt
        assert "ATR" in prompt
        assert "Bollinger" in prompt

    def test_enhanced_prompt_chinese(self):
        config = StrategyConfig(language="zh")
        pb = PromptBuilder(config)
        account = _make_account()
        ctx = MarketContext(
            symbol="ETH",
            current=_make_market_data("ETH"),
            indicators={"1h": TechnicalIndicators(rsi=45)},
        )
        prompt = pb.build_user_prompt_with_context(account, {"ETH": ctx})
        assert "市场分析" in prompt

    def test_no_market_contexts(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        account = _make_account()
        prompt = pb.build_user_prompt_with_context(account, {})
        assert "Your Task" in prompt


class TestGetSymbols:
    def test_default_symbols(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        assert pb.get_symbols() == ["BTC", "ETH"]

    def test_custom_symbols(self):
        config = StrategyConfig(symbols=["SOL", "AVAX"])
        pb = PromptBuilder(config)
        assert pb.get_symbols() == ["SOL", "AVAX"]


class TestFormatHelpers:
    def test_timeframe_sort_key(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        assert pb._timeframe_sort_key("1m") < pb._timeframe_sort_key("1h")
        assert pb._timeframe_sort_key("1h") < pb._timeframe_sort_key("1d")

    def test_get_primary_timeframe_prefers_1h(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        assert pb._get_primary_timeframe(["15m", "1h", "4h"]) == "1h"

    def test_get_primary_timeframe_prefers_15m(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        assert pb._get_primary_timeframe(["5m", "15m", "4h"]) == "15m"

    def test_get_primary_timeframe_empty(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        assert pb._get_primary_timeframe([]) is None

    def test_get_primary_timeframe_middle(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        result = pb._get_primary_timeframe(["5m", "30m", "4h"])
        assert result == "30m"  # middle of sorted list

    def test_format_no_indicators(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        result = pb._format_technical_indicators(TechnicalIndicators())
        assert "No indicators" in result or "暂无" in result

    def test_format_no_klines(self):
        config = StrategyConfig()
        pb = PromptBuilder(config)
        result = pb._format_recent_klines([])
        assert "No K-line" in result or "暂无" in result
