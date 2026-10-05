"""
Configuration settings for the Autonomous Trading Bot.
Loads environment variables from .env with robust type validation and fallbacks.
"""

import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field

    class Settings(BaseSettings):
        EXECUTION_MODE: str = Field(default="demo") # 'demo' or 'live'
        ACTIVE_BROKER: str = Field(default="bybit") # 'bybit', 'binance', 'oanda'

        STARTING_BALANCE_USD: float = Field(default=10.0)
        TRADE_SIZE_USD: float = Field(default=10.0)
        MAX_CONCURRENT_TRADES: int = Field(default=3)
        MIN_CONFIDENCE_THRESHOLD: float = Field(default=0.65)
        MAX_DAILY_DRAWDOWN_PCT: float = Field(default=3.0)

        TAKE_PROFIT_PCT: float = Field(default=0.015)
        STOP_LOSS_PCT: float = Field(default=0.006)
        TRAILING_ACTIVATION_PCT: float = Field(default=0.008)
        TRAILING_PULLBACK_PCT: float = Field(default=0.0025)

        BINANCE_API_KEY: str = Field(default="")
        BINANCE_API_SECRET: str = Field(default="")

        BYBIT_API_KEY: str = Field(default="")
        BYBIT_API_SECRET: str = Field(default="")

        OANDA_API_KEY: str = Field(default="")
        OANDA_ACCOUNT_ID: str = Field(default="")
        OANDA_ENVIRONMENT: str = Field(default="practice")

        # Deriv API Settings (Forex, Commodities & 24/7 Synthetics)
        DERIV_API_TOKEN: str = Field(default="")
        DERIV_APP_ID: str = Field(default="1089")
        DERIV_ENDPOINT: str = Field(default="wss://ws.derivws.com/websockets/v3")

        # Interactive Brokers (IBKR) Settings (Institutional DMA)
        IBKR_HOST: str = Field(default="127.0.0.1")
        IBKR_PORT: int = Field(default=4002) # 4002 for Paper, 4001 for Live IB Gateway
        IBKR_CLIENT_ID: int = Field(default=1)
        IBKR_ACCOUNT: str = Field(default="")

        SQLITE_DB_PATH: str = Field(default=str(BASE_DIR / "trading_ledger.db"))
        REDIS_HOST: str = Field(default="localhost")
        REDIS_PORT: int = Field(default=6379)
        REDIS_UNIX_SOCKET: Optional[str] = Field(default="/var/run/redis/redis.sock")
        REDIS_DB: int = Field(default=0)

        ADMIN_USERNAME: str = Field(default="admin")
        ADMIN_PASSWORD: str = Field(default="admin")
        JWT_SECRET: str = Field(default="super_secret_jwt_signing_key_replace_in_production")
        JWT_ALGORITHM: str = Field(default="HS256")
        ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)

        TELEGRAM_BOT_TOKEN: str = Field(default="")
        TELEGRAM_CHAT_ID: str = Field(default="")
        TELEGRAM_ENABLED: bool = Field(default=False)

        HOST: str = Field(default="0.0.0.0")
        PORT: int = Field(default=8000)

        class Config:
            env_file = str(BASE_DIR / ".env")
            env_file_encoding = "utf-8"
            extra = "ignore"

    settings = Settings()

except ImportError:
    # Graceful fallback if pydantic_settings is not yet installed
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BASE_DIR / ".env")

    class FallbackSettings:
        EXECUTION_MODE = os.getenv("EXECUTION_MODE", "demo")
        ACTIVE_BROKER = os.getenv("ACTIVE_BROKER", "bybit")

        STARTING_BALANCE_USD = float(os.getenv("STARTING_BALANCE_USD", "10.0"))
        TRADE_SIZE_USD = float(os.getenv("TRADE_SIZE_USD", "10.0"))
        MAX_CONCURRENT_TRADES = int(os.getenv("MAX_CONCURRENT_TRADES", "3"))
        MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.65"))
        MAX_DAILY_DRAWDOWN_PCT = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "3.0"))

        TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.015"))
        STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.006"))
        TRAILING_ACTIVATION_PCT = float(os.getenv("TRAILING_ACTIVATION_PCT", "0.008"))
        TRAILING_PULLBACK_PCT = float(os.getenv("TRAILING_PULLBACK_PCT", "0.0025"))

        BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
        BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

        BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
        BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")

        OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
        OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
        OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")

        DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "")
        DERIV_APP_ID = os.getenv("DERIV_APP_ID", "1089")
        DERIV_ENDPOINT = os.getenv("DERIV_ENDPOINT", "wss://ws.derivws.com/websockets/v3")

        IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
        IBKR_PORT = int(os.getenv("IBKR_PORT", "4002"))
        IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "1"))
        IBKR_ACCOUNT = os.getenv("IBKR_ACCOUNT", "")

        SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "trading_ledger.db"))
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        REDIS_UNIX_SOCKET = os.getenv("REDIS_UNIX_SOCKET", "/var/run/redis/redis.sock")
        REDIS_DB = int(os.getenv("REDIS_DB", "0"))

        ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
        ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
        JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_jwt_signing_key_replace_in_production")
        JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

        TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
        TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() in ("true", "1")

        HOST = os.getenv("HOST", "0.0.0.0")
        PORT = int(os.getenv("PORT", "8000"))

    settings = FallbackSettings()
