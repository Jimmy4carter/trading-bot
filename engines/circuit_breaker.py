"""
Spread-Spike Macro News Shield & Anti-Tilt Circuit Breaker.
1. Prevents suicidal entries during macro economic news releases (CPI, FOMC, NFP)
   or illiquid weekend market rollover by detecting artificial bid-ask spread expansion.
2. Implements an institutional Anti-Tilt Circuit Breaker: halts execution after 2 consecutive
   losses, initiates a 45-minute cooling period, and triggers counterfactual post-mortems.
"""

import time
import logging
from typing import Dict, Any, List, Optional

from core.database import get_system_config, set_system_config, get_recent_trades
from engines.knowledge_vault import synaptic_vault

logger = logging.getLogger("trading_bot.engine.circuit_breaker")

class AntiTiltAndSpreadShield:
    MAX_CONSECUTIVE_LOSSES = 2
    COOLING_PERIOD_SECONDS = 45 * 60  # 45 minutes
    SPREAD_EXPANSION_THRESHOLD = 2.2   # 2.2x median spread triggers shock state

    def __init__(self):
        self.rolling_spreads: Dict[str, List[float]] = {}
        self.consecutive_losses = 0
        self.cooling_until_timestamp = 0.0
        self.circuit_state = "NORMAL"  # NORMAL, SPREAD_SHOCK, COOLING_DOWN

    def evaluate_spread_safety(self, symbol: str, current_spread_pct: float) -> Dict[str, Any]:
        """
        Monitors dynamic spread ratio relative to 20-bar baseline.
        Rejects entry if spread is expanded by market makers pulling liquidity.
        """
        if symbol not in self.rolling_spreads:
            self.rolling_spreads[symbol] = []

        history = self.rolling_spreads[symbol]
        history.append(current_spread_pct)
        if len(history) > 20:
            history.pop(0)

        if len(history) < 5:
            return {"safe": True, "spread_ratio": 1.0, "reason": "warming_up"}

        median_spread = sorted(history)[len(history) // 2]
        spread_ratio = current_spread_pct / max(1e-5, median_spread)

        is_shock = spread_ratio >= self.SPREAD_EXPANSION_THRESHOLD

        if is_shock:
            logger.warning(
                f"🛡️ [SPREAD SHIELD] {symbol} spread expanded to {current_spread_pct:.4f}% "
                f"({spread_ratio:.2f}x median). Blocking entries to avoid news/rollover trap."
            )
            return {
                "safe": False,
                "spread_ratio": round(spread_ratio, 2),
                "current_spread_pct": round(current_spread_pct, 4),
                "median_spread_pct": round(median_spread, 4),
                "reason": "spread_expansion_shock"
            }

        return {
            "safe": True,
            "spread_ratio": round(spread_ratio, 2),
            "current_spread_pct": round(current_spread_pct, 4),
            "median_spread_pct": round(median_spread, 4),
            "reason": "normal_liquidity"
        }

    def check_anti_tilt_gate(self) -> Dict[str, Any]:
        """
        Checks whether the account is currently in a protective cooling-down period.
        """
        now = time.time()
        if now < self.cooling_until_timestamp:
            remaining_minutes = max(0.1, (self.cooling_until_timestamp - now) / 60.0)
            return {
                "allowed": False,
                "circuit_state": "COOLING_DOWN",
                "consecutive_losses": self.consecutive_losses,
                "remaining_minutes": round(remaining_minutes, 1),
                "reason": f"anti_tilt_cooling_active ({remaining_minutes:.1f}m left)"
            }

        # Reset state if cooling period expired
        if self.circuit_state == "COOLING_DOWN":
            self.circuit_state = "NORMAL"
            logger.info("🛡️ [CIRCUIT BREAKER] Cooling period expired. Resuming trading under dampened sizing.")

        return {
            "allowed": True,
            "circuit_state": "NORMAL",
            "consecutive_losses": self.consecutive_losses,
            "remaining_minutes": 0.0,
            "reason": "circuit_clear"
        }

    def record_trade_outcome(self, pnl_pct: float, symbol: str):
        """
        Updates consecutive loss counters upon trade closure.
        Engages the circuit breaker if 2 consecutive stop-outs occur.
        """
        if pnl_pct < 0.0:
            self.consecutive_losses += 1
            logger.warning(f"⚠️ [CIRCUIT BREAKER] Trade loss detected on {symbol} ({pnl_pct:+.2f}%). Consecutive losses: {self.consecutive_losses}")

            if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
                self.cooling_until_timestamp = time.time() + self.COOLING_PERIOD_SECONDS
                self.circuit_state = "COOLING_DOWN"
                logger.error(
                    f"🚨 [CIRCUIT BREAKER TRIGGERED] {self.consecutive_losses} consecutive losses! "
                    f"Engaging 45-minute cooling period to prevent tilt/regime drawdown."
                )
                synaptic_vault.award_experience(10)
        else:
            # Winning trade clears the consecutive loss counter
            if self.consecutive_losses > 0:
                logger.info(f"✅ [CIRCUIT BREAKER] Profitable trade on {symbol} ({pnl_pct:+.2f}%). Consecutive losses reset to 0.")
            self.consecutive_losses = 0

    def manual_reset(self):
        """Allows operator to manually unfreeze the circuit breaker via dashboard or Telegram."""
        self.consecutive_losses = 0
        self.cooling_until_timestamp = 0.0
        self.circuit_state = "NORMAL"
        logger.info("🛡️ [CIRCUIT BREAKER] Manual reset executed by operator.")

    def get_status(self) -> Dict[str, Any]:
        gate = self.check_anti_tilt_gate()
        return {
            "circuit_state": self.circuit_state,
            "consecutive_losses": self.consecutive_losses,
            "is_cooling": not gate["allowed"],
            "remaining_cooling_minutes": gate["remaining_minutes"],
            "max_allowed_consecutive_losses": self.MAX_CONSECUTIVE_LOSSES,
            "spread_shield_active": True
        }

# Singleton instance
circuit_breaker = AntiTiltAndSpreadShield()
