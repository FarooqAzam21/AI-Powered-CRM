import time
from cache.redis_client import get_cache

def check_rate_limits(key_id: int, rate_limit: int, daily_limit: int) -> tuple[bool, int, int]:
    """
    Enforces minute and daily rate limits using a cache provider.
    Returns:
        (is_allowed, remaining_minute_requests, retry_after_seconds)
    """
    cache = get_cache()
    now = int(time.time())
    
    minute_bucket = now // 60
    day_bucket = now // 86400
    
    min_key = f"rl:min:{key_id}:{minute_bucket}"
    day_key = f"rl:day:{key_id}:{day_bucket}"
    
    # Retrieve current counts
    min_val = cache.get(min_key)
    min_count = int(min_val) if min_val else 0
    
    day_val = cache.get(day_key)
    day_count = int(day_val) if day_val else 0
    
    # Enforce daily limit first
    if day_count >= daily_limit:
        retry_after = 86400 - (now % 86400)
        return False, 0, retry_after
        
    # Enforce minute rate limit
    if min_count >= rate_limit:
        retry_after = 60 - (now % 60)
        return False, 0, retry_after
        
    # Increment counts and store with appropriate TTL
    new_min = min_count + 1
    new_day = day_count + 1
    
    cache.setex(min_key, 60, str(new_min))
    cache.setex(day_key, 86400, str(new_day))
    
    remaining = max(0, rate_limit - new_min)
    return True, remaining, 0
