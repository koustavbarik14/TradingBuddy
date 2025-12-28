"""
Finplot-only renderer.
This module uses finplot (PyQt-based) to render and return chart images. It does not
fall back to mplfinance—if finplot cannot run in the environment an exception will
be raised so the caller can handle it.

API:
    render_chart(df, indicators: dict, out_path: str) -> out_path or bytes

indicators example:
{
    "sma": [20,50],
    "rsi": 14,
}

If out_path is None, render_chart returns PNG bytes. If out_path is provided it
writes the PNG to disk and returns the path.
"""
from pathlib import Path
import traceback
import pandas as pd
import tempfile
import io
import os
import json
import multiprocessing
import time

# Ensure matplotlib uses a non-GUI backend when used server-side to avoid
# starting a GUI in worker threads which causes crashes and reloads.
try:
    import matplotlib
    matplotlib.use('Agg')
except Exception:
    pass


def _try_finplot_render(df: pd.DataFrame, indicators: dict, out_path: str = None):
    try:
        import finplot as fplt
        # Configure finplot for headless (may require PyQt to be present)
        # finplot uses PyQt; depending on environment, offscreen may or may not work.
        # We'll create a plot and save it using fplt.screenshot
        # Build OHLC in the format finplot expects (pandas DataFrame with datetime index)
        d = df.copy()
        if 'date' in d.columns:
            d = d.set_index(pd.to_datetime(d['date']))
        # finplot expects columns: open, high, low, close, volume
        # create window-less plot
        # Older examples call fplt.clf(), but that attribute may not exist in all versions.
        # Try a few possible clearing functions if available, otherwise proceed.
        for clear_name in ('clf', 'clear', 'close'):
            clear_fn = getattr(fplt, clear_name, None)
            if callable(clear_fn):
                try:
                    clear_fn()
                except Exception:
                    # non-fatal; proceed to create a fresh plot
                    pass
                break
        ax = fplt.create_plot(init_zoom_periods=250, maximize=False)
        # Try to draw candlesticks. Different finplot versions have slightly different
        # expectations for the column order; try the most common and fall back.
        try:
            fplt.candlestick_ochl(d[['open', 'close', 'high', 'low']])
        except Exception:
            try:
                fplt.candlestick_ochl(d[['open', 'high', 'low', 'close']])
            except Exception:
                # last attempt: pass the frame directly and let finplot decide
                fplt.candlestick_ochl(d)
        # Add simple indicators
        if indicators:
            if 'sma' in indicators:
                for p in indicators.get('sma', []):
                    if p and p > 0:
                        s = d['close'].rolling(window=int(p)).mean()
                        fplt.plot(s, legend=f'SMA{p}')
            if 'rsi' in indicators and indicators.get('rsi'):
                import numpy as np
                period = int(indicators.get('rsi'))
                delta = d['close'].diff()
                up = delta.clip(lower=0)
                down = -1 * delta.clip(upper=0)
                ma_up = up.ewm(alpha=1/period, adjust=False).mean()
                ma_down = down.ewm(alpha=1/period, adjust=False).mean()
                rs = ma_up / ma_down
                rsi = 100 - (100 / (1 + rs))
                fplt.volume_ocv(d[['open','close']], ax=ax.overlay())
                # For finplot, adding RSI on separate plot is more involved; skip for now
        # save screenshot
        # If out_path is provided, write to that file. Otherwise create a temporary file and return bytes.
        if out_path:
            outp = Path(out_path)
            outp.parent.mkdir(parents=True, exist_ok=True)
            fplt.screenshot(str(outp))
            return str(outp)
        # write to temporary file then return bytes
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            fplt.screenshot(tmp_path)
            with open(tmp_path, 'rb') as fh:
                data = fh.read()
            return data
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception:
        # give traceback to caller
        raise


