"""
Tests for Data Access Layer components.

Tests:
- OHLCV model
- TechnicalIndicators model
- MarketContext model
- IndicatorCalculator
- DataAccessLayer
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.market_context import (
    OHLCV,
    TechnicalIndicators,
    MarketContext,
    FundingRate,
    TIMEFRAME_LIMITS,
    CACHE_TTL,
)
from app.models.strategy import StrategyConfig
from app.services.indicator_calculator import IndicatorCalculator
from app.services.data_access_layer import DataAccessLayer
from app.traders.base import MarketData


# ==================== OHLCV Tests ====================

class TestOHLCV:
    """Tests for OHLCV model"""
    
    def test_create_ohlcv(self):
        """Test basic OHLCV creation"""
        ohlcv = OHLCV(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=1000.0,
        )
        
        assert ohlcv.open == 100.0
        assert ohlcv.high == 110.0
        assert ohlcv.low == 95.0
        assert ohlcv.close == 105.0
        assert ohlcv.volume == 1000.0
    
    def test_change_percent_bullish(self):
        """Test change percent for bullish candle"""
        ohlcv = OHLCV(
            timestamp=datetime.now(UTC),
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=1000.0,
        )
        
        assert ohlcv.change_percent == 5.0
        assert ohlcv.is_bullish is True
    
    def test_change_percent_bearish(self):
        """Test change percent for bearish candle"""
        ohlcv = OHLCV(
            timestamp=datetime.now(UTC),
            open=100.0,
            high=105.0,
            low=90.0,
            close=95.0,
            volume=1000.0,
        )
        
        assert ohlcv.change_percent == -5.0
        assert ohlcv.is_bullish is False
    
    def test_body_size(self):
        """Test candle body size calculation"""
        ohlcv = OHLCV(
            timestamp=datetime.now(UTC),
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=1000.0,
        )
        
        assert ohlcv.body_size == 5.0
    
    def test_wick_sizes(self):
        """Test wick size calculations"""
        ohlcv = OHLCV(
            timestamp=datetime.now(UTC),
            open=100.0,
            high=115.0,
            low=90.0,
            close=105.0,
            volume=1000.0,
        )
        
        # Upper wick: 115 - max(100, 105) = 10
        assert ohlcv.upper_wick == 10.0
        # Lower wick: min(100, 105) - 90 = 10
        assert ohlcv.lower_wick == 10.0
    
    def test_from_ccxt(self):
        """Test creating OHLCV from CCXT format"""
        ccxt_data = [1704067200000, 100.0, 110.0, 95.0, 105.0, 1000.0]
        ohlcv = OHLCV.from_ccxt(ccxt_data)
        
        assert ohlcv.open == 100.0
        assert ohlcv.high == 110.0
        assert ohlcv.close == 105.0
        assert ohlcv.volume == 1000.0
    
    def test_to_dict(self):
        """Test conversion to dict"""
        ohlcv = OHLCV(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=100.0,
            high=110.0,
            low=95.0,
            close=105.0,
            volume=1000.0,
        )
        
        d = ohlcv.to_dict()
        assert d["open"] == 100.0
        assert d["close"] == 105.0
        assert "timestamp" in d


# ==================== TechnicalIndicators Tests ====================

class TestTechnicalIndicators:
    """Tests for TechnicalIndicators model"""
    
    def test_default_values(self):
        """Test default values"""
        ind = TechnicalIndicators()
        
        assert ind.ema == {}
        assert ind.rsi is None
        assert ind.macd == {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
        assert ind.atr is None
    
    def test_rsi_signal_overbought(self):
        """Test RSI signal when overbought"""
        ind = TechnicalIndicators(rsi=75.0)
        assert ind.rsi_signal == "overbought"
    
    def test_rsi_signal_oversold(self):
        """Test RSI signal when oversold"""
        ind = TechnicalIndicators(rsi=25.0)
        assert ind.rsi_signal == "oversold"
    
    def test_rsi_signal_neutral(self):
        """Test RSI signal when neutral"""
        ind = TechnicalIndicators(rsi=50.0)
        assert ind.rsi_signal == "neutral"
    
    def test_macd_signal_bullish(self):
        """Test MACD signal when bullish"""
        ind = TechnicalIndicators(macd={"macd": 1.0, "signal": 0.5, "histogram": 0.5})
        assert ind.macd_signal == "bullish"
    
    def test_macd_signal_bearish(self):
        """Test MACD signal when bearish"""
        ind = TechnicalIndicators(macd={"macd": 0.5, "signal": 1.0, "histogram": -0.5})
        assert ind.macd_signal == "bearish"
    
    def test_ema_trend_bullish(self):
        """Test EMA trend detection - bullish"""
        ind = TechnicalIndicators(ema={9: 105.0, 21: 100.0, 55: 95.0})
        assert ind.ema_trend == "bullish"
    
    def test_ema_trend_bearish(self):
        """Test EMA trend detection - bearish"""
        ind = TechnicalIndicators(ema={9: 95.0, 21: 100.0, 55: 105.0})
        assert ind.ema_trend == "bearish"
    
    def test_ema_trend_mixed(self):
        """Test EMA trend detection - mixed"""
        ind = TechnicalIndicators(ema={9: 100.0, 21: 105.0, 55: 102.0})
        assert ind.ema_trend == "mixed"
    
    def test_to_dict(self):
        """Test conversion to dict"""
        ind = TechnicalIndicators(
            ema={9: 100.0, 21: 99.0},
            rsi=55.0,
            atr=10.0,
        )
        
        d = ind.to_dict()
        assert d["ema"] == {9: 100.0, 21: 99.0}
        assert d["rsi"] == 55.0
        assert "ema_trend" in d


# ==================== MarketContext Tests ====================

class TestMarketContext:
    """Tests for MarketContext model"""
    
    def test_create_context(self):
        """Test basic MarketContext creation"""
        market_data = MarketData(
            symbol="BTC/USDT",
            mid_price=50000.0,
            bid_price=49990.0,
            ask_price=50010.0,
            volume_24h=1000000.0,
            funding_rate=0.0001,
        )
        
        ctx = MarketContext(
            symbol="BTC/USDT",
            current=market_data,
        )
        
        assert ctx.symbol == "BTC/USDT"
        assert ctx.current.mid_price == 50000.0
    
    def test_available_timeframes(self):
        """Test available timeframes property"""
        market_data = MarketData(
            symbol="BTC/USDT",
            mid_price=50000.0,
            bid_price=49990.0,
            ask_price=50010.0,
            volume_24h=1000000.0,
        )
        
        ctx = MarketContext(
            symbol="BTC/USDT",
            current=market_data,
            klines={
                "15m": [],
                "1h": [],
                "4h": [],
            },
        )
        
        assert "15m" in ctx.available_timeframes
        assert "1h" in ctx.available_timeframes
        assert "4h" in ctx.available_timeframes
    
    def test_latest_funding_rate(self):
        """Test latest funding rate property"""
        market_data = MarketData(
            symbol="BTC/USDT",
            mid_price=50000.0,
            bid_price=49990.0,
            ask_price=50010.0,
            volume_24h=1000000.0,
        )
        
        funding_history = [
            FundingRate(timestamp=datetime.now(UTC), rate=0.0002),
            FundingRate(timestamp=datetime.now(UTC) - timedelta(hours=8), rate=0.0001),
        ]
        
        ctx = MarketContext(
            symbol="BTC/USDT",
            current=market_data,
            funding_history=funding_history,
        )
        
        assert ctx.latest_funding_rate == 0.0002


# ==================== IndicatorCalculator Tests ====================

class TestIndicatorCalculator:
    """Tests for IndicatorCalculator"""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator with default config"""
        return IndicatorCalculator({
            "ema_periods": [9, 21],
            "rsi_period": 14,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "atr_period": 14,
            "bollinger_period": 20,
            "bollinger_std": 2.0,
        })
    
    @pytest.fixture
    def sample_klines(self):
        """Generate sample K-line data"""
        klines = []
        base_price = 100.0
        
        for i in range(100):
            # Simulate trending market
            price_change = 0.5 * (i / 100)  # Gradual increase
            open_price = base_price + price_change
            high_price = open_price + 1.0
            low_price = open_price - 0.5
            close_price = open_price + 0.3
            
            klines.append(OHLCV(
                timestamp=datetime.now(UTC) - timedelta(hours=100-i),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=1000.0 + i * 10,
            ))
        
        return klines
    
    def test_calculate_empty_klines(self, calculator):
        """Test calculation with empty klines"""
        result = calculator.calculate([])
        
        assert result.ema == {}
        assert result.rsi is None
        assert result.atr is None
    
    def test_calculate_ema(self, calculator, sample_klines):
        """Test EMA calculation"""
        result = calculator.calculate(sample_klines)
        
        assert 9 in result.ema
        assert 21 in result.ema
        assert result.ema[9] > 0
        assert result.ema[21] > 0
        # Short EMA should be closer to current price
        assert abs(result.ema[9] - sample_klines[-1].close) < abs(result.ema[21] - sample_klines[-1].close)
    
    def test_calculate_rsi(self, calculator, sample_klines):
        """Test RSI calculation"""
        result = calculator.calculate(sample_klines)
        
        assert result.rsi is not None
        assert 0 <= result.rsi <= 100
    
    def test_calculate_macd(self, calculator, sample_klines):
        """Test MACD calculation"""
        result = calculator.calculate(sample_klines)
        
        assert "macd" in result.macd
        assert "signal" in result.macd
        assert "histogram" in result.macd
    
    def test_calculate_atr(self, calculator, sample_klines):
        """Test ATR calculation"""
        result = calculator.calculate(sample_klines)
        
        assert result.atr is not None
        assert result.atr > 0
    
    def test_calculate_bollinger(self, calculator, sample_klines):
        """Test Bollinger Bands calculation"""
        result = calculator.calculate(sample_klines)
        
        assert result.bollinger["upper"] > result.bollinger["middle"]
        assert result.bollinger["middle"] > result.bollinger["lower"]
    
    def test_insufficient_data(self, calculator):
        """Test calculation with insufficient data"""
        # Only 5 candles, not enough for most indicators
        klines = [
            OHLCV(
                timestamp=datetime.now(UTC) - timedelta(hours=i),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0,
            )
            for i in range(5)
        ]
        
        result = calculator.calculate(klines)
        
        # RSI requires period + 1 data points
        assert result.rsi is None


