import os
from math import ceil
from typing import Optional
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread
import math
import requests
import os
import pandas as pd
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

    # Load .env from project root if present (simple parser) so backend can pick up keys
    try:
        project_root = os.path.abspath(os.path.join(package_dir, '..', '..'))
        env_path = os.path.join(project_root, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip('"\'')
                    # only set if not already in environment
                    if k and (k not in os.environ):
                        os.environ[k] = v
    except Exception:
        # non-fatal; continue without .env
        pass

    default_db = os.path.join(os.path.dirname(__file__), '..', '..', 'financial_data.db')
    DATABASE = db_path or default_db

    # application singletons
    app.di = DataIngestion(db_path=DATABASE)
    app.pd = PatternDetection()

    # Setup a background scheduler to run daily updates (APScheduler)
    scheduler = BackgroundScheduler()
    app.scheduler = scheduler

    def _daily_update_job():
        try:
            app.logger.info('Scheduled daily update started')
            # Use the default universe to bulk update
            app.di.update_multiple_stocks(DEFAULT_UNIVERSE)
            app.logger.info('Scheduled daily update finished')
        except Exception as e:
            app.logger.exception('Error during scheduled update: %s', e)

    # schedule at 02:00 UTC daily; start scheduler
    try:
        scheduler.add_job(_daily_update_job, 'cron', hour=2, minute=0, id='daily_update')
        scheduler.start()
        app.logger.info('APScheduler started')
    except Exception:
        # ignore scheduler start errors (may already be started in some environments)
        app.logger.exception('Failed to start APScheduler')

    def safe_float(x):
        try:
            if x is None:
                return None
            v = float(x)
            if not math.isfinite(v):
                return None
            return v
        except Exception:
            return None

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

    # Default universe: common liquid US tickers (starter list)
    DEFAULT_UNIVERSE = [
        'AAPL','MSFT','GOOG','AMZN','TSLA','NVDA','META','NFLX','INTC','AMD',
        'CSCO','ORCL','CRM','ADBE','IBM','QCOM','TXN','AVGO','AMAT','PYPL',
        'BABA','WMT','PG','KO','PEP','MCD','SBUX','DIS','BAC','JPM',
        'V','MA','AXP','C','GS','MS','BK','UBER','LYFT','SNAP','TWTR','SQ',
        'SHOP','ZM','DOCU','SPOT','ROKU','F','GM','NIO','PLTR','SNOW',
        'SQ','CRM','TSM','SAP','BMY','PFE','JNJ','MRK','ABBV','GILD'
    ]


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


    # Simple API endpoint for screening — returns JSON ranked results
    @app.route('/api/screen')
    def api_screen():
        # params
        lookback = int(request.args.get('lookback', 30))
        universe = request.args.get('symbols')
        if universe:
            symbols = [s.strip().upper() for s in universe.split(',') if s.strip()]
        else:
            # default to stored symbols or a small popular universe
            symbols = app.di.list_symbols()
            if not symbols:
                symbols = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']

        results = []
        # limit param and caching
        limit = int(request.args.get('limit', 20))

        for s in symbols:
            # check cached metrics (use if updated within 24h)
            cached = app.di.get_metrics(s)
            use_cache = False
            if cached and cached.get('last_updated'):
                try:
                    lu = cached.get('last_updated')
                    from datetime import datetime, timedelta
                    lu_dt = datetime.strptime(lu, '%Y-%m-%dT%H:%M:%S')
                    if datetime.now() - lu_dt < timedelta(hours=24):
                        use_cache = True
                except Exception:
                    use_cache = False
            if use_cache:
                results.append({
                    'symbol': s,
                    'score': int(cached.get('score', 0)),
                    **(cached.get('payload') or {})
                })
                # when cached, skip re-processing the same symbol to avoid duplicates
                continue

            df = app.di.get_price_data(s, days=lookback)
            if df is None or df.empty:
                # try fetch and save
                fetched = app.di.fetch_price_data(s, period=str(lookback) + 'd')
                if fetched is None or fetched.empty:
                    continue
                app.di.save_price_data(fetched)
                df = app.di.get_price_data(s, days=lookback)
            if df is None or df.empty or len(df) < 10:
                continue

            df = df.copy()
            df.columns = [c.lower() for c in df.columns]
            df = add_indicators(df)

            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else None

            # metrics
            try:
                last_close = float(last['close'])
            except Exception:
                continue
            prev_close = float(prev['close']) if prev is not None else None
            pct_change = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0
            rsi = float(last['rsi']) if 'rsi' in df.columns else None
            sma20 = float(last['sma_20']) if 'sma_20' in df.columns else None
            sma50 = float(last['sma_50']) if 'sma_50' in df.columns else None
            ema20 = float(last['ema_20']) if 'ema_20' in df.columns else None
            ema50 = float(last['ema_50']) if 'ema_50' in df.columns else None

            # volume spike
            vol_recent = df['volume'].iloc[-5:].mean() if 'volume' in df.columns else None
            vol_avg = df['volume'].iloc[-30:].mean() if 'volume' in df.columns and len(df) >= 30 else vol_recent
            vol_spike = (vol_recent / vol_avg) if vol_avg and vol_recent else 1.0

            # scoring (simple weighted rules)
            score = 0
            # price above moving averages
            if sma20 and sma50 and last_close > sma20 and last_close > sma50:
                score += 20
            # ema cross
            if ema20 and ema50 and ema20 > ema50:
                score += 20
            # rsi healthy
            if rsi is not None and 40 <= rsi <= 70:
                score += 15
            # volume spike
            if vol_spike and vol_spike >= 1.2:
                score += 15
            # momentum (pct change)
            if pct_change and pct_change > 0.5:
                score += 10

            # fundamentals simple filter (market cap if available)
            fund = app.di.get_fundamental_data(s)
            market_cap = fund.get('market_cap') if isinstance(fund, dict) else None
            if market_cap and market_cap >= 500_000_000:
                score += 10

            results.append({
                'symbol': s,
                'score': int(score),
                'pct_change': round(pct_change, 2) if pct_change is not None else None,
                'rsi': round(rsi, 2) if rsi is not None else None,
                'sma20': round(sma20, 2) if sma20 is not None else None,
                'sma50': round(sma50, 2) if sma50 is not None else None,
                'ema20': round(ema20, 2) if ema20 is not None else None,
                'ema50': round(ema50, 2) if ema50 is not None else None,
                'vol_spike': round(vol_spike, 2) if vol_spike is not None else None,
                'market_cap': market_cap,
            })
            # save metrics to cache
            try:
                payload = {
                    'pct_change': round(pct_change, 2) if pct_change is not None else None,
                    'rsi': round(rsi, 2) if rsi is not None else None,
                    'sma20': round(sma20, 2) if sma20 is not None else None,
                    'sma50': round(sma50, 2) if sma50 is not None else None,
                    'ema20': round(ema20, 2) if ema20 is not None else None,
                    'ema50': round(ema50, 2) if ema50 is not None else None,
                    'vol_spike': round(vol_spike, 2) if vol_spike is not None else None,
                    'market_cap': market_cap,
                }
                app.di.save_metrics(s, int(score), payload)
            except Exception:
                pass

        # sanitize numeric values (JSON does not accept NaN/Inf)
        def _sanitize(obj):
            for k, v in list(obj.items()):
                if isinstance(v, float):
                    if not math.isfinite(v):
                        obj[k] = None
                # nested dicts/lists not expected here but handle simple cases
                if isinstance(v, dict):
                    _sanitize(v)
            return obj

        results = [_sanitize(r) for r in results]

        # sort by score desc
        results.sort(key=lambda x: x.get('score', 0), reverse=True)

        # limit results
        limit = int(request.args.get('limit', 20))
        return jsonify({'count': len(results), 'results': results[:limit]})


    @app.route('/api/check_alpha')
    def api_check_alpha():
        """Check whether ALPHA_VANTAGE_KEY (from env) appears valid by making a small request.

        Returns JSON: {valid: bool, message: str}
        """
        key = os.environ.get('REACT_APP_ALPHA_VANTAGE_KEY') or os.environ.get('ALPHA_VANTAGE_KEY')
        if not key:
            return jsonify({'valid': False, 'message': 'Alpha Vantage key not set in environment.'})

        url = 'https://www.alphavantage.co/query'
        params = {'function': 'TIME_SERIES_DAILY', 'symbol': 'AAPL', 'apikey': key, 'outputsize': 'compact'}
        try:
            resp = requests.get(url, params=params, timeout=8)
            data = resp.json()
        except Exception as e:
            return jsonify({'valid': False, 'message': f'Network/error when calling Alpha Vantage: {e}'})

        # Alpha Vantage returns keys like 'Time Series (Daily)' on success
        if 'Error Message' in data:
            return jsonify({'valid': False, 'message': 'Alpha Vantage returned an error for the request.'})
        if 'Note' in data:
            return jsonify({'valid': False, 'message': 'Alpha Vantage rate limit or note: ' + data.get('Note', '')})
        if 'Time Series (Daily)' in data or 'Time Series (Daily)' in ''.join(data.keys()):
            return jsonify({'valid': True, 'message': 'Alpha Vantage key seems valid (received daily series).'} )

        # Fallback: consider missing expected keys as invalid
        return jsonify({'valid': False, 'message': 'Unexpected response structure from Alpha Vantage.'})


    @app.route('/api/update')
    def api_update():
        """Fetch and save price/fundamental data for a list of symbols (useful to pre-populate DB).

        Runs in a background thread and returns immediately with a status message.
        Accepts optional JSON body { symbols: [...], limit: int } or query params.
        """
        payload = request.get_json(force=True, silent=True) or {}
        universe = payload.get('symbols') or request.args.get('symbols')
        if universe:
            if isinstance(universe, str):
                symbols = [s.strip().upper() for s in universe.split(',') if s.strip()]
            else:
                symbols = [s.strip().upper() for s in universe]
        else:
            symbols = DEFAULT_UNIVERSE

        try:
            limit = int(payload.get('limit') or request.args.get('limit') or 50)
        except Exception:
            limit = 50

        symbols = symbols[:limit]

        def _runner(syms):
            for s in syms:
                try:
                    app.di.update_stock(s)
                except Exception:
                    app.logger.exception('Error updating %s', s)

        t = Thread(target=_runner, args=(symbols,))
        t.daemon = True
        t.start()
        return jsonify({'status': 'started', 'symbols': symbols, 'count': len(symbols)})


    @app.route('/api/ohlc')
    def api_ohlc():
        symbol = request.args.get('symbol')
        days = int(request.args.get('days', 365))
        if not symbol:
            return jsonify({'error': 'symbol is required'}), 400
        df = app.di.get_price_data(symbol.upper(), days=days)
        if df is None or df.empty:
            # try fetching
            fetched = app.di.fetch_price_data(symbol.upper(), period=str(days) + 'd')
            if fetched is None or fetched.empty:
                return jsonify({'error': 'no data for symbol'}), 404
            app.di.save_price_data(fetched)
            df = app.di.get_price_data(symbol.upper(), days=days)

        # compute indicators
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        df = add_indicators(df)

        # build JSON series
        out = {'symbol': symbol.upper(), 'rows': []}
        for _, row in df.iterrows():
            r = {
                'date': str(row['date'])[:10],
                'open': safe_float(row.get('open')),
                'high': safe_float(row.get('high')),
                'low': safe_float(row.get('low')),
                'close': safe_float(row.get('close')),
                'volume': int(row['volume']) if 'volume' in row and not pd.isna(row['volume']) else None,
                'rsi': safe_float(row.get('rsi')),
                'sma_20': safe_float(row.get('sma_20')),
                'sma_50': safe_float(row.get('sma_50')),
            }
            out['rows'].append(r)

        return jsonify(out)


    @app.route('/api/run_update', methods=['POST'])
    def api_run_update():
        """Trigger a manual update job (non-blocking). Optional JSON { symbols: [...], limit: int }"""
        payload = request.get_json(force=True, silent=True) or {}
        universe = payload.get('symbols') or request.args.get('symbols')
        if universe:
            if isinstance(universe, str):
                symbols = [s.strip().upper() for s in universe.split(',') if s.strip()]
            else:
                symbols = [s.strip().upper() for s in universe]
        else:
            symbols = DEFAULT_UNIVERSE

        try:
            limit = int(payload.get('limit') or request.args.get('limit') or 50)
        except Exception:
            limit = 50

        symbols = symbols[:limit]

        def _runner(syms):
            app.logger.info('Manual run_update started for %d symbols', len(syms))
            for s in syms:
                try:
                    app.di.update_stock(s)
                except Exception:
                    app.logger.exception('Error updating %s', s)
            app.logger.info('Manual run_update finished')

        t = Thread(target=_runner, args=(symbols,))
        t.daemon = True
        t.start()
        return jsonify({'status': 'started', 'symbols': symbols, 'count': len(symbols)})


    @app.route('/api/scheduler/start', methods=['POST'])
    def api_scheduler_start():
        try:
            if not app.scheduler.running:
                app.scheduler.start()
        except Exception:
            app.logger.exception('Failed to start scheduler')
        return jsonify({'running': True})


    @app.route('/api/scheduler/stop', methods=['POST'])
    def api_scheduler_stop():
        try:
            app.scheduler.shutdown(wait=False)
        except Exception:
            app.logger.exception('Failed to stop scheduler')
        return jsonify({'running': False})


    # Watchlist endpoints
    @app.route('/api/watchlist', methods=['GET'])
    def api_watchlist_get():
        items = app.di.list_watchlist()
        return jsonify({'items': items})

    @app.route('/api/watchlist', methods=['POST'])
    def api_watchlist_add():
        payload = request.get_json(force=True, silent=True) or {}
        symbol = payload.get('symbol') or request.args.get('symbol')
        notes = payload.get('notes') or request.args.get('notes')
        if not symbol:
            return jsonify({'error': 'symbol required'}), 400
        try:
            wid = app.di.add_watchlist(symbol, notes)
            return jsonify({'id': wid, 'symbol': symbol.upper()})
        except Exception as e:
            app.logger.exception('Failed to add watchlist entry: %s', e)
            return jsonify({'error': 'failed to add watchlist', 'detail': str(e)}), 500

    @app.route('/api/watchlist/<int:wid>', methods=['DELETE'])
    def api_watchlist_remove(wid):
        ok = app.di.remove_watchlist(wid)
        return jsonify({'ok': bool(ok)})


    # Positions endpoints
    @app.route('/api/positions', methods=['GET'])
    def api_positions_get():
        items = app.di.list_positions()
        return jsonify({'items': items})

    @app.route('/api/positions', methods=['POST'])
    def api_positions_add():
        payload = request.get_json(force=True, silent=True) or {}
        try:
            symbol = payload['symbol']
            entry_date = payload.get('entry_date') or payload.get('date')
            entry_price = float(payload.get('entry_price'))
            size = float(payload.get('size', 0))
            status = payload.get('status', 'open')
            notes = payload.get('notes')
        except Exception:
            return jsonify({'error': 'missing/invalid fields'}), 400
        pid = app.di.add_position(symbol, entry_date, entry_price, size, status, notes)
        return jsonify({'id': pid})

    @app.route('/api/positions/<int:pid>', methods=['PUT'])
    def api_positions_update(pid):
        payload = request.get_json(force=True, silent=True) or {}
        ok = app.di.update_position(pid, **payload)
        return jsonify({'ok': bool(ok)})

    @app.route('/api/positions/<int:pid>', methods=['DELETE'])
    def api_positions_remove(pid):
        ok = app.di.remove_position(pid)
        return jsonify({'ok': bool(ok)})


    @app.after_request
    def add_cors_headers(response):
        # allow local dev clients (React) to call this API
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    return app


app = create_app()


if __name__ == '__main__':
    # Run the dev server when executed as a module: python -m tradingbuddy.api.flask_app
    app.run(host='127.0.0.1', port=5000, debug=True)
