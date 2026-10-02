"""
Q-Learning Execution Filter & Risk Gatekeeper.
Uses Reinforcement Learning to decide whether to trust the BHR signal,
size down into half positions, or block the trade based on regime performance.
"""

import math
import logging
from typing import Dict, Any, Tuple

from config.settings import settings
from core.cache import cache
from core.database import get_system_config

logger = logging.getLogger("trading_bot.engine.q_filter")

class QLearningExecutionFilter:
    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.9):
        self.alpha = learning_rate
        self.gamma = discount_factor

    def _sigmoid(self, x: float) -> float:
        """Normalizes Q-values (-inf, +inf) into a 0.0 to 1.0 probability."""
        try:
            return 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, x))))
        except OverflowError:
            return 0.0 if x < 0 else 1.0

    def evaluate_entry(
        self, 
        symbol: str, 
        proposed_action: str, 
        bhr_confidence: float, 
        regime: str, 
        current_open_count: int
    ) -> Dict[str, Any]:
        """
        Evaluates whether a trade is permitted to execute, and determines position sizing.
        Returns:
            {
                'allowed': bool,
                'size_multiplier': float (0.0, 0.5, 1.0),
                'composite_score': float,
                'q_value': float,
                'reason': str
            }
        """
        # Rule 1: Max Concurrent Trades Check
        max_concurrent = int(get_system_config("max_concurrent_trades", settings.MAX_CONCURRENT_TRADES))
        if current_open_count >= max_concurrent:
            return {
                'allowed': False,
                'size_multiplier': 0.0,
                'composite_score': 0.0,
                'q_value': 0.0,
                'reason': f"max_concurrent_trades_reached ({current_open_count}/{max_concurrent})"
            }

        # Rule 2: Minimum Threshold Check
        min_threshold = float(get_system_config("min_confidence_threshold", settings.MIN_CONFIDENCE_THRESHOLD))

        state_key = f"{regime}:{proposed_action}"
        current_q = cache.get_q_value(symbol, state_key, proposed_action)
        q_confidence = self._sigmoid(current_q)

        # Composite confidence: 65% BHR resonance + 35% RL historical success
        composite_score = (bhr_confidence * 0.65) + (q_confidence * 0.35)

        if composite_score < min_threshold:
            return {
                'allowed': False,
                'size_multiplier': 0.0,
                'composite_score': round(composite_score, 4),
                'q_value': round(current_q, 4),
                'reason': f"confidence_below_threshold ({composite_score:.2f} < {min_threshold:.2f})"
            }

        # Rule 3: Dynamic Sizing based on confidence
        if composite_score >= (min_threshold + 0.15):
            size_multiplier = 1.0 # Full size
            reason = "high_confidence_full_size"
        else:
            size_multiplier = 0.5 # Half size / risk mitigation
            reason = "moderate_confidence_half_size"

        return {
            'allowed': True,
            'size_multiplier': size_multiplier,
            'composite_score': round(composite_score, 4),
            'q_value': round(current_q, 4),
            'reason': reason
        }

    def update_reinforcement(
        self, 
        symbol: str, 
        regime: str, 
        action: str, 
        realized_profit_pct: float
    ) -> float:
        """
        Applies Q-learning Bellman update when a trade closes.
        Reward is positive for net profit, negative for losses.
        """
        state_key = f"{regime}:{action}"
        current_q = cache.get_q_value(symbol, state_key, action)

        # Reward formulation: profit % minus baseline friction penalty
        reward = realized_profit_pct

        # Q-learning formula: Q = Q + alpha * (Reward - Q)
        new_q = current_q + (self.alpha * (reward - current_q))
        cache.set_q_value(symbol, state_key, action, round(new_q, 4))

        logger.info(
            f"[Q-LEARN] Updated {symbol} ({state_key}): "
            f"Reward={reward:+.2f}%, Q_old={current_q:.4f} -> Q_new={new_q:.4f}"
        )
        return new_q

# Singleton Q-filter instance
q_filter = QLearningExecutionFilter()
