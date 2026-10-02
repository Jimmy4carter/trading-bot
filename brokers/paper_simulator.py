"""
True Paper Trading Simulator.
Uses 100% real live market order books & pricing feeds from Bybit/Binance/OANDA,
but simulates order execution locally with realistic slippage and exchange fees.
Guarantees AI trains on real market dynamics without risking initial capital.
"""

import time
import uuid
import logging
from typing import Dict, Any, List, Optional

from .base import BaseBroker
from config.settings import settings
from core.database import get_system_config, set_system_config

logger = logging.getLogger("trading_bot.broker.paper")

class PaperTradingSimulator(BaseBroker):
    def __init__(self, live_broker: BaseBroker):
        super().__init__(name=f"paper_{live_broker.name}")
        self.live_broker = live_broker
        self._init_balance()

    def _init_balance(self):
        saved_balance = get_system_config("paper_balance_usd")
        if saved_balance is None:
            set_system_config("paper_balance_usd", settings.STARTING_BALANCE_USD)
            self.balance = settings.STARTING_BALANCE_USD
        else:
            self.balance = float(saved_balance)

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List[float]]:
        # Forward to live broker to get 100% real candlestick history
        return self.live_broker.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        # Forward to live broker to get 100% real bid/ask/spread
        return self.live_broker.fetch_ticker(symbol)

    def create_order(
        self, 
        symbol: str, 
        side: str, 
        amount: float, 
        order_type: str = "MARKET", 
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        ticker = self.fetch_ticker(symbol)
        last_price = ticker.get('last', 0.0)
        bid = ticker.get('bid', last_price)
        ask = ticker.get('ask', last_price)

        if last_price <= 0:
            raise ValueError(f"Cannot simulate trade for {symbol}: invalid price 0")

        # Simulate execution price with realistic spread slippage
        side_upper = side.upper()
        if side_upper == "BUY":
            # Buy orders hit the Ask, with an extra 0.03% market impact slippage
            fill_price = ask * 1.0003 if order_type.upper() == "MARKET" else (price or ask)
        else:
            # Sell orders hit the Bid, with 0.03% slippage down
            fill_price = bid * 0.9997 if order_type.upper() == "MARKET" else (price or bid)

        cost = fill_price * amount
        # Standard taker fee: 0.1% for crypto, built-in spread for forex
        fee_rate = 0.001 if "crypto" in self.live_broker.name or "bybit" in self.live_broker.name or "binance" in self.live_broker.name else 0.0002
        fee = cost * fee_rate

        # Update paper balance
        if side_upper == "BUY":
            self.balance -= (cost + fee)
        else:
            self.balance += (cost - fee)

        set_system_config("paper_balance_usd", round(self.balance, 4))

        logger.info(
            f"[PAPER TRADE] {side_upper} {amount} {symbol} filled at ${fill_price:.4f} "
            f"(Cost: ${cost:.2f}, Fee: ${fee:.4f}, New Bal: ${self.balance:.2f})"
        )

        return {
            'id': f"paper_{uuid.uuid4().hex[:10]}",
            'symbol': symbol,
            'side': side_upper,
            'type': order_type.upper(),
            'price': round(fill_price, 4),
            'amount': amount,
            'cost': round(cost, 4),
            'fee': round(fee, 4),
            'status': 'closed',
            'is_paper': True,
            'timestamp': int(time.time() * 1000)
        }

    def get_balance(self) -> Dict[str, float]:
        saved_balance = get_system_config("paper_balance_usd", self.balance)
        self.balance = float(saved_balance)
        return {
            'total_usd': round(self.balance, 4),
            'free_usd': round(self.balance, 4),
            'used_usd': 0.0
        }
