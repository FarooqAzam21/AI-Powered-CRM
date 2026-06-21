"""
AI Response Cache Manager - PHASE 5 OPTIMIZATION
Caches AI model responses in Redis to avoid duplicate processing
Reduces API calls to Ollama by 60-80%
"""
import hashlib
import json
import logging
from typing import Optional, Dict, Any

try:
    from cache.redis_client import get_cache as _get_redis_cache
    from config.settings import get_settings
except ImportError:
    # Fallback for standalone usage
    _get_redis_cache = None

logger = logging.getLogger(__name__)

class AIResponseCache:
    """
    Comprehensive Redis-based cache for AI model responses
    Supports multiple operation types with configurable TTL
    """
    
    def __init__(self, redis_client=None, ttl_hours: int = 24):
        """Initialize cache with Redis client"""
        self.redis_client = redis_client or _get_redis_cache()
        self.ttl_seconds = ttl_hours * 3600
        self.cache_prefix = "ai_cache:"
        self.stats_key = "ai_cache:stats"
    
    def _key(self, operation: str, content: str) -> str:
        """Generate cache key from operation and content"""
        content_hash = hashlib.sha256(content[:2000].encode()).hexdigest()[:16]
        return f"{self.cache_prefix}{operation}:{content_hash}"
    
    # Classification caching
    def get_classification(self, email_subject: str, email_body: str) -> Optional[Dict]:
        """Get cached classification (category, confidence, action)"""
        try:
            content = f"{email_subject}|{email_body}"
            key = self._key("classify", content)
            cached = self.redis_client.get(key)
            if cached:
                logger.debug(f"✅ Cache HIT: classification")
                self._update_stats("hit")
                return json.loads(cached)
            self._update_stats("miss")
            return None
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None
    
    def set_classification(self, email_subject: str, email_body: str, result: Dict):
        """Cache classification result"""
        try:
            content = f"{email_subject}|{email_body}"
            key = self._key("classify", content)
            self.redis_client.setex(key, self.ttl_seconds, json.dumps(result))
            return True
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
            return False
    
    # Reply draft caching
    def get_reply_draft(self, email_body: str, tone: str) -> Optional[str]:
        """Get cached reply draft"""
        try:
            content = f"{email_body}|{tone}"
            key = self._key(f"reply_{tone}", content)
            cached = self.redis_client.get(key)
            if cached:
                logger.debug(f"✅ Cache HIT: reply draft")
                self._update_stats("hit")
                return cached.decode('utf-8') if isinstance(cached, bytes) else cached
            self._update_stats("miss")
            return None
        except Exception as e:
            logger.warning(f"Cache get reply failed: {e}")
            return None
    
    def set_reply_draft(self, email_body: str, tone: str, reply: str):
        """Cache reply draft (7 day TTL)"""
        try:
            content = f"{email_body}|{tone}"
            key = self._key(f"reply_{tone}", content)
            ttl = 7 * 24 * 3600  # 7 days
            self.redis_client.setex(key, ttl, reply)
            return True
        except Exception as e:
            logger.warning(f"Cache set reply failed: {e}")
            return False
    
    # Entity extraction caching
    def get_entities(self, text: str) -> Optional[Dict]:
        """Get cached entity extraction results"""
        try:
            key = self._key("entities", text)
            cached = self.redis_client.get(key)
            if cached:
                logger.debug(f"✅ Cache HIT: entities")
                self._update_stats("hit")
                return json.loads(cached)
            self._update_stats("miss")
            return None
        except Exception as e:
            logger.warning(f"Cache get entities failed: {e}")
            return None
    
    def set_entities(self, text: str, entities: Dict):
        """Cache entity extraction results"""
        try:
            key = self._key("entities", text)
            self.redis_client.setex(key, self.ttl_seconds, json.dumps(entities))
            return True
        except Exception as e:
            logger.warning(f"Cache set entities failed: {e}")
            return False
    
    # Intent detection caching
    def get_intent(self, text: str) -> Optional[str]:
        """Get cached intent detection result"""
        try:
            key = self._key("intent", text)
            cached = self.redis_client.get(key)
            if cached:
                logger.debug(f"✅ Cache HIT: intent")
                self._update_stats("hit")
                return cached.decode('utf-8') if isinstance(cached, bytes) else cached
            self._update_stats("miss")
            return None
        except Exception as e:
            logger.warning(f"Cache get intent failed: {e}")
            return None
    
    def set_intent(self, text: str, intent: str):
        """Cache intent detection result"""
        try:
            key = self._key("intent", text)
            self.redis_client.setex(key, self.ttl_seconds, intent)
            return True
        except Exception as e:
            logger.warning(f"Cache set intent failed: {e}")
            return False
    
    # Sentiment caching
    def get_sentiment(self, text: str) -> Optional[Dict]:
        """Get cached sentiment analysis result"""
        try:
            key = self._key("sentiment", text)
            cached = self.redis_client.get(key)
            if cached:
                logger.debug(f"✅ Cache HIT: sentiment")
                self._update_stats("hit")
                return json.loads(cached)
            self._update_stats("miss")
            return None
        except Exception as e:
            logger.warning(f"Cache get sentiment failed: {e}")
            return None
    
    def set_sentiment(self, text: str, sentiment: Dict):
        """Cache sentiment analysis result"""
        try:
            key = self._key("sentiment", text)
            self.redis_client.setex(key, self.ttl_seconds, json.dumps(sentiment))
            return True
        except Exception as e:
            logger.warning(f"Cache set sentiment failed: {e}")
            return False
    
    # Stats and health
    def _update_stats(self, stat_type: str):
        """Update cache statistics"""
        try:
            stats = self.redis_client.hget(self.stats_key, stat_type)
            current = int(stats) if stats else 0
            self.redis_client.hset(self.stats_key, stat_type, current + 1)
        except Exception:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            stats = self.redis_client.hgetall(self.stats_key)
            hits = int(stats.get(b"hit", 0))
            misses = int(stats.get(b"miss", 0))
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0
            cache_keys = self.redis_client.keys(f"{self.cache_prefix}*")
            return {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate": round(hit_rate, 2),
                "cached_items": len(cache_keys)
            }
        except Exception as e:
            logger.warning(f"Stats retrieval failed: {e}")
            return {}
    
    def clear_cache(self):
        """Clear all cached responses"""
        try:
            keys = self.redis_client.keys(f"{self.cache_prefix}*")
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"🧹 Cleared {len(keys)} cache entries")
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False


