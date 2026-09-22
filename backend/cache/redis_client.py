import json
import logging
import time
from threading import RLock
from typing import Any, Optional

from config.settings import get_settings

logger = logging.getLogger(__name__)

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


class MemoryCache:
    """Thread-safe in-memory cache fallback when Redis is offline or unavailable."""
    def __init__(self):
        self._items = {}
        self._lock = RLock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            row = self._items.get(key)
            if not row:
                return None
            value, expires_at = row
            if expires_at and expires_at < time.time():
                self._items.pop(key, None)
                return None
            return value

    def setex(self, key: str, ttl: int, value: str):
        with self._lock:
            self._items[key] = (value, time.time() + ttl if ttl else None)

    def delete(self, key: str):
        with self._lock:
            self._items.pop(key, None)

    def incr(self, key: str) -> int:
        with self._lock:
            val = self.get(key)
            new_val = int(val) + 1 if val and val.isdigit() else 1
            self.setex(key, 86400, str(new_val))
            return new_val


class ResilientRedisClient:
    """Wraps redis.Redis to provide automatic failover to MemoryCache on connection errors."""
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis_client = None
        self._memory_fallback = MemoryCache()
        self._connect()

    def _connect(self):
        if redis is None:
            return
        try:
            client = redis.Redis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=0.5, socket_timeout=1.0)
            client.ping()
            self._redis_client = client
        except Exception as exc:
            logger.warning(f"Redis connection failed ({exc}) — falling back to MemoryCache")
            self._redis_client = None

    def _get_client(self):
        if self._redis_client is None:
            return self._memory_fallback
        return self._redis_client

    def get(self, key: str) -> Optional[str]:
        try:
            res = self._get_client().get(key)
            self._record_metric("hit" if res else "miss")
            return res
        except Exception as exc:
            logger.error(f"Redis GET error on key '{key}': {exc}")
            self._record_metric("error")
            return self._memory_fallback.get(key)

    def setex(self, key: str, ttl: int, value: str):
        try:
            self._get_client().setex(key, ttl, value)
        except Exception as exc:
            logger.error(f"Redis SETEX error on key '{key}': {exc}")
            self._record_metric("error")
            self._memory_fallback.setex(key, ttl, value)

    def delete(self, key: str):
        try:
            self._get_client().delete(key)
        except Exception as exc:
            logger.error(f"Redis DELETE error on key '{key}': {exc}")
            self._memory_fallback.delete(key)

    def incr(self, key: str) -> int:
        try:
            return self._get_client().incr(key)
        except Exception as exc:
            logger.error(f"Redis INCR error on key '{key}': {exc}")
            return self._memory_fallback.incr(key)

    def _record_metric(self, kind: str):
        try:
            from services.metrics_service import metrics_service
            metrics_service.inc(f"redis_{kind}s_total")
        except Exception:
            pass


_client = None


def get_cache():
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    _client = ResilientRedisClient(settings.redis_url)
    return _client


def cache_json(key: str, value: Any, ttl: int = 300):
    try:
        get_cache().setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.error(f"Failed to cache json for key '{key}': {exc}")


def get_cached_json(key: str):
    try:
        value = get_cache().get(key)
        return json.loads(value) if value else None
    except Exception as exc:
        logger.error(f"Failed to read cached json for key '{key}': {exc}")
        return None
