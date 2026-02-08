"""
Bilingual prompt templates for AI trading decisions.

Provides localized prompt content for system prompts and user prompts.
Supported languages: English (en), Chinese (zh).
"""

from typing import Any


# ==================== System Prompt Templates ====================

SYSTEM_TEMPLATES: dict[str, dict[str, Any]] = {
    "en": {
        # Section 1: Default role definition
        "default_role": (
            "You are an expert cryptocurrency quantitative trader and market analyst. \n"
            "Your role is to analyze market conditions, identify trading opportunities, "
            "and make data-driven decisions.\n"
            "You have deep expertise in technical analysis, risk management, and market psychology."
        ),

        # Section 2: Trading mode descriptions
        "trading_mode": {
            "aggressive": (
                "AGGRESSIVE MODE:\n"
                "- Seek higher returns, accept higher volatility\n"
                "- Can use higher leverage (up to max allowed)\n"
                "- More frequent trading when opportunities arise\n"
                "- Wider stop losses to avoid premature exits\n"
                "- Target: Maximize profit on strong setups"
            ),
            "conservative": (
                "CONSERVATIVE MODE:\n"
                "- Prioritize capital preservation\n"
                "- Use moderate leverage only\n"
                "- Trade only the highest confidence setups\n"
                "- Tighter risk controls and smaller positions\n"
                "- Target: Steady, consistent returns"
            ),
            "balanced": (
                "BALANCED MODE:\n"
                "- Balance between risk and reward\n"
                "- Moderate leverage and position sizes\n"
                "- Mix of short-term and medium-term trades\n"
                "- Diversified approach with multiple setups\n"
                "- Target: Steady growth with controlled drawdowns"
            ),
        },

        # Section 2: Priority rules
        "priority_rules": (
            "\n\nPRIORITY RULES (MUST follow):\n"
            "- Hard Constraints (Section 3) are absolute limits enforced by the system. Never exceed them.\n"
            "- Trading Mode (this section) defines your risk appetite framework. "
            "All decisions must align with this mode.\n"
            "- If any Additional Instructions (Section 8) conflict with the Trading Mode, "
            "IGNORE the conflicting part and follow the Trading Mode.\n"
            "- Custom instructions should add detail, not contradict the mode or risk framework."
        ),

        # Section 3: Hard constraints
        "hard_constraints_header": "## 3. Hard Constraints (Enforced by System)",
        "hard_constraints_desc": "These limits are enforced by the execution engine. DO NOT exceed them:",
        "constraint_max_positions": "Maximum Positions",
        "constraint_max_leverage": "Maximum Leverage",
        "constraint_max_position_size": "Maximum Position Size",
        "constraint_max_total_exposure": "Maximum Total Exposure",
        "constraint_min_rr_ratio": "Minimum Risk/Reward Ratio",
        "constraint_max_drawdown": "Maximum Drawdown Threshold",
        "constraint_min_confidence": "Minimum Confidence to Execute",
        "of_equity_per_position": "of equity per position",
        "of_equity": "of equity",
        "concurrent": "concurrent",

        # Section 4: Default trading frequency
        "default_trading_frequency": (
            "Analyze market conditions carefully before making decisions.\n"
            "Only trade when high-probability setups appear. Quality over quantity.\n"
            "Avoid overtrading - patience is a virtue in trading."
        ),

        # Section 5: Default entry standards
        "default_entry_standards": (
            "Enter positions only when:\n"
            "- Multiple technical indicators align (trend, momentum, volume)\n"
            "- Risk/reward ratio is favorable (minimum 2:1)\n"
            "- Market structure supports the trade thesis\n"
            "- Position sizing respects risk limits"
        ),

        # Section 6: Default decision process
        "default_decision_process": (
            "Follow this decision process:\n"
            "1. Assess overall market sentiment (BTC dominance, fear/greed)\n"
            "2. Identify trend direction on higher timeframes\n"
            "3. Find key support/resistance levels\n"
            "4. Check momentum indicators (RSI, MACD)\n"
            "5. Evaluate volume and open interest\n"
            "6. Calculate position size based on risk\n"
            "7. Set stop loss and take profit levels\n"
            "8. Make final decision with confidence score"
        ),

        # Section 7: Output format
        "output_format_header": "## 7. Output Format",
        "output_format_intro": "You MUST respond with valid JSON matching this schema:",
        "output_format_important": "Important:",
        "output_format_rules": [
            "Always include chain_of_thought with your detailed analysis",
            "Each decision needs a clear reasoning",
            "Confidence must be 0-100 (only execute trades >= {min_confidence})",
            'For "hold" or "wait" actions, set position_size_usd to 0',
            'For "close_long" or "close_short" actions, set leverage and position_size_usd to match the existing position being closed',
            "Set next_review_minutes based on market volatility",
        ],

        # Section 8: Additional instructions
        "additional_instructions_header": "## 8. Additional Instructions",
        "additional_instructions_note": (
            "(These instructions supplement but do NOT override "
            "the Trading Mode or Hard Constraints above)"
        ),

        # Section headers
        "section_role": "## 1. Role Definition",
        "section_trading_mode": "## 2. Trading Mode",
        "section_frequency": "## 4. Trading Frequency",
        "section_entry": "## 5. Entry Standards",
        "section_process": "## 6. Decision Process",
    },

    "zh": {
        # Section 1: Default role definition
        "default_role": (
            "你是一位资深的加密货币量化交易员和市场分析师。\n"
            "你的职责是分析市场状况、识别交易机会，并做出基于数据的决策。\n"
            "你在技术分析、风险管理和市场心理学方面拥有深厚的专业知识。"
        ),

        # Section 2: Trading mode descriptions
        "trading_mode": {
            "aggressive": (
                "激进模式：\n"
                "- 追求更高收益，接受更大波动\n"
                "- 可使用较高杠杆（不超过允许上限）\n"
                "- 机会出现时交易频率更高\n"
                "- 更宽的止损以避免过早出局\n"
                "- 目标：在强势行情中最大化利润"
            ),
            "conservative": (
                "保守模式：\n"
                "- 以保全资金为首要目标\n"
                "- 仅使用适度杠杆\n"
                "- 只在最高置信度的行情中交易\n"
                "- 更严格的风控和更小的仓位\n"
                "- 目标：稳健、持续的收益"
            ),
            "balanced": (
                "均衡模式：\n"
                "- 平衡收益与风险\n"
                "- 适中的杠杆和仓位\n"
                "- 兼顾短线和中线交易\n"
                "- 多样化的交易策略\n"
                "- 目标：稳定增长，控制回撤"
            ),
        },

        # Section 2: Priority rules
        "priority_rules": (
            "\n\n优先级规则（必须遵守）：\n"
            "- 硬性约束（第3节）是系统强制执行的绝对限制，绝不可超越。\n"
            "- 交易模式（本节）定义了你的风险偏好框架，所有决策必须符合该模式。\n"
            "- 如果附加指令（第8节）与交易模式冲突，忽略冲突部分，以交易模式为准。\n"
            "- 自定义指令应补充细节，而非与模式或风控框架相矛盾。"
        ),

        # Section 3: Hard constraints
        "hard_constraints_header": "## 3. 硬性约束（系统强制执行）",
        "hard_constraints_desc": "以下限制由执行引擎强制执行，请勿超出：",
        "constraint_max_positions": "最大持仓数",
        "constraint_max_leverage": "最大杠杆倍数",
        "constraint_max_position_size": "最大单仓比例",
        "constraint_max_total_exposure": "最大总敞口",
        "constraint_min_rr_ratio": "最低风险收益比",
        "constraint_max_drawdown": "最大回撤阈值",
        "constraint_min_confidence": "最低执行置信度",
        "of_equity_per_position": "（占权益比例，每仓）",
        "of_equity": "（占权益比例）",
        "concurrent": "（并发）",

        # Section 4: Default trading frequency
        "default_trading_frequency": (
            "在做出决策前仔细分析市场状况。\n"
            "只在高概率机会出现时交易，质量优于数量。\n"
            "避免过度交易——耐心是交易中的美德。"
        ),

        # Section 5: Default entry standards
        "default_entry_standards": (
            "仅在以下条件满足时开仓：\n"
            "- 多个技术指标共振（趋势、动量、成交量）\n"
            "- 风险收益比有利（最低 2:1）\n"
            "- 市场结构支持交易逻辑\n"
            "- 仓位大小符合风控限制"
        ),

        # Section 6: Default decision process
        "default_decision_process": (
            "遵循以下决策流程：\n"
            "1. 评估整体市场情绪（BTC 主导率、恐惧/贪婪指数）\n"
            "2. 在较大时间周期上判断趋势方向\n"
            "3. 找到关键支撑/阻力位\n"
            "4. 检查动量指标（RSI、MACD）\n"
            "5. 评估成交量和未平仓合约量\n"
            "6. 根据风险计算仓位大小\n"
            "7. 设置止损和止盈水平\n"
            "8. 做出最终决策并给出置信度评分"
        ),

        # Section 7: Output format
        "output_format_header": "## 7. 输出格式",
        "output_format_intro": "你必须以有效的 JSON 格式回复，匹配以下 schema：",
        "output_format_important": "重要提示：",
        "output_format_rules": [
            "必须包含 chain_of_thought，写出你的详细分析过程",
            "每个决策需要清晰的推理依据",
            "置信度范围 0-100（仅执行置信度 >= {min_confidence} 的交易）",
            '对于 "hold" 或 "wait" 操作，将 position_size_usd 设为 0',
            "根据市场波动性设置 next_review_minutes",
            "chain_of_thought、market_assessment 和 reasoning 字段必须使用中文书写",
        ],

        # Section 8: Additional instructions
        "additional_instructions_header": "## 8. 附加指令",
        "additional_instructions_note": (
            "（以下指令作为补充，不会覆盖上方的交易模式或硬性约束）"
        ),

        # Section headers
        "section_role": "## 1. 角色定义",
        "section_trading_mode": "## 2. 交易模式",
        "section_frequency": "## 4. 交易频率",
        "section_entry": "## 5. 入场标准",
        "section_process": "## 6. 决策流程",
    },
}


