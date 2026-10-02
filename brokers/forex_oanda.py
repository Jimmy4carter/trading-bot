"""
OANDA v20 Forex Broker Connector.
Direct REST API integration supporting practice and trade environments,
micro-unit sizing, and spread monitoring.
"""

import time
import logging
from typing import Dict, Any, List, Optional
import requests

from .base import BaseBroker
from config.settings import settings

logger = logging.getLogger("trading_bot.broker.forex")

class OandaForexBroker(BaseBroker):
    def __init__(self):
        super().__init__(name="oanda")
        self.api_key = settings.OANDA_API_KEY
        self.account_id = settings.OANDA_ACCOUNT_ID
        self.environment = settings.OANDA_ENVIRONMENT.lower()

        if self.environment == "trade":
            self.base_url = "https://api-fxtrade.oanda.com/v3"
        else:
            self.base_url = "https://api-fxpractice.oanda.com/v3"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339"
        }

    def _normalize_instrument(self, symbol: str) -> str:
        """Converts EUR/USD or EUR-USD to EUR_USD."""
        return symbol.replace('/', '_').replace('-', '_').upper()

    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List[float]]:
        instrument = self._normalize_instrument(symbol)
        granularity_map = {
            '1m': 'M1',
            '5m': 'M5',
            '15m': 'M15',
            '1h': 'H1',
            '4h': 'H4',
            '1d': 'D'
        }
        granularity = granularity_map.get(timeframe, 'H1')
        url = f"{self.base_url}/instruments/{instrument}/candles"
        params = {"count": limit, "granularity": granularity, "price": "M"}

        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=10)
            if res.status_code != 200:
                logger.error(f"OANDA candles error ({res.status_code}): {res.text}")
                return []

            data = res.json()
            candles = []
            for c in data.get("candles", []):
                if not c.get("complete"):
                    continue
                # Time format RFC3339 string to ms timestamp
                t_str = c["time"]
                # Parse close, open, high, low
                mid = c["mid"]
                o = float(mid["o"])
                h = float(mid["h"])
                l = float(mid["l"])
                close = float(mid["c"])
                v = int(c.get("volume", 0))
                # For simplified usage, pass ms timestamp as 0 or approximate
                candles.append([0, o, h, l, close, v])

            return candles
        except Exception as e:
            logger.error(f"OANDA fetch_ohlcv exception for {symbol}: {e}")
            return []

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        instrument = self._normalize_instrument(symbol)
        url = f"{self.base_url}/accounts/{self.account_id}/pricing"
        params = {"instruments": instrument}

        try:
            res = requests.get(url, headers=self.headers, params=params, timeout=5)
            if res.status_code != 200:
                logger.warning(f"OANDA pricing error ({res.status_code}): {res.text}")
                return {'symbol': symbol, 'last': 0.0, 'bid': 0.0, 'ask': 0.0, 'spread': 0.0, 'spread_pct': 0.0, 'timestamp': int(time.time() * 1000)}

            data = res.json()
            prices = data.get("prices", [])
            if not prices:
                return {'symbol': symbol, 'last': 0.0, 'bid': 0.0, 'ask': 0.0, 'spread': 0.0, 'spread_pct': 0.0, 'timestamp': int(time.time() * 1000)}

            p = prices[0]
            bids = p.get("bids", [])
            asks = p.get("asks", [])
            bid = float(bids[0]["price"]) if bids else float(p.get("closeoutBid", 0.0))
            ask = float(asks[0]["price"]) if asks else float(p.get("closeoutAsk", 0.0))
            last = round((bid + ask) / 2.0, 5)
            spread = max(0.0, ask - bid)
            spread_pct = (spread / last * 100.0) if last > 0 else 0.0

            return {
                'symbol': symbol,
                'last': last,
                'bid': bid,
                'ask': ask,
                'spread': spread,
                'spread_pct': spread_pct,
                'timestamp': int(time.time() * 1000)
            }
        except Exception as e:
            logger.error(f"OANDA fetch_ticker exception: {e}")
            return {'symbol': symbol, 'last': 0.0, 'bid': 0.0, 'ask': 0.0, 'spread': 0.0, 'spread_pct': 0.0, 'timestamp': int(time.time() * 1000)}

    def create_order(
        self, 
        symbol: str, 
        side: str, 
        amount: float, 
        order_type: str = "MARKET", 
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        instrument = self._normalize_instrument(symbol)
        # OANDA units: positive for BUY, negative for SELL
        units = int(amount) if side.upper() == "BUY" else -int(amount)
        if units == 0:
            units = 1 if side.upper() == "BUY" else -1

        url = f"{self.base_url}/accounts/{self.account_id}/orders"
        payload = {
            "order": {
                "instrument": instrument,
                "units": str(units),
                "type": order_type.upper(),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT"
            }
        }

        try:
            res = requests.post(url, headers=self.headers, json=payload, timeout=10)
            data = res.json()
            fill = data.get("orderFillTransaction", {})
            executed_price = float(fill.get("price", 0.0))
            filled_units = abs(float(fill.get("units", amount)))

            return {
                'id': str(fill.get("id", int(time.time() * 1000))),
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'price': executed_price,
                'amount': filled_units,
                'cost': filled_units * executed_price,
                'fee': 0.0, # OANDA builds fee into the spread
                'status': 'closed' if fill else 'rejected'
            }
        except Exception as e:
            logger.error(f"OANDA order error: {e}")
            raise

    def get_balance(self) -> Dict[str, float]:
        url = f"{self.base_url}/accounts/{self.account_id}/summary"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                acc = res.json().get("account", {})
                balance = float(acc.get("balance", 0.0))
                nav = float(acc.get("NAV", balance))
                margin_used = float(acc.get("marginUsed", 0.0))
                margin_avail = float(acc.get("marginAvailable", balance))
                return {'total_usd': nav, 'free_usd': margin_avail, 'used_usd': margin_used}
            return {'total_usd': 0.0, 'free_usd': 0.0, 'used_usd': 0.0}
        except Exception as e:
            logger.warning(f"OANDA get_balance error: {e}")
            return {'total_usd': 0.0, 'free_usd': 0.0, 'used_usd': 0.0}