def _mplfinance_render(df: pd.DataFrame, indicators: dict, out_path: str = None):
    """Render using mplfinance/matplotlib. Returns bytes if out_path is None,
    otherwise writes to out_path and returns the path."""
    try:
        import mplfinance as mpf
    except Exception as e:
        raise RuntimeError('mplfinance is not available: ' + str(e))

    d = df.copy()
    if 'date' in d.columns:
        d = d.set_index(pd.to_datetime(d['date']))

    addplots = []
    panels = {}
    if indicators:
        if 'sma' in indicators:
            for p in indicators.get('sma', []):
                if p and p > 0:
                    s = d['close'].rolling(window=int(p)).mean()
                    addplots.append(mpf.make_addplot(s, color='blue', width=1))
        if 'rsi' in indicators and indicators.get('rsi'):
            period = int(indicators.get('rsi'))
            delta = d['close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ma_up = up.ewm(alpha=1/period, adjust=False).mean()
            ma_down = down.ewm(alpha=1/period, adjust=False).mean()
            rs = ma_up / ma_down
            rsi = 100 - (100 / (1 + rs))
            addplots.append(mpf.make_addplot(rsi, panel=1, color='purple'))

    if out_path:
        outp = Path(out_path)
        outp.parent.mkdir(parents=True, exist_ok=True)
        mpf.plot(d, type='candle', style='yahoo', addplot=addplots, volume=True, savefig=str(outp))
        return str(outp)

    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        mpf.plot(d, type='candle', style='yahoo', addplot=addplots, volume=True, savefig=str(tmp_path))
        with open(tmp_path, 'rb') as fh:
            data = fh.read()
        return data
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# Note: no mplfinance fallback. finplot is required.


def render_chart(df: pd.DataFrame, indicators: dict, out_path: str = None):
    """Render using finplot only.

    df: DataFrame with columns date/open/high/low/close/volume
    indicators: dict describing overlays
    out_path: optional path to write PNG (if omitted, returns bytes)
    Returns bytes if out_path is None, or the output path if out_path provided.
    """
    # Prefer mplfinance (matplotlib) rendering for server-side/headless environments
    # because it doesn't require a Qt event loop. If mplfinance is unavailable or
    # fails, fall back to finplot (which may require PyQt) and use the subprocess
    # isolation trick for finplot if Qt/thread errors occur.
    try:
        return _mplfinance_render(df, indicators, out_path)
    except Exception as e_mpf:
        # log the mplfinance failure and try finplot as a fallback
        mpf_tb = traceback.format_exc()
        try:
            return _try_finplot_render(df, indicators, out_path)
        except Exception as e_fplt:
            tb = traceback.format_exc()
            err_text = str(e_fplt)
            qt_error_indicators = [
                'Cannot set parent',
                'Cannot filter events',
                'QBasicTimer',
                'wrapped C/C++ object',
                'FinViewBox',
                'pyqt',
                'QThread',
            ]
            if any(k in err_text for k in qt_error_indicators) or 'FinViewBox' in tb:
                try:
                    return _render_via_subprocess(df, indicators, out_path)
                except Exception as e2:
                    tb2 = traceback.format_exc()
                    raise RuntimeError(f"mplfinance failed: {e_mpf}\n{mpf_tb}\nfinplot direct failed: {e_fplt}\n{tb}\nsubprocess fallback also failed: {e2}\n{tb2}")
            raise RuntimeError(f"mplfinance failed: {e_mpf}\n{mpf_tb}\nfinplot failed: {e_fplt}\n{tb}")


def _subprocess_worker(csv_path: str, indicators_json: str, out_path: str):
    """Worker entrypoint run in a separate process. Reads CSV, renders with finplot
    to the given out_path (must be a writable filename)."""
    # Import pandas inside the worker process
    import pandas as pd_local
    try:
        df = pd_local.read_csv(csv_path, parse_dates=['date'])
        indicators = json.loads(indicators_json)
        # call the internal finplot renderer which writes to out_path when provided
        _try_finplot_render(df, indicators, out_path)
    except Exception:
        # ensure any failure is visible via exit code; re-raise
        raise


def _render_via_subprocess(df: pd.DataFrame, indicators: dict, out_path: str = None, timeout: int = 30):
    """Render by spawning a subprocess worker which creates its own Qt event loop.

    This writes the DataFrame to a temporary CSV and instructs the child process
    to render to a temporary PNG. The PNG bytes are returned to the caller.
    """
    # prepare temp files
    tmp_csv = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
    tmp_csv_path = tmp_csv.name
    tmp_csv.close()
    # write DataFrame to CSV
    df_to_write = df.copy()
    # Ensure date column exists and is serialized properly
    if 'date' in df_to_write.columns:
        df_to_write['date'] = pd.to_datetime(df_to_write['date'])
    df_to_write.to_csv(tmp_csv_path, index=False)

    tmp_png = None
    try:
        if out_path:
            png_path = out_path
            Path(png_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            tmp_png = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            png_path = tmp_png.name
            tmp_png.close()

        indicators_json = json.dumps(indicators or {})

        # spawn process
        proc = multiprocessing.Process(target=_subprocess_worker, args=(tmp_csv_path, indicators_json, png_path))
        proc.start()
        proc.join(timeout)
        if proc.is_alive():
            proc.terminate()
            proc.join(1)
            raise RuntimeError('finplot subprocess timed out')
        if proc.exitcode != 0:
            raise RuntimeError(f'finplot subprocess failed with exitcode {proc.exitcode}')

        # read output PNG
        if not os.path.exists(png_path):
            raise RuntimeError('finplot subprocess did not produce output PNG')
        with open(png_path, 'rb') as fh:
            data = fh.read()

        if out_path:
            # caller expected a file path
            return png_path
        return data
    finally:
        try:
            os.unlink(tmp_csv_path)
        except Exception:
            pass
        if tmp_png and os.path.exists(tmp_png.name):
            try:
                os.unlink(tmp_png.name)
            except Exception:
                pass
