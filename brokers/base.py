"""
Abstract Base Broker Interface & Precision Normalizer.
Enforces strict contract across Binance, Bybit, OANDA, and Paper Simulator.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import math
import logging

logger = logging.getLogger("trading_bot.broker.base")

class BaseBroker(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List[float]]:
        """
        Fetches OHLCV candlestick bars.
        Returns: list of [timestamp, open, high, low, close, volume]
        """
        pass

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches current ticker information.
        Returns dict with at least: {'bid': float, 'ask': float, 'last': float, 'spread': float}
        """
        pass

    @abstractmethod
    def create_order(
        self, 
        symbol: str, 
        side: str, 
        amount: float, 
        order_type: str = "MARKET", 
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes or simulates an order.
        Returns: {'id': str, 'symbol': str, 'side': str, 'price': float, 'amount': float, 'cost': float, 'fee': float}
        """
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        """
        Returns account balance: {'total_usd': float, 'free_usd': float, 'used_usd': float}
        """
        pass

    def normalize_amount(self, symbol: str, target_cost_usd: float, current_price: float, min_notional: float = 5.0, step_size: float = 0.0001) -> float:
        """
        Calculates safe lot amount from USD allocation, enforcing exchange minimum notional
        and stepping down to exchange-supported precision to prevent rejection.
        """
        if current_price <= 0:
            raise ValueError(f"Invalid current price for {symbol}: {current_price}")

        # Ensure trade size meets or exceeds minimum notional (plus 5% safety buffer for price fluctuation)
        effective_cost = max(target_cost_usd, min_notional * 1.05)
        raw_amount = effective_cost / current_price

        # Round down to allowed step size
        precision_decimals = max(0, int(round(-math.log10(step_size)))) if step_size < 1 else 0
        factor = 10 ** precision_decimals
        clean_amount = math.floor(raw_amount * factor) / factor

        # Double check resulting cost meets minimum
        if (clean_amount * current_price) < min_notional:
            clean_amount = math.ceil(raw_amount * factor) / factor

        return float(clean_amount)

    def normalize_price(self, price: float, tick_size: float = 0.01) -> float:
        """Rounds price to nearest exchange tick size."""
        if tick_size <= 0:
            return round(price, 4)
        precision = max(0, int(round(-math.log10(tick_size)))) if tick_size < 1 else 0
        return round(round(price / tick_size) * tick_size, precision)
