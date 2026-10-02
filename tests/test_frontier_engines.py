"""
Unit Test Suite for Frontier Trading Paradigms:
1. Hyperdimensional Computing (HDC) VSA operations & One-Shot memory
2. Cellular Automaton Lattice (Rule 110 Glider coherence & Turing-complete transition)
3. Navier-Stokes Liquidity Hydraulics & Viscosity Index (μ)
4. Adversarial Shadow Self-Play stop hardening
5. Cross-Asset Entropy Wave Collapse
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engines.hdc import hdc_brain
from engines.automaton import automaton_engine
from engines.hydraulics import hydraulics_engine
from engines.shadow_adversary import adversary_sandbox
from engines.entropy import entropy_engine

class TestFrontierEngines(unittest.TestCase):
    def test_01_hdc_vsa_operations(self):
        # 1. Test binding (XOR)
        v1 = hdc_brain._random_hypervector()
        v2 = hdc_brain._random_hypervector()
        bound = hdc_brain.bind(v1, v2)
        self.assertEqual(len(bound), 16)
        # Self-inverse property: A ^ B ^ B = A
        recovered = hdc_brain.bind(bound, v2)
        np.testing.assert_array_equal(v1, recovered)

        # 2. Test permutation
        permuted = hdc_brain.permute(v1, 1)
        self.assertEqual(len(permuted), 16)

        # 3. Test orthogonal distance
        dist = hdc_brain.hamming_distance(v1, v2)
        # Random 1024-bit vectors should have ~512 bits distance (+- 80)
        self.assertTrue(420 <= dist <= 600, f"Distance {dist} outside expected orthogonal distribution")

        # 4. Test One-Shot memory
        state_v = hdc_brain.encode_state({"regime": "BULL", "rsi": 25.0, "atr_ratio": 1.5, "volume_delta": 500})
        hdc_brain.store_one_shot_memory("BTC/USDT", state_v, "BUY", profit_pct=3.2)
        recall = hdc_brain.query_associative_recall("BTC/USDT", state_v)
        self.assertEqual(recall["action"], "BUY")
        self.assertGreaterEqual(recall["similarity"], 0.95)

    def test_02_automaton_rule_110(self):
        # Test Turing-complete bitwise Rule 110 transition
        # 0001000 single seed test
        seed = np.zeros(128, dtype=np.uint8)
        seed[64] = 1
        history = automaton_engine.evolve_rule_110(seed, steps=10)
        self.assertEqual(history.shape, (10, 128))
        # Verify gliders expand
        self.assertGreater(np.sum(history[-1]), 1)

        # Test market glider coherence analysis
        synthetic_ohlcv = [[i * 1000, 100 + i, 102 + i, 99 + i, 101 + i, 500] for i in range(30)]
        analysis = automaton_engine.analyze_glider_coherence(synthetic_ohlcv)
        self.assertIn("regime", analysis)
        self.assertIn("coherence_score", analysis)
        self.assertIsInstance(analysis["is_tradable"], bool)

    def test_03_liquidity_hydraulics(self):
        # Generate synthetic candles with high velocity and low volume (vacuum expansion)
        synthetic_ohlcv = []
        p = 1000.0
        for i in range(25):
            # Sudden explosive jump with low volume
            p += (50.0 if i > 20 else 1.0)
            vol = 50.0 if i > 20 else 500.0
            synthetic_ohlcv.append([i * 1000, p, p + 2, p - 2, p, vol])

        hydraulics = hydraulics_engine.calculate_hydraulics(synthetic_ohlcv, spread_pct=0.02)
        self.assertIn("viscosity_index", hydraulics)
        self.assertIn("kinetic_energy", hydraulics)
        self.assertIn("state", hydraulics)
        self.assertGreater(hydraulics["kinetic_energy"], 0)

    def test_04_shadow_adversary_stress_test(self):
        # Stress test trailing stop against predatory sweeps
        result = adversary_sandbox.stress_test_exit_geometry(
            symbol="ETH/USDT",
            side="BUY",
            entry_price=3000.0,
            base_sl_pct=0.006,
            base_trailing_activation=0.008,
            recent_volatility_pct=0.005
        )
        self.assertIn("hardened_sl_pct", result)
        self.assertIn("hardened_trailing_activation", result)
        self.assertIn("survival_rate", result)
        self.assertGreaterEqual(result["hardened_sl_pct"], 0.006)

    def test_05_entropy_wave_collapse(self):
        # Multi-pair synchronized trend test
        multi_candles = {
            "BTC/USDT": [[i, 100 + i*2, 101 + i*2, 99 + i*2, 100 + i*2, 100] for i in range(20)],
            "ETH/USDT": [[i, 50 + i*1, 51 + i*1, 49 + i*1, 50 + i*1, 80] for i in range(20)],
            "SOL/USDT": [[i, 20 + i*0.5, 21 + i*0.5, 19 + i*0.5, 20 + i*0.5, 60] for i in range(20)]
        }
        ewc = entropy_engine.analyze_cross_asset_entanglement(multi_candles)
        self.assertIn("joint_entropy", ewc)
        self.assertIn("wave_collapse_detected", ewc)
        self.assertIn("dominant_direction", ewc)
        self.assertLessEqual(ewc["joint_entropy"], 1.0)

if __name__ == "__main__":
    unittest.main()
