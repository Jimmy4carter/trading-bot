"""
CCXT Crypto Broker Connector for Bybit and Binance.
Handles rate limits, precision formatting, and unified market execution.
"""

import time
import logging
from typing import Dict, Any, List, Optional
try:
    import ccxt
except ImportError:
    ccxt = None


from .base import BaseBroker
from config.settings import settings

logger = logging.getLogger("trading_bot.broker.crypto")

class CCXTCryptoBroker(BaseBroker):
    def __init__(self, exchange_id: str = "bybit"):
        super().__init__(name=exchange_id.lower())
        self.exchange_id = exchange_id.lower()
        self.exchange = self._init_exchange()
        self.markets = {}
        # Markets will be loaded lazily on demand


    def _init_exchange(self):
        if not ccxt:
            logger.warning(f"ccxt library not available. {self.exchange_id} running in mock mode.")
            return None

        api_key = settings.BYBIT_API_KEY if self.exchange_id == "bybit" else settings.BINANCE_API_KEY

        api_secret = settings.BYBIT_API_SECRET if self.exchange_id == "bybit" else settings.BINANCE_API_SECRET

        exchange_class = getattr(ccxt, self.exchange_id, None)
        if not exchange_class:
            raise ValueError(f"Unsupported CCXT exchange: {self.exchange_id}")

        client = exchange_class({
            'apiKey': api_key or "",
            'secret': api_secret or "",
            'enableRateLimit': True,
            'timeout': 15000,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True
            }
        })
        return client

    def _load_markets(self):
        if not self.exchange:
            return
        try:
            self.markets = self.exchange.load_markets()
            logger.info(f"Loaded {len(self.markets)} markets from {self.exchange_id}")
        except Exception as e:
            logger.warning(f"Failed to load markets from {self.exchange_id}: {e}")

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List[float]]:
        if not self.exchange:
            return []
        try:

            return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol} on {self.exchange_id}: {e}")
            return []

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            last = float(ticker.get('last') or ticker.get('close') or 0.0)
            bid = float(ticker.get('bid') or last)
            ask = float(ticker.get('ask') or last)
            spread = max(0.0, ask - bid)
            spread_pct = (spread / last * 100.0) if last > 0 else 0.0

            return {
                'symbol': symbol,
                'last': last,
                'bid': bid,
                'ask': ask,
                'spread': spread,
                'spread_pct': spread_pct,
                'timestamp': ticker.get('timestamp') or int(time.time() * 1000)
            }
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol} on {self.exchange_id}: {e}")
            return {'symbol': symbol, 'last': 0.0, 'bid': 0.0, 'ask': 0.0, 'spread': 0.0, 'spread_pct': 0.0, 'timestamp': int(time.time() * 1000)}

    def create_order(
        self, 
        symbol: str, 
        side: str, 
        amount: float, 
        order_type: str = "MARKET", 
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        side_lower = side.lower()
        type_lower = order_type.lower()

        try:
            if type_lower == "market":
                order = self.exchange.create_order(symbol, 'market', side_lower, amount)
            else:
                if price is None:
                    raise ValueError("Price required for limit orders")
                order = self.exchange.create_order(symbol, 'limit', side_lower, amount, price)

            executed_price = float(order.get('average') or order.get('price') or price or 0.0)
            filled_amount = float(order.get('filled') or amount)
            cost = float(order.get('cost') or (executed_price * filled_amount))
            fee = float(order.get('fee', {}).get('cost', cost * 0.001) if order.get('fee') else cost * 0.001)

            return {
                'id': str(order.get('id', int(time.time() * 1000))),
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'price': executed_price,
                'amount': filled_amount,
                'cost': cost,
                'fee': fee,
                'status': order.get('status', 'closed')
            }
        except Exception as e:
            logger.error(f"Order placement failed for {symbol} {side} on {self.exchange_id}: {e}")
            raise

    def get_balance(self) -> Dict[str, float]:
        try:
            bal = self.exchange.fetch_balance()
            total_usd = float(bal.get('total', {}).get('USDT', 0.0))
            free_usd = float(bal.get('free', {}).get('USDT', 0.0))
            used_usd = float(bal.get('used', {}).get('USDT', 0.0))
            return {'total_usd': total_usd, 'free_usd': free_usd, 'used_usd': used_usd}
        except Exception as e:
            logger.warning(f"Failed to fetch balance from {self.exchange_id}: {e}")
            return {'total_usd': 0.0, 'free_usd': 0.0, 'used_usd': 0.0}

    def get_market_rules(self, symbol: str) -> Dict[str, float]:
        """Fetches limits and precision for this symbol."""
        if not self.markets and self.exchange:
            self._load_markets()
        market = self.markets.get(symbol)
        if not market:
            return {'min_notional': 5.0, 'amount_step': 0.0001, 'price_tick': 0.01}

        min_cost = float(market.get('limits', {}).get('cost', {}).get('min') or 5.0)
        amount_precision = market.get('precision', {}).get('amount')
        price_precision = market.get('precision', {}).get('price')

        amount_step = 10 ** (-amount_precision) if isinstance(amount_precision, int) else 0.0001
        price_tick = 10 ** (-price_precision) if isinstance(price_precision, int) else 0.01

        return {
            'min_notional': max(5.0, min_cost),
            'amount_step': amount_step,
            'price_tick': price_tick
        }