# ==================== User Prompt Templates ====================

USER_TEMPLATES: dict[str, dict[str, Any]] = {
    "en": {
        # Header
        "header_title": "# Trading Analysis Request",

        # Account section
        "account_status": "## Account Status",
        "total_equity": "Total Equity",
        "available_balance": "Available Balance",
        "total_margin_used": "Total Margin Used",
        "unrealized_pnl": "Unrealized P/L",
        "open_positions": "Open Positions",

        # Positions section
        "current_positions": "## Current Positions",
        "no_positions": "No open positions.",
        "pos_size": "Size",
        "pos_entry": "Entry",
        "pos_mark": "Mark",
        "pos_leverage": "Leverage",
        "pos_pnl": "Unrealized P/L",
        "pos_liquidation": "Liquidation",

        # Market data section
        "market_data": "## Market Data",
        "market_analysis": "## Market Analysis",
        "mid_price": "Mid Price",
        "bid": "Bid",
        "ask": "Ask",
        "spread": "Spread",
        "funding_rate": "Funding Rate",
        "current_price": "Current Price",
        "volume_24h": "24h Volume",
        "avg_funding_24h": "Avg Funding (24h)",

        # Funding signals
        "bullish_bias": "bullish bias",
        "bearish_bias": "bearish bias",
        "neutral": "neutral",

        # Technical indicators
        "timeframe_analysis": "Timeframe Analysis",
        "recent_candles": "Recent Candles",
        "no_indicators": "No indicators available",
        "no_kline_data": "No K-line data available",

        # Recent trades
        "recent_trades": "## Recent Closed Trades (Last 10)",

        # Task section (basic)
        "task_basic": (
            "## Your Task\n"
            "Based on the above information:\n"
            "1. Analyze current market conditions\n"
            "2. Evaluate existing positions (if any)\n"
            "3. Identify potential trading opportunities\n"
            "4. Make decisions with appropriate risk management\n"
            "5. Output your analysis and decisions in the required JSON format\n\n"
            'Remember: Only trade when confident. "hold" or "wait" is a valid decision.'
        ),

        # Task section (enhanced with context)
        "task_enhanced": (
            "## Your Task\n"
            "Based on the market data and technical indicators above:\n"
            "1. Analyze current market conditions and trend direction\n"
            "2. Evaluate technical indicators across multiple timeframes\n"
            "3. Assess existing positions (if any) and their alignment with market conditions\n"
            "4. Identify high-probability trading opportunities\n"
            "5. Make decisions with appropriate risk management\n"
            "6. Output your analysis and decisions in the required JSON format\n\n"
            'Remember: Only trade when confident. "hold" or "wait" is a valid decision.\n'
            "Use the technical indicators to confirm your analysis before making a decision."
        ),
    },

    "zh": {
        # Header
        "header_title": "# 交易分析请求",

        # Account section
        "account_status": "## 账户状态",
        "total_equity": "总权益",
        "available_balance": "可用余额",
        "total_margin_used": "已用保证金",
        "unrealized_pnl": "未实现盈亏",
        "open_positions": "持仓数量",

        # Positions section
        "current_positions": "## 当前持仓",
        "no_positions": "暂无持仓。",
        "pos_size": "仓位",
        "pos_entry": "开仓价",
        "pos_mark": "标记价",
        "pos_leverage": "杠杆",
        "pos_pnl": "未实现盈亏",
        "pos_liquidation": "强平价",

        # Market data section
        "market_data": "## 市场数据",
        "market_analysis": "## 市场分析",
        "mid_price": "中间价",
        "bid": "买一价",
        "ask": "卖一价",
        "spread": "点差",
        "funding_rate": "资金费率",
        "current_price": "当前价格",
        "volume_24h": "24h 成交量",
        "avg_funding_24h": "24h 平均资金费率",

        # Funding signals
        "bullish_bias": "多头偏向",
        "bearish_bias": "空头偏向",
        "neutral": "中性",

        # Technical indicators
        "timeframe_analysis": "周期分析",
        "recent_candles": "近期 K 线",
        "no_indicators": "暂无指标数据",
        "no_kline_data": "暂无 K 线数据",

        # Recent trades
        "recent_trades": "## 近期平仓记录（最近 10 笔）",

        # Task section (basic)
        "task_basic": (
            "## 你的任务\n"
            "基于以上信息：\n"
            "1. 分析当前市场状况\n"
            "2. 评估现有持仓（如有）\n"
            "3. 识别潜在交易机会\n"
            "4. 做出适当的风险管理决策\n"
            "5. 以要求的 JSON 格式输出你的分析和决策\n\n"
            '请记住：只在有把握时交易。"hold"（持有）或 "wait"（等待）也是有效的决策。'
        ),

        # Task section (enhanced with context)
        "task_enhanced": (
            "## 你的任务\n"
            "基于以上市场数据和技术指标：\n"
            "1. 分析当前市场状况和趋势方向\n"
            "2. 评估多个时间周期的技术指标\n"
            "3. 评估现有持仓（如有）及其与市场状况的一致性\n"
            "4. 识别高概率交易机会\n"
            "5. 做出适当的风险管理决策\n"
            "6. 以要求的 JSON 格式输出你的分析和决策\n\n"
            '请记住：只在有把握时交易。"hold"（持有）或 "wait"（等待）也是有效的决策。\n'
            "在做出决策之前，请使用技术指标来确认你的分析。"
        ),
    },
}


