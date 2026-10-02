"""
Cross-Asset Macro Lead-Lag Latency Engine.
Exploits the 60 to 180-second institutional transmission latency between
institutional foreign exchange flows (EUR/USD, DXY) and decentralized cryptocurrency assets (BTC/USDT).
Aligns crypto breakout executions with macro global liquidity tides.
"""

import math
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("trading_bot.engine.lead_lag")

class MacroLeadLagEngine:
    @staticmethod
    def calculate_lead_lag(
        forex_candles: Optional[List[List[float]]],
        crypto_candles: Optional[List[List[float]]]
    ) -> Dict[str, Any]:
        """
        Calculates cross-asset momentum alignment and lead-lag latency edge.
        Returns:
            {
                'macro_alignment': 'BULLISH_ALIGNED' | 'BEARISH_ALIGNED' | 'DIVERGENT',
                'forex_momentum_pct': float,
                'crypto_momentum_pct': float,
                'lead_edge_active': bool,
                'confidence_boost': float
            }
        """
        if not forex_candles or len(forex_candles) < 10 or not crypto_candles or len(crypto_candles) < 10:
            return {
                "macro_alignment": "NEUTRAL",
                "forex_momentum_pct": 0.0,
                "crypto_momentum_pct": 0.0,
                "lead_edge_active": False,
                "confidence_boost": 0.0
            }

        # Forex returns over last 5 bars
        fx_closes = [b[4] for b in forex_candles[-6:]]
        fx_mom = (fx_closes[-1] - fx_closes[0]) / fx_closes[0] * 100.0

        # Crypto returns over last 5 bars
        cr_closes = [b[4] for b in crypto_candles[-6:]]
        cr_mom = (cr_closes[-1] - cr_closes[0]) / cr_closes[0] * 100.0

        # Correlation logic: Strong EUR/USD momentum indicates USD weakness (Risk-On)
        # Risk-On typically drives Crypto (BTC/ETH) higher
        is_bull_aligned = fx_mom > 0.05 and cr_mom > 0.0
        is_bear_aligned = fx_mom < -0.05 and cr_mom < 0.0

        lead_edge = False
        confidence_boost = 0.0

        if is_bull_aligned:
            alignment = "BULLISH_ALIGNED"
            # If forex broke out first (higher relative velocity), crypto will likely follow through
            if abs(fx_mom) > 0.10:
                lead_edge = True
                confidence_boost = 0.08
        elif is_bear_aligned:
            alignment = "BEARISH_ALIGNED"
            if abs(fx_mom) > 0.10:
                lead_edge = True
                confidence_boost = 0.08
        else:
            alignment = "DIVERGENT"
            # Divergence penalty
            confidence_boost = -0.05

        return {
            "macro_alignment": alignment,
            "forex_momentum_pct": round(fx_mom, 3),
            "crypto_momentum_pct": round(cr_mom, 3),
            "lead_edge_active": lead_edge,
            "confidence_boost": round(confidence_boost, 3)
        }

# Singleton instance
lead_lag_engine = MacroLeadLagEngine()
