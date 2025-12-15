# ============================================================================
# COMPONENT 1: DATA INGESTION PIPELINE
# ============================================================================

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from typing import List, Dict, Optional
import requests
import time

class DataIngestion:
    """
    Handles data collection from multiple sources and stores in database
    """
    
    def __init__(self, db_path: str = "financial_data.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()
        
        # Price data table
        cursor.execute("""
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
        
        # Fundamental data table
        cursor.execute("""
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
        """)
        
        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_metadata (
                symbol TEXT PRIMARY KEY,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                country TEXT,
                exchange TEXT
            )
        """)
        
        self.conn.commit()
    
    def fetch_price_data(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        """
        Fetch historical price data using yfinance
        
        Args:
            symbol: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            df['symbol'] = symbol
            df.index.name = 'date'
            df.reset_index(inplace=True)
            
            print(f"✓ Fetched {len(df)} records for {symbol}")
            return df
        except Exception as e:
            print(f"✗ Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_fundamental_data(self, symbol: str) -> Dict:
        """Fetch fundamental data using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
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
            
            # Metadata
            metadata = {
                'symbol': symbol,
                'company_name': info.get('longName', symbol),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'country': info.get('country', 'Unknown'),
                'exchange': info.get('exchange', 'Unknown')
            }
            
            print(f"✓ Fetched fundamentals for {symbol}")
            return {'fundamentals': fundamentals, 'metadata': metadata}
        except Exception as e:
            print(f"✗ Error fetching fundamentals for {symbol}: {e}")
            return {'fundamentals': {}, 'metadata': {}}
    
    def save_price_data(self, df: pd.DataFrame):
        """Save price data to database"""
        if df.empty:
            return
        
        df_clean = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']].copy()
        df_clean['date'] = df_clean['date'].astype(str).str[:10]
        df_clean.to_sql('price_data', self.conn, if_exists='replace', index=False)
        self.conn.commit()
    
    def save_fundamental_data(self, data: Dict):
        """Save fundamental data to database"""
        if not data.get('fundamentals'):
            return
        
        # Save fundamentals
        df_fund = pd.DataFrame([data['fundamentals']])
        df_fund.to_sql('fundamental_data', self.conn, if_exists='replace', index=False)
        
        # Save metadata
        if data.get('metadata'):
            df_meta = pd.DataFrame([data['metadata']])
            df_meta.to_sql('stock_metadata', self.conn, if_exists='replace', index=False)
        
        self.conn.commit()
    
    def update_stock(self, symbol: str):
        """Update both price and fundamental data for a stock"""
        print(f"\n📊 Updating {symbol}...")
        
        # Fetch and save price data
        price_df = self.fetch_price_data(symbol)
        if not price_df.empty:
            self.save_price_data(price_df)
        
        # Fetch and save fundamental data
        fund_data = self.fetch_fundamental_data(symbol)
        self.save_fundamental_data(fund_data)
        
        time.sleep(1)  # Rate limiting
    
    def update_multiple_stocks(self, symbols: List[str]):
        """Update data for multiple stocks"""
        print(f"\n🔄 Updating {len(symbols)} stocks...")
        for symbol in symbols:
            self.update_stock(symbol)
        print("\n✅ Update complete!")
    
    def get_price_data(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """Retrieve price data from database"""
        query = f"""
            SELECT * FROM price_data 
            WHERE symbol = '{symbol}'
            ORDER BY date DESC
            LIMIT {days}
        """
        df = pd.read_sql_query(query, self.conn)
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values('date')
    
    def get_fundamental_data(self, symbol: str) -> Dict:
        """Retrieve fundamental data from database"""
        query = f"SELECT * FROM fundamental_data WHERE symbol = '{symbol}'"
        df = pd.read_sql_query(query, self.conn)
        return df.to_dict('records')[0] if not df.empty else {}


# ============================================================================
# COMPONENT 2: PATTERN DETECTION MODULE
# ============================================================================

class PatternDetection:
    """
    Detects technical chart patterns and formations
    """
    
    def __init__(self):
        self.patterns = []
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """MACD Indicator"""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, period: int = 20, std: float = 2) -> Dict:
        """Bollinger Bands"""
        sma = data.rolling(window=period).mean()
        rolling_std = data.rolling(window=period).std()
        
        return {
            'upper': sma + (rolling_std * std),
            'middle': sma,
            'lower': sma - (rolling_std * std)
        }
    
    def detect_support_resistance(self, df: pd.DataFrame, window: int = 20, threshold: float = 0.02) -> Dict:
        """
        Detect support and resistance levels
        
        Args:
            df: DataFrame with OHLC data
            window: Lookback window for local extrema
            threshold: Price similarity threshold (2% default)
        """
        highs = df['high'].values
        lows = df['low'].values
        
        # Find local maxima (resistance)
        resistance_levels = []
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i-window:i+window]):
                resistance_levels.append(highs[i])
        
        # Find local minima (support)
        support_levels = []
        for i in range(window, len(lows) - window):
            if lows[i] == min(lows[i-window:i+window]):
                support_levels.append(lows[i])
        
        # Cluster similar levels
        def cluster_levels(levels, threshold):
            if not levels:
                return []
            levels = sorted(levels)
            clusters = [[levels[0]]]
            for level in levels[1:]:
                if abs(level - np.mean(clusters[-1])) / np.mean(clusters[-1]) < threshold:
                    clusters[-1].append(level)
                else:
                    clusters.append([level])
            return [np.mean(cluster) for cluster in clusters]
        
        return {
            'support': cluster_levels(support_levels, threshold),
            'resistance': cluster_levels(resistance_levels, threshold)
        }
    
    def detect_breakout(self, df: pd.DataFrame, lookback: int = 20, volume_multiplier: float = 1.5) -> Dict:
        """
        Detect price breakouts with volume confirmation
        
        Returns dict with breakout signals and type
        """
        if len(df) < lookback + 1:
            return {'breakout': False, 'type': None}
        
        current = df.iloc[-1]
        recent = df.iloc[-lookback-1:-1]
        
        # Calculate levels
        resistance = recent['high'].max()
        support = recent['low'].min()
        avg_volume = recent['volume'].mean()
        
        # Price breakout conditions
        price_breakout_up = current['close'] > resistance
        price_breakout_down = current['close'] < support
        
        # Volume confirmation
        volume_surge = current['volume'] > (avg_volume * volume_multiplier)
        
        if price_breakout_up and volume_surge:
            return {
                'breakout': True,
                'type': 'bullish',
                'level': resistance,
                'volume_ratio': current['volume'] / avg_volume
            }
        elif price_breakout_down and volume_surge:
            return {
                'breakout': True,
                'type': 'bearish',
                'level': support,
                'volume_ratio': current['volume'] / avg_volume
            }
        else:
            return {'breakout': False, 'type': None}
    
    def detect_candlestick_patterns(self, df: pd.DataFrame) -> List[str]:
        """
        Detect common candlestick patterns
        Returns list of detected patterns
        """
        patterns = []
        
        if len(df) < 3:
            return patterns
        
        # Get last 3 candles
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        
        # Helper functions
        def is_bullish(candle):
            return candle['close'] > candle['open']
        
        def is_bearish(candle):
            return candle['close'] < candle['open']
        
        def body_size(candle):
            return abs(candle['close'] - candle['open'])
        
        def range_size(candle):
            return candle['high'] - candle['low']
        
        # Doji
        if body_size(c3) < range_size(c3) * 0.1:
            patterns.append('doji')
        
        # Hammer (bullish reversal)
        if (is_bullish(c3) and 
            (c3['high'] - c3['close']) < body_size(c3) * 0.3 and
            (c3['close'] - c3['low']) > body_size(c3) * 2):
            patterns.append('hammer')
        
        # Shooting Star (bearish reversal)
        if (is_bearish(c3) and 
            (c3['close'] - c3['low']) < body_size(c3) * 0.3 and
            (c3['high'] - c3['open']) > body_size(c3) * 2):
            patterns.append('shooting_star')
        
        # Bullish Engulfing
        if (is_bearish(c2) and is_bullish(c3) and
            c3['open'] < c2['close'] and c3['close'] > c2['open']):
            patterns.append('bullish_engulfing')
        
        # Bearish Engulfing
        if (is_bullish(c2) and is_bearish(c3) and
            c3['open'] > c2['close'] and c3['close'] < c2['open']):
            patterns.append('bearish_engulfing')
        
        # Morning Star (3-candle bullish reversal)
        if (is_bearish(c1) and body_size(c2) < body_size(c1) * 0.5 and
            is_bullish(c3) and c3['close'] > (c1['open'] + c1['close']) / 2):
            patterns.append('morning_star')
        
        # Evening Star (3-candle bearish reversal)
        if (is_bullish(c1) and body_size(c2) < body_size(c1) * 0.5 and
            is_bearish(c3) and c3['close'] < (c1['open'] + c1['close']) / 2):
            patterns.append('evening_star')
        
        return patterns
    
    def analyze_stock(self, df: pd.DataFrame) -> Dict:
        """
        Comprehensive technical analysis of a stock
        """
        if df.empty or len(df) < 50:
            return {}
        
        # Calculate indicators
        df['SMA_20'] = self.calculate_sma(df['close'], 20)
        df['SMA_50'] = self.calculate_sma(df['close'], 50)
        df['EMA_12'] = self.calculate_ema(df['close'], 12)
        df['RSI'] = self.calculate_rsi(df['close'])
        
        macd = self.calculate_macd(df['close'])
        df['MACD'] = macd['macd']
        df['MACD_Signal'] = macd['signal']
        
        bb = self.calculate_bollinger_bands(df['close'])
        df['BB_Upper'] = bb['upper']
        df['BB_Middle'] = bb['middle']
        df['BB_Lower'] = bb['lower']
        
        # Pattern detection
        support_resistance = self.detect_support_resistance(df)
        breakout = self.detect_breakout(df)
        candlestick = self.detect_candlestick_patterns(df)
        
        # Current values
        current = df.iloc[-1]
        
        return {
            'current_price': current['close'],
            'rsi': current['RSI'],
            'macd': current['MACD'],
            'macd_signal': current['MACD_Signal'],
            'sma_20': current['SMA_20'],
            'sma_50': current['SMA_50'],
            'trend': 'bullish' if current['SMA_20'] > current['SMA_50'] else 'bearish',
            'support_levels': support_resistance['support'],
            'resistance_levels': support_resistance['resistance'],
            'breakout': breakout,
            'candlestick_patterns': candlestick,
            'bollinger_position': self._bollinger_position(current),
            'volume_trend': 'increasing' if df['volume'].iloc[-5:].mean() > df['volume'].iloc[-20:].mean() else 'decreasing'
        }
    
    def _bollinger_position(self, row: pd.Series) -> str:
        """Determine position relative to Bollinger Bands"""
        if pd.isna(row['BB_Upper']) or pd.isna(row['BB_Lower']):
            return 'unknown'
        
        if row['close'] > row['BB_Upper']:
            return 'overbought'
        elif row['close'] < row['BB_Lower']:
            return 'oversold'
        else:
            return 'neutral'


