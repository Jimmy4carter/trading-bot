"""
Omni-Broker Router & Dispatcher.
Manages connections to Binance, Bybit, and OANDA, dynamically switching
between True Paper Simulation and Live execution based on runtime configuration.
"""

import logging
from typing import Dict, Any, Optional

from .base import BaseBroker
from .crypto_ccxt import CCXTCryptoBroker
from .forex_oanda import OandaForexBroker
from .forex_deriv import DerivForexBroker
from .forex_ibkr import InteractiveBrokersAdapter
from .paper_simulator import PaperTradingSimulator
from config.settings import settings
from core.database import get_system_config

logger = logging.getLogger("trading_bot.broker.router")

class OmniBrokerRouter:
    def __init__(self):
        # 1. Initialize underlying live broker instances
        self.live_brokers: Dict[str, BaseBroker] = {
            'bybit': CCXTCryptoBroker('bybit'),
            'binance': CCXTCryptoBroker('binance'),
            'deriv': DerivForexBroker(),
            'ibkr': InteractiveBrokersAdapter(),
            'oanda': OandaForexBroker()
        }

        # 2. Initialize corresponding paper trading simulators
        self.paper_brokers: Dict[str, BaseBroker] = {
            name: PaperTradingSimulator(broker) 
            for name, broker in self.live_brokers.items()
        }

    def get_execution_mode(self) -> str:
        """Returns 'demo' or 'live' from system config (or .env default)."""
        return get_system_config("execution_mode", settings.EXECUTION_MODE).lower()

    def get_active_broker_name(self) -> str:
        """Returns the default active broker name ('bybit', 'binance', or 'oanda')."""
        return get_system_config("active_broker", settings.ACTIVE_BROKER).lower()

    @property
    def active_broker(self) -> str:
        """Convenience property returning the active broker name."""
        return self.get_active_broker_name()

    def get_broker(self, broker_name: Optional[str] = None) -> BaseBroker:
        """
        Retrieves the appropriate broker instance based on name and execution mode.
        If execution_mode is 'demo', returns the PaperTradingSimulator wrapping the live feed.
        """
        name = (broker_name or self.get_active_broker_name()).lower()
        mode = self.get_execution_mode()

        if mode == 'live':
            broker = self.live_brokers.get(name)
            if not broker:
                logger.warning(f"Live broker '{name}' not found, falling back to Bybit")
                broker = self.live_brokers['bybit']
            return broker
        else:
            broker = self.paper_brokers.get(name)
            if not broker:
                logger.warning(f"Paper broker '{name}' not found, falling back to Bybit")
                broker = self.paper_brokers['bybit']
            return broker

    def get_broker_for_symbol(self, symbol: str, preferred_broker: Optional[str] = None) -> BaseBroker:
        """Auto-detects broker type based on symbol if not specified."""
        if preferred_broker:
            return self.get_broker(preferred_broker)

        # Deriv 24/7 Synthetics
        if any(symbol.startswith(prefix) for prefix in ['R_', '1HZ', 'BOOM', 'CRASH', 'STEP', 'JUMP']):
            return self.get_broker('deriv')

        # Forex & Metals heuristic: route to Deriv (micro-capital & 24/7 friendly)
        if '_' in symbol or any(pair in symbol for pair in ['EUR', 'GBP', 'USD', 'JPY', 'AUD', 'CAD', 'CHF', 'XAU']) and 'USDT' not in symbol:
            return self.get_broker('deriv')

        return self.get_broker()

# Singleton Omni-Router instance
router = OmniBrokerRouter()

__all__ = [
    "BaseBroker",
    "CCXTCryptoBroker",
    "OandaForexBroker",
    "DerivForexBroker",
    "InteractiveBrokersAdapter",
    "PaperTradingSimulator",
    "OmniBrokerRouter",
    "router"
]
