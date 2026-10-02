"""
Cache & High-Speed In-Memory Brain Layer.
Connects to Redis via Unix Domain Socket for microsecond access on Hetzner VPS,
with automatic fallback to TCP, and a thread-safe in-memory cache if Redis is unavailable.
"""

import os
import logging
from typing import Optional, Any, Dict

from config.settings import settings

logger = logging.getLogger("trading_bot.cache")

class InMemoryFallbackCache:
    """Thread-safe in-memory fallback store when Redis is unavailable."""
    def __init__(self):
        self._store: Dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._store[key] = str(value)
        return True

    def delete(self, key: str) -> bool:
        return bool(self._store.pop(key, None))

    def ping(self) -> bool:
        return True


class CacheManager:
    def __init__(self):
        self.client = self._init_client()

    def _init_client(self):
        try:
            import redis
            # 1. Try Unix domain socket first (Zero latency on Hetzner VPS)
            if settings.REDIS_UNIX_SOCKET and os.path.exists(settings.REDIS_UNIX_SOCKET):
                try:
                    client = redis.Redis(
                        unix_socket_path=settings.REDIS_UNIX_SOCKET,
                        db=settings.REDIS_DB,
                        decode_responses=True
                    )
                    client.ping()
                    logger.info(f"Connected to Redis via Unix Domain Socket: {settings.REDIS_UNIX_SOCKET}")
                    return client
                except Exception as e:
                    logger.warning(f"Unix socket connection failed: {e}. Falling back to TCP.")

            # 2. Try TCP Redis
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2
            )
            client.ping()
            logger.info(f"Connected to Redis via TCP: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            return client

        except Exception as e:
            logger.warning(f"Redis is unavailable ({e}). Using in-memory fallback cache.")
            return InMemoryFallbackCache()

    def get(self, key: str) -> Optional[str]:
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        try:
            return bool(self.client.set(key, str(value), ex=expire_seconds))
        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {e}")
            return False

    # --- Domain Specific Q-Learning & Genetic Mask Helpers ---

    def get_q_value(self, symbol: str, state_hash: str, action: str) -> float:
        """Retrieves learned Q-value for a specific state-action pair."""
        key = f"q:{symbol}:{state_hash}:{action}"
        val = self.get(key)
        try:
            return float(val) if val is not None else 0.0
        except ValueError:
            return 0.0

    def set_q_value(self, symbol: str, state_hash: str, action: str, q_value: float) -> bool:
        """Stores updated Q-value instantly into hot memory."""
        key = f"q:{symbol}:{state_hash}:{action}"
        return self.set(key, q_value)

    def get_genetic_mask(self, symbol: str) -> int:
        """
        Retrieves the 64-bit integer bitmask evolved by the Genetic Engine for this symbol.
        Defaults to all 1s (0xFFFFFFFFFFFFFFFF) if not yet evolved.
        """
        key = f"mask:{symbol}"
        val = self.get(key)
        if val:
            try:
                return int(val)
            except ValueError:
                pass
        return 0xFFFFFFFFFFFFFFFF

    def set_genetic_mask(self, symbol: str, mask: int) -> bool:
        """Stores the newly evolved 64-bit mask for this symbol."""
        key = f"mask:{symbol}"
        return self.set(key, str(mask))


# Singleton instance
cache = CacheManager()
