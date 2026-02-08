"""
Tests for app.services.indicator_calculator.

Covers IndicatorCalculator: EMA, SMA, RSI, MACD, ATR, Bollinger,
trend_strength, support/resistance.
"""

from datetime import datetime, timedelta

import pytest

from app.services.indicator_calculator import IndicatorCalculator
from app.traders.base import OHLCV


def _make_klines(closes, base_price=50000):
    """Create OHLCV list from close prices."""
    klines = []
    for i, close in enumerate(closes):
        klines.append(OHLCV(
            timestamp=datetime(2024, 1, 1) + timedelta(hours=i),
            open=close - 10,
            high=close + 50,
            low=close - 50,
            close=close,
            volume=1000 + i,
        ))
    return klines


def _make_trending_klines(start=100, end=200, count=50):
    """Create trending klines (uptrend by default)."""
    step = (end - start) / (count - 1)
    closes = [start + step * i for i in range(count)]
    return _make_klines(closes)


class TestIndicatorCalculatorInit:
    def test_default_config(self):
        calc = IndicatorCalculator()
        assert calc.ema_periods == [9, 21, 55]
        assert calc.rsi_period == 14
        assert calc.macd_fast == 12
        assert calc.macd_slow == 26
        assert calc.bollinger_period == 20

    def test_custom_config(self):
        calc = IndicatorCalculator({
            "ema_periods": [5, 10],
            "rsi_period": 7,
            "macd_fast": 8,
        })
        assert calc.ema_periods == [5, 10]
        assert calc.rsi_period == 7
        assert calc.macd_fast == 8
        assert calc.macd_slow == 26  # default unchanged

    def test_empty_config(self):
        calc = IndicatorCalculator({})
        assert calc.ema_periods == [9, 21, 55]


class TestCalculateEmpty:
    def test_empty_klines(self):
        calc = IndicatorCalculator()
        result = calc.calculate([])
        assert result.ema == {}
        assert result.rsi is None
        assert result.atr is None


class TestEMA:
    def test_ema_with_enough_data(self):
        closes = list(range(100, 160))  # 60 data points
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"ema_periods": [9, 21]})
        result = calc.calculate(klines)
        assert 9 in result.ema
        assert 21 in result.ema

    def test_ema_insufficient_data(self):
        closes = [100, 101, 102]  # only 3 points
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"ema_periods": [9]})
        result = calc.calculate(klines)
        assert 9 not in result.ema

    def test_ema_exact_period(self):
        closes = list(range(100, 109))  # exactly 9 points
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"ema_periods": [9]})
        result = calc.calculate(klines)
        assert 9 in result.ema


class TestSMA:
    def test_sma_basic(self):
        closes = [10.0] * 20
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"sma_periods": [20]})
        result = calc.calculate(klines)
        assert 20 in result.sma
        assert result.sma[20] == pytest.approx(10.0)

    def test_sma_insufficient_data(self):
        closes = [10.0] * 5
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"sma_periods": [20]})
        result = calc.calculate(klines)
        assert 20 not in result.sma


class TestRSI:
    def test_rsi_uptrend(self):
        closes = list(range(100, 130))  # 30 points uptrend
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"rsi_period": 14})
        result = calc.calculate(klines)
        assert result.rsi is not None
        assert result.rsi > 50  # uptrend should have high RSI

    def test_rsi_downtrend(self):
        closes = list(range(200, 170, -1))  # 30 points downtrend
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"rsi_period": 14})
        result = calc.calculate(klines)
        assert result.rsi is not None
        assert result.rsi < 50

    def test_rsi_insufficient_data(self):
        closes = [100, 101, 102]
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"rsi_period": 14})
        result = calc.calculate(klines)
        assert result.rsi is None

    def test_rsi_all_gains(self):
        """When there's no loss, RSI should be 100."""
        closes = list(range(100, 120))  # 20 points, all gains
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"rsi_period": 14})
        result = calc.calculate(klines)
        assert result.rsi is not None
        assert result.rsi == 100.0

    def test_rsi_disabled(self):
        closes = list(range(100, 130))
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"rsi_period": 0})
        result = calc.calculate(klines)
        assert result.rsi is None


class TestMACD:
    def test_macd_with_enough_data(self):
        closes = list(range(100, 200))  # 100 data points
        klines = _make_klines(closes)
        calc = IndicatorCalculator()
        result = calc.calculate(klines)
        assert result.macd["macd"] != 0 or result.macd["signal"] != 0

    def test_macd_insufficient_data(self):
        closes = list(range(100, 110))  # only 10 points
        klines = _make_klines(closes)
        calc = IndicatorCalculator()
        result = calc.calculate(klines)
        assert result.macd["macd"] == 0.0

    def test_macd_disabled(self):
        closes = list(range(100, 200))
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"macd_fast": 0})
        result = calc.calculate(klines)
        assert result.macd == {"macd": 0.0, "signal": 0.0, "histogram": 0.0}


