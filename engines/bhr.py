"""
Bitwise Holographic Router (BHR) Engine.
Executes hardware-level XOR Hamming distance matching across historical market states,
applying Pair-Specific Genetic Bitmasks to filter out feature noise in sub-milliseconds.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from core.database import get_strategy_memories
from core.cache import cache

logger = logging.getLogger("trading_bot.engine.bhr")

class BitwiseHolographicRouter:
    def __init__(self, max_hamming_distance: int = 5):
        self.max_hamming_distance = max_hamming_distance

    def find_resonance(
        self, 
        symbol: str, 
        current_fingerprint: int, 
        regime: str = "UNKNOWN"
    ) -> Dict[str, Any]:
        """
        Scans historical memory for the closest resonant market fingerprint.
        Returns:
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'confidence': float (0.0 to 1.0),
                'distance': int (0 to 64),
                'sample_size': int,
                'win_rate': float
            }
        """
        # 1. Fetch Pair-Specific Genetic Bitmask from hot cache
        mask = cache.get_genetic_mask(symbol)
        masked_current = current_fingerprint & mask

        # 2. Fetch historical memories for this symbol
        memories = get_strategy_memories(symbol)
        if not memories:
            return {
                'action': 'HOLD',
                'confidence': 0.0,
                'distance': 64,
                'sample_size': 0,
                'win_rate': 0.0,
                'reason': 'no_historical_memory'
            }

        # 3. Vectorized / High-Speed Hamming Distance Calculation
        best_action = 'HOLD'
        lowest_distance = 64
        best_win_rate = 0.0
        best_sample_size = 0
        best_profit = 0.0

        for mem in memories:
            hist_fp = int(mem['fingerprint'])
            masked_hist = hist_fp & mask

            # Hardware-level XOR: 1s indicate differing feature bits
            xor_result = masked_current ^ masked_hist
            distance = bin(xor_result).count('1')

            # Look for closest resonance
            if distance < lowest_distance:
                lowest_distance = distance
                best_action = mem['action']
                best_win_rate = float(mem.get('win_rate', 0.0))
                best_sample_size = int(mem.get('sample_size', 1))
                best_profit = float(mem.get('total_profit', 0.0))
            elif distance == lowest_distance:
                # Tie-breaker: choose memory with higher win rate and sample size
                if float(mem.get('win_rate', 0.0)) > best_win_rate:
                    best_action = mem['action']
                    best_win_rate = float(mem.get('win_rate', 0.0))
                    best_sample_size = int(mem.get('sample_size', 1))
                    best_profit = float(mem.get('total_profit', 0.0))

        # Check resonance criteria
        if lowest_distance <= self.max_hamming_distance and best_win_rate >= 0.55:
            # Active resonance achieved
            confidence = (1.0 - (lowest_distance / 64.0)) * best_win_rate
            return {
                'action': best_action,
                'confidence': round(confidence, 4),
                'distance': lowest_distance,
                'sample_size': best_sample_size,
                'win_rate': round(best_win_rate, 4),
                'expected_profit': round(best_profit / max(1, best_sample_size), 4),
                'reason': 'resonance_matched'
            }

        return {
            'action': 'HOLD',
            'confidence': 0.0,
            'distance': lowest_distance,
            'sample_size': best_sample_size,
            'win_rate': round(best_win_rate, 4),
            'reason': f'insufficient_resonance (dist={lowest_distance}, win_rate={best_win_rate:.2f})'
        }

# Singleton BHR engine
bhr_engine = BitwiseHolographicRouter()
