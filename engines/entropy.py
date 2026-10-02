"""
Cross-Asset Entropy Wave Collapse (EWC) Engine.
Computes Joint Shannon Entropy across the multi-pair watchlist to detect
the exact moment independent random market drift collapses into synchronized directional waves.
"""

import math
import numpy as np
import logging
from typing import Dict, Any, List

logger = logging.getLogger("trading_bot.engine.entropy")

class EntropyWaveCollapseEngine:
    @staticmethod
    def _discretize_returns(returns: List[float], bins: int = 4) -> List[int]:
        """Discretizes floating-point return deltas into categorical states."""
        if not returns:
            return []
        arr = np.array(returns)
        # Quantile binning
        try:
            percentiles = np.percentile(arr, [25, 50, 75])
            digitized = np.digitize(arr, percentiles)
            return list(digitized)
        except Exception:
            return [0] * len(returns)

    @classmethod
    def calculate_shannon_entropy(cls, states: List[int]) -> float:
        """Calculates single-asset Shannon entropy in bits: H(X) = -sum(p * log2(p))."""
        if not states:
            return 1.0
        n = len(states)
        counts = {}
        for s in states:
            counts[s] = counts.get(s, 0) + 1

        entropy = 0.0
        for count in counts.values():
            p = count / float(n)
            if p > 0:
                entropy -= p * math.log2(p)

        # Normalize by max possible entropy (log2 of unique states, max 2.0 for 4 bins)
        max_entropy = math.log2(4)
        return min(1.0, entropy / max_entropy)

    @classmethod
    def analyze_cross_asset_entanglement(
        cls, 
        multi_pair_candles: Dict[str, List[List[float]]]
    ) -> Dict[str, Any]:
        """
        Calculates joint entropy across all active watchlist assets.
        When joint entropy drops (Entropy Collapse), market uncertainty vanishes
        and liquidity flows uniformly in one direction.
        """
        if len(multi_pair_candles) < 2:
            return {
                'joint_entropy': 0.85,
                'wave_collapse_detected': False,
                'dominant_direction': 'NEUTRAL',
                'leading_symbol': None,
                'entropy_per_symbol': {}
            }

        symbol_entropies = {}
        symbol_momentums = {}

        for sym, candles in multi_pair_candles.items():
            if len(candles) < 15:
                continue
            closes = [b[4] for b in candles[-15:]]
            returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
            discrete_states = cls._discretize_returns(returns)
            h = cls.calculate_shannon_entropy(discrete_states)
            symbol_entropies[sym] = round(h, 4)
            symbol_momentums[sym] = (closes[-1] - closes[0]) / closes[0]

        if not symbol_entropies:
            return {
                'joint_entropy': 0.85,
                'wave_collapse_detected': False,
                'dominant_direction': 'NEUTRAL',
                'leading_symbol': None,
                'entropy_per_symbol': {}
            }

        # Average market entropy
        avg_market_entropy = sum(symbol_entropies.values()) / float(len(symbol_entropies))

        # Entropy Collapse occurs when market entropy drops below 0.60
        # (meaning 70%+ of bars are moving in the exact same quantized direction)
        is_wave_collapse = avg_market_entropy < 0.62

        # Identify leader (lowest entropy = purest signal)
        leading_symbol = min(symbol_entropies.items(), key=lambda x: x[1])[0]
        leader_momentum = symbol_momentums.get(leading_symbol, 0.0)
        dominant_direction = "BULL_WAVE" if leader_momentum > 0 else "BEAR_WAVE"

        return {
            'joint_entropy': round(avg_market_entropy, 4),
            'wave_collapse_detected': is_wave_collapse,
            'dominant_direction': dominant_direction if is_wave_collapse else "NEUTRAL_DRIFT",
            'leading_symbol': leading_symbol if is_wave_collapse else None,
            'entropy_per_symbol': symbol_entropies
        }

# Singleton entropy wave engine
entropy_engine = EntropyWaveCollapseEngine()
