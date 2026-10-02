"""
VPS Self-Funding Treasury & Dynamic Fractional Kelly Compounding Engine.
1. Automatically sweeps 15% of realized net profits into a dedicated VPS Hosting Reserve
   until the monthly Hetzner VPS cost (~$4.50 / €3.79) is covered.
2. Implements Fractional Kelly Criterion for dynamic capital compounding on small accounts ($50+),
   ensuring position size scales safely with organic profits while capping maximum risk at 12% equity.
"""

import math
import logging
from typing import Dict, Any, Optional

from config.settings import settings
from core.database import get_system_config, set_system_config, get_performance_summary

logger = logging.getLogger("trading_bot.engine.treasury")

class VPSTreasuryAndCompounding:
    MONTHLY_VPS_TARGET_USD = 4.50  # Covers Hetzner CX22 (€3.79 + VAT)
    PROFIT_SWEEP_RATE = 0.15       # 15% of net profit swept to VPS reserve
    MIN_TRADE_NOTIONAL_USD = 5.25  # Exchange minimum ($5.00) + safety buffer
    MAX_ACCOUNT_ALLOCATION_PCT = 0.12 # Never risk more than 12% of equity per trade

    def __init__(self):
        self._init_treasury()

    def _init_treasury(self):
        reserve = get_system_config("vps_reserve_usd")
        if reserve is None:
            set_system_config("vps_reserve_usd", 0.0)

    def get_treasury_status(self) -> Dict[str, Any]:
        """Returns the current status of the VPS hosting reserve and self-funding progress."""
        reserve = float(get_system_config("vps_reserve_usd", 0.0))
        funded_pct = min(100.0, (reserve / self.MONTHLY_VPS_TARGET_USD) * 100.0)
        is_fully_funded = reserve >= self.MONTHLY_VPS_TARGET_USD

        return {
            "vps_reserve_usd": round(reserve, 2),
            "monthly_target_usd": self.MONTHLY_VPS_TARGET_USD,
            "funded_percentage": round(funded_pct, 1),
            "is_fully_funded": is_fully_funded,
            "status_text": "FULLY FUNDED" if is_fully_funded else f"${reserve:.2f} / ${self.MONTHLY_VPS_TARGET_USD:.2f}"
        }

    def sweep_profit(self, profit_usd: float) -> float:
        """
        Sweeps 15% of net trade profit into the VPS hosting reserve until the monthly target is met.
        Returns the amount swept.
        """
        if profit_usd <= 0:
            return 0.0

        current_reserve = float(get_system_config("vps_reserve_usd", 0.0))
        remaining_needed = max(0.0, self.MONTHLY_VPS_TARGET_USD - current_reserve)

        if remaining_needed <= 0:
            return 0.0  # Already fully funded for this billing cycle

        sweep_amount = min(remaining_needed, profit_usd * self.PROFIT_SWEEP_RATE)
        new_reserve = current_reserve + sweep_amount
        set_system_config("vps_reserve_usd", round(new_reserve, 4))

        logger.info(
            f"💰 [VPS TREASURY] Swept ${sweep_amount:.3f} from profit into VPS reserve. "
            f"Total reserve: ${new_reserve:.2f} / ${self.MONTHLY_VPS_TARGET_USD:.2f} ({new_reserve/self.MONTHLY_VPS_TARGET_USD*100:.1f}%)"
        )
        return sweep_amount

    def calculate_compounded_trade_size(self, current_equity_usd: float) -> Dict[str, Any]:
        """
        Calculates optimal trade size using Conservative Fractional Kelly Criterion.
        Adjusts dynamically as account equity compounds from $50 -> $75 -> $150.
        """
        is_compounding_enabled = bool(get_system_config("dynamic_compounding_enabled", True))
        base_size = float(get_system_config("trade_size_usd", settings.TRADE_SIZE_USD))

        if not is_compounding_enabled or current_equity_usd <= 0:
            return {
                "trade_size_usd": max(self.MIN_TRADE_NOTIONAL_USD, base_size),
                "kelly_fraction": 0.0,
                "allocation_pct": round((base_size / max(1.0, current_equity_usd)) * 100.0, 1),
                "mode": "FIXED_STATIC"
            }

        # Retrieve historical win rate and win/loss ratio from ledger
        perf = get_performance_summary()
        total_trades = perf.get("total_trades", 0)
        win_rate = (perf.get("win_rate_pct", 55.0)) / 100.0

        # If less than 10 trades recorded, use safe baseline (55% win rate, 1.5 win/loss ratio)
        if total_trades < 10:
            win_rate = 0.55
            win_loss_ratio = 1.5
        else:
            avg_win = float(perf.get("avg_win_usd", 0.08) or 0.08)
            avg_loss = abs(float(perf.get("avg_loss_usd", 0.04) or 0.04))
            win_loss_ratio = max(0.5, (avg_win / max(0.01, avg_loss)))

        # Full Kelly Formula: K = (W * R - (1 - W)) / R
        kelly_full = (win_rate * win_loss_ratio - (1.0 - win_rate)) / win_loss_ratio

        # Conservative Quarter-Kelly (K * 0.25) to prevent tail risk
        conservative_kelly = max(0.05, kelly_full * 0.25) if kelly_full > 0 else 0.05

        # Cap trade size at MAX_ACCOUNT_ALLOCATION_PCT (12% of total equity)
        capped_kelly = min(self.MAX_ACCOUNT_ALLOCATION_PCT, conservative_kelly)

        compounded_size = current_equity_usd * capped_kelly

        # Ensure order size always meets minimum notional ($5.25)
        final_size = max(self.MIN_TRADE_NOTIONAL_USD, compounded_size)

        return {
            "trade_size_usd": round(final_size, 2),
            "kelly_fraction": round(conservative_kelly, 4),
            "allocation_pct": round((final_size / current_equity_usd) * 100.0, 1),
            "win_rate": round(win_rate * 100.0, 1),
            "win_loss_ratio": round(win_loss_ratio, 2),
            "mode": "DYNAMIC_FRACTIONAL_KELLY"
        }

    def reset_treasury(self):
        """Resets the VPS reserve (e.g. at the start of a new billing month after paying Hetzner)."""
        set_system_config("vps_reserve_usd", 0.0)
        logger.info("💰 [VPS TREASURY] Monthly reserve reset to $0.00 for new billing cycle.")

# Singleton instance
vps_treasury = VPSTreasuryAndCompounding()
