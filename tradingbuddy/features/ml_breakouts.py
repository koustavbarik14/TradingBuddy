"""
ML/AI-powered breakout pattern detection using technical analysis.

Detects multiple breakout patterns across different timeframes:
- Darvas Box
- Cup and Handle
- Flag patterns (bullish/bearish)
- Double Bottom/Top
- Triangle breakouts
- RSI Divergence
- Volume Spike breakout
- MACD crossover
- Bollinger Band squeeze breakout
- Moving Average crossover
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class BreakoutPattern:
    """Represents a detected breakout pattern or pattern formation"""
    symbol: str
    pattern_type: str
    confidence: float  # 0-1 confidence score
    entry_price: float
    breakout_date: str
    description: str
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    status: str = "forming"  # 'forming' or 'confirmed' - NEW FIELD
    timeframe: str = "daily"  # 'daily', 'weekly', or 'monthly'


class MLBreakoutDetector:
    """AI/ML-powered breakout pattern detector with pre-breakout alerts"""
    
    def __init__(self, timeframe: str = 'daily', pre_breakout_mode: bool = True):
        """
        Initialize detector with timeframe.
        
        Args:
            timeframe: 'daily', 'weekly', or 'monthly'
            pre_breakout_mode: If True, detect patterns FORMING (before breakout). If False, detect confirmed breakouts only.
        """
        self.timeframe = timeframe.lower()
        self.pre_breakout_mode = pre_breakout_mode
        self.min_candles_for_pattern = 20
        self.min_pattern_length = 5
        self.tolerance = 0.02  # 2% tolerance for level confirmation
        
        # Pre-breakout detection uses wider tolerances
        if pre_breakout_mode:
            self.proximity_threshold = 0.03  # 3% from resistance to trigger alert
            self.volume_increase_threshold = 1.3  # 30% above average
        else:
            self.proximity_threshold = 0.005  # Must actually break through
            self.volume_increase_threshold = 1.5  # 50% above average
    
    def _get_min_candles(self, default: int) -> int:
        """Adjust minimum candles based on timeframe"""
        if self.timeframe == 'monthly':
            # For monthly, we need fewer candles (each is a month)
            return max(6, int(default * 0.3))
        elif self.timeframe == 'weekly':
            # For weekly, reduce slightly
            return max(10, int(default * 0.5))
        return default
    
    def detect_all_patterns(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """Detect all available breakout patterns in OHLC data"""
        if df is None or df.empty or len(df) < self.min_candles_for_pattern:
            return []
        
        patterns = []
        
        # Detect all pattern types with error handling
        try:
            darvas = self._detect_darvas_box(df, symbol)
            if darvas:
                patterns.extend(darvas)
        except Exception:
            pass
        
        try:
            cup_handle = self._detect_cup_handle(df, symbol)
            if cup_handle:
                patterns.extend(cup_handle)
        except Exception:
            pass
        
        try:
            flags = self._detect_flag_pattern(df, symbol)
            if flags:
                patterns.extend(flags)
        except Exception:
            pass
        
        try:
            double_patterns = self._detect_double_patterns(df, symbol)
            if double_patterns:
                patterns.extend(double_patterns)
        except Exception:
            pass
        
        try:
            triangle = self._detect_triangle_breakout(df, symbol)
            if triangle:
                patterns.extend(triangle)
        except Exception:
            pass
        
        try:
            rsi_div = self._detect_rsi_divergence(df, symbol)
            if rsi_div:
                patterns.extend(rsi_div)
        except Exception:
            pass
        
        try:
            vol_spike = self._detect_volume_spike_breakout(df, symbol)
            if vol_spike:
                patterns.extend(vol_spike)
        except Exception:
            pass
        
        try:
            macd = self._detect_macd_crossover(df, symbol)
            if macd:
                patterns.extend(macd)
        except Exception:
            pass
        
        try:
            bb_squeeze = self._detect_bollinger_squeeze(df, symbol)
            if bb_squeeze:
                patterns.extend(bb_squeeze)
        except Exception:
            pass
        
        try:
            ma_cross = self._detect_moving_average_crossover(df, symbol)
            if ma_cross:
                patterns.extend(ma_cross)
        except Exception:
            pass
        
        try:
            channel = self._detect_channel_breakout(df, symbol)
            if channel:
                patterns.extend(channel)
        except Exception:
            pass
        
        try:
            hs = self._detect_head_shoulders(df, symbol)
            if hs:
                patterns.extend(hs)
        except Exception:
            pass
        
        try:
            ihs = self._detect_inverse_head_shoulders(df, symbol)
            if ihs:
                patterns.extend(ihs)
        except Exception:
            pass
        
        # Pre-breakout mode: Add generic resistance test pattern - DISABLED
        # User wants to see only patterns that are testing resistance, not standalone resistance tests
        # if self.pre_breakout_mode:
        #     try:
        #         resistance_test = self._detect_resistance_test(df, symbol)
        #         if resistance_test:
        #             patterns.extend(resistance_test)
        #     except Exception:
        #         pass
        
        # Sort by confidence descending
        patterns.sort(key=lambda x: x.confidence, reverse=True)
        
        return patterns
    
    def _detect_resistance_test(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """Generic resistance test: Price approaching a key resistance level"""
        patterns = []
        min_candles = self._get_min_candles(30)
        if len(df) < min_candles:
            return patterns
        
        try:
            current_price = df['close'].iloc[-1]
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].tail(20).mean()
            
            # Find resistance levels (multiple touches at similar price)
            lookback = 20 if self.timeframe == 'daily' else (10 if self.timeframe == 'weekly' else 5)
            recent_highs = df['high'].tail(lookback)
            
            # Group similar highs (within 1.5% of each other)
            from collections import Counter
            price_clusters = []
            for high in recent_highs:
                added = False
                for cluster in price_clusters:
                    if abs(high - cluster['price']) / cluster['price'] < 0.015:
                        cluster['count'] += 1
                        cluster['price'] = (cluster['price'] * (cluster['count'] - 1) + high) / cluster['count']
                        added = True
                        break
                if not added:
                    price_clusters.append({'price': high, 'count': 1})
            
            # Find strongest resistance (most touches)
            if price_clusters:
                resistance_level = max(price_clusters, key=lambda x: x['count'])
                
                if resistance_level['count'] >= 2:  # At least 2 touches
                    distance_pct = (resistance_level['price'] - current_price) / resistance_level['price']
                    
                    # Alert if within 2% of resistance
                    if 0 <= distance_pct <= 0.02:
                        confidence = 0.65 + (resistance_level['count'] - 2) * 0.05
                        if current_volume > avg_volume * 1.2:
                            confidence += 0.10
                        
                        patterns.append(BreakoutPattern(
                            symbol=symbol,
                            pattern_type='resistance_test',
                            confidence=min(0.85, confidence),
                            entry_price=round(current_price, 2),
                            breakout_date=str(df.index[-1].date()) if hasattr(df.index[-1], 'date') else str(len(df)-1),
                            description=f'Testing resistance at ${resistance_level["price"]:.2f} ({resistance_level["count"]} touches, {self.timeframe})',
                            support_level=round(df['low'].tail(lookback).min(), 2),
                            resistance_level=round(resistance_level['price'], 2),
                            status='forming',
                            timeframe=self.timeframe
                        ))
        except Exception:
            pass
        
        return patterns
    
    def _detect_darvas_box(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """Darvas Box: Detects consolidation near highs with potential breakout"""
        patterns = []
        min_candles = self._get_min_candles(25)
        if len(df) < min_candles:
            return patterns
        
        try:
            # Adjust lookback based on timeframe
            if self.timeframe == 'daily':
                lookback = 21  # 3 weeks
            elif self.timeframe == 'weekly':
                lookback = 12  # 3 months
            else:  # monthly
                lookback = 6   # 6 months
            
            # Get recent data
            recent_df = df.tail(lookback)
            high_prev = recent_df['high'].iloc[:-1].max()
            current_price = df['close'].iloc[-1]
            current_high = df['high'].iloc[-1]
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].tail(20).mean()
            
            # Check for consolidation (last 5 candles)
            consolidation_window = df.tail(5)
            consolidation_range = consolidation_window['high'].max() - consolidation_window['low'].min()
            consolidation_pct = consolidation_range / high_prev
            
            # PRE-BREAKOUT MODE: Price near resistance with consolidation
            if self.pre_breakout_mode:
                # Price within 3% of resistance
                distance_to_resistance = (high_prev - current_price) / high_prev
                
                if 0 <= distance_to_resistance <= self.proximity_threshold and consolidation_pct < 0.03:
                    confidence = 0.70 + (1 - distance_to_resistance / self.proximity_threshold) * 0.15
                    if current_volume > avg_volume * 1.2:
                        confidence += 0.10  # Volume surge bonus
                    
                    patterns.append(BreakoutPattern(
                        symbol=symbol,
                        pattern_type='darvas_box',
                        confidence=min(0.95, confidence),
                        entry_price=round(current_price, 2),
                        breakout_date=str(df.index[-1].date()) if hasattr(df.index[-1], 'date') else str(len(df)-1),
                        description=f'Darvas Box forming - testing resistance ${high_prev:.2f} ({self.timeframe})',
                        support_level=round(consolidation_window['low'].min(), 2),
                        resistance_level=round(high_prev, 2),
                        status='forming',
                        timeframe=self.timeframe
                    ))
            
            # CONFIRMED BREAKOUT: Price broke above resistance
            if current_high > high_prev * 1.01:
                if consolidation_pct < 0.03:  # Tight consolidation before breakout
                    confidence = min(0.90, 0.65 + (current_high - high_prev) / high_prev * 10)
                    if current_volume > avg_volume * 1.5:
                        confidence += 0.10
                    
                    patterns.append(BreakoutPattern(
                        symbol=symbol,
                        pattern_type='darvas_box',
                        confidence=min(0.95, confidence),
                        entry_price=round(current_high, 2),
                        breakout_date=str(df.index[-1].date()) if hasattr(df.index[-1], 'date') else str(len(df)-1),
                        description=f'Darvas Box BREAKOUT confirmed above ${high_prev:.2f} ({self.timeframe})',
                        support_level=round(consolidation_window['low'].min(), 2),
                        resistance_level=round(current_high, 2),
                        status='confirmed',
                        timeframe=self.timeframe
                    ))
                    
        except Exception:
            pass
        
        return patterns[:1] if patterns else []
    
    def _detect_cup_handle(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """
        Cup and Handle pattern: U-shaped price action followed by small flag/pennant.
        Pattern: Down move, rounded bottom (cup), up move, small consolidation (handle), breakout up.
        """
        patterns = []
        
        min_candles = self._get_min_candles(40)
        if len(df) < min_candles:
            return patterns
        
        try:
            # Look for recent breakouts
            for i in range(len(df) - 5, len(df)):
                # Look back 40 candles for cup formation
                window = 40
                start_idx = max(0, i - window)
                
                window_data = df.iloc[start_idx:i+1].copy()
                window_close = window_data['close'].values
                
                if len(window_close) < 20:
                    continue
                
                # Find the dip (cup bottom)
                cup_bottom_idx = np.argmin(window_close[5:-5]) + 5
                
                # Check if we have an up move after bottom
                left_side = window_close[5:cup_bottom_idx]
                right_side = window_close[cup_bottom_idx:-5]
                
                if len(left_side) < 5 or len(right_side) < 5:
                    continue
                
                # Both sides should be going down then up (U-shape)
                if left_side[-1] > left_side[0] and right_side[-1] > right_side[0]:
                    # Check for small consolidation (handle) at end
                    handle_volatility = np.std(right_side[-5:])
                    avg_volatility = np.std(window_close)
                    
                    if handle_volatility < avg_volatility * 0.5:
                        # Current price should be breaking out
                        cup_bottom = window_close[cup_bottom_idx]
                        cup_top = max(left_side[0], right_side[-1])
                        current_price = window_close[-1]
                        
                        if current_price > cup_top * (1 - self.tolerance):
                            confidence = 0.70 + (0.25 * min(1.0, handle_volatility / avg_volatility))
                            breakout_date = df.index[i].strftime('%Y-%m-%d') if hasattr(df.index[i], 'strftime') else str(df.index[i])
                            
                            patterns.append(BreakoutPattern(
                                symbol=symbol,
                                pattern_type='cup_handle',
                                confidence=confidence,
                                entry_price=cup_top,
                                breakout_date=breakout_date,
                                description=f'Cup and Handle pattern, breakout above ${cup_top:.2f}',
                                resistance_level=cup_top,
                                support_level=cup_bottom,
                                timeframe=self.timeframe
                            ))
        except Exception as e:
            pass
        
        return patterns[:1]  # Return top 1
    
    def _detect_flag_pattern(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """
        Flag pattern: Strong move (flagpole) followed by small parallel consolidation (flag).
        Can be bullish (uptrend) or bearish (downtrend).
        """
        patterns = []
        
        min_candles = self._get_min_candles(30)
        if len(df) < min_candles:
            return patterns
        
        try:
            # Look for recent breakouts
            for i in range(len(df) - 5, len(df)):
                window = 30
                start_idx = max(0, i - window)
                
                window_data = df.iloc[start_idx:i+1].copy()
                close = window_data['close'].values
                high = window_data['high'].values
                low = window_data['low'].values
                
                # Find trend change point (flagpole)
                for pole_idx in range(5, len(close) - 10):
                    # Check for strong move before and consolidation after
                    before = close[:pole_idx]
                    after = close[pole_idx:]
                    
                    if len(before) < 5 or len(after) < 5:
                        continue
                    
                    before_move = abs(before[-1] - before[0]) / before[0]
                    after_move = abs(after[-1] - after[0]) / after[0]
                    after_volatility = np.std(after)
                    
                    # Strong move followed by consolidation
                    if before_move > 0.05 and after_move < before_move * 0.5:
                        flag_breakout = close[-1] > max(high[pole_idx:])
                        
                        if flag_breakout:
                            # Bullish flag if up move, bearish if down move
                            is_bullish = before[-1] > before[0]
                            confidence = 0.65 + (0.3 * min(1.0, before_move / 0.15))
                            
                            entry_price = max(high[pole_idx:]) if is_bullish else min(low[pole_idx:])
                            breakout_date = df.index[i].strftime('%Y-%m-%d') if hasattr(df.index[i], 'strftime') else str(df.index[i])
                            
                            pattern_type = 'bullish_flag' if is_bullish else 'bearish_flag'
                            
                            patterns.append(BreakoutPattern(
                                symbol=symbol,
                                pattern_type=pattern_type,
                                confidence=confidence,
                                entry_price=entry_price,
                                breakout_date=breakout_date,
                                description=f'{"Bullish" if is_bullish else "Bearish"} flag breakout',
                                resistance_level=max(high[pole_idx:]),
                                support_level=min(low[pole_idx:]),
                                timeframe=self.timeframe
                            ))
                            break
        except Exception as e:
            pass
        
        return patterns[:1]  # Return top 1
    
    def _detect_double_patterns(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """
        Double Bottom/Top: Two troughs/peaks at similar level with consolidation between.
        """
        patterns = []
        
        min_candles = self._get_min_candles(35)
        if len(df) < min_candles:
            return patterns
        
        try:
            for i in range(len(df) - 5, len(df)):
                window = 35
                start_idx = max(0, i - window)
                
                window_data = df.iloc[start_idx:i+1].copy()
                low = window_data['low'].values
                high = window_data['high'].values
                close = window_data['close'].values
                
                # Find two local lows (double bottom)
                for j in range(5, len(low) - 15):
                    for k in range(j + 10, len(low) - 5):
                        # Two lows within tolerance
                        if abs(low[j] - low[k]) < low[j] * self.tolerance:
                            # Check for middle peak
                            middle_high = max(high[j:k])
                            
                            # Current price should be breaking above middle high
                            if close[-1] > middle_high * (1 - self.tolerance):
                                confidence = 0.70
                                breakout_date = df.index[i].strftime('%Y-%m-%d') if hasattr(df.index[i], 'strftime') else str(df.index[i])
                                
                                patterns.append(BreakoutPattern(
                                    symbol=symbol,
                                    pattern_type='double_bottom',
                                    confidence=confidence,
                                    entry_price=middle_high,
                                    breakout_date=breakout_date,
                                    description=f'Double bottom pattern, breakout above ${middle_high:.2f}',
                                    resistance_level=middle_high,
                                    support_level=low[j],
                                    timeframe=self.timeframe
                                ))
                                return patterns
        except Exception as e:
            pass
        
        return patterns[:1]
    
    def _detect_triangle_breakout(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """
        Triangle pattern: Converging highs and lows forming a triangle.
        Ascending: rising lows, falling highs. Descending: falling lows, rising highs.
        """
        patterns = []
        
        min_candles = self._get_min_candles(25)
        if len(df) < min_candles:
            return patterns
        
        try:
            for i in range(len(df) - 5, len(df)):
                window = 25
                start_idx = max(0, i - window)
                
                window_data = df.iloc[start_idx:i+1].copy()
                high = window_data['high'].values
                low = window_data['low'].values
                close = window_data['close'].values
                
                # Find local highs and lows
                local_highs = []
                local_lows = []
                
                for j in range(2, len(high) - 2):
                    if high[j] > high[j-1] and high[j] > high[j+1]:
                        local_highs.append((j, high[j]))
                    if low[j] < low[j-1] and low[j] < low[j+1]:
                        local_lows.append((j, low[j]))
                
                # Check for converging pattern
                if len(local_highs) >= 2 and len(local_lows) >= 2:
                    high_diff = local_highs[-1][1] - local_highs[-2][1]
                    low_diff = local_lows[-1][1] - local_lows[-2][1]
                    
                    # Ascending triangle: rising lows, falling highs
                    if low_diff > 0 and high_diff < 0 and close[-1] > local_highs[-1][1]:
                        confidence = 0.68
                        breakout_date = df.index[i].strftime('%Y-%m-%d') if hasattr(df.index[i], 'strftime') else str(df.index[i])
                        
                        patterns.append(BreakoutPattern(
                            symbol=symbol,
                            pattern_type='ascending_triangle',
                            confidence=confidence,
                            entry_price=local_highs[-1][1],
                            breakout_date=breakout_date,
                            description=f'Ascending triangle breakout above ${local_highs[-1][1]:.2f}',
                            resistance_level=local_highs[-1][1],
                            support_level=local_lows[-1][1],
                            timeframe=self.timeframe
                        ))
                        return patterns
        except Exception as e:
            pass
        
        return patterns[:1]
    
    def _detect_rsi_divergence(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """RSI Divergence: Price makes new high but RSI doesn't - bullish setup"""
        patterns = []
        min_candles = self._get_min_candles(30)
        if len(df) < min_candles:
            return patterns
        
        try:
            # Calculate RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            for i in range(25, len(df)):
                lookback = 15
                start_idx = max(0, i - lookback)
                
                price_high = df['high'].iloc[start_idx:i].max()
                current_high = df['high'].iloc[i]
                rsi_high = rsi.iloc[start_idx:i-1].max()
                current_rsi = rsi.iloc[i]
                
                if current_high > price_high and current_rsi < rsi_high and current_rsi > 50:
                    confidence = 0.72
                    breakout_date = str(df.index[i].date()) if hasattr(df.index[i], 'date') else str(i)
                    
                    patterns.append(BreakoutPattern(
                        symbol=symbol,
                        pattern_type='rsi_divergence',
                        confidence=confidence,
                        entry_price=round(df['close'].iloc[i], 2),
                        breakout_date=breakout_date,
                        description=f'Bullish RSI Divergence ({self.timeframe}, RSI: {current_rsi:.0f})',
                        support_level=round(df['low'].iloc[start_idx:i].min(), 2),
                        resistance_level=round(current_high, 2),
                        timeframe=self.timeframe
                    ))
                    return patterns
        except Exception:
            pass
        
        return patterns
    
    def _detect_volume_spike_breakout(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """Volume Spike: Detects unusual volume with price approaching resistance"""
        patterns = []
        if len(df) < 20 or 'volume' not in df.columns:
            return patterns
        
        try:
            avg_volume = df['volume'].tail(20).mean()
            current_volume = df['volume'].iloc[-1]
            current_price = df['close'].iloc[-1]
            current_high = df['high'].iloc[-1]
            
            # Get resistance level (recent high)
            lookback = 10 if self.timeframe == 'daily' else (5 if self.timeframe == 'weekly' else 2)
            recent_high = df['high'].tail(lookback + 5).iloc[:-1].max()
            
            volume_ratio = current_volume / avg_volume
            
            # PRE-BREAKOUT: Volume spike near resistance
            if self.pre_breakout_mode and volume_ratio > self.volume_increase_threshold:
                distance_to_resistance = (recent_high - current_price) / recent_high
                
                if 0 <= distance_to_resistance <= self.proximity_threshold:
                    confidence = 0.70 + (volume_ratio - self.volume_increase_threshold) * 0.1
                    confidence = min(0.90, confidence)
                    
                    patterns.append(BreakoutPattern(
                        symbol=symbol,
                        pattern_type='volume_surge',
                        confidence=confidence,
                        entry_price=round(current_price, 2),
                        breakout_date=str(df.index[-1].date()) if hasattr(df.index[-1], 'date') else str(len(df)-1),
                        description=f'Volume surge near resistance (vol: {volume_ratio:.1f}x avg, {self.timeframe})',
                        support_level=round(df['low'].tail(lookback).min(), 2),
                        resistance_level=round(recent_high, 2),
                        status='forming',
                        timeframe=self.timeframe
                    ))
            
            # CONFIRMED: Volume spike with breakout
            if current_high > recent_high and volume_ratio > 1.5:
                confidence = 0.75 + min(0.15, (volume_ratio - 1.5) * 0.05)
                
                patterns.append(BreakoutPattern(
                    symbol=symbol,
                    pattern_type='volume_surge',
                    confidence=min(0.92, confidence),
                    entry_price=round(current_high, 2),
                    breakout_date=str(df.index[-1].date()) if hasattr(df.index[-1], 'date') else str(len(df)-1),
                    description=f'Volume Spike BREAKOUT (vol: {volume_ratio:.1f}x avg, {self.timeframe})',
                    support_level=round(df['low'].tail(lookback).min(), 2),
                    resistance_level=round(current_high, 2),
                    status='confirmed',
                    timeframe=self.timeframe
                ))
        except Exception:
            pass
        
        return patterns
    
    def _detect_macd_crossover(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """MACD Crossover: MACD line crosses signal line"""
        patterns = []
        min_candles = self._get_min_candles(30)
        if len(df) < min_candles:
            return patterns
        
        try:
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9).mean()
            
            for i in range(len(df) - 2, len(df)):
                prev_macd = macd.iloc[i-1]
                prev_signal = signal.iloc[i-1]
                curr_macd = macd.iloc[i]
                curr_signal = signal.iloc[i]
                
                # Bullish crossover
                if prev_macd < prev_signal and curr_macd > curr_signal and curr_macd > 0:
                    confidence = 0.70
                    breakout_date = str(df.index[i].date()) if hasattr(df.index[i], 'date') else str(i)
                    
                    patterns.append(BreakoutPattern(
                        symbol=symbol,
                        pattern_type='macd_bullish_crossover',
                        confidence=confidence,
                        entry_price=round(df['close'].iloc[i], 2),
                        breakout_date=breakout_date,
                        description=f'MACD Bullish Crossover ({self.timeframe})',
                        support_level=round(df['low'].iloc[max(0, i-5):i].min(), 2),
                        resistance_level=round(df['high'].iloc[max(0, i-5):i].max(), 2),
                        timeframe=self.timeframe
                    ))
                    return patterns
        except Exception:
            pass
        
        return patterns
    
    def _detect_bollinger_squeeze(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """Bollinger Band Squeeze: Bands contract then expand with breakout"""
        patterns = []
        min_candles = self._get_min_candles(25)
        if len(df) < min_candles:
            return patterns
        
        try:
            sma = df['close'].rolling(window=20).mean()
            std = df['close'].rolling(window=20).std()
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)
            
            for i in range(20, len(df)):
                band_width = upper_band.iloc[i] - lower_band.iloc[i]
                avg_band_width = (upper_band.iloc[max(0, i-10):i] - lower_band.iloc[max(0, i-10):i]).mean()
                
                if band_width < avg_band_width * 0.5:
                    if df['close'].iloc[i] > upper_band.iloc[i]:
                        confidence = 0.75
                        breakout_date = str(df.index[i].date()) if hasattr(df.index[i], 'date') else str(i)
                        
                        patterns.append(BreakoutPattern(
                            symbol=symbol,
                            pattern_type='bollinger_squeeze_breakout',
                            confidence=confidence,
                            entry_price=round(df['close'].iloc[i], 2),
                            breakout_date=breakout_date,
                            description=f'Bollinger Squeeze Breakout ({self.timeframe})',
                            support_level=round(lower_band.iloc[i], 2),
                            resistance_level=round(upper_band.iloc[i], 2),
                            timeframe=self.timeframe
                        ))
                        return patterns
        except Exception:
            pass
        
        return patterns
    
    def _detect_moving_average_crossover(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """Moving Average Crossover: Fast MA crosses above slow MA (Golden Cross)"""
        patterns = []
        min_candles = self._get_min_candles(55)
        if len(df) < min_candles:
            return patterns
        
        try:
            fast_ma = df['close'].rolling(window=20).mean()
            slow_ma = df['close'].rolling(window=50).mean()
            
            for i in range(50, len(df)):
                prev_fast = fast_ma.iloc[i-1]
                prev_slow = slow_ma.iloc[i-1]
                curr_fast = fast_ma.iloc[i]
                curr_slow = slow_ma.iloc[i]
                
                # Golden cross: fast MA crosses above slow MA
                if prev_fast <= prev_slow and curr_fast > curr_slow:
                    confidence = 0.73
                    breakout_date = str(df.index[i].date()) if hasattr(df.index[i], 'date') else str(i)
                    
                    patterns.append(BreakoutPattern(
                        symbol=symbol,
                        pattern_type='golden_cross',
                        confidence=confidence,
                        entry_price=round(df['close'].iloc[i], 2),
                        breakout_date=breakout_date,
                        description=f'Golden Cross (20/50 MA, {self.timeframe})',
                        support_level=round(slow_ma.iloc[i], 2),
                        resistance_level=round(df['high'].iloc[max(0, i-5):i].max(), 2),
                        timeframe=self.timeframe
                    ))
                    return patterns
        except Exception:
            pass
        
        return patterns
    
    def _detect_channel_breakout(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """Detect breakout from ascending/descending channel"""
        patterns = []
        
        try:
            # Need at least 30 candles for channel
            if len(df) < 30:
                return patterns
            
            # Calculate linear regression for highs and lows
            from scipy.stats import linregress
            
            # Use last 30 candles to identify channel
            window = df.tail(30)
            x = np.arange(len(window))
            
            # Regression on highs (upper channel line)
            slope_high, intercept_high, r_high, _, _ = linregress(x, window['high'].values)
            
            # Regression on lows (lower channel line)
            slope_low, intercept_low, r_low, _, _ = linregress(x, window['low'].values)
            
            # Check if channel exists (R-squared > 0.7 for both)
            if r_high ** 2 > 0.7 and r_low ** 2 > 0.7:
                # Calculate channel lines at current position
                current_x = len(window) - 1
                upper_channel = slope_high * current_x + intercept_high
                lower_channel = slope_low * current_x + intercept_low
                
                current_close = df['close'].iloc[-1]
                prev_close = df['close'].iloc[-2]
                
                # Detect breakout above upper channel
                if current_close > upper_channel and prev_close <= upper_channel:
                    confidence = min(0.95, (r_high ** 2 + r_low ** 2) / 2)
                    
                    patterns.append(BreakoutPattern(
                        symbol=symbol,
                        pattern_type='channel_breakout',
                        confidence=confidence,
                        entry_price=current_close,
                        breakout_date=str(df.index[-1].date()),
                        support_level=lower_channel,
                        resistance_level=upper_channel,
                        description=f'Breakout above {"ascending" if slope_high > 0 else "descending"} channel',
                        timeframe=self.timeframe
                    ))
        
        except Exception:
            pass
        
        return patterns
    
    def _detect_head_shoulders(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """Detect Head and Shoulders pattern (bearish reversal)"""
        patterns = []
        
        try:
            if len(df) < 40:
                return patterns
            
            # Look for 3 peaks in last 40 candles
            window = df.tail(40)
            highs = window['high'].values
            
            # Find local maxima (peaks)
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(highs, distance=5, prominence=highs.std() * 0.5)
            
            if len(peaks) >= 3:
                # Check last 3 peaks for head and shoulders pattern
                left_shoulder = highs[peaks[-3]]
                head = highs[peaks[-2]]
                right_shoulder = highs[peaks[-1]]
                
                # Head should be higher than both shoulders
                # Shoulders should be roughly equal (within 3%)
                shoulder_diff = abs(left_shoulder - right_shoulder) / left_shoulder
                
                if (head > left_shoulder * 1.05 and 
                    head > right_shoulder * 1.05 and 
                    shoulder_diff < 0.03):
                    
                    # Find neckline (support between shoulders)
                    neckline_start = window['low'].iloc[peaks[-3]:peaks[-2]].min()
                    neckline_end = window['low'].iloc[peaks[-2]:peaks[-1]].min()
                    neckline = (neckline_start + neckline_end) / 2
                    
                    current_close = df['close'].iloc[-1]
                    
                    # Breakdown below neckline confirms pattern
                    if current_close < neckline:
                        confidence = 0.75 + (head / max(left_shoulder, right_shoulder) - 1) * 2
                        confidence = min(0.95, confidence)
                        
                        patterns.append(BreakoutPattern(
                            symbol=symbol,
                            pattern_type='head_shoulders',
                            confidence=confidence,
                            entry_price=current_close,
                            breakout_date=str(df.index[-1].date()),
                            support_level=neckline * 0.95,
                            resistance_level=neckline,
                            description=f'Head & Shoulders breakdown - bearish reversal signal',
                            timeframe=self.timeframe
                        ))
        
        except Exception:
            pass
        
        return patterns
    
    def _detect_inverse_head_shoulders(self, df: pd.DataFrame, symbol: str) -> List[BreakoutPattern]:
        """Detect Inverse Head and Shoulders pattern (bullish reversal)"""
        patterns = []
        
        try:
            if len(df) < 40:
                return patterns
            
            # Look for 3 troughs in last 40 candles
            window = df.tail(40)
            lows = window['low'].values
            
            # Find local minima (troughs)
            from scipy.signal import find_peaks
            troughs, _ = find_peaks(-lows, distance=5, prominence=lows.std() * 0.5)
            
            if len(troughs) >= 3:
                # Check last 3 troughs for inverse head and shoulders
                left_shoulder = lows[troughs[-3]]
                head = lows[troughs[-2]]
                right_shoulder = lows[troughs[-1]]
                
                # Head should be lower than both shoulders
                # Shoulders should be roughly equal (within 3%)
                shoulder_diff = abs(left_shoulder - right_shoulder) / left_shoulder
                
                if (head < left_shoulder * 0.95 and 
                    head < right_shoulder * 0.95 and 
                    shoulder_diff < 0.03):
                    
                    # Find neckline (resistance between shoulders)
                    neckline_start = window['high'].iloc[troughs[-3]:troughs[-2]].max()
                    neckline_end = window['high'].iloc[troughs[-2]:troughs[-1]].max()
                    neckline = (neckline_start + neckline_end) / 2
                    
                    current_close = df['close'].iloc[-1]
                    
                    # Breakout above neckline confirms pattern
                    if current_close > neckline:
                        confidence = 0.75 + (min(left_shoulder, right_shoulder) / head - 1) * 2
                        confidence = min(0.95, confidence)
                        
                        patterns.append(BreakoutPattern(
                            symbol=symbol,
                            pattern_type='inverse_head_shoulders',
                            confidence=confidence,
                            entry_price=current_close,
                            breakout_date=str(df.index[-1].date()),
                            support_level=neckline,
                            resistance_level=neckline * 1.05,
                            description=f'Inverse Head & Shoulders breakout - bullish reversal signal',
                            timeframe=self.timeframe
                        ))
        
        except Exception:
            pass
        
        return patterns


def detect_breakouts_for_universe(data_loader, symbols: List[str], limit: int = 10, timeframe: str = 'daily', pre_breakout_mode: bool = True) -> List[BreakoutPattern]:
    """
    Scan a universe of symbols and detect breakout patterns.
    
    Args:
        data_loader: Function that returns OHLC data for a symbol
        symbols: List of stock symbols to scan
        limit: Max patterns to return
        timeframe: 'daily', 'weekly', or 'monthly'
        pre_breakout_mode: If True, detect patterns FORMING (before breakout). If False, only confirmed breakouts.
    
    Returns:
        List of top N BreakoutPattern objects sorted by confidence
    """
    detector = MLBreakoutDetector(timeframe=timeframe, pre_breakout_mode=pre_breakout_mode)
    all_patterns = []
    
    for symbol in symbols:
        try:
            df = data_loader(symbol)
            if df is not None and not df.empty:
                patterns = detector.detect_all_patterns(df, symbol)
                all_patterns.extend(patterns)
        except Exception:
            pass
    
    # Sort by confidence descending and return top N
    all_patterns.sort(key=lambda x: x.confidence, reverse=True)
    return all_patterns[:limit]
