import yfinance as yf
import pandas as pd
import sqlite3
from datetime import datetime
from typing import Dict

class DataIngestion:
    """Simple data ingestion helper using yfinance and SQLite (starter).

    Methods are intentionally small and clear so you can extend them later.
    """

    def __init__(self, db_path: str = "financial_data.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS price_data (
                symbol TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                adj_close REAL,
                PRIMARY KEY (symbol, date)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fundamental_data (
                symbol TEXT PRIMARY KEY,
                pe_ratio REAL,
                market_cap REAL,
                roe REAL,
                updated_date TEXT
            )
        """)
        self.conn.commit()

    def fetch_price_data(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return df
        df = df.reset_index()
        df['symbol'] = symbol
        # Ensure column names expected by the rest of the code
        df = df.rename(columns={
            'Adj Close': 'adj_close'
        })
        return df

    def fetch_fundamentals(self, symbol: str) -> Dict:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        return {
            'symbol': symbol,
            'pe_ratio': info.get('trailingPE'),
            'market_cap': info.get('marketCap'),
            'roe': info.get('returnOnEquity'),
            'updated_date': datetime.utcnow().strftime('%Y-%m-%d')
        }

    def save_price_data(self, df: pd.DataFrame):
        if df.empty:
            return
        df_to_save = df[['symbol', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'adj_close']].copy()
        # Normalize column names to lowercase expected by some modules
        df_to_save.columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']
        df_to_save['date'] = df_to_save['date'].astype(str).str[:10]
        df_to_save.to_sql('price_data', self.conn, if_exists='append', index=False)

    def save_fundamentals(self, data: Dict):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO fundamental_data (symbol, pe_ratio, market_cap, roe, updated_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (data['symbol'], data.get('pe_ratio'), data.get('market_cap'), data.get('roe'), data.get('updated_date'))
        )
        self.conn.commit()
