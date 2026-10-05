"""
Unit Test Suite for Deriv API, Interactive Brokers (IBKR), Multi-Broker Fleet, and Admin Controls.
"""

import unittest
from brokers.forex_deriv import DerivForexBroker
from brokers.forex_ibkr import InteractiveBrokersAdapter
from brokers import OmniBrokerRouter, PaperTradingSimulator

class TestDerivBroker(unittest.TestCase):
    def setUp(self):
        self.broker = DerivForexBroker()

    def test_symbol_normalization(self):
        self.assertEqual(self.broker._normalize_instrument("EUR_USD"), "frxEURUSD")
        self.assertEqual(self.broker._normalize_instrument("EUR/USD"), "frxEURUSD")
        self.assertEqual(self.broker._normalize_instrument("GBP_USD"), "frxGBPUSD")
        self.assertEqual(self.broker._normalize_instrument("XAU_USD"), "frxXAUUSD")
        self.assertEqual(self.broker._normalize_instrument("R_50"), "R_50")
        self.assertEqual(self.broker._normalize_instrument("1HZ100V"), "1HZ100V")

    def test_fetch_ticker(self):
        ticker = self.broker.fetch_ticker("EUR_USD")
        self.assertIn("last", ticker)
        self.assertIn("bid", ticker)
        self.assertIn("ask", ticker)
        self.assertGreater(ticker["ask"], ticker["bid"])
        self.assertGreater(ticker["spread"], 0)
        self.assertAlmostEqual(ticker["last"], 1.085, delta=0.05)

    def test_fetch_synthetic_ticker(self):
        ticker = self.broker.fetch_ticker("R_50")
        self.assertIn("last", ticker)
        self.assertGreater(ticker["last"], 100.0)
        self.assertGreater(ticker["ask"], ticker["bid"])

    def test_fetch_ohlcv(self):
        candles = self.broker.fetch_ohlcv("EUR_USD", timeframe="1h", limit=50)
        self.assertEqual(len(candles), 50)
        # Check candle structure: [timestamp, open, high, low, close, volume]
        c0 = candles[0]
        self.assertEqual(len(c0), 6)
        self.assertGreater(c0[2], 0) # High > 0
        self.assertGreaterEqual(c0[2], c0[3]) # High >= Low

    def test_create_order_and_balance(self):
        init_bal = self.broker.get_balance()
        self.assertIn("total_usd", init_bal)
        self.assertGreater(init_bal["total_usd"], 0)

        order = self.broker.create_order("EUR_USD", "BUY", amount=5.0, order_type="MARKET")
        self.assertEqual(order["status"], "closed")
        self.assertEqual(order["side"], "BUY")
        self.assertGreater(order["cost"], 0)

        new_bal = self.broker.get_balance()
        self.assertLessEqual(new_bal["total_usd"], init_bal["total_usd"])


class TestIBKRBroker(unittest.TestCase):
    def setUp(self):
        self.broker = InteractiveBrokersAdapter()

    def test_symbol_normalization(self):
        self.assertEqual(self.broker._normalize_symbol("EUR_USD"), "EUR.USD")
        self.assertEqual(self.broker._normalize_symbol("GBP/USD"), "GBP.USD")

    def test_fetch_ticker_ecn_spread(self):
        ticker = self.broker.fetch_ticker("EUR_USD")
        self.assertIn("last", ticker)
        self.assertGreater(ticker["ask"], ticker["bid"])
        # ECN raw spread is ultra-tight (~0.15 pips = ~0.000015)
        self.assertLess(ticker["spread"], 0.0001)

    def test_fetch_ohlcv(self):
        candles = self.broker.fetch_ohlcv("EUR_USD", timeframe="1h", limit=30)
        self.assertEqual(len(candles), 30)
        self.assertGreaterEqual(candles[0][2], candles[0][3])

    def test_create_order(self):
        order = self.broker.create_order("EUR_USD", "BUY", amount=10.0)
        self.assertEqual(order["status"], "closed")
        self.assertIn("ibkr_", order["id"])


class TestOmniRouterFleet(unittest.TestCase):
    def setUp(self):
        self.router = OmniBrokerRouter()

    def test_fleet_membership(self):
        self.assertIn("bybit", self.router.live_brokers)
        self.assertIn("binance", self.router.live_brokers)
        self.assertIn("deriv", self.router.live_brokers)
        self.assertIn("ibkr", self.router.live_brokers)

    def test_route_symbols(self):
        deriv_b = self.router.get_broker_for_symbol("EUR_USD")
        self.assertIn("deriv", deriv_b.name)

        synthetic_b = self.router.get_broker_for_symbol("R_50")
        self.assertIn("deriv", synthetic_b.name)

        gold_b = self.router.get_broker_for_symbol("XAU_USD")
        self.assertIn("deriv", gold_b.name)

        crypto_b = self.router.get_broker_for_symbol("BTC/USDT")
        self.assertIn("bybit", crypto_b.name)

    def test_paper_trading_wrapper(self):
        deriv_paper = self.router.paper_brokers["deriv"]
        self.assertIsInstance(deriv_paper, PaperTradingSimulator)
        ticker = deriv_paper.fetch_ticker("EUR_USD")
        self.assertGreater(ticker["last"], 0)

if __name__ == "__main__":
    unittest.main()
