"""Stock information utilities for fetching detailed stock data"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional


def get_stock_exchange(symbol: str) -> str:
    """
    Get the exchange where a stock is listed (NYSE, NASDAQ, etc).
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Exchange code (e.g., 'NYSE', 'NASDAQ', 'AMEX') or empty string if unknown
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Try to get exchange from info
        exchange = info.get('exchange', '')
        
        # Map common exchanges to TradingView format
        exchange_map = {
            'NMS': 'NASDAQ',  # NASDAQ Global Market
            'NGM': 'NASDAQ',  # NASDAQ Global Market
            'NCM': 'NASDAQ',  # NASDAQ Capital Market
            'NYQ': 'NYSE',    # NYSE
            'ASE': 'AMEX',    # American Stock Exchange
            'PCX': 'ARCA',    # NYSE Arca
        }
        
        return exchange_map.get(exchange, exchange if exchange else 'NASDAQ')
    
    except Exception:
        # Default to NASDAQ if can't determine
        return 'NASDAQ'


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    Calculate RSI (Relative Strength Index) for a price series.
    
    Args:
        prices: Series of closing prices
        period: RSI period (default 14)
        
    Returns:
        Current RSI value (0-100)
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral if not enough data
    
    try:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    
    except Exception:
        return 50.0


def get_stock_info(symbol: str, data_ingestion=None) -> Dict:
    """
    Get comprehensive stock information including price data and fundamentals.
    
    Args:
        symbol: Stock ticker symbol
        data_ingestion: Optional DataIngestion instance for cached data
        
    Returns:
        Dictionary with stock information
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get historical data for calculations
        if data_ingestion:
            df = data_ingestion.get_price_data(symbol, days=90)
            if df is None or df.empty:
                # Fetch fresh data
                hist = ticker.history(period='3mo')
            else:
                hist = df.set_index('date') if 'date' in df.columns else df
        else:
            hist = ticker.history(period='3mo')
        
        # Get latest OHLC
        if not hist.empty:
            latest = hist.iloc[-1]
            open_price = float(latest.get('Open', latest.get('open', 0)))
            high_price = float(latest.get('High', latest.get('high', 0)))
            low_price = float(latest.get('Low', latest.get('low', 0)))
            close_price = float(latest.get('Close', latest.get('close', 0)))
            volume = int(latest.get('Volume', latest.get('volume', 0)))
            
            # Calculate RSI
            close_col = 'Close' if 'Close' in hist.columns else 'close'
            rsi = calculate_rsi(hist[close_col], period=14)
        else:
            open_price = high_price = low_price = close_price = 0
            volume = 0
            rsi = 50.0
        
        # Get fundamental data
        market_cap = info.get('marketCap', 0)
        pe_ratio = info.get('trailingPE', info.get('forwardPE', 0))
        week_52_high = info.get('fiftyTwoWeekHigh', 0)
        week_52_low = info.get('fiftyTwoWeekLow', 0)
        avg_volume = info.get('averageVolume', 0)
        company_name = info.get('longName', info.get('shortName', symbol))
        exchange = get_stock_exchange(symbol)
        
        # Get analyst recommendations if available
        recommendations = []
        try:
            rec_data = ticker.recommendations
            if rec_data is not None and not rec_data.empty:
                # Get last 10 recommendations
                recent_recs = rec_data.tail(15)
                for idx, row in recent_recs.iterrows():
                    recommendations.append({
                        'firm': row.get('Firm', 'Unknown'),
                        'to_grade': row.get('To Grade', 'N/A'),
                        'from_grade': row.get('From Grade', ''),
                        'action': row.get('Action', 'Maintain')
                    })
        except Exception:
            pass
        
        return {
            'symbol': symbol,
            'company_name': company_name,
            'exchange': exchange,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume,
            'avg_volume': avg_volume,
            'rsi_14': round(rsi, 2),
            'market_cap': market_cap,
            'pe_ratio': round(pe_ratio, 2) if pe_ratio else None,
            'week_52_high': round(week_52_high, 2) if week_52_high else None,
            'week_52_low': round(week_52_low, 2) if week_52_low else None,
            'recommendations': recommendations
        }
    
    except Exception as e:
        return {
            'symbol': symbol,
            'error': str(e),
            'company_name': symbol,
            'exchange': 'NASDAQ',
            'open': 0,
            'high': 0,
            'low': 0,
            'close': 0,
            'volume': 0,
            'avg_volume': 0,
            'rsi_14': 50.0,
            'market_cap': 0,
            'pe_ratio': None,
            'week_52_high': None,
            'week_52_low': None,
            'recommendations': []
        }
