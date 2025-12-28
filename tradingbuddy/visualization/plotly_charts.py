"""Plotly chart generation for breakout analysis with custom annotations"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Optional


def create_breakout_chart(symbol: str, pattern_data: Dict, price_df: pd.DataFrame) -> str:
    """
    Generate interactive Plotly chart with breakout annotations.
    
    Args:
        symbol: Stock ticker symbol
        pattern_data: Dictionary with pattern info (pattern_type, resistance_level, support_level, etc.)
        price_df: DataFrame with OHLC data (must have 'open', 'high', 'low', 'close', 'volume' columns)
    
    Returns:
        HTML string of the Plotly chart
    """
    # Create figure with secondary y-axis for volume
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{symbol} - {pattern_data.get('pattern_type', 'Breakout').replace('_', ' ').title()}", 'Volume')
    )
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=price_df.index,
            open=price_df['open'],
            high=price_df['high'],
            low=price_df['low'],
            close=price_df['close'],
            name=symbol,
            increasing_line_color='#10b981',
            decreasing_line_color='#ef4444'
        ),
        row=1, col=1
    )
    
    # Add volume bars
    colors = ['#10b981' if close >= open else '#ef4444' 
              for close, open in zip(price_df['close'], price_df['open'])]
    
    fig.add_trace(
        go.Bar(
            x=price_df.index,
            y=price_df['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.5
        ),
        row=2, col=1
    )
    
    # Add breakout/resistance level
    if pattern_data.get('resistance_level'):
        resistance = pattern_data['resistance_level']
        fig.add_shape(
            type="line",
            x0=price_df.index[0],
            x1=price_df.index[-1],
            y0=resistance,
            y1=resistance,
            line=dict(color="#10b981", width=2, dash="dash"),
            row=1, col=1
        )
        
        # Add annotation for resistance
        fig.add_annotation(
            x=price_df.index[-1],
            y=resistance,
            text=f"Breakout: ${resistance:.2f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#10b981",
            bgcolor="#10b981",
            font=dict(color="white", size=11),
            row=1, col=1
        )
    
    # Add support level
    if pattern_data.get('support_level'):
        support = pattern_data['support_level']
        fig.add_shape(
            type="line",
            x0=price_df.index[0],
            x1=price_df.index[-1],
            y0=support,
            y1=support,
            line=dict(color="#ef4444", width=2, dash="dash"),
            row=1, col=1
        )
        
        # Add annotation for support
        fig.add_annotation(
            x=price_df.index[-1],
            y=support,
            text=f"Support: ${support:.2f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#ef4444",
            bgcolor="#ef4444",
            font=dict(color="white", size=11),
            row=1, col=1
        )
    
    # Add entry price marker if available
    if pattern_data.get('entry_price') and pattern_data.get('breakout_date'):
        entry_price = pattern_data['entry_price']
        try:
            breakout_date = pd.to_datetime(pattern_data['breakout_date'])
            if breakout_date in price_df.index:
                fig.add_trace(
                    go.Scatter(
                        x=[breakout_date],
                        y=[entry_price],
                        mode='markers',
                        marker=dict(
                            size=15,
                            color='#3b82f6',
                            symbol='star',
                            line=dict(color='white', width=2)
                        ),
                        name='Entry Point',
                        showlegend=True
                    ),
                    row=1, col=1
                )
        except:
            pass
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f"{symbol} - {pattern_data.get('description', 'Breakout Pattern')}",
            font=dict(size=16, color='#e5e7eb')
        ),
        template="plotly_dark",
        height=600,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        paper_bgcolor='#0f172a',
        plot_bgcolor='#1a1f2e',
        font=dict(color='#e5e7eb')
    )
    
    # Update axes
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='#2a2e3a',
        row=1, col=1
    )
    fig.update_yaxes(
        title_text="Price ($)",
        showgrid=True,
        gridwidth=1,
        gridcolor='#2a2e3a',
        row=1, col=1
    )
    fig.update_yaxes(
        title_text="Volume",
        showgrid=False,
        row=2, col=1
    )
    
    # Return HTML
    return fig.to_html(
        full_html=False,
        include_plotlyjs='cdn',
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d']
        }
    )


def create_simple_chart(symbol: str, price_df: pd.DataFrame, title: Optional[str] = None) -> str:
    """
    Generate a simple Plotly candlestick chart without annotations.
    
    Args:
        symbol: Stock ticker symbol
        price_df: DataFrame with OHLC data
        title: Optional custom title
    
    Returns:
        HTML string of the Plotly chart
    """
    fig = go.Figure(data=[go.Candlestick(
        x=price_df.index,
        open=price_df['open'],
        high=price_df['high'],
        low=price_df['low'],
        close=price_df['close'],
        name=symbol,
        increasing_line_color='#10b981',
        decreasing_line_color='#ef4444'
    )])
    
    fig.update_layout(
        title=title or f"{symbol} Price Chart",
        template="plotly_dark",
        height=500,
        xaxis_rangeslider_visible=False,
        paper_bgcolor='#0f172a',
        plot_bgcolor='#1a1f2e',
        font=dict(color='#e5e7eb')
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#2a2e3a')
    fig.update_yaxes(title_text="Price ($)", showgrid=True, gridwidth=1, gridcolor='#2a2e3a')
    
    return fig.to_html(
        full_html=False,
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'displaylogo': False}
    )