# ==================== DataAccessLayer Tests ====================

class TestDataAccessLayer:
    """Tests for DataAccessLayer"""
    
    @pytest.fixture
    def mock_trader(self):
        """Create mock trader"""
        trader = MagicMock()
        trader.exchange_name = "binance"
        trader.get_market_data = AsyncMock(return_value=MarketData(
            symbol="BTC/USDT",
            mid_price=50000.0,
            bid_price=49990.0,
            ask_price=50010.0,
            volume_24h=1000000.0,
            funding_rate=0.0001,
        ))
        trader.get_klines = AsyncMock(return_value=[
            OHLCV(
                timestamp=datetime.now(UTC) - timedelta(hours=i),
                open=50000.0 + i * 10,
                high=50100.0 + i * 10,
                low=49900.0 + i * 10,
                close=50050.0 + i * 10,
                volume=1000.0,
            )
            for i in range(100)
        ])
        trader.get_funding_history = AsyncMock(return_value=[
            FundingRate(
                timestamp=datetime.now(UTC) - timedelta(hours=i * 8),
                rate=0.0001 * (1 + i * 0.1),
            )
            for i in range(10)
        ])
        return trader
    
    @pytest.fixture
    def config(self):
        """Create strategy config"""
        return StrategyConfig(
            symbols=["BTC/USDT", "ETH/USDT"],
            timeframes=["15m", "1h"],
            indicators={
                "ema_periods": [9, 21],
                "rsi_period": 14,
            },
        )
    
    @pytest.fixture
    def dal(self, mock_trader, config):
        """Create DataAccessLayer"""
        return DataAccessLayer(
            trader=mock_trader,
            config=config,
        )
    
    @pytest.mark.asyncio
    async def test_get_market_context(self, dal, mock_trader):
        """Test getting single market context"""
        # Mock Redis to avoid actual connection
        with patch.object(dal, '_get_redis', new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value.get = AsyncMock(return_value=None)
            mock_redis.return_value.set = AsyncMock()
            
            ctx = await dal.get_market_context("BTC/USDT")
            
            assert ctx.symbol == "BTC/USDT"
            assert ctx.current.mid_price == 50000.0
            assert "15m" in ctx.indicators
            assert "1h" in ctx.indicators
    
    @pytest.mark.asyncio
    async def test_get_market_contexts(self, dal, mock_trader):
        """Test getting multiple market contexts"""
        with patch.object(dal, '_get_redis', new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value.get = AsyncMock(return_value=None)
            mock_redis.return_value.set = AsyncMock()
            
            contexts = await dal.get_market_contexts(["BTC/USDT", "ETH/USDT"])
            
            assert "BTC/USDT" in contexts
            assert "ETH/USDT" in contexts
    
    @pytest.mark.asyncio
    async def test_indicators_calculated(self, dal):
        """Test that indicators are calculated"""
        with patch.object(dal, '_get_redis', new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value.get = AsyncMock(return_value=None)
            mock_redis.return_value.set = AsyncMock()
            
            ctx = await dal.get_market_context("BTC/USDT")
            
            # Check indicators were calculated
            for tf in ["15m", "1h"]:
                ind = ctx.indicators.get(tf)
                assert ind is not None
                assert 9 in ind.ema
                assert 21 in ind.ema


# ==================== Constants Tests ====================

class TestConstants:
    """Test timeframe limits and cache TTL constants"""
    
    def test_timeframe_limits(self):
        """Test TIMEFRAME_LIMITS constant"""
        assert TIMEFRAME_LIMITS["1m"] == 60
        assert TIMEFRAME_LIMITS["15m"] == 96
        assert TIMEFRAME_LIMITS["1h"] == 168
        assert TIMEFRAME_LIMITS["1d"] == 90
    
    def test_cache_ttl(self):
        """Test CACHE_TTL constant"""
        assert CACHE_TTL["1m"] == 60
        assert CACHE_TTL["15m"] == 900
        assert CACHE_TTL["1h"] == 1800
        assert CACHE_TTL["1d"] == 3600
