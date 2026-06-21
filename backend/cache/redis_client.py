import json
import time
from threading import RLock
from typing import Any, Optional

from config.settings import get_settings

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


class MemoryCache:
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


_client = None


def get_cache():
    global _client
    if _client is not None:
        return _client
    if redis is None:
        _client = MemoryCache()
        return _client
    try:
        client = redis.Redis.from_url(get_settings().redis_url, decode_responses=True, socket_connect_timeout=0.25)
        client.ping()
        _client = client
    except Exception:
        _client = MemoryCache()
    return _client


def cache_json(key: str, value: Any, ttl: int = 300):
    get_cache().setex(key, ttl, json.dumps(value, default=str))


def get_cached_json(key: str):
    value = get_cache().get(key)
    return json.loads(value) if value else None
