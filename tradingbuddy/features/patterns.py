from typing import Dict, List
import pandas as pd
import numpy as np


class PatternDetection:
    """Extended pattern detection: breakouts, candlesticks and simple structural patterns.
    """

    def __init__(self):
        pass

    @staticmethod
    def detect_support_resistance(df: pd.DataFrame, window: int = 20, threshold: float = 0.02) -> Dict:
        highs = df['high'].values
        lows = df['low'].values
        resistance_levels = []
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i-window:i+window]):
                resistance_levels.append(highs[i])
        support_levels = []
        for i in range(window, len(lows) - window):
            if lows[i] == min(lows[i-window:i+window]):
                support_levels.append(lows[i])
        def cluster_levels(levels, threshold):
            if not levels:
                return []
            levels = sorted(levels)
            clusters = [[levels[0]]]
            for level in levels[1:]:
                if abs(level - np.mean(clusters[-1])) / np.mean(clusters[-1]) < threshold:
                    clusters[-1].append(level)
                else:
                    clusters.append([level])
            return [np.mean(cluster) for cluster in clusters]
        return {
            'support': cluster_levels(support_levels, threshold),
            'resistance': cluster_levels(resistance_levels, threshold)
        }

    @staticmethod
    def detect_breakout(df: pd.DataFrame, lookback: int = 20, volume_multiplier: float = 1.5) -> Dict:
        if len(df) < lookback + 1:
            return {'breakout': False}
        current = df.iloc[-1]
        recent = df.iloc[-lookback-1:-1]
        resistance = recent['high'].max()
        support = recent['low'].min()
        avg_volume = recent['volume'].mean()
        price_breakout_up = current['close'] > resistance
        price_breakout_down = current['close'] < support
        volume_surge = current['volume'] > (avg_volume * volume_multiplier)
        if price_breakout_up and volume_surge:
            return {'breakout': True, 'type': 'bullish', 'level': float(resistance), 'volume_ratio': float(current['volume'] / avg_volume)}
        elif price_breakout_down and volume_surge:
            return {'breakout': True, 'type': 'bearish', 'level': float(support), 'volume_ratio': float(current['volume'] / avg_volume)}
        else:
            return {'breakout': False, 'type': None}

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
        if body_size(c3) < range_size(c3) * 0.1:
            patterns.append('doji')
        if is_bearish(c2) and is_bullish(c3) and c3['open'] < c2['close'] and c3['close'] > c2['open']:
            patterns.append('bullish_engulfing')
        if is_bullish(c2) and is_bearish(c3) and c3['open'] > c2['close'] and c3['close'] < c2['open']:
            patterns.append('bearish_engulfing')
        if is_bullish(c3) and (c3['close'] - c3['low']) > body_size(c3) * 2 and (c3['high'] - c3['close']) < body_size(c3) * 0.3:
            patterns.append('hammer')
        if is_bearish(c3) and (c3['high'] - c3['open']) > body_size(c3) * 2 and (c3['close'] - c3['low']) < body_size(c3) * 0.3:
            patterns.append('shooting_star')
        return patterns

    @staticmethod
    def detect_head_and_shoulders(df: pd.DataFrame, window: int = 60) -> Dict:
        if len(df) < window:
            return {'pattern': False}
        recent = df['high'].iloc[-window:]
        peaks_idx = (np.diff(np.sign(np.diff(recent))) < 0).nonzero()[0] + 1
        if len(peaks_idx) < 3:
            return {'pattern': False}
        p = peaks_idx[-3:]
        h1, h2, h3 = recent.iloc[p[0]], recent.iloc[p[1]], recent.iloc[p[2]]
        if h2 > h1 and h2 > h3 and abs(h1 - h3) / max(h1, h3) < 0.15:
            return {'pattern': True, 'left_shoulder': float(h1), 'head': float(h2), 'right_shoulder': float(h3)}
        return {'pattern': False}

    @staticmethod
    def detect_triangle(df: pd.DataFrame, lookback: int = 60) -> Dict:
        if len(df) < lookback:
            return {'pattern': False}
        recent = df[-lookback:]
        highs = recent['high'].values
        lows = recent['low'].values
        x = np.arange(len(highs))
        hi_coef = np.polyfit(x, highs, 1)
        lo_coef = np.polyfit(x, lows, 1)
        if hi_coef[0] < 0 and lo_coef[0] > 0:
            hi_range = highs.max() - highs.min()
            lo_range = lows.max() - lows.min()
            if hi_range > 0 and lo_range > 0 and (hi_range + lo_range) / (recent['close'].mean()) < 0.25:
                return {'pattern': True, 'hi_slope': float(hi_coef[0]), 'lo_slope': float(lo_coef[0])}
        return {'pattern': False}

    @staticmethod
    def detect_cup_and_handle(df: pd.DataFrame, lookback: int = 200) -> Dict:
        if len(df) < lookback:
            return {'pattern': False}
        recent = df['close'].iloc[-lookback:]
        mid = len(recent) // 2
        left_peak = recent[:mid].max()
        right_peak = recent[mid:].max()
        bottom = recent.min()
        if abs(left_peak - right_peak) / max(left_peak, right_peak) < 0.12 and bottom < 0.9 * min(left_peak, right_peak):
            handle = recent.iloc[int(len(recent)*0.75):]
            if handle.max() < right_peak and handle.std() < recent.std() * 0.6:
                return {'pattern': True, 'left_peak': float(left_peak), 'right_peak': float(right_peak), 'bottom': float(bottom)}
        return {'pattern': False}
