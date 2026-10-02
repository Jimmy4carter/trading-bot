"""
Unit tests for Owner Safeguards & Production Engines:
- VPS Self-Funding Treasury & Fractional Kelly Compounding
- Spread-Spike News Shield & Anti-Tilt Circuit Breaker
- Maker-First Smart Order Router
- Cross-Asset Macro Lead-Lag Latency Engine
"""

import unittest
from engines.treasury import VPSTreasuryAndCompounding, vps_treasury
from engines.circuit_breaker import AntiTiltAndSpreadShield, circuit_breaker
from engines.smart_router import SmartOrderRouter, smart_router
from engines.lead_lag import MacroLeadLagEngine, lead_lag_engine

class MockBroker:
    def __init__(self):
        self.name = "mock_broker"

    def normalize_price(self, price: float, tick_size: float = 0.01) -> float:
        return round(price, 4)

    def create_order(self, symbol: str, side: str, amount: float, order_type: str = "MARKET", price: float = None):
        return {
            "id": "mock_order_123",
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "type": order_type,
            "price": price or 100.0,
            "status": "closed"
        }

class TestOwnerProductionEngines(unittest.TestCase):
    def setUp(self):
        self.treasury = VPSTreasuryAndCompounding()
        self.treasury.reset_treasury()
        self.circuit = AntiTiltAndSpreadShield()
        self.circuit.manual_reset()
        self.broker = MockBroker()

    def test_vps_treasury_sweep_and_status(self):
        status = self.treasury.get_treasury_status()
        self.assertEqual(status["vps_reserve_usd"], 0.0)
        self.assertFalse(status["is_fully_funded"])

        # Sweep from $10.00 profit (15% = $1.50)
        swept = self.treasury.sweep_profit(10.0)
        self.assertAlmostEqual(swept, 1.50, places=2)

        status_after = self.treasury.get_treasury_status()
        self.assertAlmostEqual(status_after["vps_reserve_usd"], 1.50, places=2)

        # Sweep remaining to hit $4.50 cap
        self.treasury.sweep_profit(30.0)
        status_capped = self.treasury.get_treasury_status()
        self.assertEqual(status_capped["vps_reserve_usd"], 4.50)
        self.assertTrue(status_capped["is_fully_funded"])

    def test_fractional_kelly_compounding_sizing(self):
        # Test on $50 starting account
        sizing_50 = self.treasury.calculate_compounded_trade_size(50.0)
        self.assertGreaterEqual(sizing_50["trade_size_usd"], 5.25)
        self.assertLessEqual(sizing_50["trade_size_usd"], 50.0 * 0.12 + 0.5)

        # Test on $200 compounded account
        sizing_200 = self.treasury.calculate_compounded_trade_size(200.0)
        self.assertGreater(sizing_200["trade_size_usd"], 5.25)
        self.assertLessEqual(sizing_200["trade_size_usd"], 200.0 * 0.12 + 0.5)

    def test_spread_shield_expansion_detection(self):
        symbol = "BTC/USDT"
        # Seed 10 normal spreads of 0.02%
        for _ in range(10):
            res_normal = self.circuit.evaluate_spread_safety(symbol, 0.02)
            self.assertTrue(res_normal["safe"])

        # Simulate spread shock (0.08% spread = 4x median)
        res_shock = self.circuit.evaluate_spread_safety(symbol, 0.08)
        self.assertFalse(res_shock["safe"])
        self.assertEqual(res_shock["reason"], "spread_expansion_shock")

    def test_anti_tilt_circuit_breaker(self):
        # 1. Normal state
        gate1 = self.circuit.check_anti_tilt_gate()
        self.assertTrue(gate1["allowed"])

        # 2. Record 1 loss
        self.circuit.record_trade_outcome(-0.6, "SOL/USDT")
        gate2 = self.circuit.check_anti_tilt_gate()
        self.assertTrue(gate2["allowed"])

        # 3. Record 2nd consecutive loss -> triggers cooling period
        self.circuit.record_trade_outcome(-0.5, "ETH/USDT")
        gate3 = self.circuit.check_anti_tilt_gate()
        self.assertFalse(gate3["allowed"])
        self.assertEqual(gate3["circuit_state"], "COOLING_DOWN")

        # 4. Manual reset unfreezes gate
        self.circuit.manual_reset()
        gate4 = self.circuit.check_anti_tilt_gate()
        self.assertTrue(gate4["allowed"])

    def test_smart_order_router(self):
        ticker = {"last": 60000.0, "bid": 59995.0, "ask": 60005.0}

        # Normal condition -> Maker Limit order inside spread
        order_maker = smart_router.execute_optimal_order(
            broker=self.broker,
            symbol="BTC/USDT",
            side="BUY",
            amount=0.001,
            current_ticker=ticker,
            is_cavitation_breakout=False
        )
        self.assertTrue(order_maker.get("is_maker", False))

        # Cavitation breakout condition -> Immediate Market order
        order_market = smart_router.execute_optimal_order(
            broker=self.broker,
            symbol="BTC/USDT",
            side="BUY",
            amount=0.001,
            current_ticker=ticker,
            is_cavitation_breakout=True
        )
        self.assertEqual(order_market.get("type"), "MARKET")

    def test_macro_lead_lag_alignment(self):
        forex_candles = [[0, 1.080, 1.085, 1.079, 1.084, 1000] for _ in range(12)]
        forex_candles[-1][4] = 1.088  # Strong EUR/USD breakout up

        crypto_candles = [[0, 60000, 60200, 59900, 60100, 500] for _ in range(12)]
        crypto_candles[-1][4] = 60300 # BTC/USDT breaking out up

        result = lead_lag_engine.calculate_lead_lag(forex_candles, crypto_candles)
        self.assertEqual(result["macro_alignment"], "BULLISH_ALIGNED")
        self.assertTrue(result["lead_edge_active"])
        self.assertGreater(result["confidence_boost"], 0.0)

if __name__ == '__main__':
    unittest.main()
