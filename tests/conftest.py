"""
Pytest configuration and fixtures for TradingBuddy tests.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_ohlc_data():
    """Generate sample OHLC data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    close_prices = 100 + np.cumsum(np.random.randn(100) * 2)
    
    df = pd.DataFrame({
        'open': close_prices + np.random.randn(100) * 0.5,
        'high': close_prices + abs(np.random.randn(100) * 1.5),
        'low': close_prices - abs(np.random.randn(100) * 1.5),
        'close': close_prices,
        'volume': np.random.randint(1000000, 10000000, 100)
    }, index=dates)
    
    # Ensure high is highest and low is lowest
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


@pytest.fixture
def flask_app():
    """Create Flask app for testing."""
    from tradingbuddy.api.flask_app import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def flask_client(flask_app):
    """Create Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def breakout_pattern_data():
    """Sample breakout pattern data."""
    return {
        'symbol': 'AAPL',
        'pattern_type': 'darvas_box',
        'confidence': 0.85,
        'entry_price': 150.0,
        'breakout_date': '2024-01-15',
        'description': 'Darvas Box breakout above $150',
        'support_level': 145.0,
        'resistance_level': 152.0
    }
