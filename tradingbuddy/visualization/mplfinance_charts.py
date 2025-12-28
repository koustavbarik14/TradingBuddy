"""
Static chart generator for breakout patterns using matplotlib and mplfinance.
Generates PNG images with annotated support/resistance levels and pattern markers.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
import mplfinance as mpf
from io import BytesIO
import base64
from typing import Optional, Dict, Any


def create_pattern_chart(symbol: str, df: pd.DataFrame, pattern_data: Dict[str, Any]) -> str:
    """
    Create a static candlestick chart with pattern annotations.
    
    Args:
        symbol: Stock ticker symbol
        df: DataFrame with OHLC data (columns: open, high, low, close, volume)
        pattern_data: Dict with pattern info (resistance, support, entry_price, breakout_date, pattern_type, description)
    
    Returns:
        Base64 encoded PNG image string (for embedding in HTML)
    """
    try:
        # Prepare data - last 60 days for visibility
        df = df.tail(60).copy()
        
        # Ensure proper index
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # Normalize column names
        df.columns = [c.lower() for c in df.columns]
        
        # Rename for mplfinance compatibility
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        # Extract pattern info
        resistance = pattern_data.get('resistance_level') or pattern_data.get('resistance')
        support = pattern_data.get('support_level') or pattern_data.get('support')
        entry_price = pattern_data.get('entry_price')
        breakout_date = pattern_data.get('breakout_date')
        pattern_type = pattern_data.get('pattern_type', 'Breakout')
        timeframe = pattern_data.get('timeframe', 'daily').upper()  # Get timeframe
        
        # Create horizontal lines for support/resistance
        hlines = []
        colors = []
        linewidths = []
        
        if resistance:
            hlines.append(resistance)
            colors.append('red')
            linewidths.append(1.5)
        
        if support:
            hlines.append(support)
            colors.append('green')
            linewidths.append(1.5)
        
        if entry_price and entry_price not in hlines:
            hlines.append(entry_price)
            colors.append('yellow')
            linewidths.append(2)
        
        # Create custom style
        mc = mpf.make_marketcolors(
            up='#26a69a',
            down='#ef5350',
            edge='inherit',
            wick='inherit',
            volume='in',
            alpha=0.9
        )
        
        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='-',
            gridcolor='#2d2d2d',
            facecolor='#1a1a1a',
            figcolor='#0f172a',
            edgecolor='#2d2d2d',
            rc={
                'font.size': 8,
                'axes.labelsize': 9,
                'axes.titlesize': 10,
                'xtick.labelsize': 8,
                'ytick.labelsize': 8,
                'axes.edgecolor': '#2d2d2d',
                'axes.labelcolor': '#9ca3af',
                'text.color': '#9ca3af',
                'xtick.color': '#9ca3af',
                'ytick.color': '#9ca3af'
            }
        )
        
        # Create the plot
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=style,
            volume=True,
            hlines=dict(hlines=hlines, colors=colors, linewidths=linewidths) if hlines else None,
            title=f"{symbol} - {pattern_type} ({timeframe})",
            ylabel='Price ($)',
            ylabel_lower='Volume',
            figsize=(10, 6),
            returnfig=True,
            warn_too_much_data=100000
        )
        
        # Add legend for lines
        ax = axes[0]
        legend_elements = []
        
        if resistance:
            legend_elements.append(plt.Line2D([0], [0], color='red', lw=1.5, label=f'Resistance: ${resistance:.2f}'))
        if support:
            legend_elements.append(plt.Line2D([0], [0], color='green', lw=1.5, label=f'Support: ${support:.2f}'))
        if entry_price:
            legend_elements.append(plt.Line2D([0], [0], color='yellow', lw=2, label=f'Entry: ${entry_price:.2f}'))
        
        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper left', fontsize=8, 
                     facecolor='#1a1a1a', edgecolor='#2d2d2d', labelcolor='#9ca3af')
        
        # Add breakout date marker if available
        if breakout_date:
            try:
                breakout_idx = pd.to_datetime(breakout_date)
                if breakout_idx in df.index:
                    idx_pos = df.index.get_loc(breakout_idx)
                    price = df.loc[breakout_idx, 'High']
                    ax.annotate('⬆ BREAKOUT', xy=(idx_pos, price), 
                               xytext=(idx_pos, price * 1.03),
                               fontsize=8, color='yellow', weight='bold',
                               ha='center',
                               arrowprops=dict(arrowstyle='->', color='yellow', lw=1.5))
            except Exception:
                pass
        
        # Convert to base64 PNG
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight', 
                   facecolor='#0f172a', edgecolor='none')
        plt.close(fig)
        
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return f"data:image/png;base64,{image_base64}"
    
    except Exception as e:
        # Return error placeholder
        print(f"Error creating chart for {symbol}: {e}")
        return None


def create_simple_chart(symbol: str, df: pd.DataFrame) -> str:
    """
    Create a simple candlestick chart without pattern annotations.
    
    Args:
        symbol: Stock ticker symbol
        df: DataFrame with OHLC data
    
    Returns:
        Base64 encoded PNG image string
    """
    return create_pattern_chart(symbol, df, {})