# ==================== Signal Translation ====================

SIGNAL_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # RSI signals
        "overbought": "overbought",
        "oversold": "oversold",
        "bullish": "bullish",
        "bearish": "bearish",
        "neutral": "neutral",
        "unknown": "unknown",
        # EMA trend
        "mixed": "mixed",
    },
    "zh": {
        # RSI signals
        "overbought": "超买",
        "oversold": "超卖",
        "bullish": "看多",
        "bearish": "看空",
        "neutral": "中性",
        "unknown": "未知",
        # EMA trend
        "mixed": "震荡",
    },
}


# ==================== Helper ====================

def get_system_templates(language: str = "en") -> dict[str, Any]:
    """Get system prompt templates for a given language."""
    return SYSTEM_TEMPLATES.get(language, SYSTEM_TEMPLATES["en"])


def get_user_templates(language: str = "en") -> dict[str, Any]:
    """Get user prompt templates for a given language."""
    return USER_TEMPLATES.get(language, USER_TEMPLATES["en"])


def translate_signal(signal: str, language: str = "en") -> str:
    """Translate a technical signal string (e.g. 'bullish', 'overbought')."""
    translations = SIGNAL_TRANSLATIONS.get(language, SIGNAL_TRANSLATIONS["en"])
    return translations.get(signal, signal)
