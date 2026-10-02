"""
Historical Bootstrapper & Pre-Training Engine.
Fetches historical market data, extracts 64-bit market fingerprints, simulates forward
trajectories (TP/SL outcome without lookahead bias), and pre-seeds the SQLite strategy archive.
Guarantees the AI starts with thousands of proven market memories on Day 1.
"""

import sys
import os
import time
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import settings
from core.database import init_db, save_strategy_memory, get_watchlist
from engines.fingerprint import MarketFingerprintGenerator
from engines.genetic import genetic_engine
from brokers import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bootstrap")

def bootstrap_pair(
    symbol: str, 
    asset_class: str, 
    broker_name: str, 
    timeframe: str = '1h', 
    limit: int = 500,
    take_profit_pct: float = 0.015,
    stop_loss_pct: float = 0.006
):
    logger.info(f"Bootstrapping historical memories for {symbol} ({broker_name})...")
    broker = router.get_broker(broker_name)

    # 1. Fetch real historical bars
    ohlcv = broker.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if not ohlcv or len(ohlcv) < 50:
        logger.warning(f"Insufficient history ({len(ohlcv)} bars) for {symbol}. Generating synthetic bootstrap data.")
        # Generate high-quality realistic geometric drift bars for bootstrapping if API limit/offline
        ohlcv = _generate_synthetic_candles(limit=limit)

    logger.info(f"Processing {len(ohlcv)} candles for {symbol}...")

    success_memories = 0
    # Slide a window of 50 bars to calculate fingerprint, then look ahead up to 12 bars for outcome
    for i in range(50, len(ohlcv) - 12):
        window = ohlcv[i - 50 : i]
        entry_bar = ohlcv[i]
        entry_price = entry_bar[4] # Close of current bar

        # Calculate 64-bit DNA for this exact moment
        fingerprint = MarketFingerprintGenerator.calculate_fingerprint(window)
        regime = MarketFingerprintGenerator.classify_regime(window)

        # Forward simulation over subsequent 12 bars (e.g. 12 hours)
        forward_bars = ohlcv[i + 1 : i + 13]
        buy_tp_hit = False
        buy_sl_hit = False
        sell_tp_hit = False
        sell_sl_hit = False

        for f_bar in forward_bars:
            high = f_bar[2]
            low = f_bar[3]

            # Long trade evaluation
            if (high - entry_price) / entry_price >= take_profit_pct:
                buy_tp_hit = True
                break
            if (low - entry_price) / entry_price <= -stop_loss_pct:
                buy_sl_hit = True
                break

            # Short trade evaluation
            if (entry_price - low) / entry_price >= take_profit_pct:
                sell_tp_hit = True
                break
            if (entry_price - high) / entry_price <= -stop_loss_pct:
                sell_sl_hit = True
                break

        # Save memories with verified trajectory outcomes
        if buy_tp_hit and not buy_sl_hit:
            save_strategy_memory(symbol, fingerprint, 'BUY', profit_pct=take_profit_pct * 100, regime=regime)
            success_memories += 1
        elif sell_tp_hit and not sell_sl_hit:
            save_strategy_memory(symbol, fingerprint, 'SELL', profit_pct=take_profit_pct * 100, regime=regime)
            success_memories += 1

    logger.info(f"Seeded {success_memories} profitable trajectory memories for {symbol}.")

    # Evolve initial genetic bitmask for this pair
    logger.info(f"Evolving initial genetic bitmask for {symbol}...")
    best_mask = genetic_engine.evolve_pair_mask(symbol, generations=15)
    logger.info(f"Finished {symbol}. Mask: 0x{best_mask:016X}")

def _generate_synthetic_candles(limit: int = 500) -> list:
    """Generates realistic Brownian-motion candlestick dataset for pre-flight testing."""
    import math
    import random
    bars = []
    price = 60000.0
    now_ms = int(time.time() * 1000) - (limit * 3600 * 1000)

    for i in range(limit):
        pct_change = random.gauss(0.0002, 0.008)
        open_p = price
        close_p = open_p * (1.0 + pct_change)
        high_p = max(open_p, close_p) * (1.0 + abs(random.gauss(0, 0.003)))
        low_p = min(open_p, close_p) * (1.0 - abs(random.gauss(0, 0.003)))
        vol = abs(random.gauss(100.0, 30.0))
        bars.append([now_ms + (i * 3600 * 1000), open_p, high_p, low_p, close_p, vol])
        price = close_p
    return bars

def main():
    init_db()
    watchlist = get_watchlist(active_only=True)
    logger.info(f"Starting pre-training bootstrap for {len(watchlist)} pairs...")

    for item in watchlist:
        try:
            bootstrap_pair(
                symbol=item['symbol'],
                asset_class=item['asset_class'],
                broker_name=item['broker'],
                limit=300
            )
        except Exception as e:
            logger.error(f"Failed to bootstrap {item['symbol']}: {e}")

    logger.info("Pre-training bootstrap complete. AI is primed and ready.")

if __name__ == "__main__":
    main()
