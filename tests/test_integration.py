"""
Integration tests for end-to-end workflows.
"""
import pytest
import pandas as pd
from tradingbuddy.features.ml_breakouts import detect_breakouts_for_universe


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_detect_breakouts_for_universe_daily(self, sample_ohlc_data):
        """Test complete breakout detection workflow for daily timeframe."""
        def mock_data_loader(symbol):
            return sample_ohlc_data.copy()
        
        symbols = ['TEST1', 'TEST2']
        patterns = detect_breakouts_for_universe(
            mock_data_loader,
            symbols,
            limit=10,
            timeframe='daily',
            pre_breakout_mode=True
        )
        
        assert isinstance(patterns, list)
        # Patterns may be empty if no breakouts detected
        for pattern in patterns:
            assert pattern.symbol in symbols
            assert pattern.timeframe == 'daily'
    
    def test_detect_breakouts_for_universe_weekly(self, sample_ohlc_data):
        """Test complete breakout detection workflow for weekly timeframe."""
        def mock_data_loader(symbol):
            return sample_ohlc_data.copy()
        
        symbols = ['TEST']
        patterns = detect_breakouts_for_universe(
            mock_data_loader,
            symbols,
            limit=5,
            timeframe='weekly',
            pre_breakout_mode=True
        )
        
        assert isinstance(patterns, list)
        for pattern in patterns:
            assert pattern.timeframe == 'weekly'
    
    def test_detect_breakouts_for_universe_monthly(self, sample_ohlc_data):
        """Test complete breakout detection workflow for monthly timeframe."""
        def mock_data_loader(symbol):
            return sample_ohlc_data.copy()
        
        symbols = ['TEST']
        patterns = detect_breakouts_for_universe(
            mock_data_loader,
            symbols,
            limit=5,
            timeframe='monthly',
            pre_breakout_mode=False
        )
        
        assert isinstance(patterns, list)
        for pattern in patterns:
            assert pattern.timeframe == 'monthly'
    
    def test_detect_breakouts_with_empty_data_loader(self):
        """Test breakout detection with empty data."""
        def empty_data_loader(symbol):
            return pd.DataFrame()
        
        patterns = detect_breakouts_for_universe(
            empty_data_loader,
            ['TEST'],
            limit=10,
            timeframe='daily'
        )
        
        assert patterns == []
    
    def test_detect_breakouts_multiple_symbols(self, sample_ohlc_data):
        """Test breakout detection across multiple symbols."""
        def mock_data_loader(symbol):
            return sample_ohlc_data.copy()
        
        symbols = ['AAPL', 'MSFT', 'GOOG', 'AMZN']
        patterns = detect_breakouts_for_universe(
            mock_data_loader,
            symbols,
            limit=20,
            timeframe='daily',
            pre_breakout_mode=True
        )
        
        assert isinstance(patterns, list)
        # Should not exceed limit
        assert len(patterns) <= 20
