import pandas as pd

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add basic technical indicators to the DataFrame.

    Expects df with lowercase columns: 'open','high','low','close','volume'
    """
    df = df.copy()
    # SMA
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()

    # EMA
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Bollinger Bands
    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['BB_upper'] = sma20 + (std20 * 2)
    df['BB_middle'] = sma20
    df['BB_lower'] = sma20 - (std20 * 2)

    return df
