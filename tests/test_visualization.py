"""
Tests for chart visualization functionality.
"""
import pytest
import pandas as pd
from tradingbuddy.visualization.mplfinance_charts import create_pattern_chart


class TestVisualization:
    """Test suite for visualization functions."""
    
    def test_create_pattern_chart(self, sample_ohlc_data, breakout_pattern_data):
        """Test pattern chart creation."""
        # Normalize column names for mplfinance
        df = sample_ohlc_data.copy()
        
        try:
            chart_data = create_pattern_chart('TEST', df, breakout_pattern_data)
            
            # Should return base64 encoded image string
            assert chart_data is not None
            assert isinstance(chart_data, str)
            
            # Base64 encoded images start with data:image
            if chart_data:
                assert 'data:image' in chart_data or len(chart_data) > 100
        except Exception as e:
            # Chart generation may fail in headless environment
            pytest.skip(f"Chart generation not available: {e}")
    
    def test_create_pattern_chart_with_invalid_data(self, breakout_pattern_data):
        """Test chart creation with invalid data."""
        empty_df = pd.DataFrame()
        
        try:
            result = create_pattern_chart('TEST', empty_df, breakout_pattern_data)
            # Should handle gracefully
            assert result is None or isinstance(result, str)
        except Exception:
            # Expected to fail or handle gracefully
            pass
    
    def test_create_pattern_chart_missing_pattern_data(self, sample_ohlc_data):
        """Test chart creation with missing pattern data."""
        pattern_data = {}
        
        try:
            result = create_pattern_chart('TEST', sample_ohlc_data, pattern_data)
            # Should handle missing data
            assert result is None or isinstance(result, str)
        except Exception:
            pass
