"""
Prompt Builder for AI trading decisions.

Constructs system and user prompts following the 8-section structure
inspired by NoFx's Strategy Studio.

Supports bilingual prompts (en/zh) via prompt_templates.
"""

from datetime import UTC, datetime
from typing import Optional

from ..models.decision import get_decision_json_schema
from ..models.market_context import MarketContext, TechnicalIndicators
from ..models.strategy import StrategyConfig, TradingMode
from ..traders.base import AccountState, MarketData
from .prompt_templates import (
    get_system_templates,
    get_user_templates,
    translate_signal,
)


class PromptBuilder:
    """
    Builds prompts for AI trading decisions.
    
    System prompt structure (8 sections):
    1. Role Definition
    2. Trading Mode Variant
    3. Hard Constraints (code-enforced)
    4. Trading Frequency
    5. Entry Standards
    6. Decision Process
    7. Output Format
    8. Custom Prompt
    
    User prompt includes:
    - Current timestamp
    - Account state (balance, positions)
    - Market data for candidate symbols
    - Recent trade history
    
    All text is rendered in the configured language (en/zh).
    """
    
    def __init__(
        self,
        config: StrategyConfig,
        trading_mode: TradingMode = TradingMode.CONSERVATIVE,
        custom_prompt: str = "",
    ):
        """
        Initialize prompt builder.
        
        Args:
            config: Strategy configuration (includes language setting)
            trading_mode: Trading mode (aggressive/balanced/conservative)
            custom_prompt: Additional custom instructions
        """
        self.config = config
        self.trading_mode = trading_mode
        self.custom_prompt = custom_prompt
        self.risk_controls = config.risk_controls
        self.language = getattr(config, "language", "en") or "en"
        self._sys = get_system_templates(self.language)
        self._usr = get_user_templates(self.language)
    
    # ==================== System Prompt ====================
    
    def build_system_prompt(self) -> str:
        """
        Build the system prompt with all 8 sections.
        
        Returns:
            Complete system prompt string
        """
        sections = []
        ps = self.config.prompt_sections
        t = self._sys
        
        # 1. Role Definition
        role = ps.role_definition or t["default_role"]
        sections.append(f"{t['section_role']}\n{role}")
        
        # 2. Trading Mode
        mode_key = self.trading_mode.value  # "aggressive" / "balanced" / "conservative"
        mode_desc = t["trading_mode"].get(
            mode_key,
            t["trading_mode"]["conservative"],
        )
        priority_note = t["priority_rules"]
        sections.append(f"{t['section_trading_mode']}\n{mode_desc}{priority_note}")
        
        # 3. Hard Constraints (code-enforced)
        rc = self.risk_controls
        constraints = (
            f"{t['hard_constraints_header']}\n"
            f"{t['hard_constraints_desc']}\n"
            f"- {t['constraint_max_positions']}: {rc.max_leverage} {t['concurrent']}\n"
            f"- {t['constraint_max_leverage']}: {rc.max_leverage}x\n"
            f"- {t['constraint_max_position_size']}: {rc.max_position_ratio * 100:.0f}% {t['of_equity_per_position']}\n"
            f"- {t['constraint_max_total_exposure']}: {rc.max_total_exposure * 100:.0f}% {t['of_equity']}\n"
            f"- {t['constraint_min_rr_ratio']}: 1:{rc.min_risk_reward_ratio}\n"
            f"- {t['constraint_max_drawdown']}: {rc.max_drawdown_percent * 100:.0f}%\n"
            f"- {t['constraint_min_confidence']}: {rc.min_confidence}%"
        )
        sections.append(constraints)
        
        # 4. Trading Frequency
        frequency = ps.trading_frequency or t["default_trading_frequency"]
        sections.append(f"{t['section_frequency']}\n{frequency}")
        
        # 5. Entry Standards
        entry = ps.entry_standards or t["default_entry_standards"]
        sections.append(f"{t['section_entry']}\n{entry}")
        
        # 6. Decision Process
        process = ps.decision_process or t["default_decision_process"]
        sections.append(f"{t['section_process']}\n{process}")
        
        # 7. Output Format
        rules_lines = "\n".join(
            f"- {rule.format(min_confidence=rc.min_confidence)}"
            for rule in t["output_format_rules"]
        )
        output_format = (
            f"{t['output_format_header']}\n"
            f"{t['output_format_intro']}\n"
            f"```json\n{get_decision_json_schema(self.language)}\n```\n\n"
            f"{t['output_format_important']}\n"
            f"{rules_lines}"
        )
        sections.append(output_format)
        
        # 8. Custom Prompt (if provided)
        if self.custom_prompt:
            sections.append(
                f"{t['additional_instructions_header']}\n"
                f"{t['additional_instructions_note']}\n\n"
                f"{self.custom_prompt}"
            )
        
        return "\n\n".join(sections)
    
    # ==================== User Prompt (basic) ====================
    
    def build_user_prompt(
        self,
        account: AccountState,
        market_data: dict[str, MarketData],
        recent_trades: Optional[list[dict]] = None,
    ) -> str:
        """
        Build the user prompt with current market and account data.
        
        Args:
            account: Current account state
            market_data: Market data for each symbol
            recent_trades: Recent closed trades (optional)
            
        Returns:
            User prompt string with all context
        """
        sections = []
        u = self._usr
        
        # Header
        now = datetime.now(UTC)
        header = f"""{u['header_title']}
Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
        sections.append(header)
        
        # Account Status
        sections.append(self._format_account_status(account))
        
        # Current Positions
        sections.append(self._format_positions(account))
        
        # Market Data for Candidate Symbols
        if market_data:
            market_lines = [u["market_data"]]
            for symbol, data in market_data.items():
                funding_str = f"{data.funding_rate*100:.4f}%" if data.funding_rate else "N/A"
                market_lines.append(f"""
