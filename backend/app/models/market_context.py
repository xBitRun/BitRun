"""
Market context models for AI trading decisions.

Provides structured data types for:
- K-line (OHLCV) data
- Technical indicators
- Complete market context for prompt building
"""

from dataclasses import dataclass, field
from typing import Optional

from ..traders.base import FundingRate, MarketData, OHLCV

# Re-export for backwards compatibility
__all__ = [
    "OHLCV",
    "FundingRate",
    "TechnicalIndicators",
    "MarketContext",
    "TIMEFRAME_LIMITS",
    "CACHE_TTL",
]


@dataclass
class TechnicalIndicators:
    """
    Technical indicators calculated from K-line data.

    Contains common indicators used for trading decisions:
    - EMA (Exponential Moving Average) at multiple periods
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - ATR (Average True Range)
    - Bollinger Bands
    """

    # EMA values at different periods {period: value}
    ema: dict[int, float] = field(default_factory=dict)

    # RSI value (0-100)
    rsi: Optional[float] = None

    # MACD values {macd, signal, histogram}
    macd: dict[str, float] = field(
        default_factory=lambda: {
            "macd": 0.0,
            "signal": 0.0,
            "histogram": 0.0,
        }
    )

    # ATR (Average True Range)
    atr: Optional[float] = None

    # Bollinger Bands {upper, middle, lower}
    bollinger: dict[str, float] = field(
        default_factory=lambda: {
            "upper": 0.0,
            "middle": 0.0,
            "lower": 0.0,
        }
    )

    # Additional indicators
    sma: dict[int, float] = field(default_factory=dict)  # Simple Moving Average
    volume_sma: Optional[float] = None  # Volume SMA for comparison

    @property
    def rsi_signal(self) -> str:
        """Get RSI signal interpretation"""
        if self.rsi is None:
            return "unknown"
        if self.rsi >= 70:
            return "overbought"
        elif self.rsi <= 30:
            return "oversold"
        elif self.rsi >= 60:
            return "bullish"
        elif self.rsi <= 40:
            return "bearish"
        return "neutral"

    @property
    def macd_signal(self) -> str:
        """Get MACD signal interpretation"""
        histogram = self.macd.get("histogram", 0)
        if histogram > 0:
            return "bullish"
        elif histogram < 0:
            return "bearish"
        return "neutral"

    @property
    def ema_trend(self) -> str:
        """
        Determine trend based on EMA alignment.

        Bullish: Short EMA > Medium EMA > Long EMA
        Bearish: Short EMA < Medium EMA < Long EMA
        """
        periods = sorted(self.ema.keys())
        if len(periods) < 2:
            return "unknown"

        values = [self.ema[p] for p in periods]

        # Check if EMAs are in descending order (bullish)
        if all(values[i] > values[i + 1] for i in range(len(values) - 1)):
            return "bullish"
        # Check if EMAs are in ascending order (bearish)
        elif all(values[i] < values[i + 1] for i in range(len(values) - 1)):
            return "bearish"
        return "mixed"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "ema": self.ema,
            "rsi": self.rsi,
            "rsi_signal": self.rsi_signal,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "atr": self.atr,
            "bollinger": self.bollinger,
            "ema_trend": self.ema_trend,
        }


