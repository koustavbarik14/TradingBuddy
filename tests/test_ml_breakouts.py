"""
Tests for ML breakout detection functionality.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tradingbuddy.features.ml_breakouts import MLBreakoutDetector, BreakoutPattern


class TestMLBreakoutDetector:
    """Test suite for MLBreakoutDetector class."""
    
    def test_detector_initialization_daily(self):
        """Test detector initialization with daily timeframe."""
        detector = MLBreakoutDetector(timeframe='daily', pre_breakout_mode=True)
        assert detector.timeframe == 'daily'
        assert detector.pre_breakout_mode == True
        assert detector.proximity_threshold == 0.03
        assert detector.volume_increase_threshold == 1.3
    
    def test_detector_initialization_weekly(self):
        """Test detector initialization with weekly timeframe."""
        detector = MLBreakoutDetector(timeframe='weekly', pre_breakout_mode=False)
        assert detector.timeframe == 'weekly'
        assert detector.pre_breakout_mode == False
        assert detector.proximity_threshold == 0.005
        assert detector.volume_increase_threshold == 1.5
    
    def test_detector_initialization_monthly(self):
        """Test detector initialization with monthly timeframe."""
        detector = MLBreakoutDetector(timeframe='monthly', pre_breakout_mode=True)
        assert detector.timeframe == 'monthly'
    
    def test_get_min_candles_daily(self):
        """Test minimum candles calculation for daily timeframe."""
        detector = MLBreakoutDetector(timeframe='daily')
        assert detector._get_min_candles(30) == 30
        assert detector._get_min_candles(50) == 50
    
    def test_get_min_candles_weekly(self):
        """Test minimum candles calculation for weekly timeframe."""
        detector = MLBreakoutDetector(timeframe='weekly')
        assert detector._get_min_candles(30) == 15  # 50% of 30
        assert detector._get_min_candles(40) == 20  # 50% of 40
    
    def test_get_min_candles_monthly(self):
        """Test minimum candles calculation for monthly timeframe."""
        detector = MLBreakoutDetector(timeframe='monthly')
        assert detector._get_min_candles(30) == 9   # 30% of 30
        assert detector._get_min_candles(50) == 15  # 30% of 50
    
    def test_detect_all_patterns_empty_df(self):
        """Test pattern detection with empty dataframe."""
        detector = MLBreakoutDetector()
        df = pd.DataFrame()
        patterns = detector.detect_all_patterns(df, 'TEST')
        assert patterns == []
    
    def test_detect_all_patterns_insufficient_data(self):
        """Test pattern detection with insufficient data."""
        detector = MLBreakoutDetector()
        df = pd.DataFrame({
            'open': [100, 101],
            'high': [102, 103],
            'low': [99, 100],
            'close': [101, 102],
            'volume': [1000, 1100]
        })
        patterns = detector.detect_all_patterns(df, 'TEST')
        assert patterns == []
    
    def test_detect_darvas_box_with_valid_data(self, sample_ohlc_data):
        """Test Darvas Box detection with valid data."""
        detector = MLBreakoutDetector(timeframe='daily', pre_breakout_mode=True)
        patterns = detector._detect_darvas_box(sample_ohlc_data, 'TEST')
        
        # Should return a list (may be empty if no pattern found)
        assert isinstance(patterns, list)
        
        # If patterns found, validate structure
        for pattern in patterns:
            assert isinstance(pattern, BreakoutPattern)
            assert pattern.symbol == 'TEST'
            assert pattern.pattern_type == 'darvas_box'
            assert 0 <= pattern.confidence <= 1
            assert pattern.entry_price > 0
            assert pattern.status in ['forming', 'confirmed']
    
    def test_detect_volume_spike_breakout(self, sample_ohlc_data):
        """Test volume spike breakout detection."""
        # Create data with clear volume spike
        df = sample_ohlc_data.copy()
        df.loc[df.index[-1], 'volume'] = df['volume'].mean() * 2.5
        
        detector = MLBreakoutDetector(timeframe='daily', pre_breakout_mode=True)
        patterns = detector._detect_volume_spike_breakout(df, 'TEST')
        
        assert isinstance(patterns, list)
        for pattern in patterns:
            assert pattern.pattern_type == 'volume_surge'
    
    def test_breakout_pattern_dataclass(self):
        """Test BreakoutPattern dataclass creation."""
        pattern = BreakoutPattern(
            symbol='AAPL',
            pattern_type='darvas_box',
            confidence=0.85,
            entry_price=150.0,
            breakout_date='2024-01-15',
            description='Test pattern',
            support_level=145.0,
            resistance_level=152.0,
            status='forming'
        )
        
        assert pattern.symbol == 'AAPL'
        assert pattern.pattern_type == 'darvas_box'
        assert pattern.confidence == 0.85
        assert pattern.entry_price == 150.0
        assert pattern.status == 'forming'
        assert pattern.support_level == 145.0
        assert pattern.resistance_level == 152.0
    
    def test_detect_all_patterns_returns_sorted(self, sample_ohlc_data):
        """Test that detect_all_patterns returns patterns sorted by confidence."""
        detector = MLBreakoutDetector(timeframe='daily', pre_breakout_mode=True)
        patterns = detector.detect_all_patterns(sample_ohlc_data, 'TEST')
        
        # Check patterns are sorted by confidence descending
        if len(patterns) > 1:
            for i in range(len(patterns) - 1):
                assert patterns[i].confidence >= patterns[i+1].confidence
