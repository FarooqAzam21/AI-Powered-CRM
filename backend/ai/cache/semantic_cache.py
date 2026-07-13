import hashlib
import logging
from cache.redis_client import get_cache
from config.settings import get_settings

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    Caches LLM requests based on prompt hashes to save compute.
    """

    def __init__(self):
        self.cache = get_cache()
        self.ttl = get_settings().ai_cache_ttl_seconds

    def _hash_prompt(self, prompt: str, system_prompt: str = None) -> str:
        content = prompt
        if system_prompt:
            content += f"|||{system_prompt}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def get(self, prompt: str, system_prompt: str = None) -> str:
        """
        Retrieves a cached response if it exists.
        """
        key = f"ai_cache:{self._hash_prompt(prompt, system_prompt)}"
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.error(f"Semantic cache GET failed: {e}")
            return None

    def set(self, prompt: str, response: str, system_prompt: str = None):
        """
        Stores a response in the cache.
        """
        if not response or not response.strip():
            return

        key = f"ai_cache:{self._hash_prompt(prompt, system_prompt)}"
        try:
            self.cache.setex(key, self.ttl, response)
        except Exception as e:
            logger.error(f"Semantic cache SET failed: {e}")


_cache = None

def get_semantic_cache() -> SemanticCache:
    global _cache
    if _cache is None:
        _cache = SemanticCache()
    return _cache
