import os
from math import ceil
from typing import Optional
from flask import Flask, render_template, request
from tradingbuddy.core import DataIngestion
from tradingbuddy.features.patterns import PatternDetection
from tradingbuddy.features.technical import add_indicators
from plotly import graph_objs as go
from plotly.offline import plot


def create_app(db_path: Optional[str] = None):
    package_dir = os.path.dirname(__file__)
    templates_dir = os.path.join(package_dir, 'templates')
    static_dir = os.path.join(package_dir, 'static')

    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    default_db = os.path.join(os.path.dirname(__file__), '..', '..', 'financial_data.db')
    DATABASE = db_path or default_db

    # application singletons
    app.di = DataIngestion(db_path=DATABASE)
    app.pd = PatternDetection()

    # map friendly periods to yfinance periods
    PERIOD_MAP = {
        '1d': '1d',
        '1w': '7d',
        '1m': '1mo',
        '6m': '6mo',
        '1y': '1y',
        '3y': '3y',
        '5y': '5y',
        'max': 'max'
    }


    @app.route('/')
    def index():
        symbol = request.args.get('symbol', 'AAPL').upper()
        period_key = request.args.get('period', '1y')
        period = PERIOD_MAP.get(period_key, '1y')

        # Try get from DB first (use a reasonable days mapping)
        days_map = {
            '1d': 1,
            '1w': 7,
            '1m': 30,
            '6m': 180,
            '1y': 365,
            '3y': 365 * 3,
            '5y': 365 * 5,
            'max': 365 * 10,
        }
        days = days_map.get(period_key, 365)

        df = app.di.get_price_data(symbol, days=days)
        if df is None or df.empty:
            # fetch and save
            price_df = app.di.fetch_price_data(symbol, period=period)
            if price_df is not None and not price_df.empty:
                app.di.save_price_data(price_df)
                df = app.di.get_price_data(symbol, days=days)

        chart_div = ""
        info = {}
        if df is not None and not df.empty:
            # Ensure the required columns exist
            if {'date', 'open', 'high', 'low', 'close'}.issubset(set(df.columns)):
                fig = go.Figure(
                    data=[
                        go.Candlestick(
                            x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close']
                        )
                    ]
                )
                fig.update_layout(title=f"{symbol} price ({period_key})")
                chart_div = plot(fig, output_type='div', include_plotlyjs=False)

                # compute small info panel
                try:
                    last_close = float(df['close'].iloc[-1])
                    prev_close = float(df['close'].iloc[-2]) if len(df) > 1 else None
                    pct = ((last_close - prev_close) / prev_close * 100) if prev_close else None
                    volume = int(df['volume'].iloc[-1]) if 'volume' in df.columns else None
                    df_ind = add_indicators(df.copy())
                    rsi = float(df_ind['rsi'].iloc[-1]) if 'rsi' in df_ind.columns else None
                    sma20 = df_ind['sma_20'].iloc[-1] if 'sma_20' in df_ind.columns else None
                    sma50 = df_ind['sma_50'].iloc[-1] if 'sma_50' in df_ind.columns else None
                    if sma20 is not None and sma50 is not None:
                        sma_cross = 'above' if sma20 > sma50 else 'below'
                    else:
                        sma_cross = None
                    info = {
                        'last_close': last_close,
                        'pct_change': pct,
                        'volume': volume,
                        'rsi': rsi,
                        'sma_cross': sma_cross,
                    }
                except Exception:
                    info = {}

        # periods list for template
        periods = list(PERIOD_MAP.keys())

        return render_template('main.html', chart_div=chart_div, symbol=symbol, period_key=period_key, periods=periods, info=info)


    @app.route('/breakouts')
    def breakouts():
        lookback = int(request.args.get('lookback', 30))
        volume_multiplier = float(request.args.get('volume_multiplier', 1.5))
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))
        sort_by = request.args.get('sort_by', 'symbol')
        sort_dir = request.args.get('sort_dir', 'asc')

        symbols = app.di.list_symbols()
        results = []
        for s in symbols:
            df = app.di.get_price_data(s, days=lookback)
            if df is None or df.empty:
                continue

            # compute indicators for metrics
            df_ind = add_indicators(df.copy())
            last_close = float(df_ind['close'].iloc[-1])
            prev_close = float(df_ind['close'].iloc[-2]) if len(df_ind) > 1 else None
            pct = ((last_close - prev_close) / prev_close * 100) if prev_close else None
            rsi = float(df_ind['rsi'].iloc[-1]) if 'rsi' in df_ind.columns else None
            sma20 = df_ind['sma_20'].iloc[-1] if 'sma_20' in df_ind.columns else None
            sma50 = df_ind['sma_50'].iloc[-1] if 'sma_50' in df_ind.columns else None
            sma_cross = None
            if sma20 is not None and sma50 is not None:
                sma_cross = 'above' if sma20 > sma50 else 'below'

            # Use the feature PatternDetection
            res = app.pd.detect_breakout(df, lookback=lookback, volume_multiplier=volume_multiplier)
            if isinstance(res, dict):
                rec = {'symbol': s, **res}
            else:
                rec = {'symbol': s, 'result': res}

            # attach metrics
            rec['pct_change'] = round(pct, 2) if pct is not None else None
            rec['rsi'] = round(rsi, 2) if rsi is not None else None
            rec['sma_cross'] = sma_cross

            results.append(rec)

        # Build metrics columns if missing
        for r in results:
            r.setdefault('result', 'none')
            r.setdefault('level', None)
            r.setdefault('volume_ratio', None)

        # Sorting
        reverse = sort_dir == 'desc'
        results.sort(key=lambda x: (x.get(sort_by) is None, x.get(sort_by)), reverse=reverse)

        # Pagination
        total = len(results)
        total_pages = max(1, ceil(total / page_size))
        start = (page - 1) * page_size
        end = start + page_size
        page_items = results[start:end]

        return render_template(
            'breakouts.html',
            items=page_items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            sort_by=sort_by,
            sort_dir=sort_dir,
            lookback=lookback,
            volume_multiplier=volume_multiplier,
        )

    return app


app = create_app()


if __name__ == '__main__':
    # Run the dev server when executed as a module: python -m tradingbuddy.api.flask_app
    app.run(host='127.0.0.1', port=5000, debug=True)
