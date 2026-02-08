"""
Tests for app.services.prompt_templates.

Covers get_system_templates, get_user_templates, translate_signal.
"""

import pytest

from app.services.prompt_templates import (
    SIGNAL_TRANSLATIONS,
    SYSTEM_TEMPLATES,
    USER_TEMPLATES,
    get_system_templates,
    get_user_templates,
    translate_signal,
)


class TestGetSystemTemplates:
    def test_english(self):
        t = get_system_templates("en")
        assert "default_role" in t
        assert "trading_mode" in t
        assert "aggressive" in t["trading_mode"]
        assert "conservative" in t["trading_mode"]
        assert "balanced" in t["trading_mode"]

    def test_chinese(self):
        t = get_system_templates("zh")
        assert "default_role" in t
        assert "资深" in t["default_role"]  # Chinese content
        assert "trading_mode" in t

    def test_fallback_to_english(self):
        t = get_system_templates("fr")  # unsupported
        assert t == SYSTEM_TEMPLATES["en"]

    def test_default_is_english(self):
        assert get_system_templates() == get_system_templates("en")

    def test_has_section_headers(self):
        t = get_system_templates("en")
        assert "section_role" in t
        assert "section_trading_mode" in t
        assert "section_frequency" in t
        assert "section_entry" in t
        assert "section_process" in t

    def test_has_output_format(self):
        t = get_system_templates("en")
        assert "output_format_header" in t
        assert "output_format_rules" in t
        assert isinstance(t["output_format_rules"], list)

    def test_has_hard_constraints(self):
        t = get_system_templates("en")
        assert "hard_constraints_header" in t
        assert "constraint_max_leverage" in t


class TestGetUserTemplates:
    def test_english(self):
        t = get_user_templates("en")
        assert "header_title" in t
        assert "account_status" in t
        assert "task_basic" in t
        assert "task_enhanced" in t

    def test_chinese(self):
        t = get_user_templates("zh")
        assert "交易分析" in t["header_title"]

    def test_fallback_to_english(self):
        t = get_user_templates("jp")
        assert t == USER_TEMPLATES["en"]

    def test_default_is_english(self):
        assert get_user_templates() == get_user_templates("en")

    def test_has_market_labels(self):
        t = get_user_templates("en")
        assert "mid_price" in t
        assert "bid" in t
        assert "ask" in t
        assert "spread" in t
        assert "funding_rate" in t


class TestTranslateSignal:
    def test_english_signals(self):
        assert translate_signal("overbought", "en") == "overbought"
        assert translate_signal("oversold", "en") == "oversold"
        assert translate_signal("bullish", "en") == "bullish"
        assert translate_signal("bearish", "en") == "bearish"
        assert translate_signal("neutral", "en") == "neutral"
        assert translate_signal("mixed", "en") == "mixed"

    def test_chinese_signals(self):
        assert translate_signal("overbought", "zh") == "超买"
        assert translate_signal("oversold", "zh") == "超卖"
        assert translate_signal("bullish", "zh") == "看多"
        assert translate_signal("bearish", "zh") == "看空"

    def test_unknown_signal_passthrough(self):
        assert translate_signal("foobar", "en") == "foobar"
        assert translate_signal("foobar", "zh") == "foobar"

    def test_unsupported_language_fallback(self):
        result = translate_signal("bullish", "fr")
        assert result == "bullish"  # falls back to English

    def test_default_is_english(self):
        assert translate_signal("bullish") == "bullish"