### {symbol}
- {u['mid_price']}: ${data.mid_price:,.2f}
- {u['bid']}: ${data.bid_price:,.2f} | {u['ask']}: ${data.ask_price:,.2f}
- {u['spread']}: {((data.ask_price - data.bid_price) / data.mid_price) * 100:.3f}%
- {u['funding_rate']}: {funding_str}""")
            sections.append("\n".join(market_lines))
        
        # Recent Trades (if available)
        if recent_trades:
            trade_lines = [u["recent_trades"]]
            for trade in recent_trades[:10]:
                pnl = trade.get("pnl", 0)
                trade_lines.append(
                    f"- {trade.get('symbol', 'N/A')} {trade.get('side', 'N/A')}: "
                    f"${pnl:+,.2f} ({trade.get('timestamp', 'N/A')})"
                )
            sections.append("\n".join(trade_lines))
        
        # Analysis Request
        sections.append(u["task_basic"])
        
        return "\n\n".join(sections)
    
    def get_symbols(self) -> list[str]:
        """Get list of symbols to analyze"""
        return self.config.symbols
    
    # ==================== Enhanced Prompts with MarketContext ====================
    
    def build_user_prompt_with_context(
        self,
        account: AccountState,
        market_contexts: dict[str, MarketContext],
        recent_trades: Optional[list[dict]] = None,
    ) -> str:
        """
        Build enhanced user prompt with full market context.
        
        This method includes K-line data and technical indicators
        for more informed AI trading decisions.
        
        Args:
            account: Current account state
            market_contexts: MarketContext for each symbol
            recent_trades: Recent closed trades (optional)
            
        Returns:
            User prompt string with complete market analysis
        """
        sections = []
        u = self._usr
        
        # Header
        now = datetime.now(UTC)
        header = f"""{u['header_title']}
Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
        sections.append(header)
        
        # Account Status
        sections.append(self._format_account_status(account))
        
        # Current Positions
        sections.append(self._format_positions(account))
        
        # Market Data with Technical Analysis
        if market_contexts:
            sections.append(u["market_analysis"])
            for symbol, ctx in market_contexts.items():
                sections.append(self._format_market_context(ctx))
        
        # Recent Trades (if available)
        if recent_trades:
            trade_lines = [u["recent_trades"]]
            for trade in recent_trades[:10]:
                pnl = trade.get("pnl", 0)
                trade_lines.append(
                    f"- {trade.get('symbol', 'N/A')} {trade.get('side', 'N/A')}: "
                    f"${pnl:+,.2f} ({trade.get('timestamp', 'N/A')})"
                )
            sections.append("\n".join(trade_lines))
        
        # Analysis Request
        sections.append(u["task_enhanced"])
        
        return "\n\n".join(sections)
    
    # ==================== Shared Formatting Helpers ====================
    
    def _format_account_status(self, account: AccountState) -> str:
        """Format account status section."""
        u = self._usr
        return (
            f"{u['account_status']}\n"
            f"- {u['total_equity']}: ${account.equity:,.2f}\n"
            f"- {u['available_balance']}: ${account.available_balance:,.2f}\n"
            f"- {u['total_margin_used']}: ${account.total_margin_used:,.2f} ({account.margin_usage_percent:.1f}%)\n"
            f"- {u['unrealized_pnl']}: ${account.unrealized_pnl:+,.2f}\n"
            f"- {u['open_positions']}: {account.position_count}"
        )
    
    def _format_positions(self, account: AccountState) -> str:
        """Format current positions section."""
        u = self._usr
        if not account.positions:
            return f"{u['current_positions']}\n{u['no_positions']}"
        
        pos_lines = [u["current_positions"]]
        for pos in account.positions:
            profit_emoji = "📈" if pos.is_profitable else "📉"
            liq_str = f"${pos.liquidation_price:,.2f}" if pos.liquidation_price is not None else "N/A"
            pos_lines.append(f"""
### {pos.symbol} ({pos.side.upper()}) {profit_emoji}
- {u['pos_size']}: {pos.size:.4f} (${pos.size_usd:,.2f})
- {u['pos_entry']}: ${pos.entry_price:,.2f} | {u['pos_mark']}: ${pos.mark_price:,.2f}
- {u['pos_leverage']}: {pos.leverage}x
- {u['pos_pnl']}: ${pos.unrealized_pnl:+,.2f} ({pos.unrealized_pnl_percent:+.2f}%)
- {u['pos_liquidation']}: {liq_str}""")
        return "\n".join(pos_lines)
    
    def _format_market_context(self, ctx: MarketContext) -> str:
        """
        Format a MarketContext into a readable prompt section.
        
        Includes current price, technical indicators, and recent K-line summary.
        """
        u = self._usr
        exchange_label = f" (via {ctx.exchange_name.capitalize()})" if ctx.exchange_name else ""
        lines = [f"### {ctx.symbol}{exchange_label}"]
        
        # Current market data
        current = ctx.current
        funding_str = f"{current.funding_rate * 100:.4f}%" if current.funding_rate else "N/A"
        spread_pct = 0.0
        if current.mid_price > 0:
            spread_pct = ((current.ask_price - current.bid_price) / current.mid_price) * 100
        
        lines.append(f"**{u['current_price']}:** ${current.mid_price:,.2f}")
        lines.append(f"- {u['bid']}: ${current.bid_price:,.2f} | {u['ask']}: ${current.ask_price:,.2f}")
        lines.append(f"- {u['spread']}: {spread_pct:.3f}%")
        lines.append(f"- {u['volume_24h']}: ${current.volume_24h:,.0f}")
        lines.append(f"- {u['funding_rate']}: {funding_str}")
        
        # Funding rate analysis
        if ctx.funding_history:
            avg_funding = ctx.avg_funding_rate_24h
            if avg_funding is not None:
                if avg_funding > 0:
                    funding_signal = u["bullish_bias"]
                elif avg_funding < 0:
                    funding_signal = u["bearish_bias"]
                else:
                    funding_signal = u["neutral"]
                lines.append(f"- {u['avg_funding_24h']}: {avg_funding * 100:.4f}% ({funding_signal})")
        
        # Technical indicators by timeframe
        for tf in sorted(ctx.indicators.keys(), key=self._timeframe_sort_key):
            ind = ctx.indicators[tf]
            lines.append(f"\n**{tf.upper()} {u['timeframe_analysis']}:**")
            lines.append(self._format_technical_indicators(ind))
        
        # Recent K-lines summary (use the primary timeframe)
        primary_tf = self._get_primary_timeframe(list(ctx.klines.keys()))
        if primary_tf and ctx.klines.get(primary_tf):
            lines.append(f"\n**{u['recent_candles']} ({primary_tf}):**")
            lines.append(self._format_recent_klines(ctx.klines[primary_tf], limit=5))
        
        return "\n".join(lines)
    
    def _format_technical_indicators(self, ind: TechnicalIndicators) -> str:
        """Format technical indicators into readable text."""
        lines = []
        lang = self.language
        
        # EMA
        if ind.ema:
            ema_parts = [f"{period}={value:,.2f}" for period, value in sorted(ind.ema.items())]
            ema_str = ", ".join(ema_parts)
            trend = translate_signal(ind.ema_trend, lang)
            lines.append(f"- EMA: {ema_str} ({trend})")
        
        # RSI
        if ind.rsi is not None:
            rsi_sig = translate_signal(ind.rsi_signal, lang)
            lines.append(f"- RSI: {ind.rsi:.1f} ({rsi_sig})")
        
        # MACD
        if ind.macd.get("histogram", 0) != 0:
            histogram = ind.macd["histogram"]
            macd_val = ind.macd.get("macd", 0)
            signal_val = ind.macd.get("signal", 0)
            histogram_sign = "+" if histogram > 0 else ""
            macd_sig = translate_signal(ind.macd_signal, lang)
            lines.append(f"- MACD: {macd_val:.4f}, Signal: {signal_val:.4f}, Histogram: {histogram_sign}{histogram:.4f} ({macd_sig})")
        
        # ATR
        if ind.atr is not None:
            lines.append(f"- ATR: {ind.atr:,.2f}")
        
        # Bollinger Bands
        if ind.bollinger.get("middle", 0) > 0:
            bb = ind.bollinger
            lines.append(f"- Bollinger Bands: Upper={bb['upper']:,.2f}, Middle={bb['middle']:,.2f}, Lower={bb['lower']:,.2f}")
        
        u = self._usr
        return "\n".join(lines) if lines else f"- {u['no_indicators']}"
    
    def _format_recent_klines(self, klines: list, limit: int = 5) -> str:
        """Format recent K-lines into a summary."""
        u = self._usr
        if not klines:
            return f"- {u['no_kline_data']}"
        
        recent = klines[-limit:]
        lines = []
        
        for k in recent:
            change_pct = k.change_percent
            emoji = "🟢" if k.is_bullish else "🔴"
            time_str = k.timestamp.strftime("%m-%d %H:%M")
            lines.append(f"- {time_str}: {emoji} {change_pct:+.2f}% (O:{k.open:,.2f} H:{k.high:,.2f} L:{k.low:,.2f} C:{k.close:,.2f})")
        
        return "\n".join(lines)
    
    def _timeframe_sort_key(self, tf: str) -> int:
        """Sort key for timeframes (smallest to largest)."""
        order = {"1m": 1, "5m": 2, "15m": 3, "30m": 4, "1h": 5, "4h": 6, "1d": 7}
        return order.get(tf, 99)
    
    def _get_primary_timeframe(self, timeframes: list[str]) -> Optional[str]:
        """Get the primary (middle) timeframe for K-line display."""
        if not timeframes:
            return None
        
        # Prefer 1h, then 15m, then the middle of the list
        if "1h" in timeframes:
            return "1h"
        if "15m" in timeframes:
            return "15m"
        
        sorted_tfs = sorted(timeframes, key=self._timeframe_sort_key)
        return sorted_tfs[len(sorted_tfs) // 2]
