import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import helper classes from the tradingbuddy package wrapper
from tradingbuddy import DataIngestion, PatternDetection
from features.technical import add_indicators

st.set_page_config(page_title="Techno-Fundamental Analysis", layout="wide")

@st.cache_resource
def init_system():
    di = DataIngestion()
    pd_obj = PatternDetection()
    return di, pd_obj


di, pattern_detector = init_system()

st.title("📈 Techno-Fundamental Stock Analyzer")

with st.sidebar:
    st.header("Settings")
    symbol_input = st.text_input("Enter Stock Symbol", value="AAPL").upper()
    if st.button("📥 Update Data"):
        with st.spinner(f"Fetching data for {symbol_input}..."):
            di.update_stock(symbol_input)
            st.success("Data updated!")

    show_sma = st.checkbox("SMA (20,50)", value=True)
    show_bollinger = st.checkbox("Bollinger Bands", value=False)
    show_rsi = st.checkbox("RSI", value=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Price Chart - {symbol_input}")
    df = di.get_price_data(symbol_input, days=365)
    if df.empty:
        st.warning(f"No data available for {symbol_input}. Click 'Update Data' to fetch.")
    else:
        df = df.copy()
        # Normalize columns (some sources return capitalized names)
        df.columns = [c.lower() for c in df.columns]
        df = add_indicators(df)
        analysis = pattern_detector.analyze_stock(df)

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                            row_heights=[0.6, 0.2, 0.2])
        fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'), row=1, col=1)

        if show_sma:
            fig.add_trace(go.Scatter(x=df['date'], y=df['sma_20'] if 'sma_20' in df.columns else df['SMA_20'], name='SMA 20', line=dict(color='orange', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['date'], y=df['sma_50'] if 'sma_50' in df.columns else df['SMA_50'], name='SMA 50', line=dict(color='blue', width=1)), row=1, col=1)

        if show_bollinger:
            if 'bb_upper' in df.columns:
                fig.add_trace(go.Scatter(x=df['date'], y=df['bb_upper'], name='BB Upper', line=dict(color='gray', dash='dash')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df['date'], y=df['bb_lower'], name='BB Lower', line=dict(color='gray', dash='dash')), row=1, col=1)

        colors = ['red' if row['close'] < row['open'] else 'green' for _, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df['date'], y=df['volume'], name='Volume', marker_color=colors), row=2, col=1)

        if show_rsi and 'RSI' in df.columns:
            fig.add_trace(go.Scatter(x=df['date'], y=df['RSI'], name='RSI', line=dict(color='purple')), row=3, col=1)
            fig.add_hline(y=70, line_dash='dash', line_color='red', row=3, col=1)
            fig.add_hline(y=30, line_dash='dash', line_color='green', row=3, col=1)

        fig.update_layout(height=800, showlegend=True, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Analysis Summary")
    if not df.empty and analysis:
        st.metric("Current Price", f"${analysis['current_price']:.2f}")
        st.metric("RSI", f"{analysis['rsi']:.1f}")
        st.metric("Trend", analysis['trend'].upper())

        breakout = analysis['breakout']
        if breakout.get('breakout'):
            st.success(f"**{breakout['type'].upper()} BREAKOUT DETECTED!**")
            st.write(f"Level: ${breakout.get('level',0):.2f}")
        else:
            st.info("No breakout detected")

        st.subheader("📊 Patterns")
        patterns = analysis.get('candlestick_patterns', [])
        if patterns:
            for pattern in patterns:
                st.write(f"✓ {pattern.replace('_', ' ').title()}")
        else:
            st.write("No patterns detected")

        st.subheader("💼 Fundamentals")
        fund_data = di.get_fundamental_data(symbol_input)
        if fund_data:
            if fund_data.get('pe_ratio') is not None:
                st.write(f"P/E Ratio: {fund_data['pe_ratio']}")
            if fund_data.get('roe') is not None:
                try:
                    st.write(f"ROE: {fund_data['roe']*100:.1f}%")
                except Exception:
                    st.write(f"ROE: {fund_data['roe']}")
