import numpy as np
import pandas as pd
from typing import List, Dict


def _safe_clip(x: float) -> float:
    try:
        return float(np.clip(x, -1.0, 1.0))
    except Exception:
        return 0.0


def ma50_score(df: pd.DataFrame) -> float:
    """MA50-based score as described in the notebook transcript.

    Components:
    - distance from MA50 (relative)
    - slope of MA50 over 5 periods (scaled)
    - regime: MA50 > MA200 -> +1 else -1
    Weighting: 0.5, 0.3, 0.2
    """
    try:
        close = df['close'].dropna()
        if len(close) < 50:
            return 0.0

        ma50 = close.rolling(window=50).mean()
        ma200 = close.rolling(window=200).mean()

        ma50_last = ma50.iloc[-1]
        ma50_5ago = ma50.iloc[-5] if len(ma50) > 5 else ma50.iloc[0]
        ma200_last = ma200.iloc[-1] if len(ma200) >= 1 else ma50_last
        close_last = close.iloc[-1]

        dist = (close_last - ma50_last) / (ma50_last if ma50_last != 0 else 1)
        dist_score = _safe_clip(dist)

        slope = (ma50_last - ma50_5ago) / (ma50_5ago if ma50_5ago != 0 else ma50_last)
        slope_score = _safe_clip(slope * 5.0)

        regime = 1.0 if ma50_last > ma200_last else -1.0

        score = 0.5 * dist_score + 0.3 * slope_score + 0.2 * regime
        return _safe_clip(score)
    except Exception:
        return 0.0


def rsi_score_momentum(df: pd.DataFrame, period: int = 14, lookback: int = 20) -> float:
    """RSI momentum score: normalize last RSI change by 2*rolling stddev."""
    try:
        close = df['close'].dropna()
        if len(close) < (period + lookback):
            return 0.0

        # compute RSI using Wilder smoothing
        delta = close.diff()
        up = delta.clip(lower=0.0)
        down = -delta.clip(upper=0.0)
        roll_up = up.ewm(alpha=1/period, adjust=False).mean()
        roll_down = down.ewm(alpha=1/period, adjust=False).mean()
        rs = roll_up / roll_down
        rsi = 100 - (100 / (1 + rs))

        rsi_change = rsi.diff()
        change = rsi_change.iloc[-1]
        stdev = rsi_change.rolling(window=lookback).std().iloc[-1]
        if pd.isna(stdev) or stdev == 0:
            return 0.0
        score = change / (2.0 * stdev)
        return _safe_clip(score)
    except Exception:
        return 0.0


def vol_score(df: pd.DataFrame, lookback_vol: int = 20) -> float:
    """Volume score: current volume relative to lookback average (scaled) * trend sign."""
    try:
        vol = df['volume'].dropna()
        close = df['close'].dropna()
        if len(vol) < lookback_vol + 1 or len(close) < 2:
            return 0.0

        avg_vol = vol.rolling(window=lookback_vol).mean().iloc[-1]
        curr_vol = vol.iloc[-1]
        if pd.isna(avg_vol) or avg_vol == 0:
            return 0.0

        raw_ratio = float(curr_vol / avg_vol)
        ratio_scaled = min(raw_ratio / 5.0, 1.0)

        if close.iloc[-1] > close.iloc[-2]:
            trend_sign = 1.0
        elif close.iloc[-1] < close.iloc[-2]:
            trend_sign = -1.0
        else:
            trend_sign = 0.0

        return _safe_clip(ratio_scaled * trend_sign)
    except Exception:
        return 0.0


def compute_scores_for_universe(data_loader, symbols: List[str]) -> pd.DataFrame:
    """
    Compute scores for a list of symbols. data_loader should be a callable that
    accepts a symbol and returns a DataFrame with lowercase columns: open,high,low,close,volume
    """
    rows: List[Dict] = []
    for s in symbols:
        try:
            df = data_loader(s)
            if df is None or df.empty or len(df) < 20:
                rows.append({'symbol': s, 'ma_score': 0.0, 'rsi_score': 0.0, 'vol_score': 0.0, 'final_score': 0.0})
                continue

            m = ma50_score(df)
            r = rsi_score_momentum(df)
            v = vol_score(df)
            final = _safe_clip(0.5 * m + 0.3 * r + 0.2 * v)
            rows.append({'symbol': s, 'ma_score': m, 'rsi_score': r, 'vol_score': v, 'final_score': final})
        except Exception:
            rows.append({'symbol': s, 'ma_score': 0.0, 'rsi_score': 0.0, 'vol_score': 0.0, 'final_score': 0.0})

    return pd.DataFrame(rows)
