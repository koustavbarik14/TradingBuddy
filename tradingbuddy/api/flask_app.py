import os
from math import ceil
from typing import Optional
from flask import Flask, render_template, request, jsonify, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread
import math
import requests
import os
import pandas as pd
from tradingbuddy.core import DataIngestion
from tradingbuddy.features.patterns import PatternDetection
from tradingbuddy.features.technical import add_indicators
from tradingbuddy.features.scanner import compute_scores_for_universe
from tradingbuddy.features.ml_breakouts import detect_breakouts_for_universe, BreakoutPattern
import json


def create_app(db_path: Optional[str] = None):
    package_dir = os.path.dirname(__file__)
    templates_dir = os.path.join(package_dir, 'templates')
    static_dir = os.path.join(package_dir, 'static')

    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    # ensure the logger prints INFO+ messages to console so we can see incoming API calls
    try:
        import logging
        app.logger.setLevel(logging.INFO)
    except Exception:
        pass

    @app.before_request
    def _log_incoming_request():
        # Log method and path for every incoming request to help surface clicks/requests from the frontend
        try:
            app.logger.info(f"Incoming request: {request.method} {request.path} from {request.remote_addr}")
        except Exception:
            pass

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
    
    # Add dummy trades for demo purposes if none exist
    try:
        existing_positions = app.di.list_positions()
        if not existing_positions or len(existing_positions) == 0:
            # Add 5 sample trades
            app.di.add_position('AAPL', '2024-11-15', 185.50, 10, 'closed', 'Breakout from Darvas Box - nice momentum')
            app.di.add_position('TSLA', '2024-12-01', 245.30, 5, 'open', 'Head & Shoulders pattern forming')
            app.di.add_position('NVDA', '2024-11-20', 495.75, 8, 'closed', 'AI rally continuation - sold at resistance')
            app.di.add_position('MSFT', '2024-12-10', 375.20, 12, 'open', 'Cup & Handle breakout - strong volume')
            app.di.add_position('META', '2024-12-05', 340.00, 6, 'closed', 'Channel breakout - took profits at 360')
            app.logger.info('Added 5 demo trades')
    except Exception as e:
        app.logger.warning('Could not add demo trades: %s', e)

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

    # If a built React frontend is present, serve static files from it (single-server mode)
    try:
        build_dir = os.path.join(project_root, 'frontend', 'dist')
        if os.path.exists(build_dir):
            @app.route('/<path:filename>')
            def _serve_frontend_file(filename):
                full = os.path.join(build_dir, filename)
                if os.path.exists(full):
                    return send_from_directory(build_dir, filename)
                # fallback to index for SPA routes
                return send_from_directory(build_dir, 'index.html')
    except Exception:
        pass

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
    # Will be dynamically enhanced with yfinance data validation
    DEFAULT_UNIVERSE = [
        'AAPL','MSFT','GOOG','AMZN','TSLA','NVDA','META','NFLX','INTC','AMD',
        'CSCO','ORCL','CRM','ADBE','IBM','QCOM','TXN','AVGO','AMAT','PYPL',
        'WMT','PG','KO','PEP','MCD','SBUX','DIS','BAC','JPM',
        'V','MA','AXP','C','GS','MS','BK','UBER','LYFT','SNAP','TWTR','SQ',
        'SHOP','ZM','DOCU','SPOT','ROKU','F','GM','PLTR','SNOW'
    ]
    
    def _validate_symbol(symbol):
        """Validate that a symbol is valid (can fetch data from yfinance)."""
        try:
            # Try to fetch minimal data for the symbol
            df = app.di.fetch_price_data(symbol, period='5d')
            return df is not None and not df.empty
        except Exception:
            return False
    
    def _get_dynamic_universe(limit=50):
        """Get validated symbols from DEFAULT_UNIVERSE, removing any invalid ones."""
        import yfinance as yf
        valid_symbols = []
        for symbol in DEFAULT_UNIVERSE[:limit]:
            try:
                # Quick validation: fetch 1 day of data
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='1d')
                if not hist.empty:
                    valid_symbols.append(symbol)
            except Exception:
                # Skip invalid symbols silently
                pass
        return valid_symbols if valid_symbols else DEFAULT_UNIVERSE[:20]  # fallback to first 20 if all fail


    @app.route('/')
    def index():
        """Main landing page - show breakout patterns"""
        return breakouts()

    @app.route('/breakouts')
    def breakouts():
        """Display AI/ML-detected breakout patterns"""
        limit = int(request.args.get('limit', 10))
        symbols_param = request.args.get('symbols')
        
        if symbols_param:
            symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
            symbols = [s for s in symbols if ':' not in s and s.isalpha()]
        else:
            symbols = _get_dynamic_universe(50)

        # Data loader for ML detector
        def data_loader(sym):
            try:
                df = app.di.get_price_data(sym, days=365)
                if df is None or df.empty:
                    fetched = app.di.fetch_price_data(sym, period='1y')
                    if fetched is not None and not fetched.empty:
                        try:
                            app.di.save_price_data(fetched)
                        except Exception:
                            pass
                        df = app.di.get_price_data(sym, days=365)
                if df is None or df.empty:
                    return pd.DataFrame()
                df = df.copy()
                df.columns = [c.lower() for c in df.columns]
                return df
            except Exception:
                return pd.DataFrame()
        
        # Detect breakouts using ML
        items = []
        try:
            patterns = detect_breakouts_for_universe(data_loader, symbols, limit=limit, timeframe='daily')
            items = [
                {
                    'symbol': p.symbol,
                    'pattern': p.pattern_type.replace('_', ' ').title(),
                    'status': 'forming',  # Default status for initial render
                    'confidence': round(p.confidence * 100, 1),  # Convert to percentage
                    'entry_price': round(p.entry_price, 2),
                    'breakout_date': p.breakout_date,
                    'description': p.description,
                    'support': round(p.support_level, 2) if p.support_level else 'N/A',
                    'resistance': round(p.resistance_level, 2) if p.resistance_level else 'N/A',
                }
                for p in patterns
            ]
        except Exception as e:
            app.logger.exception('Breakout detection error: %s', e)
            items = []
        
        return render_template(
            'breakouts.html',
            items=items,
            total=len(items),
            limit=limit
        )

    @app.route('/test-plotly')
    def test_plotly():
        """Test page for Plotly chart integration"""
        return render_template('test_plotly.html')

    @app.route('/test-simple')
    def test_simple():
        """Very simple test route"""
        return "Hello from Flask!"

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


    @app.route('/scanner')
    def scanner():
        # render scanner UI; use validated universe that filters invalid symbols
        validated_universe = _get_dynamic_universe(50)
        return render_template('scanner.html', DEFAULT_UNIVERSE=validated_universe)

    @app.route('/trades')
    def trades():
        # render trades management UI
        return render_template('trades.html')

    @app.route('/api/scanner')
    def api_scanner():
        # returns JSON list of scoring results using the notebook logic
        # Filters invalid symbols automatically (e.g., NASDAQ:BABA, invalid tickers)
        symbols_param = request.args.get('symbols')
        if symbols_param:
            symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
            # Filter to remove invalid symbols (symbols with ':' or other invalid formats)
            symbols = [s for s in symbols if ':' not in s and s.isalpha()]
        else:
            symbols = _get_dynamic_universe(30)

        # data loader closure: attempts to read local DB, otherwise fetch from source
        def data_loader(sym):
            try:
                df = app.di.get_price_data(sym, days=365)
                if df is None or df.empty:
                    fetched = app.di.fetch_price_data(sym, period='1y')
                    if fetched is not None and not fetched.empty:
                        try:
                            app.di.save_price_data(fetched)
                        except Exception:
                            pass
                        df = app.di.get_price_data(sym, days=365)
                if df is None or df.empty:
                    return pd.DataFrame()
                df = df.copy()
                df.columns = [c.lower() for c in df.columns]
                return df
            except Exception:
                return pd.DataFrame()

        # Filter symbols to only those that have data available
        valid_symbols = []
        for sym in symbols:
            try:
                data = data_loader(sym)
                if not data.empty:
                    valid_symbols.append(sym)
            except Exception:
                pass
        
        # Use valid symbols, or fallback to default if none found
        symbols_to_score = valid_symbols if valid_symbols else _get_dynamic_universe(15)
        
        df_scores = compute_scores_for_universe(data_loader, symbols_to_score)
        # sanitize and return (convert numpy types to native python)
        out = df_scores.fillna(0).to_dict(orient='records')
        try:
            safe = json.loads(json.dumps(out, default=lambda x: (x.item() if hasattr(x, 'item') else x)))
        except Exception:
            safe = out
        return jsonify(safe)

    @app.route('/api/ml_breakouts')
    def api_ml_breakouts():
        """ML-powered breakout detection endpoint.
        
        Returns list of detected breakout patterns sorted by confidence.
        Query params:
            - symbols: comma-separated symbol list (optional, defaults to universe)
            - limit: max patterns to return (default: 10)
            - timeframe: 'daily', 'weekly', or 'monthly' (default: 'daily')
        """
        symbols_param = request.args.get('symbols')
        limit = int(request.args.get('limit', 10))
        timeframe = request.args.get('timeframe', 'daily').lower()
        
        # Map timeframe to days
        timeframe_days = {
            'daily': 365,
            'weekly': 365 * 4,
            'monthly': 365 * 2
        }
        days_to_fetch = timeframe_days.get(timeframe, 365)
        
        if symbols_param:
            symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
            # Filter invalid symbols
            symbols = [s for s in symbols if ':' not in s and s.isalpha()]
        else:
            symbols = _get_dynamic_universe(50)
        
        # Data loader for ML detector - fetch more data based on timeframe
        def data_loader(sym):
            try:
                df = app.di.get_price_data(sym, days=days_to_fetch)
                if df is None or df.empty:
                    fetched = app.di.fetch_price_data(sym, period='2y')
                    if fetched is not None and not fetched.empty:
                        try:
                            app.di.save_price_data(fetched)
                        except Exception:
                            pass
                        df = app.di.get_price_data(sym, days=days_to_fetch)
                if df is None or df.empty:
                    return pd.DataFrame()
                df = df.copy()
                df.columns = [c.lower() for c in df.columns]
                
                # Drop symbol column before resampling (it's not numeric and causes issues)
                if 'symbol' in df.columns:
                    df = df.drop('symbol', axis=1)
                
                # CRITICAL: Set date column as index for resampling to work
                # resample() requires DatetimeIndex, not integer index
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                
                # Resample data for weekly/monthly if needed
                if timeframe == 'weekly':
                    df = df.resample('W').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                elif timeframe == 'monthly':
                    df = df.resample('M').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                
                return df
            except Exception:
                return pd.DataFrame()
        
        # Detect breakouts (use pre-breakout mode by default)
        try:
            patterns = detect_breakouts_for_universe(data_loader, symbols, limit=limit, timeframe=timeframe, pre_breakout_mode=True)
            
            # Get current prices for status calculation
            current_prices = {}
            for sym in symbols:
                df = data_loader(sym)
                if not df.empty:
                    current_prices[sym] = float(df['close'].iloc[-1])
            
            # Convert to JSON-serializable format
            out = []
            for p in patterns:
                current_price = current_prices.get(p.symbol, p.entry_price)
                
                # Determine status based on entry_price vs current_price
                # For buy signals: confirmed if entry_price < current_price (already moved up)
                # For buy signals: forming if entry_price >= current_price (waiting to enter)
                if p.entry_price < current_price:
                    status = 'confirmed'
                else:
                    status = 'forming'
                
                out.append({
                    'symbol': p.symbol,
                    'pattern_type': p.pattern_type,
                    'confidence': round(float(p.confidence) * 100, 1),  # Convert to percentage
                    'entry_price': round(float(p.entry_price), 2),
                    'current_price': round(current_price, 2),
                    'breakout_date': p.breakout_date,
                    'description': p.description,
                    'support_level': round(float(p.support_level), 2) if p.support_level else None,
                    'resistance_level': round(float(p.resistance_level), 2) if p.resistance_level else None,
                    'status': status
                })
            
            # Consolidate multiple patterns per stock
            consolidated = {}
            for pattern in out:
                sym = pattern['symbol']
                if sym in consolidated:
                    # Combine pattern types
                    existing = consolidated[sym]
                    existing['pattern_type'] += ', ' + pattern['pattern_type']
                    # Keep highest confidence
                    if pattern['confidence'] > existing['confidence']:
                        existing['confidence'] = pattern['confidence']
                    # Combine descriptions
                    if pattern['description'] not in existing['description']:
                        existing['description'] += '; ' + pattern['description']
                    # Use most optimistic status
                    if pattern['status'] == 'confirmed' or existing['status'] == 'confirmed':
                        existing['status'] = 'confirmed'
                else:
                    consolidated[sym] = pattern
            
            # Convert back to list and sort by confidence
            result = list(consolidated.values())
            result.sort(key=lambda x: x['confidence'], reverse=True)
            
            return jsonify(result)
        except Exception as e:
            app.logger.exception('ML breakout detection failed: %s', e)
            return jsonify({'error': 'detection_failed', 'detail': str(e)}), 500

    @app.route('/api/stock_info/<symbol>')
    def api_stock_info(symbol: str):
        """Get comprehensive stock information including OHLC, RSI, fundamentals, and analyst recommendations"""
        try:
            from tradingbuddy.features.stock_info import get_stock_info
            
            info = get_stock_info(symbol.upper(), data_ingestion=app.di)
            return jsonify(info)
        except Exception as e:
            app.logger.exception('Stock info fetch failed: %s', e)
            return jsonify({
                'error': 'fetch_failed',
                'detail': str(e),
                'symbol': symbol.upper(),
                'exchange': 'NASDAQ'
            }), 500

    @app.route('/api/breakout_chart/<symbol>')
    def api_breakout_chart(symbol: str):
        """Generate static candlestick chart with breakout pattern annotations"""
        try:
            from tradingbuddy.visualization.mplfinance_charts import create_pattern_chart
            from tradingbuddy.features.ml_breakouts import detect_breakouts_for_universe
            
            # Get timeframe from query params
            timeframe = request.args.get('timeframe', 'daily')
            
            # Adjust days based on timeframe to get enough candles
            if timeframe == 'monthly':
                days = 730  # 2 years for monthly charts
            elif timeframe == 'weekly':
                days = 365  # 1 year for weekly charts
            else:
                days = 90   # 90 days for daily charts
            
            # Get pattern data for this symbol
            def data_loader(sym):
                df = app.di.get_price_data(sym, days=days)
                if df is None or df.empty:
                    return pd.DataFrame()
                df = df.copy()
                df.columns = [c.lower() for c in df.columns]
                if 'symbol' in df.columns:
                    df = df.drop('symbol', axis=1)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                
                # Resample for weekly/monthly
                if timeframe == 'weekly':
                    df = df.resample('W').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                elif timeframe == 'monthly':
                    df = df.resample('M').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                
                return df
            
            patterns = detect_breakouts_for_universe(data_loader, [symbol.upper()], limit=1, timeframe=timeframe)
            
            if not patterns:
                return jsonify({'error': 'No breakout pattern found for this symbol'}), 404
            
            pattern = patterns[0]
            price_df = data_loader(symbol.upper())
            
            if price_df.empty:
                return jsonify({'error': 'No price data available'}), 404
            
            # Create pattern data dict
            pattern_data = {
                'pattern_type': pattern.pattern_type,
                'resistance_level': pattern.resistance_level,
                'support_level': pattern.support_level,
                'entry_price': pattern.entry_price,
                'breakout_date': pattern.breakout_date,
                'description': pattern.description,
                'timeframe': timeframe  # Add timeframe to pattern data
            }
            
            # Generate static chart image (base64 encoded)
            image_data = create_pattern_chart(symbol.upper(), price_df, pattern_data)
            
            if not image_data:
                return jsonify({'error': 'Chart generation failed'}), 500
            
            return jsonify({'image': image_data, 'pattern': pattern_data})
        
        except Exception as e:
            app.logger.exception('Breakout chart generation failed: %s', e)
            return jsonify({'error': 'chart_generation_failed', 'detail': str(e)}), 500

    @app.route('/api/ohlc/<symbol>')
    def api_ohlc_symbol(symbol: str):
        # return OHLC series for a single ticker as JSON
        period_key = request.args.get('period', '1y')
        days_map = {
            '1d': 1,
            '1w': 7,
            '1m': 30,
            '6m': 180,
            '1y': 365,
            '3y': 365*3,
            '5y': 365*5,
            'max': 365*10
        }
        days = days_map.get(period_key, 365)
        df = app.di.get_price_data(symbol.upper(), days=days)
        if df is None or df.empty:
            fetched = app.di.fetch_price_data(symbol.upper(), period='1y')
            if fetched is not None and not fetched.empty:
                try:
                    app.di.save_price_data(fetched)
                except Exception:
                    pass
                df = app.di.get_price_data(symbol.upper(), days=days)

        if df is None or df.empty:
            return jsonify([])

        # normalize columns and return list of dicts
        df = df.copy()
        # prefer a 'date' column, otherwise use index
        if 'date' not in df.columns:
            try:
                df = df.reset_index()
            except Exception:
                pass
        df.columns = [c.lower() for c in df.columns]
        out_cols = []
        for _, row in df.iterrows():
            rec = {}
            # date
            if 'date' in df.columns:
                try:
                    rec['date'] = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
                except Exception:
                    rec['date'] = str(row['date'])
            else:
                rec['date'] = ''
            rec['open'] = float(row.get('open', 0)) if not pd.isna(row.get('open', None)) else None
            rec['high'] = float(row.get('high', 0)) if not pd.isna(row.get('high', None)) else None
            rec['low'] = float(row.get('low', 0)) if not pd.isna(row.get('low', None)) else None
            rec['close'] = float(row.get('close', 0)) if not pd.isna(row.get('close', None)) else None
            rec['volume'] = int(row.get('volume', 0)) if not pd.isna(row.get('volume', None)) else None
            out_cols.append(rec)

        return jsonify(out_cols)


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


    # Chart config endpoints
    @app.route('/api/chart/config', methods=['POST'])
    def api_chart_config_save():
        payload = request.get_json(force=True, silent=True) or {}
        name = payload.get('name')
        config = payload.get('config')
        if not name or not isinstance(config, dict):
            return jsonify({'error': 'name and config (object) required'}), 400
        try:
            cid = app.di.save_chart_config(name, config)
            return jsonify({'ok': True, 'id': cid})
        except Exception as e:
            app.logger.exception('Failed to save chart config: %s', e)
            return jsonify({'error': 'failed to save config', 'detail': str(e)}), 500

    @app.route('/api/chart/config/<name>', methods=['GET', 'DELETE'])
    def api_chart_config_get_delete(name):
        if request.method == 'GET':
            cfg = app.di.get_chart_config(name)
            if not cfg:
                return jsonify({'error': 'not found'}), 404
            return jsonify(cfg)
        else:
            ok = app.di.remove_chart_config(name)
            return jsonify({'ok': bool(ok)})

    @app.route('/api/chart/configs')
    def api_chart_configs_list():
        items = app.di.list_chart_configs()
        return jsonify({'items': items})


    @app.route('/api/chart/render', methods=['POST'])
    def api_chart_render():
        """Chart rendering endpoint (deprecated in favor of TradingView).
        
        Returns 501 to trigger frontend fallback to TradingView widget.
        """
        return jsonify({'error': 'chart_rendering_disabled', 'message': 'Use TradingView widget instead'}), 501

    @app.route('/api/chart/render', methods=['GET'])
    def api_chart_render_get():
        """Chart rendering endpoint (deprecated in favor of TradingView).
        
        Returns 501 to trigger frontend fallback to TradingView widget.
        """
        return jsonify({'error': 'chart_rendering_disabled', 'message': 'Use TradingView widget instead'}), 501


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

    @app.route('/api/client_log', methods=['POST'])
    def api_client_log():
        """Receive client-side logs (from browser) to help debugging network/JS issues.

        Body JSON: { level: 'info'|'warn'|'error', msg: str }
        """
        payload = request.get_json(force=True, silent=True) or {}
        level = (payload.get('level') or 'info').lower()
        msg = payload.get('msg') or ''
        try:
            if level == 'error':
                app.logger.error('CLIENT: %s', msg)
            elif level == 'warn':
                app.logger.warning('CLIENT: %s', msg)
            else:
                app.logger.info('CLIENT: %s', msg)
        except Exception:
            pass
        return jsonify({'ok': True})

    return app


app = create_app()


if __name__ == '__main__':
    # Run the dev server when executed as a module: python -m tradingbuddy.api.flask_app
    # Run without the reloader/debugger to avoid watchdog restarts caused by
    # third-party library file changes (matplotlib/mplfinance). For development
    # you can set debug=True explicitly, but production runs should avoid the
    # reloader when using server-side rendering of charts.
    app.run(host='127.0.0.1', port=5000, debug=False)