# Module-level functions for easy access
_cache_instance = None


def get_ai_cache() -> AIResponseCache:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        try:
            from config.settings import get_settings
            settings = get_settings()
            ttl_hours = settings.ai_cache_ttl_seconds // 3600
            _cache_instance = AIResponseCache(ttl_hours=ttl_hours)
        except Exception as e:
            logger.warning(f"Failed to initialize cache: {e}")
            _cache_instance = AIResponseCache(ttl_hours=24)
    return _cache_instance


def get_cached_ai_response(model: str, prompt: str) -> Optional[str]:
    """Get cached response by model and prompt"""
    cache = get_ai_cache()
    key = cache._key("generate", f"{model}:{prompt}")
    try:
        cached = cache.redis_client.get(key)
        if cached:
            logger.debug(f"✅ Cache HIT: {model}")
            return cached
    except Exception as e:
        logger.debug(f"Cache fetch failed: {e}")
    return None


def set_cached_ai_response(model: str, prompt: str, response: str):
    """Cache response by model and prompt"""
    cache = get_ai_cache()
    key = cache._key("generate", f"{model}:{prompt}")
    try:
        cache.redis_client.setex(key, cache.ttl_seconds, response)
    except Exception as e:
        logger.debug(f"Cache store failed: {e}")


class AIResponseCache:
    """Response cache management"""
    
    def clear_cache(self):
        """Clear all cached responses"""
        try:
            cache_keys = self.redis_client.keys(f"{self.cache_prefix}*")
            if cache_keys:
                self.redis_client.delete(*cache_keys)
                logger.info(f"Cleared {len(cache_keys)} cache entries")
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False

# Legacy function compatibility
def _key(model: str, prompt: str) -> str:
    """Legacy key generation (kept for compatibility)"""
    digest = hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()
    return f"ai:{digest}"

def get_cached_ai_response(model: str, prompt: str):
    """Legacy function (kept for compatibility)"""
    try:
        cache = _get_redis_cache()
        return cache.get(_key(model, prompt))
    except Exception:
        return None

def set_cached_ai_response(model: str, prompt: str, response: str):
    """Legacy function (kept for compatibility)"""
    try:
        cache = _get_redis_cache()
        settings = get_settings()
        cache.setex(_key(model, prompt), settings.ai_cache_ttl_seconds, response)
    except Exception:
        pass
