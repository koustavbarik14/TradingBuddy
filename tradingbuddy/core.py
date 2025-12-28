# Core module moved into the package to provide a stable package layout.
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3
from typing import List, Dict, Optional
import time


class DataIngestion:
    """Handles data collection from multiple sources and stores in database.

    This implementation normalizes incoming DataFrame column names so the storage
    code is robust to yfinance's varying column names (capitalized or not).
    """

    def __init__(self, db_path: str = "financial_data.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def _connect(self):
        """Return the active sqlite3 connection (kept for compatibility with context usage)."""
        return self.conn

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
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
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fundamental_data (
                symbol TEXT PRIMARY KEY,
                market_cap REAL,
                pe_ratio REAL,
                pb_ratio REAL,
                revenue REAL,
                revenue_growth REAL,
                profit_margin REAL,
                roe REAL,
                debt_to_equity REAL,
                current_ratio REAL,
                updated_date TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_metadata (
                symbol TEXT PRIMARY KEY,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                country TEXT,
                exchange TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                notes TEXT,
                created_at TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                entry_date TEXT,
                entry_price REAL,
                size REAL,
                status TEXT,
                notes TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                symbol TEXT PRIMARY KEY,
                last_updated TEXT,
                score INTEGER,
                payload TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chart_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                config TEXT,
                created_at TEXT
            )
            """
        )
        self.conn.commit()

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        # make a copy and lowercase column names
        df = df.copy()
        df_columns = {c: c for c in df.columns}
        lower_map = {c: c.lower() for c in df.columns}
        df.rename(columns=lower_map, inplace=True)

        # Common variations
        if 'adj close' in df.columns and 'adj_close' not in df.columns:
            df.rename(columns={'adj close': 'adj_close'}, inplace=True)
        if 'date' not in df.columns and 'index' in df.columns:
            df = df.reset_index()

        # Ensure symbol present
        if 'symbol' not in df.columns:
            # maybe provided externally; keep missing for caller to set
            pass

        return df

    def fetch_price_data(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                return pd.DataFrame()
            df = df.reset_index()
            df['symbol'] = symbol
            # Normalize column names
            df = self._normalize_columns(df)
            # Keep expected capitalizations for callers that expect them
            return df
        except Exception as e:
            print(f"✗ Error fetching {symbol}: {e}")
            return pd.DataFrame()

    def fetch_fundamental_data(self, symbol: str) -> Dict:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            fundamentals = {
                'symbol': symbol,
                'market_cap': info.get('marketCap', None),
                'pe_ratio': info.get('trailingPE', None),
                'pb_ratio': info.get('priceToBook', None),
                'revenue': info.get('totalRevenue', None),
                'revenue_growth': info.get('revenueGrowth', None),
                'profit_margin': info.get('profitMargins', None),
                'roe': info.get('returnOnEquity', None),
                'debt_to_equity': info.get('debtToEquity', None),
                'current_ratio': info.get('currentRatio', None),
                'updated_date': datetime.now().strftime('%Y-%m-%d')
            }
            metadata = {
                'symbol': symbol,
                'company_name': info.get('longName', symbol),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'country': info.get('country', 'Unknown'),
                'exchange': info.get('exchange', 'Unknown')
            }
            return {'fundamentals': fundamentals, 'metadata': metadata}
        except Exception as e:
            print(f"✗ Error fetching fundamentals for {symbol}: {e}")
            return {'fundamentals': {}, 'metadata': {}}

    def save_price_data(self, df: pd.DataFrame):
        if df is None or df.empty:
            return
        df = df.copy()
        # Normalize columns to lowercase
        df = self._normalize_columns(df)

        # Accept multiple variants of column names
        col_map = {}
        for expected in ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']:
            if expected in df.columns:
                col_map[expected] = expected
            else:
                # try capitalized variants
                alt = expected.replace('_', ' ')
                if alt in df.columns:
                    col_map[expected] = alt

        # If date is datetime, format to YYYY-MM-DD
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).astype(str).str[:10]

        # Ensure required symbol column exists
        if 'symbol' not in df.columns:
            # try to infer symbol from a single-value column
            if 'symbol' in df.columns:
                pass

        # Build save dataframe with defaults for missing columns
        save_df = pd.DataFrame()
        n = len(df)
        save_df['symbol'] = df['symbol'] if 'symbol' in df.columns else pd.Series([None] * n)
        save_df['date'] = df['date'] if 'date' in df.columns else pd.Series([None] * n)

        def _pick_series(df, *names):
            """Return first existing series from names or a None-filled series."""
            for name in names:
                if name in df.columns:
                    return df[name]
            return pd.Series([None] * n)

        save_df['open'] = _pick_series(df, 'open', 'Open')
        save_df['high'] = _pick_series(df, 'high', 'High')
        save_df['low'] = _pick_series(df, 'low', 'Low')
        save_df['close'] = _pick_series(df, 'close', 'Close')
        save_df['volume'] = _pick_series(df, 'volume', 'Volume')

        # Adj close handling
        save_df['adj_close'] = _pick_series(df, 'adj_close', 'adj close', 'adjclose', 'Adj Close')
        # If adj_close is all None, fall back to close
        if save_df['adj_close'].isna().all():
            save_df['adj_close'] = save_df['close']

        # Drop rows without date or symbol
        save_df = save_df.dropna(subset=['symbol', 'date'])

        # Bulk upsert using a temporary table for better performance on large batches.
        cur = self.conn.cursor()

        # Create a temporary table
        cur.execute(
            """
            CREATE TEMP TABLE IF NOT EXISTS temp_price_data (
                symbol TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                adj_close REAL
            )
            """
        )

        insert_temp_sql = (
            "INSERT INTO temp_price_data (symbol, date, open, high, low, close, volume, adj_close)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )

        data_tuples = []
        for _, row in save_df.iterrows():
            data_tuples.append(
                (
                    row['symbol'],
                    row['date'],
                    float(row['open']) if pd.notna(row['open']) else None,
                    float(row['high']) if pd.notna(row['high']) else None,
                    float(row['low']) if pd.notna(row['low']) else None,
                    float(row['close']) if pd.notna(row['close']) else None,
                    int(row['volume']) if pd.notna(row['volume']) else None,
                    float(row['adj_close']) if pd.notna(row['adj_close']) else None,
                )
            )

        # Bulk insert into temp table
        cur.executemany(insert_temp_sql, data_tuples)

        # Single upsert from temp table into main table
        cur.execute(
            "INSERT OR REPLACE INTO price_data (symbol, date, open, high, low, close, volume, adj_close)"
            " SELECT symbol, date, open, high, low, close, volume, adj_close FROM temp_price_data"
        )

        # Clear temp table
        cur.execute("DROP TABLE IF EXISTS temp_price_data")

        self.conn.commit()

    def save_fundamental_data(self, data: Dict):
        if not data.get('fundamentals'):
            return
        df_fund = pd.DataFrame([data['fundamentals']])
        df_fund.to_sql('fundamental_data', self.conn, if_exists='replace', index=False)
        if data.get('metadata'):
            df_meta = pd.DataFrame([data['metadata']])
            df_meta.to_sql('stock_metadata', self.conn, if_exists='replace', index=False)
        self.conn.commit()

    def update_stock(self, symbol: str):
        print(f"\n📊 Updating {symbol}...")
        price_df = self.fetch_price_data(symbol)
        if not price_df.empty:
            self.save_price_data(price_df)
        fund_data = self.fetch_fundamental_data(symbol)
        self.save_fundamental_data(fund_data)
        time.sleep(1)

    def update_multiple_stocks(self, symbols: List[str]):
        print(f"\n🔄 Updating {len(symbols)} stocks...")
        for symbol in symbols:
            self.update_stock(symbol)
        print("\n✅ Update complete!")

    def get_price_data(self, symbol: str, days: int = 365) -> pd.DataFrame:
        query = f"""
            SELECT * FROM price_data 
            WHERE symbol = '{symbol}'
            ORDER BY date DESC
            LIMIT {days}
        """
        df = pd.read_sql_query(query, self.conn)
        if df.empty:
            return df
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values('date')

    def list_symbols(self) -> List[str]:
        """Return list of distinct symbols stored in the price_data table."""
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM price_data")
        rows = cur.fetchall()
        return [r[0] for r in rows]

    def save_metrics(self, symbol: str, score: int, payload: dict):
        """Save computed metrics (JSON payload) for a symbol into metrics table."""
        import json
        cur = self.conn.cursor()
        now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        cur.execute(
            "INSERT OR REPLACE INTO metrics (symbol, last_updated, score, payload) VALUES (?, ?, ?, ?)",
            (symbol, now, score, json.dumps(payload))
        )
        self.conn.commit()

    def get_metrics(self, symbol: str) -> Optional[dict]:
        """Return metrics record for a symbol or None."""
        import json
        cur = self.conn.cursor()
        cur.execute("SELECT last_updated, score, payload FROM metrics WHERE symbol = ?", (symbol,))
        row = cur.fetchone()
        if not row:
            return None
        last_updated, score, payload = row
        try:
            payload_obj = json.loads(payload) if payload else {}
        except Exception:
            payload_obj = {}
        return {'symbol': symbol, 'last_updated': last_updated, 'score': score, 'payload': payload_obj}

    # -----------------------------
    # Watchlist / Positions helpers
    # -----------------------------
    def add_watchlist(self, symbol: str, notes: Optional[str] = None) -> int:
        """Add a symbol to server-side watchlist. Returns the inserted row id."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO watchlist (symbol, notes, created_at) VALUES (?, ?, ?)",
                (symbol.upper(), notes or "", datetime.utcnow().isoformat()),
            )
            return cursor.lastrowid

    def list_watchlist(self) -> list:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, symbol, notes, created_at FROM watchlist ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [
                {"id": r[0], "symbol": r[1], "notes": r[2], "created_at": r[3]} for r in rows
            ]

    def remove_watchlist(self, wid: int) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist WHERE id = ?", (wid,))
            return cursor.rowcount > 0

    def add_position(self, symbol: str, entry_date: str, entry_price: float, size: float, status: str = "open", notes: Optional[str] = None) -> int:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO positions (symbol, entry_date, entry_price, size, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (symbol.upper(), entry_date, entry_price, size, status, notes or ""),
            )
            return cursor.lastrowid

    def list_positions(self) -> list:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, symbol, entry_date, entry_price, size, status, notes FROM positions ORDER BY id DESC")
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "symbol": r[1],
                    "entry_date": r[2],
                    "entry_price": r[3],
                    "size": r[4],
                    "status": r[5],
                    "notes": r[6],
                }
                for r in rows
            ]

    def update_position(self, pid: int, **fields) -> bool:
        allowed = {"entry_date", "entry_price", "size", "status", "notes"}
        set_parts = []
        params = []
        for k, v in fields.items():
            if k in allowed:
                set_parts.append(f"{k} = ?")
                params.append(v)
        if not set_parts:
            return False
        params.append(pid)
        cur = self.conn.cursor()
        sql = f"UPDATE positions SET {', '.join(set_parts)} WHERE id = ?"
        cur.execute(sql, params)
        self.conn.commit()
        return cur.rowcount > 0

    # -----------------------------
    # Chart configuration helpers
    # -----------------------------
    def save_chart_config(self, name: str, config: dict) -> int:
        """Save a named chart configuration (JSON). Returns the row id."""
        import json
        with self._connect() as conn:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()
            try:
                cur.execute("INSERT OR REPLACE INTO chart_configs (name, config, created_at) VALUES (?, ?, ?)", (name, json.dumps(config), now))
                conn.commit()
                # fetch id
                cur.execute("SELECT id FROM chart_configs WHERE name = ?", (name,))
                row = cur.fetchone()
                return row[0] if row else None
            except Exception:
                conn.rollback()
                raise

    def get_chart_config(self, name: str) -> Optional[dict]:
        import json
        cur = self.conn.cursor()
        cur.execute("SELECT config, created_at FROM chart_configs WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            return None
        try:
            cfg = json.loads(row[0]) if row[0] else {}
        except Exception:
            cfg = {}
        return {"name": name, "config": cfg, "created_at": row[1]}

    def list_chart_configs(self) -> list:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, created_at FROM chart_configs ORDER BY created_at DESC")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]

    def remove_chart_config(self, name: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM chart_configs WHERE name = ?", (name,))
        self.conn.commit()
        return cur.rowcount > 0
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE positions SET {', '.join(set_parts)} WHERE id = ?", tuple(params))
            return cursor.rowcount > 0

    def remove_position(self, pid: int) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM positions WHERE id = ?", (pid,))
            return cursor.rowcount > 0

    def get_fundamental_data(self, symbol: str) -> Dict:
        query = f"SELECT * FROM fundamental_data WHERE symbol = '{symbol}'"
        df = pd.read_sql_query(query, self.conn)
        return df.to_dict('records')[0] if not df.empty else {}


class PatternDetection:
    # Reuse the existing PatternDetection logic from the starter; keep simple wrappers here.
    def __init__(self):
        pass

    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        return data.rolling(window=period).mean()

    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    # For brevity, import heavier pattern detection from features.patterns when needed
    def analyze_stock(self, df: pd.DataFrame) -> Dict:
        from features.patterns import PatternDetection as PD
        from features.technical import add_indicators

        if df.empty or len(df) < 20:
            return {}
        # normalize columns
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        df = add_indicators(df)
        pd_obj = PD()
        support_resistance = pd_obj.detect_support_resistance(df) if hasattr(pd_obj, 'detect_support_resistance') else {'support': [], 'resistance': []}
        breakout = pd_obj.detect_breakout(df)
        candlestick = pd_obj.detect_candlestick_patterns(df)
        current = df.iloc[-1]
        return {
            'current_price': float(current['close']),
            'rsi': float(current.get('rsi', np.nan)),
            'macd': float(current.get('macd', np.nan)),
            'macd_signal': float(current.get('macd_signal', np.nan)),
            'sma_20': float(current.get('sma_20', np.nan)),
            'sma_50': float(current.get('sma_50', np.nan)),
            'trend': 'bullish' if current.get('sma_20', 0) > current.get('sma_50', 0) else 'bearish',
            'support_levels': support_resistance.get('support', []),
            'resistance_levels': support_resistance.get('resistance', []),
            'breakout': breakout,
            'candlestick_patterns': candlestick,
            'bollinger_position': 'unknown',
            'volume_trend': 'increasing' if df['volume'].iloc[-5:].mean() > df['volume'].iloc[-20:].mean() else 'decreasing'
        }
