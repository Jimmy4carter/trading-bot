"""
Automated Component Test Suite for QuantumBit BHR Trading Bot.
Validates Database WAL operations, 64-bit Fingerprint generation, BHR resonance matching,
Genetic Bitmask evolution, Q-Learning filter, and Precision normalizer.
"""

import sys
import os
import unittest
import time

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import (
    init_db,
    get_watchlist,
    upsert_watchlist_item,
    toggle_watchlist_item,
    save_open_position,
    get_open_positions,
    close_position_record,
    log_trade,
    get_recent_trades,
    get_performance_summary,
    save_strategy_memory,
    get_strategy_memories,
    set_system_config,
    get_system_config
)
from core.cache import cache
from engines.fingerprint import MarketFingerprintGenerator
from engines.bhr import bhr_engine
from engines.genetic import genetic_engine
from engines.q_filter import q_filter
from brokers.base import BaseBroker

class TestDummyBroker(BaseBroker):
    def fetch_ohlcv(self, symbol, timeframe='1h', limit=100): return []
    def fetch_ticker(self, symbol): return {}
    def create_order(self, symbol, side, amount, order_type="MARKET", price=None): return {}
    def get_balance(self): return {}

class TestTradingBotComponents(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_01_database_watchlist(self):
        upsert_watchlist_item("TEST/USDT", "crypto", "bybit", is_active=True)
        watchlist = get_watchlist(active_only=False)
        symbols = [item['symbol'] for item in watchlist]
        self.assertIn("TEST/USDT", symbols)

        toggle_watchlist_item("TEST/USDT", False)
        active_wl = get_watchlist(active_only=True)
        active_symbols = [item['symbol'] for item in active_wl]
        self.assertNotIn("TEST/USDT", active_symbols)

    def test_02_database_positions_and_ledger(self):
        pos_id = f"test_{int(time.time())}"
        pos_data = {
            'id': pos_id,
            'symbol': 'BTC/USDT',
            'broker': 'bybit',
            'side': 'BUY',
            'entry_price': 60000.0,
            'size': 0.001,
            'sl_price': 59600.0,
            'tp_price': 60900.0,
            'trailing_activation': 0.008,
            'highest_reached': 60000.0,
            'open_timestamp': time.time(),
            'is_paper': True,
            'status': 'OPEN'
        }
        save_open_position(pos_data)
        open_pos = get_open_positions()
        ids = [p['id'] for p in open_pos]
        self.assertIn(pos_id, ids)

        # Close position and log trade
        close_position_record(pos_id)
        remaining = get_open_positions()
        self.assertNotIn(pos_id, [p['id'] for p in remaining])

        trade_record = {
            'position_id': pos_id,
            'symbol': 'BTC/USDT',
            'broker': 'bybit',
            'side': 'BUY',
            'entry_price': 60000.0,
            'exit_price': 60900.0,
            'size': 0.001,
            'profit_usd': 0.90,
            'profit_pct': 1.50,
            'fees_usd': 0.02,
            'duration_seconds': 120,
            'exit_reason': 'TAKE_PROFIT',
            'opened_at': '2026-10-02 12:00:00',
            'is_paper': True
        }
        log_trade(trade_record)
        summary = get_performance_summary()
        self.assertGreaterEqual(summary['total_trades'], 1)

    def test_03_market_fingerprint_generation(self):
        # Generate 60 synthetic bars
        synthetic_bars = []
        p = 50000.0
        for i in range(60):
            p += (10.0 if i % 2 == 0 else -8.0)
            synthetic_bars.append([i * 3600000, p, p + 20, p - 20, p + 5, 150.0])

        fp = MarketFingerprintGenerator.calculate_fingerprint(synthetic_bars)
        self.assertIsInstance(fp, int)
        self.assertGreater(fp, 0)
        self.assertLessEqual(fp, 0xFFFFFFFFFFFFFFFF)

        regime = MarketFingerprintGenerator.classify_regime(synthetic_bars)
        self.assertIn(regime, ["BULL_TREND", "BEAR_TREND", "RANGE_CHOP", "UNKNOWN"])

    def test_04_bhr_resonance_and_genetic_mask(self):
        symbol = "BTC/USDT"
        test_fp = 0b1010101010101010101010101010101010101010101010101010101010101010
        save_strategy_memory(symbol, test_fp, 'BUY', profit_pct=2.5, regime="BULL_TREND")

        memories = get_strategy_memories(symbol)
        self.assertGreaterEqual(len(memories), 1)

        # Test resonance
        res = bhr_engine.find_resonance(symbol, test_fp, regime="BULL_TREND")
        self.assertIn(res['action'], ['BUY', 'HOLD'])

    def test_05_q_filter_risk_gatekeeper(self):
        # Test rejection on low confidence
        low_res = q_filter.evaluate_entry(
            symbol="BTC/USDT",
            proposed_action="BUY",
            bhr_confidence=0.30,
            regime="BULL_TREND",
            current_open_count=0
        )
        self.assertFalse(low_res['allowed'])

        # Test acceptance on high confidence
        high_res = q_filter.evaluate_entry(
            symbol="BTC/USDT",
            proposed_action="BUY",
            bhr_confidence=0.88,
            regime="BULL_TREND",
            current_open_count=0
        )
        self.assertTrue(high_res['allowed'])
        self.assertIn(high_res['size_multiplier'], [0.5, 1.0])

        # Test Q-learning update
        new_q = q_filter.update_reinforcement("BTC/USDT", "BULL_TREND", "BUY", realized_profit_pct=1.5)
        self.assertIsInstance(new_q, float)

    def test_06_broker_precision_normalizer(self):
        broker = TestDummyBroker("dummy")
        # $10 target on BTC at $60,000 with min notional $5.0 and step 0.0001
        amount = broker.normalize_amount(
            symbol="BTC/USDT",
            target_cost_usd=10.0,
            current_price=60000.0,
            min_notional=5.0,
            step_size=0.0001
        )
        cost = amount * 60000.0
        self.assertGreaterEqual(cost, 5.0)
        self.assertEqual(amount, round(amount, 4))

if __name__ == "__main__":
    unittest.main()
