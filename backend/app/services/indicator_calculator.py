"""
Technical Indicator Calculator.

Calculates common technical indicators from K-line (OHLCV) data.
Supports EMA, SMA, RSI, MACD, ATR, and Bollinger Bands.
"""

import logging
from typing import Optional

from ..models.market_context import TechnicalIndicators
from ..traders.base import OHLCV

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """
    Technical indicator calculator.
    
    Calculates indicators from K-line data without external dependencies.
    Uses pure Python implementations for portability.
    
    Supported indicators:
    - EMA (Exponential Moving Average)
    - SMA (Simple Moving Average)
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - ATR (Average True Range)
    - Bollinger Bands
    
    Usage:
        calculator = IndicatorCalculator(config)
        indicators = calculator.calculate(klines)
    """
    
    def __init__(self, indicator_config: Optional[dict] = None):
        """
        Initialize indicator calculator.
        
        Args:
            indicator_config: Configuration dict with indicator parameters.
                Example:
                {
                    "ema_periods": [9, 21, 55],
                    "sma_periods": [20, 50],
                    "rsi_period": 14,
                    "macd_fast": 12,
                    "macd_slow": 26,
                    "macd_signal": 9,
                    "atr_period": 14,
                    "bollinger_period": 20,
                    "bollinger_std": 2.0,
                }
        """
        self.config = indicator_config or {}
        
        # Default parameters
        self.ema_periods = self.config.get("ema_periods", [9, 21, 55])
        self.sma_periods = self.config.get("sma_periods", [20])
        self.rsi_period = self.config.get("rsi_period", 14)
        self.macd_fast = self.config.get("macd_fast", 12)
        self.macd_slow = self.config.get("macd_slow", 26)
        self.macd_signal = self.config.get("macd_signal", 9)
        self.atr_period = self.config.get("atr_period", 14)
        self.bollinger_period = self.config.get("bollinger_period", 20)
        self.bollinger_std = self.config.get("bollinger_std", 2.0)
    
    def calculate(self, klines: list[OHLCV]) -> TechnicalIndicators:
        """
        Calculate all configured technical indicators.
        
        Args:
            klines: List of OHLCV objects (oldest first)
            
        Returns:
            TechnicalIndicators object with all calculated values
        """
        if not klines:
            return TechnicalIndicators()
        
        # Extract price arrays
        closes = [k.close for k in klines]
        highs = [k.high for k in klines]
        lows = [k.low for k in klines]
        volumes = [k.volume for k in klines]
        
        # Calculate indicators (skip disabled ones where period=0)
        indicators = TechnicalIndicators(
            ema=self._calc_ema_multi(closes),
            sma=self._calc_sma_multi(closes),
            rsi=self._calc_rsi(closes) if self.rsi_period > 0 else None,
            macd=(
                self._calc_macd(closes)
                if self.macd_fast > 0 and self.macd_slow > 0
                else {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
            ),
            atr=self._calc_atr(highs, lows, closes) if self.atr_period > 0 else None,
            bollinger=self._calc_bollinger(closes),
            volume_sma=self._calc_sma(volumes, self.bollinger_period),
        )
        
        return indicators
    
    # ==================== EMA (Exponential Moving Average) ====================
    
    def _calc_ema_multi(self, closes: list[float]) -> dict[int, float]:
        """Calculate EMA for multiple periods"""
        result = {}
        for period in self.ema_periods:
            ema = self._calc_ema(closes, period)
            if ema is not None:
                result[period] = ema
        return result
    
    def _calc_ema(self, data: list[float], period: int) -> Optional[float]:
        """
        Calculate Exponential Moving Average.
        
        EMA = Price(t) * k + EMA(y) * (1 - k)
        where k = 2 / (period + 1)
        """
        if len(data) < period:
            return None
        
        # Multiplier
        k = 2 / (period + 1)
        
        # Start with SMA for first EMA value
        ema = sum(data[:period]) / period
        
        # Calculate EMA for remaining values
        for price in data[period:]:
            ema = price * k + ema * (1 - k)
        
        return round(ema, 8)
    
    # ==================== SMA (Simple Moving Average) ====================
    
    def _calc_sma_multi(self, closes: list[float]) -> dict[int, float]:
        """Calculate SMA for multiple periods"""
        result = {}
        for period in self.sma_periods:
            sma = self._calc_sma(closes, period)
            if sma is not None:
                result[period] = sma
        return result
    
    def _calc_sma(self, data: list[float], period: int) -> Optional[float]:
        """
        Calculate Simple Moving Average.
        
        SMA = Sum of last N prices / N
        """
        if len(data) < period:
            return None
        
        return round(sum(data[-period:]) / period, 8)
    
    # ==================== RSI (Relative Strength Index) ====================
    
    def _calc_rsi(self, closes: list[float]) -> Optional[float]:
        """
        Calculate Relative Strength Index.
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        
        Uses Wilder's smoothing method (exponential moving average).
        """
        period = self.rsi_period
        
        if len(closes) < period + 1:
            return None
        
        # Calculate price changes
        changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # Separate gains and losses
        gains = [max(0, change) for change in changes]
        losses = [abs(min(0, change)) for change in changes]
        
        # Initial average gain and loss (SMA)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Smooth using Wilder's method
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # Calculate RSI
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    # ==================== MACD (Moving Average Convergence Divergence) ====================
    
    def _calc_macd(self, closes: list[float]) -> dict[str, float]:
        """
        Calculate MACD indicator.
        
        MACD Line = EMA(fast) - EMA(slow)
        Signal Line = EMA of MACD Line
        Histogram = MACD Line - Signal Line
        """
        result = {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
        
        min_required = max(self.macd_slow, self.macd_fast) + self.macd_signal
        if len(closes) < min_required:
            return result
        
        # Calculate fast and slow EMAs
        fast_ema = self._calc_ema(closes, self.macd_fast)
        slow_ema = self._calc_ema(closes, self.macd_slow)
        
        if fast_ema is None or slow_ema is None:
            return result
        
        # Calculate MACD line for all data points
        macd_values = []
        
        # Need to calculate EMA series to get MACD history for signal line
        k_fast = 2 / (self.macd_fast + 1)
        k_slow = 2 / (self.macd_slow + 1)
        
        # Initialize EMAs
        ema_fast = sum(closes[:self.macd_fast]) / self.macd_fast
        ema_slow = sum(closes[:self.macd_slow]) / self.macd_slow
        
        # Calculate MACD values
        for i in range(self.macd_slow, len(closes)):
            # Update fast EMA
            if i >= self.macd_fast:
                ema_fast = closes[i] * k_fast + ema_fast * (1 - k_fast)
            
            # Update slow EMA  
            ema_slow = closes[i] * k_slow + ema_slow * (1 - k_slow)
            
            macd_values.append(ema_fast - ema_slow)
        
        if len(macd_values) < self.macd_signal:
            return result
        
        # Calculate signal line (EMA of MACD)
        signal = self._calc_ema(macd_values, self.macd_signal)
        
        if signal is None:
            return result
        
        macd_line = macd_values[-1] if macd_values else 0
        histogram = macd_line - signal
        
        return {
            "macd": round(macd_line, 8),
            "signal": round(signal, 8),
            "histogram": round(histogram, 8),
        }
    
    # ==================== ATR (Average True Range) ====================
    
    def _calc_atr(
        self,
        highs: list[float],
        lows: list[float],
        closes: list[float],
    ) -> Optional[float]:
        """
        Calculate Average True Range.
        
        True Range = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close)
        )
        
        ATR = EMA or SMA of True Range
        """
        period = self.atr_period
        
        if len(closes) < period + 1:
            return None
        
        # Calculate True Range for each period
        true_ranges = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            
            tr = max(high_low, high_close, low_close)
            true_ranges.append(tr)
        
        if len(true_ranges) < period:
            return None
        
        # Calculate ATR using Wilder's smoothing
        atr = sum(true_ranges[:period]) / period
        
        for tr in true_ranges[period:]:
            atr = (atr * (period - 1) + tr) / period
        
        return round(atr, 8)
    
    # ==================== Bollinger Bands ====================
    
    def _calc_bollinger(self, closes: list[float]) -> dict[str, float]:
        """
        Calculate Bollinger Bands.
        
        Middle Band = SMA(period)
        Upper Band = Middle Band + (std_dev * multiplier)
        Lower Band = Middle Band - (std_dev * multiplier)
        """
        result = {"upper": 0.0, "middle": 0.0, "lower": 0.0}
        
        period = self.bollinger_period
        multiplier = self.bollinger_std
        
        if len(closes) < period:
            return result
        
        # Calculate SMA (middle band)
        recent_closes = closes[-period:]
        middle = sum(recent_closes) / period
        
        # Calculate standard deviation
        variance = sum((x - middle) ** 2 for x in recent_closes) / period
        std_dev = variance ** 0.5
        
        upper = middle + (std_dev * multiplier)
        lower = middle - (std_dev * multiplier)
        
        return {
            "upper": round(upper, 8),
            "middle": round(middle, 8),
            "lower": round(lower, 8),
        }
    
    # ==================== Additional Utilities ====================
    
    def calculate_trend_strength(
        self,
        klines: list[OHLCV],
        period: int = 20,
    ) -> Optional[float]:
        """
        Calculate trend strength using ADX-like calculation.
        
        Returns value 0-100 where:
        - 0-25: Weak trend
        - 25-50: Moderate trend
        - 50-75: Strong trend
        - 75-100: Very strong trend
        """
        if len(klines) < period + 1:
            return None
        
        closes = [k.close for k in klines]
        highs = [k.high for k in klines]
        lows = [k.low for k in klines]
        
        # Calculate directional movement
        plus_dm = []
        minus_dm = []
        
        for i in range(1, len(klines)):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)
            
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)
        
        # Calculate ATR
        atr = self._calc_atr(highs, lows, closes)
        if atr is None or atr == 0:
            return None
        
        # Smooth directional movement
        smooth_plus = sum(plus_dm[-period:]) / period
        smooth_minus = sum(minus_dm[-period:]) / period
        
        # Calculate directional indicators
        plus_di = (smooth_plus / atr) * 100
        minus_di = (smooth_minus / atr) * 100
        
        # Calculate DX
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return 0
        
        dx = abs(plus_di - minus_di) / di_sum * 100
        
        return round(dx, 2)
    
    def identify_support_resistance(
        self,
        klines: list[OHLCV],
        lookback: int = 20,
        threshold: float = 0.02,
    ) -> dict[str, list[float]]:
        """
        Identify support and resistance levels.
        
        Uses local minima/maxima within lookback period.
        
        Args:
            klines: K-line data
            lookback: Number of periods to analyze
            threshold: Minimum distance between levels (as ratio)
            
        Returns:
            Dict with 'support' and 'resistance' lists
        """
        if len(klines) < lookback:
            return {"support": [], "resistance": []}
        
        recent = klines[-lookback:]
        current_price = recent[-1].close
        
        supports = []
        resistances = []
        
        # Find local minima (support) and maxima (resistance)
        for i in range(1, len(recent) - 1):
            prev_low = recent[i-1].low
            curr_low = recent[i].low
            next_low = recent[i+1].low
            
            prev_high = recent[i-1].high
            curr_high = recent[i].high
            next_high = recent[i+1].high
            
            # Local minimum (support)
            if curr_low <= prev_low and curr_low <= next_low:
                supports.append(curr_low)
            
            # Local maximum (resistance)
            if curr_high >= prev_high and curr_high >= next_high:
                resistances.append(curr_high)
        
        # Filter levels too close together
        def filter_levels(levels: list[float]) -> list[float]:
            if not levels:
                return []
            
            levels = sorted(set(levels))
            filtered = [levels[0]]
            
            for level in levels[1:]:
                if abs(level - filtered[-1]) / filtered[-1] > threshold:
                    filtered.append(level)
            
            return filtered
        
        # Only keep supports below price and resistances above
        supports = [s for s in filter_levels(supports) if s < current_price]
        resistances = [r for r in filter_levels(resistances) if r > current_price]
        
        return {
            "support": sorted(supports, reverse=True)[:3],  # Top 3 nearest
            "resistance": sorted(resistances)[:3],  # Top 3 nearest
        }