class TestATR:
    def test_atr_with_enough_data(self):
        closes = list(range(100, 130))
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"atr_period": 14})
        result = calc.calculate(klines)
        assert result.atr is not None
        assert result.atr > 0

    def test_atr_insufficient_data(self):
        closes = list(range(100, 105))
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"atr_period": 14})
        result = calc.calculate(klines)
        assert result.atr is None

    def test_atr_disabled(self):
        closes = list(range(100, 130))
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"atr_period": 0})
        result = calc.calculate(klines)
        assert result.atr is None


class TestBollingerBands:
    def test_bollinger_basic(self):
        closes = [100.0] * 20
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"bollinger_period": 20, "bollinger_std": 2.0})
        result = calc.calculate(klines)
        # All same price => std=0 => upper=middle=lower
        assert result.bollinger["middle"] == pytest.approx(100.0)
        assert result.bollinger["upper"] == pytest.approx(100.0)
        assert result.bollinger["lower"] == pytest.approx(100.0)

    def test_bollinger_with_variance(self):
        closes = list(range(90, 110))  # 20 points from 90 to 109
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"bollinger_period": 20, "bollinger_std": 2.0})
        result = calc.calculate(klines)
        assert result.bollinger["upper"] > result.bollinger["middle"]
        assert result.bollinger["lower"] < result.bollinger["middle"]

    def test_bollinger_insufficient_data(self):
        closes = [100.0] * 5
        klines = _make_klines(closes)
        calc = IndicatorCalculator({"bollinger_period": 20})
        result = calc.calculate(klines)
        assert result.bollinger["middle"] == 0.0


class TestTrendStrength:
    def test_strong_uptrend(self):
        klines = _make_trending_klines(100, 200, 50)
        calc = IndicatorCalculator()
        strength = calc.calculate_trend_strength(klines, period=20)
        assert strength is not None
        assert strength > 0

    def test_insufficient_data(self):
        klines = _make_klines([100, 101, 102])
        calc = IndicatorCalculator()
        strength = calc.calculate_trend_strength(klines, period=20)
        assert strength is None


class TestSupportResistance:
    def test_insufficient_data(self):
        klines = _make_klines([100, 101])
        calc = IndicatorCalculator()
        result = calc.identify_support_resistance(klines, lookback=20)
        assert result == {"support": [], "resistance": []}

    def test_with_swing_points(self):
        # Create data with clear peaks and troughs
        closes = []
        for i in range(30):
            if i % 6 < 3:
                closes.append(100 + i % 6 * 10)  # up
            else:
                closes.append(120 - (i % 6 - 3) * 10)  # down
        # End at a middle price so we have both supports and resistances
        closes[-1] = 110
        klines = []
        for i, c in enumerate(closes):
            klines.append(OHLCV(
                timestamp=datetime(2024, 1, 1) + timedelta(hours=i),
                open=c - 2,
                high=c + 5,
                low=c - 5,
                close=c,
                volume=100,
            ))
        calc = IndicatorCalculator()
        result = calc.identify_support_resistance(klines, lookback=30)
        assert "support" in result
        assert "resistance" in result

    def test_max_three_levels(self):
        # Large dataset to potentially get many levels
        closes = []
        for cycle in range(10):
            closes.extend([100, 110, 120, 110, 100, 90, 80, 90, 100])
        # End in the middle
        closes[-1] = 105
        klines = []
        for i, c in enumerate(closes):
            klines.append(OHLCV(
                timestamp=datetime(2024, 1, 1) + timedelta(hours=i),
                open=c,
                high=c + 3,
                low=c - 3,
                close=c,
                volume=100,
            ))
        calc = IndicatorCalculator()
        result = calc.identify_support_resistance(klines, lookback=60, threshold=0.01)
        assert len(result["support"]) <= 3
        assert len(result["resistance"]) <= 3


class TestFullCalculation:
    def test_all_indicators(self):
        """Full integration test with enough data for all indicators."""
        closes = list(range(100, 200))  # 100 data points
        klines = _make_klines(closes)
        calc = IndicatorCalculator()
        result = calc.calculate(klines)

        assert len(result.ema) > 0
        assert len(result.sma) > 0
        assert result.rsi is not None
        assert result.atr is not None
        assert result.bollinger["middle"] > 0
        # volume_sma should be calculated
        assert result.volume_sma is not None
