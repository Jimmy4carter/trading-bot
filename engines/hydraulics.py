"""
Navier-Stokes Liquidity Hydraulics & Viscosity Engine.
Models market order books as fluid channels of variable resistance.
Calculates Liquidity Viscosity Index (μ), Kinetic Energy (Ek = 1/2 m v^2),
and detects Cavitation Shocks (Liquidity Vacuum Breakouts).
"""

import math
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("trading_bot.engine.hydraulics")

class LiquidityHydraulicsEngine:
    @staticmethod
    def calculate_hydraulics(ohlcv: List[List[float]], spread_pct: float = 0.05) -> Dict[str, Any]:
        """
        Analyzes the fluid dynamics of recent price flow and volume resistance.
        Returns:
            {
                'viscosity_index': float,
                'cavitation_shock': bool,
                'kinetic_energy': float,
                'fluid_pressure': float,
                'state': str ('VACUUM_EXPANSION_BULL', 'VACUUM_EXPANSION_BEAR', 'STICKY_VISCOUS_CHOP', 'LAMINAR_TREND'),
                'is_vacuum_breakout': bool
            }
        """
        if not ohlcv or len(ohlcv) < 20:
            return {
                'viscosity_index': 1.0,
                'cavitation_shock': False,
                'kinetic_energy': 0.0,
                'fluid_pressure': 0.0,
                'state': 'LAMINAR_TREND',
                'is_vacuum_breakout': False
            }

        closes = [b[4] for b in ohlcv]
        highs = [b[2] for b in ohlcv]
        lows = [b[3] for b in ohlcv]
        volumes = [b[5] for b in ohlcv]

        # 1. Price Displacement Velocity (v) over last 3 bars
        recent_delta_p = closes[-1] - closes[-4]
        price_velocity = abs(recent_delta_p) / (closes[-1] * 0.01 + 1e-6) # Normalized %/tick
        price_direction = 1 if recent_delta_p > 0 else -1

        # 2. Cumulative Mass / Volume (m)
        recent_mass = sum(volumes[-4:])
        avg_mass = sum(volumes[-20:]) / 5.0 # Baseline mass

        # 3. Kinetic Energy: Ek = 1/2 * m * v^2
        kinetic_energy = 0.5 * (recent_mass / max(1.0, avg_mass)) * (price_velocity ** 2)

        # 4. Liquidity Viscosity Index (μ)
        # μ = Volume Consumed / Price Displacement
        # High μ = Honey (Requires massive volume to budge price 1%)
        # Low μ = Air / Vacuum (Price slides effortlessly through thin books)
        displacements = [abs(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(len(closes) - 19, len(closes))]
        vols = volumes[-19:]

        historical_viscosities = []
        for i in range(len(displacements)):
            visc = vols[i] / (displacements[i] * 1000.0 + 1e-4)
            historical_viscosities.append(visc)

        current_viscosity = vols[-1] / (displacements[-1] * 1000.0 + 1e-4)
        median_viscosity = sorted(historical_viscosities)[len(historical_viscosities) // 2]
        viscosity_ratio = current_viscosity / max(1e-4, median_viscosity)

        # 5. Fluid Pressure P = Force / Area
        # Force = Mass * Acceleration (Volume * Price Change)
        # Area = Spread Width (Order Book Slippage Gap)
        effective_area = max(0.01, spread_pct)
        fluid_pressure = (recent_mass / max(1.0, avg_mass)) * price_velocity / effective_area

        # 6. Cavitation Shock Detection (Liquidity Vacuum)
        # Occurs when viscosity drops below 40% of normal, while kinetic energy surges > 2.0x
        is_cavitation = (viscosity_ratio < 0.45) and (kinetic_energy > 0.8)

        if is_cavitation:
            state = "VACUUM_EXPANSION_BULL" if price_direction > 0 else "VACUUM_EXPANSION_BEAR"
        elif viscosity_ratio > 2.5:
            state = "STICKY_VISCOUS_CHOP"  # Heavy resistance, mean-reverting
        elif kinetic_energy > 1.2:
            state = "LAMINAR_TREND"        # Healthy momentum
        else:
            state = "EQUILIBRIUM_FLOW"

        return {
            'viscosity_index': round(viscosity_ratio, 4),
            'cavitation_shock': is_cavitation,
            'kinetic_energy': round(kinetic_energy, 4),
            'fluid_pressure': round(fluid_pressure, 4),
            'state': state,
            'direction': "BUY" if price_direction > 0 else "SELL",
            'is_vacuum_breakout': is_cavitation and (kinetic_energy >= 1.0)
        }

# Singleton hydraulics instance
hydraulics_engine = LiquidityHydraulicsEngine()
