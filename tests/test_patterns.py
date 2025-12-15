import pandas as pd
from tradingbuddy.features.patterns import PatternDetection


def make_candles():
    # Build three candles for engulfing
    data = [
        {'open': 10, 'high': 11, 'low': 9.5, 'close': 10.5, 'volume': 1000},
        {'open': 10.6, 'high': 11.2, 'low': 10.4, 'close': 10.2, 'volume': 1100},
        {'open': 10.1, 'high': 11.5, 'low': 10.0, 'close': 11.4, 'volume': 2000},
    ]
    df = pd.DataFrame(data)
    return df


def test_candlestick_detection():
    df = make_candles()
    patterns = PatternDetection.detect_candlestick_patterns(df)
    assert 'bullish_engulfing' in patterns


def test_triangle_detection():
    # Build a synthetic triangle: highs descending, lows ascending
    import numpy as np
    n = 80
    x = np.linspace(0, 1, n)
    highs = 20 - x * 2 + np.random.normal(0, 0.05, n)
    lows = 10 + x * 1.5 + np.random.normal(0, 0.05, n)
    close = (highs + lows) / 2
    df = pd.DataFrame({'high': highs, 'low': lows, 'close': close, 'open': close*0.99, 'volume': 1000 + np.arange(n)})
    res = PatternDetection.detect_triangle(df, lookback=60)
    assert res['pattern'] is True
