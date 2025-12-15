import pandas as pd
from tradingbuddy.features.technical import add_indicators


def make_sample_df():
    dates = pd.date_range(end=pd.Timestamp.today(), periods=60, freq='D')
    close = pd.Series([100 + i*0.5 for i in range(len(dates))])
    df = pd.DataFrame({
        'date': dates,
        'open': close - 0.2,
        'high': close + 0.5,
        'low': close - 0.5,
        'close': close,
        'volume': [1000 + i*10 for i in range(len(dates))]
    })
    return df


def test_add_indicators_basic():
    df = make_sample_df()
    df2 = add_indicators(df)
    # SMA and EMA columns exist
    assert 'SMA_20' in df2.columns or 'sma_20' in df2.columns
    assert 'RSI' in df2.columns or 'rsi' in df2.columns
    # Last RSI should be a float and not NaN
    rsi_col = 'RSI' if 'RSI' in df2.columns else 'rsi'
    assert not pd.isna(df2[rsi_col].iloc[-1])
    assert 'MACD' in df2.columns or 'macd' in df2.columns