@dataclass
class MarketContext:
    """
    Complete market context for AI trading decisions.

    Contains all data needed for the AI to make informed trading decisions:
    - Current real-time market data
    - Historical K-line data at multiple timeframes
    - Calculated technical indicators
    - Funding rate history
    - Open interest history (optional)
    """

    symbol: str

    # Current real-time market data
    current: MarketData

    # Data source exchange name (e.g., "binance", "bybit", "okx")
    exchange_name: str = ""

    # K-line data by timeframe {"15m": [OHLCV, ...], "1h": [...]}
    klines: dict[str, list[OHLCV]] = field(default_factory=dict)

    # Technical indicators by timeframe {"15m": TechnicalIndicators, "1h": ...}
    indicators: dict[str, TechnicalIndicators] = field(default_factory=dict)

    # Funding rate history (most recent first)
    funding_history: list[FundingRate] = field(default_factory=list)

    # Open interest history (optional)
    open_interest_history: list[dict] = field(default_factory=list)

    # Market sentiment indicators (optional)
    fear_greed_index: Optional[int] = None
    long_short_ratio: Optional[float] = None

    @property
    def available_timeframes(self) -> list[str]:
        """Get list of available timeframes"""
        return list(self.klines.keys())

    @property
    def latest_funding_rate(self) -> Optional[float]:
        """Get the most recent funding rate"""
        if self.funding_history:
            return self.funding_history[0].rate
        return self.current.funding_rate

    @property
    def avg_funding_rate_24h(self) -> Optional[float]:
        """Calculate average funding rate over last 24 hours (3 funding periods)"""
        # Funding rate is typically every 8 hours, so 3 periods = 24h
        if len(self.funding_history) >= 3:
            return sum(f.rate for f in self.funding_history[:3]) / 3
        elif self.funding_history:
            return sum(f.rate for f in self.funding_history) / len(self.funding_history)
        return None

    def get_trend_summary(self, timeframe: str) -> dict:
        """
        Get trend summary for a specific timeframe.

        Returns dict with trend direction, strength, and key levels.
        """
        if timeframe not in self.indicators:
            return {"error": f"Timeframe {timeframe} not available"}

        ind = self.indicators[timeframe]
        klines = self.klines.get(timeframe, [])

        summary = {
            "timeframe": timeframe,
            "ema_trend": ind.ema_trend,
            "rsi": ind.rsi,
            "rsi_signal": ind.rsi_signal,
            "macd_signal": ind.macd_signal,
        }

        # Add price levels if klines available
        if klines:
            recent_highs = [k.high for k in klines[-20:]]
            recent_lows = [k.low for k in klines[-20:]]
            summary["recent_high"] = max(recent_highs) if recent_highs else None
            summary["recent_low"] = min(recent_lows) if recent_lows else None
            summary["current_price"] = klines[-1].close if klines else None

        return summary

    def to_dict(self, kline_limit: int = 5) -> dict:
        """
        Convert to dictionary for serialization.

        Args:
            kline_limit: Max number of recent K-lines to include per timeframe.
                        Defaults to 5 to keep snapshot size manageable.
        """
        return {
            "symbol": self.symbol,
            "exchange_name": self.exchange_name,
            "current": {
                "mid_price": self.current.mid_price,
                "bid_price": self.current.bid_price,
                "ask_price": self.current.ask_price,
                "volume_24h": self.current.volume_24h,
                "funding_rate": self.current.funding_rate,
            },
            "klines": {
                tf: [k.to_dict() for k in klines[-kline_limit:]]
                for tf, klines in self.klines.items()
            },
            "indicators": {tf: ind.to_dict() for tf, ind in self.indicators.items()},
            "funding_history": [f.to_dict() for f in self.funding_history],
            "available_timeframes": self.available_timeframes,
        }


# Timeframe configurations - how many candles to fetch for each timeframe
TIMEFRAME_LIMITS = {
    "1m": 60,  # 1 hour of data
    "5m": 48,  # 4 hours of data
    "15m": 96,  # 24 hours of data
    "30m": 96,  # 48 hours of data
    "1h": 168,  # 7 days of data
    "4h": 90,  # 15 days of data
    "1d": 90,  # 90 days of data
}

# Cache TTL configurations (in seconds)
CACHE_TTL = {
    "1m": 60,  # 1 minute
    "5m": 300,  # 5 minutes
    "15m": 900,  # 15 minutes
    "30m": 1800,  # 30 minutes
    "1h": 1800,  # 30 minutes
    "4h": 3600,  # 1 hour
    "1d": 3600,  # 1 hour
}
