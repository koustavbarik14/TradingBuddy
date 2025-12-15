from typing import Dict, List
import pandas as pd
import numpy as np


class PatternDetection:
    """Extended pattern detection: breakouts, candlesticks and simple structural patterns.

    NOTE: These are heuristic detectors (not exhaustive) and intended as a starter.
    """

    @staticmethod
    def detect_breakout(df: pd.DataFrame, lookback: int = 20, volume_multiplier: float = 1.5) -> Dict:
        if len(df) < lookback + 1:
            return {'breakout': False}
        recent = df.iloc[-lookback-1:-1]
        resistance = recent['high'].max()
        support = recent['low'].min()
        avg_volume = recent['volume'].mean()
        current = df.iloc[-1]
        price_breakout_up = current['close'] > resistance
        price_breakout_down = current['close'] < support
        volume_surge = current['volume'] > (avg_volume * volume_multiplier)
        if price_breakout_up and volume_surge:
            return {'breakout': True, 'type': 'bullish', 'level': float(resistance)}
        if price_breakout_down and volume_surge:
            return {'breakout': True, 'type': 'bearish', 'level': float(support)}
        return {'breakout': False}

    @staticmethod
    def detect_candlestick_patterns(df: pd.DataFrame) -> List[str]:
        patterns = []
        if len(df) < 3:
            return patterns
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        def is_bullish(c):
            return c['close'] > c['open']

        def is_bearish(c):
            return c['close'] < c['open']

        def body_size(c):
            return abs(c['close'] - c['open'])

        def range_size(c):
            return c['high'] - c['low']

        # Doji
        if body_size(c3) < range_size(c3) * 0.1:
            patterns.append('doji')

        # Bullish Engulfing
        if is_bearish(c2) and is_bullish(c3) and c3['open'] < c2['close'] and c3['close'] > c2['open']:
            patterns.append('bullish_engulfing')

        # Bearish Engulfing
        if is_bullish(c2) and is_bearish(c3) and c3['open'] > c2['close'] and c3['close'] < c2['open']:
            patterns.append('bearish_engulfing')

        # Hammer
        if is_bullish(c3) and (c3['close'] - c3['low']) > body_size(c3) * 2 and (c3['high'] - c3['close']) < body_size(c3) * 0.3:
            patterns.append('hammer')

        # Shooting star
        if is_bearish(c3) and (c3['high'] - c3['open']) > body_size(c3) * 2 and (c3['close'] - c3['low']) < body_size(c3) * 0.3:
            patterns.append('shooting_star')

        return patterns

    @staticmethod
    def detect_head_and_shoulders(df: pd.DataFrame, window: int = 60) -> Dict:
        """Very simple head-and-shoulders detector over recent window.

        Returns a dict with 'pattern': True/False and approximate points when found.
        This is heuristic: find three peaks with the middle higher than the sides and troughs between them.
        """
        if len(df) < window:
            return {'pattern': False}
        recent = df['high'].iloc[-window:]
        peaks_idx = (np.diff(np.sign(np.diff(recent))) < 0).nonzero()[0] + 1
        if len(peaks_idx) < 3:
            return {'pattern': False}
        # Select last three peaks
        p = peaks_idx[-3:]
        h1, h2, h3 = recent.iloc[p[0]], recent.iloc[p[1]], recent.iloc[p[2]]
        # Middle peak should be the highest and shoulders somewhat similar
        if h2 > h1 and h2 > h3 and abs(h1 - h3) / max(h1, h3) < 0.15:
            return {'pattern': True, 'left_shoulder': float(h1), 'head': float(h2), 'right_shoulder': float(h3)}
        return {'pattern': False}

    @staticmethod
    def detect_triangle(df: pd.DataFrame, lookback: int = 60, tolerance: float = 0.02) -> Dict:
        """Detect simple contracting highs/lows (triangle consolidation).

        Heuristic: within lookback, highs form a descending line and lows an ascending line.
        """
        if len(df) < lookback:
            return {'pattern': False}
        recent = df[-lookback:]
        highs = recent['high'].values
        lows = recent['low'].values
        x = np.arange(len(highs))
        # fit first-degree polynomial
        hi_coef = np.polyfit(x, highs, 1)
        lo_coef = np.polyfit(x, lows, 1)
        # descending highs and ascending lows
        if hi_coef[0] < 0 and lo_coef[0] > 0:
            # check contraction magnitude
            hi_range = highs.max() - highs.min()
            lo_range = lows.max() - lows.min()
            if hi_range > 0 and lo_range > 0 and (hi_range + lo_range) / (recent['close'].mean()) < 0.25:
                return {'pattern': True, 'hi_slope': float(hi_coef[0]), 'lo_slope': float(lo_coef[0])}
        return {'pattern': False}

    @staticmethod
    def detect_cup_and_handle(df: pd.DataFrame, lookback: int = 200) -> Dict:
        """Very naive cup & handle detector: looks for a U-shaped bottom followed by a small pullback.

        This is a loose heuristic: find a rounded bottom where left and right peaks are similar and center is lower.
        """
        if len(df) < lookback:
            return {'pattern': False}
        recent = df['close'].iloc[-lookback:]
        mid = len(recent) // 2
        left_peak = recent[:mid].max()
        right_peak = recent[mid:].max()
        bottom = recent.min()
        # Peaks roughly similar and bottom significantly lower
        if abs(left_peak - right_peak) / max(left_peak, right_peak) < 0.12 and bottom < 0.9 * min(left_peak, right_peak):
            # check small handle in last 20% of the series
            handle = recent.iloc[int(len(recent)*0.75):]
            if handle.max() < right_peak and handle.std() < recent.std() * 0.6:
                return {'pattern': True, 'left_peak': float(left_peak), 'right_peak': float(right_peak), 'bottom': float(bottom)}
        return {'pattern': False}
