"""
64-Bit Market DNA Fingerprint Generator.
Translates multi-dimensional candlestick data into a single 64-bit unsigned integer.
Enables sub-millisecond Bitwise Holographic pattern matching.
"""

from typing import List, Dict, Any
import math

class MarketFingerprintGenerator:
    """
    Bit Allocation (64 bits):
    [0 - 15]  : Trend & Moving Averages (EMA 9, 21, 50, 200, MACD trend)
    [16 - 31] : Momentum & Oscillators (RSI thresholds, Stochastic, Momentum slope)
    [32 - 43] : Volatility & Channels (ATR ratio, Bollinger Band position, squeeze)
    [44 - 55] : Volume & Flow (Volume vs 20MA, OBV slope, candle volume delta)
    [56 - 63] : Candlestick Anatomy & Multi-timeframe structure
    """

    @staticmethod
    def calculate_fingerprint(ohlcv: List[List[float]]) -> int:
        """
        Takes OHLCV list [[ts, o, h, l, c, v], ...] with at least 50 bars.
        Returns a 64-bit unsigned integer (0 to 2^64 - 1).
        """
        if len(ohlcv) < 20:
            return 0

        closes = [bar[4] for bar in ohlcv]
        highs = [bar[2] for bar in ohlcv]
        lows = [bar[3] for bar in ohlcv]
        opens = [bar[1] for bar in ohlcv]
        volumes = [bar[5] for bar in ohlcv]

        c = closes[-1]
        c_prev = closes[-2]
        o = opens[-1]
        h = highs[-1]
        l = lows[-1]
        v = volumes[-1]

        fp = 0

        # --- Helper Functions ---
        def ema(series, period):
            k = 2.0 / (period + 1)
            val = series[0]
            for price in series[1:]:
                val = (price * k) + (val * (1 - k))
            return val

        def sma(series, period):
            sub = series[-period:] if len(series) >= period else series
            return sum(sub) / len(sub)

        def rsi(series, period=14):
            if len(series) <= period:
                return 50.0
            gains, losses = [], []
            for i in range(1, len(series)):
                diff = series[i] - series[i - 1]
                if diff > 0:
                    gains.append(diff)
                    losses.append(0.0)
                else:
                    gains.append(0.0)
                    losses.append(abs(diff))
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            return 100.0 - (100.0 / (1.0 + rs))

        # --- Compute Technical Primitives ---
        ema_9 = ema(closes, 9)
        ema_21 = ema(closes, 21)
        ema_50 = ema(closes, 50) if len(closes) >= 50 else ema(closes, len(closes))
        rsi_14 = rsi(closes, 14)
        vol_sma_20 = sma(volumes, 20)

        # 1. Trend & Moving Averages (Bits 0 - 15)
        if c > ema_9:        fp |= (1 << 0)
        if c > ema_21:       fp |= (1 << 1)
        if c > ema_50:       fp |= (1 << 2)
        if ema_9 > ema_21:   fp |= (1 << 3)
        if ema_21 > ema_50:  fp |= (1 << 4)
        if c > c_prev:       fp |= (1 << 5)  # Momentum UP
        if c > closes[-5]:   fp |= (1 << 6)  # 5-bar trend UP
        if c > closes[-10]:  fp |= (1 << 7)  # 10-bar trend UP
        if ema_9 > closes[-2]: fp |= (1 << 8)

        # 2. Momentum & Oscillators (Bits 16 - 31)
        if rsi_14 < 30:      fp |= (1 << 16) # Oversold
        if rsi_14 < 20:      fp |= (1 << 17) # Deep oversold
        if rsi_14 > 70:      fp |= (1 << 18) # Overbought
        if rsi_14 > 80:      fp |= (1 << 19) # Extreme overbought
        if 45 <= rsi_14 <= 55: fp |= (1 << 20) # RSI Neutral/Consolidation
        if rsi_14 > rsi(closes[:-1], 14): fp |= (1 << 21) # RSI Slope Rising

        # Fast Stochastic (%K)
        lowest_14 = min(lows[-14:])
        highest_14 = max(highs[-14:])
        stoch_k = ((c - lowest_14) / (highest_14 - lowest_14) * 100.0) if (highest_14 - lowest_14) > 0 else 50.0
        if stoch_k < 20:     fp |= (1 << 22)
        if stoch_k > 80:     fp |= (1 << 23)

        # 3. Volatility & Bands (Bits 32 - 43)
        mean_20 = sma(closes, 20)
        variance = sum((x - mean_20) ** 2 for x in closes[-20:]) / 20.0
        std_20 = math.sqrt(variance)
        bb_upper = mean_20 + (2.0 * std_20)
        bb_lower = mean_20 - (2.0 * std_20)

        if c >= bb_upper:    fp |= (1 << 32) # Piercing Upper BB
        if c <= bb_lower:    fp |= (1 << 33) # Piercing Lower BB
        if std_20 < (mean_20 * 0.005): fp |= (1 << 34) # Bollinger Squeeze (Low Volatility)
        if std_20 > (mean_20 * 0.02):  fp |= (1 << 35) # High Volatility Expansion

        # ATR Ratio
        tr_list = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])) for i in range(1, len(closes))]
        current_tr = tr_list[-1] if tr_list else (h - l)
        avg_tr = sma(tr_list, 14) if tr_list else current_tr
        if current_tr > (avg_tr * 1.5): fp |= (1 << 36) # Volatility Spike

        # 4. Volume & Order Flow (Bits 44 - 55)
        if v > vol_sma_20:       fp |= (1 << 44) # High Volume
        if v > (vol_sma_20 * 2): fp |= (1 << 45) # Climax Volume Spike
        if v < (vol_sma_20 * 0.5): fp |= (1 << 46) # Low Volume Drift
        # Approximate Volume Delta: if close > open, assume buyer dominant
        if c > o and v > vol_sma_20: fp |= (1 << 47) # Bullish Volume Delta
        if c < o and v > vol_sma_20: fp |= (1 << 48) # Bearish Volume Delta

        # 5. Candlestick Anatomy & Reversal Patterns (Bits 56 - 63)
        candle_body = abs(c - o)
        upper_wick = h - max(c, o)
        lower_wick = min(c, o) - l
        total_range = h - l if (h - l) > 0 else 0.0001

        if c > o: fp |= (1 << 56) # Bullish Green Candle
        if c < o: fp |= (1 << 57) # Bearish Red Candle
        if lower_wick > (candle_body * 2): fp |= (1 << 58) # Hammer / Bullish Rejection Pin
        if upper_wick > (candle_body * 2): fp |= (1 << 59) # Shooting Star / Bearish Rejection Pin
        if candle_body < (total_range * 0.15): fp |= (1 << 60) # Doji / Indecision
        if c > highs[-2] and c_prev < opens[-2]: fp |= (1 << 61) # Bullish Engulfing
        if c < lows[-2] and c_prev > opens[-2]: fp |= (1 << 62) # Bearish Engulfing

        return fp & 0xFFFFFFFFFFFFFFFF # Ensure 64-bit unsigned integer

    @staticmethod
    def classify_regime(ohlcv: List[List[float]]) -> str:
        """Determines macro market regime: 'BULL', 'BEAR', or 'CHOP'."""
        if len(ohlcv) < 30:
            return "UNKNOWN"
        closes = [bar[4] for bar in ohlcv]
        ema_20 = sum(closes[-20:]) / 20.0
        ema_50 = sum(closes[-50:]) / 50.0 if len(closes) >= 50 else ema_20
        c = closes[-1]

        if c > ema_20 > ema_50:
            return "BULL_TREND"
        elif c < ema_20 < ema_50:
            return "BEAR_TREND"
        else:
            return "RANGE_CHOP"