# ============================================================================
# COMPONENT 3: BASIC STREAMLIT DASHBOARD
# ============================================================================

# Save this as a separate file: dashboard.py

"""
DASHBOARD CODE (dashboard.py):

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import the classes above
from finance_tool import DataIngestion, PatternDetection

st.set_page_config(page_title="Techno-Fundamental Analysis", layout="wide")

# Initialize
@st.cache_resource
def init_system():
    di = DataIngestion()
    pd_obj = PatternDetection()
    return di, pd_obj

di, pattern_detector = init_system()

st.title("📈 Techno-Fundamental Stock Analyzer")

# Sidebar
with st.sidebar:
    st.header("Settings")
    
    # Stock input
    symbol_input = st.text_input("Enter Stock Symbol", value="AAPL").upper()
    
    # Update data button
    if st.button("📥 Update Data"):
        with st.spinner(f"Fetching data for {symbol_input}..."):
            di.update_stock(symbol_input)
            st.success("Data updated!")
    
    # Filters
    st.subheader("Filters")
    show_support_resistance = st.checkbox("Show Support/Resistance", value=True)
    show_volume = st.checkbox("Show Volume", value=True)
    
    # Technical indicators
    st.subheader("Indicators")
    show_sma = st.checkbox("SMA (20, 50)", value=True)
    show_bollinger = st.checkbox("Bollinger Bands", value=False)
    show_rsi = st.checkbox("RSI", value=True)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Price Chart - {symbol_input}")
    
    # Get data
    df = di.get_price_data(symbol_input, days=365)
    
    if not df.empty:
        # Analyze
        analysis = pattern_detector.analyze_stock(df)
        
        # Create candlestick chart
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=('Price', 'Volume', 'RSI')
        )
        
        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df['date'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price'
            ),
            row=1, col=1
        )
        
        # SMAs
        if show_sma:
            fig.add_trace(go.Scatter(x=df['date'], y=df['SMA_20'], 
                                     name='SMA 20', line=dict(color='orange', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['date'], y=df['SMA_50'], 
                                     name='SMA 50', line=dict(color='blue', width=1)), row=1, col=1)
        
        # Bollinger Bands
        if show_bollinger:
            fig.add_trace(go.Scatter(x=df['date'], y=df['BB_Upper'], 
                                     name='BB Upper', line=dict(color='gray', dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['date'], y=df['BB_Lower'], 
                                     name='BB Lower', line=dict(color='gray', dash='dash')), row=1, col=1)
        
        # Support/Resistance
        if show_support_resistance and analysis:
            for level in analysis.get('support_levels', [])[:3]:
                fig.add_hline(y=level, line_dash="dash", line_color="green", 
                             annotation_text=f"Support: ${level:.2f}", row=1, col=1)
            for level in analysis.get('resistance_levels', [])[:3]:
                fig.add_hline(y=level, line_dash="dash", line_color="red", 
                             annotation_text=f"Resistance: ${level:.2f}", row=1, col=1)
        
        # Volume
        if show_volume:
            colors = ['red' if row['close'] < row['open'] else 'green' for _, row in df.iterrows()]
            fig.add_trace(
                go.Bar(x=df['date'], y=df['volume'], name='Volume', marker_color=colors),
                row=2, col=1
            )
        
        # RSI
        if show_rsi:
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['RSI'], name='RSI', line=dict(color='purple')),
                row=3, col=1
            )
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        
        fig.update_layout(height=800, showlegend=True, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"No data available for {symbol_input}. Click 'Update Data' to fetch.")

with col2:
    st.subheader("Analysis Summary")
    
    if not df.empty and analysis:
        # Current metrics
        st.metric("Current Price", f"${analysis['current_price']:.2f}")
        st.metric("RSI", f"{analysis['rsi']:.1f}")
        st.metric("Trend", analysis['trend'].upper())
        
        # Breakout detection
        st.subheader("🎯 Breakout Detection")
        breakout = analysis['breakout']
        if breakout['breakout']:
            st.success(f"**{breakout['type'].upper()} BREAKOUT DETECTED!**")
            st.write(f"Level: ${breakout['level']:.2f}")
            st.write(f"Volume Surge: {breakout['volume_ratio']:.1f}x")
        else:
            st.info("No breakout detected")
        
        # Candlestick patterns
        st.subheader("📊 Patterns")
        patterns = analysis['candlestick_patterns']
        if patterns:
            for pattern in patterns:
                st.write(f"✓ {pattern.replace('_', ' ').title()}")
        else:
            st.write("No patterns detected")
        
        # Bollinger position
        st.subheader("📍 Position")
        st.write(f"Bollinger: {analysis['bollinger_position'].title()}")
        st.write(f"Volume: {analysis['volume_trend'].title()}")
        
        # Fundamental data
        st.subheader("💼 Fundamentals")
        fund_data = di.get_fundamental_data(symbol_input)
        if fund_data:
            if fund_data.get('pe_ratio'):
                st.write(f"P/E Ratio: {fund_data['pe_ratio']:.2f}")
            if fund_data.get('roe'):
                st.write(f"ROE: {fund_data['roe']*100:.1f}%")
            if fund_data.get('debt_to_equity'):
                st.write(f"D/E: {fund_data['debt_to_equity']:.2f}")

# Run with: streamlit run dashboard.py
"""


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize
    di = DataIngestion()
    pattern = PatternDetection()
    
    # Example: Update data for stocks
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
    di.update_multiple_stocks(symbols)
    
    # Example: Analyze a stock
    print("\n" + "="*60)
    print("TECHNICAL ANALYSIS FOR AAPL")
    print("="*60)
    
    df = di.get_price_data("AAPL", days=180)
    analysis = pattern.analyze_stock(df)
    
    print(f"\nCurrent Price: ${analysis['current_price']:.2f}")
    print(f"Trend: {analysis['trend'].upper()}")
    print(f"RSI: {analysis['rsi']:.1f}")
    print(f"\nSupport Levels: {[f'${x:.2f}' for x in analysis['support_levels'][:3]]}")
    print(f"Resistance Levels: {[f'${x:.2f}' for x in analysis['resistance_levels'][:3]]}")
    
    breakout = analysis['breakout']
    if breakout['breakout']:
        print(f"\n🎯 BREAKOUT DETECTED: {breakout['type'].upper()}")
        print(f"   Level: ${breakout['level']:.2f}")
        print(f"   Volume: {breakout['volume_ratio']:.1f}x average")
    
    if analysis['candlestick_patterns']:
        print(f"\n📊 Patterns: {', '.join(analysis['candlestick_patterns'])}")
    
    print("\n" + "="*60)