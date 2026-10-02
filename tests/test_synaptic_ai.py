"""
Unit tests for the Synaptic Mini-AI Learning Core:
- Neuro-Symbolic Formula Synthesizer
- Synaptic Knowledge Vault & Markov Regime Transitions
- Self-Distillation & Counterfactual Replay
"""

import unittest
import math
import os
from engines.symbolic_formula import NeuroSymbolicFormulaSynthesizer, FormulaGene
from engines.knowledge_vault import SynapticKnowledgeVault
from engines.self_distillation import SelfDistillationEngine

class TestSynapticMiniAI(unittest.TestCase):
    def setUp(self):
        self.synthesizer = NeuroSymbolicFormulaSynthesizer(population_size=6)
        test_vault_path = "tests/test_brain.json"
        if os.path.exists(test_vault_path):
            os.remove(test_vault_path)
        self.vault = SynapticKnowledgeVault(storage_path=test_vault_path)
        self.distiller = SelfDistillationEngine()

    def tearDown(self):
        test_vault_path = "tests/test_brain.json"
        if os.path.exists(test_vault_path):
            os.remove(test_vault_path)

    def test_formula_synthesizer_evaluation(self):
        variables = {
            "v_price": 0.5,
            "viscosity": 1.0,
            "entropy": 0.5,
            "rsi_norm": 0.6,
            "kinetic_energy": 0.8,
            "vol_ratio": 1.2
        }
        res = self.synthesizer.calculate_ensemble_signal(variables)
        self.assertIn("symbolic_action", res)
        self.assertIn(res["symbolic_action"], ["BUY", "SELL", "HOLD"])
        self.assertTrue(-1.0 <= res["alpha_score"] <= 1.0)
        self.assertTrue(len(res["top_formulas"]) > 0)

    def test_formula_evolution(self):
        initial_top = self.synthesizer.gene_pool[0].expression
        variables = {
            "v_price": 1.0,
            "viscosity": 0.8,
            "entropy": 0.4,
            "rsi_norm": 0.7,
            "kinetic_energy": 1.5,
            "vol_ratio": 1.4
        }
        # Simulate profitable feedback
        self.synthesizer.evolve_formulas(outcome_pnl_pct=1.5, variables=variables)
        self.assertEqual(len(self.synthesizer.gene_pool), self.synthesizer.population_size)
        self.assertTrue(self.synthesizer.gene_pool[0].total_evaluations > 0)

    def test_knowledge_vault_experience_and_iq(self):
        initial_iq = self.vault.ai_iq
        initial_level = self.vault.ai_level

        # Award 500 XP
        self.vault.award_experience(500)
        self.assertGreater(self.vault.ai_level, initial_level)
        self.assertGreater(self.vault.ai_iq, initial_iq)

    def test_regime_markov_transitions(self):
        self.vault.record_regime_transition("BULL_TREND")
        self.vault.record_regime_transition("LIQUIDITY_CAVITATION")
        probs = self.vault.get_regime_probabilities("BULL_TREND")
        self.assertIn("LIQUIDITY_CAVITATION", probs)
        self.assertGreater(probs["LIQUIDITY_CAVITATION"], 0.0)

    def test_post_mortem_and_checkpoint(self):
        self.vault.record_post_mortem(
            position_id="test_pos_1",
            symbol="BTC/USDT",
            realized_pnl=-0.6,
            regime="BULL_TREND",
            mistake_cause="High volatility stop sweep",
            lesson="Widen stop-loss buffer during liquidity sweeps"
        )
        self.assertGreater(len(self.vault.distilled_insights), 0)
        snapshot = self.vault.checkpoint_brain(top_formula="math.tanh(v_price)")
        self.assertIn("ai_iq", snapshot)
        self.assertIn("ai_level", snapshot)
        self.assertEqual(snapshot["top_formula"], "math.tanh(v_price)")

if __name__ == '__main__':
    unittest.main()
