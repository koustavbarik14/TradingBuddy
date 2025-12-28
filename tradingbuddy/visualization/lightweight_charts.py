"""TradingView Lightweight Charts generation for breakout analysis"""
import json
from typing import Dict, List
import pandas as pd


def create_lightweight_chart(symbol: str, pattern_data: Dict, price_df: pd.DataFrame) -> str:
    """
    Generate TradingView Lightweight Charts HTML with breakout annotations.
    
    This uses the official TradingView Lightweight Charts library which is:
    - Lightweight and fast
    - Designed specifically for financial charts
    - Highly performant even with large datasets
    - Better than Plotly for real-time trading data
    
    Args:
        symbol: Stock ticker symbol
        pattern_data: Dictionary with pattern info
        price_df: DataFrame with OHLC data
    
    Returns:
        HTML string with embedded lightweight chart
    """
    # Prepare candlestick data
    candles = []
    for idx, row in price_df.iterrows():
        candles.append({
            'time': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })
    
    # Prepare volume data
    volumes = []
    for idx, row in price_df.iterrows():
        volumes.append({
            'time': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
            'value': float(row['volume']),
            'color': '#26a69a' if row['close'] >= row['open'] else '#ef5350'
        })
    
    # Prepare marker for entry point
    markers = []
    if pattern_data.get('entry_price') and pattern_data.get('breakout_date'):
        markers.append({
            'time': pattern_data['breakout_date'],
            'position': 'belowBar',
            'color': '#2196F3',
            'shape': 'arrowUp',
            'text': f"Entry: ${pattern_data['entry_price']:.2f}"
        })
    
    # Prepare price lines for support/resistance
    resistance = pattern_data.get('resistance_level')
    support = pattern_data.get('support_level')
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} - Breakout Analysis</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #0f172a;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        #chart-container {{
            width: 100%;
            height: 600px;
            position: relative;
        }}
        .chart-info {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(15, 23, 42, 0.9);
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid #334155;
            color: #e5e7eb;
            z-index: 100;
            font-size: 13px;
        }}
        .chart-info h3 {{
            margin: 0 0 8px 0;
            font-size: 16px;
            color: #3b82f6;
        }}
        .chart-info div {{
            margin: 4px 0;
        }}
        .resistance {{
            color: #10b981;
            font-weight: 600;
        }}
        .support {{
            color: #ef4444;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div id="chart-container">
        <div class="chart-info">
            <h3>{symbol} - {pattern_data.get('pattern_type', 'Breakout').replace('_', ' ').title()}</h3>
            <div>{pattern_data.get('description', '')}</div>
            {f'<div class="resistance">Resistance: ${resistance:.2f}</div>' if resistance else ''}
            {f'<div class="support">Support: ${support:.2f}</div>' if support else ''}
        </div>
    </div>
    
    <script>
        const chartContainer = document.getElementById('chart-container');
        
        // Create chart
        const chart = LightweightCharts.createChart(chartContainer, {{
            layout: {{
                background: {{ color: '#0f172a' }},
                textColor: '#9ca3af',
            }},
            grid: {{
                vertLines: {{ color: '#1e293b' }},
                horzLines: {{ color: '#1e293b' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            rightPriceScale: {{
                borderColor: '#334155',
            }},
            timeScale: {{
                borderColor: '#334155',
                timeVisible: true,
            }},
            width: chartContainer.offsetWidth,
            height: 500,
        }});
        
        // Add candlestick series
        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        }});
        
        // Set candlestick data
        const candleData = {json.dumps(candles)};
        candlestickSeries.setData(candleData);
        
        // Add markers
        const markers = {json.dumps(markers)};
        if (markers.length > 0) {{
            candlestickSeries.setMarkers(markers);
        }}
        
        // Add volume series
        const volumeSeries = chart.addHistogramSeries({{
            color: '#26a69a',
            priceFormat: {{
                type: 'volume',
            }},
            priceScaleId: 'volume',
            scaleMargins: {{
                top: 0.8,
                bottom: 0,
            }},
        }});
        
        const volumeData = {json.dumps(volumes)};
        volumeSeries.setData(volumeData);
        
        // Add resistance line
        {f'''
        candlestickSeries.createPriceLine({{
            price: {resistance},
            color: '#10b981',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'Resistance',
        }});
        ''' if resistance else ''}
        
        // Add support line
        {f'''
        candlestickSeries.createPriceLine({{
            price: {support},
            color: '#ef4444',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'Support',
        }});
        ''' if support else ''}
        
        // Auto-resize
        window.addEventListener('resize', () => {{
            chart.applyOptions({{
                width: chartContainer.offsetWidth,
            }});
        }});
        
        // Fit content
        chart.timeScale().fitContent();
    </script>
</body>
</html>
    """
    
    return html


def create_lightweight_chart_embedded(symbol: str, pattern_data: Dict, price_df: pd.DataFrame) -> str:
    """
    Generate embedded TradingView Lightweight Charts (for injection into existing page).
    
    Returns just the chart div and script without full HTML structure.
    """
    # Prepare data (same as above)
    candles = []
    for idx, row in price_df.iterrows():
        candles.append({
            'time': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })
    
    volumes = []
    for idx, row in price_df.iterrows():
        volumes.append({
            'time': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
            'value': float(row['volume']),
            'color': '#26a69a' if row['close'] >= row['open'] else '#ef5350'
        })
    
    markers = []
    if pattern_data.get('entry_price') and pattern_data.get('breakout_date'):
        markers.append({
            'time': pattern_data['breakout_date'],
            'position': 'belowBar',
            'color': '#2196F3',
            'shape': 'arrowUp',
            'text': f"Entry: ${pattern_data['entry_price']:.2f}"
        })
    
    resistance = pattern_data.get('resistance_level')
    support = pattern_data.get('support_level')
    
    # Generate embedded HTML
    html = f"""
<div id="lwc-chart" style="width:100%;height:500px;position:relative;">
    <div style="position:absolute;top:10px;left:10px;background:rgba(15,23,42,0.95);padding:12px 16px;border-radius:8px;border:1px solid #334155;color:#e5e7eb;z-index:100;font-size:13px;">
        <h3 style="margin:0 0 8px 0;font-size:16px;color:#3b82f6;">{symbol} - {pattern_data.get('pattern_type', 'Breakout').replace('_', ' ').title()}</h3>
        <div style="margin:4px 0;">{pattern_data.get('description', '')}</div>
        {f'<div style="color:#10b981;font-weight:600;margin:4px 0;">Resistance: ${resistance:.2f}</div>' if resistance else ''}
        {f'<div style="color:#ef4444;font-weight:600;margin:4px 0;">Support: ${support:.2f}</div>' if support else ''}
    </div>
</div>

<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function() {{
    const container = document.getElementById('lwc-chart');
    const chart = LightweightCharts.createChart(container, {{
        layout: {{
            background: {{ color: '#0f172a' }},
            textColor: '#9ca3af',
        }},
        grid: {{
            vertLines: {{ color: '#1e293b' }},
            horzLines: {{ color: '#1e293b' }},
        }},
        crosshair: {{
            mode: LightweightCharts.CrosshairMode.Normal,
        }},
        rightPriceScale: {{
            borderColor: '#334155',
        }},
        timeScale: {{
            borderColor: '#334155',
            timeVisible: true,
        }},
        width: container.offsetWidth,
        height: 500,
    }});
    
    const candlestickSeries = chart.addCandlestickSeries({{
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
    }});
    
    candlestickSeries.setData({json.dumps(candles)});
    
    const markers = {json.dumps(markers)};
    if (markers.length > 0) {{
        candlestickSeries.setMarkers(markers);
    }}
    
    const volumeSeries = chart.addHistogramSeries({{
        color: '#26a69a',
        priceFormat: {{ type: 'volume' }},
        priceScaleId: 'volume',
        scaleMargins: {{ top: 0.8, bottom: 0 }},
    }});
    
    volumeSeries.setData({json.dumps(volumes)});
    
    {f'''
    candlestickSeries.createPriceLine({{
        price: {resistance},
        color: '#10b981',
        lineWidth: 2,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        axisLabelVisible: true,
        title: 'Resistance',
    }});
    ''' if resistance else ''}
    
    {f'''
    candlestickSeries.createPriceLine({{
        price: {support},
        color: '#ef4444',
        lineWidth: 2,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        axisLabelVisible: true,
        title: 'Support',
    }});
    ''' if support else ''}
    
    window.addEventListener('resize', () => {{
        chart.applyOptions({{ width: container.offsetWidth }});
    }});
    
    chart.timeScale().fitContent();
}})();
</script>
"""
    
    return html
