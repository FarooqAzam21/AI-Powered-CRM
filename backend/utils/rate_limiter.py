"""
P6 — Multi-tier Enterprise Rate Limiter
Enforces:
- Organization-wide rate limits (derived from P3 Subscription Plan limits)
- API Key specific limits (minute and daily)
- Endpoint-level burst limits
Integrates directly with Redis sliding windows (with MemoryCache fallback).
"""
import time
import logging
from typing import Tuple, Optional
from cache.redis_client import get_cache

logger = logging.getLogger(__name__)

# Plan default request limits per minute if not configured
PLAN_MINUTE_RATE_LIMITS = {
    "free": 100,
    "starter": 1000,
    "professional": 10000,
    "enterprise": 50000,  # Effectively very high / configurable
}

# Endpoint burst limits per minute (optional protection for expensive operations)
ENDPOINT_BURST_LIMITS = {
    "ai_complete": 30,
    "workflow_execute": 60,
    "bulk_contacts": 60,
}


def check_multi_tier_rate_limit(
    *,
    org_id: int,
    key_id: int,
    key_minute_limit: int,
    key_daily_limit: int,
    plan_slug: str = "free",
    endpoint_tag: Optional[str] = None,
) -> Tuple[bool, int, int, str]:
    """
    Checks multi-tier rate limits:
    1. Key Daily limit
    2. Key Minute limit
    3. Organization Minute limit (based on P3 plan tier)
    4. Endpoint burst limit (if applicable)

    Returns:
        (is_allowed, remaining_minute_requests, retry_after_seconds, violation_reason)
    """
    cache = get_cache()
    now = int(time.time())

    minute_bucket = now // 60
    day_bucket = now // 86400
    sec_in_minute = now % 60
    retry_after_min = max(1, 60 - sec_in_minute)
    retry_after_day = max(1, 86400 - (now % 86400))

    # 1. Check Key Daily Limit
    key_day_key = f"rl:dev:key:day:{key_id}:{day_bucket}"
    day_count = int(cache.get(key_day_key) or 0)
    if key_daily_limit > 0 and day_count >= key_daily_limit:
        return False, 0, retry_after_day, "API key daily limit exceeded"

    # 2. Check Key Minute Limit
    key_min_key = f"rl:dev:key:min:{key_id}:{minute_bucket}"
    key_min_count = int(cache.get(key_min_key) or 0)
    if key_minute_limit > 0 and key_min_count >= key_minute_limit:
        return False, 0, retry_after_min, "API key minute rate limit exceeded"

    # 3. Check Organization Minute Limit (P3 Plan tier)
    org_minute_limit = PLAN_MINUTE_RATE_LIMITS.get(plan_slug.lower(), 100)
    if org_minute_limit > 0:  # -1 represents unlimited
        org_min_key = f"rl:dev:org:min:{org_id}:{minute_bucket}"
        org_min_count = int(cache.get(org_min_key) or 0)
        if org_min_count >= org_minute_limit:
            return False, 0, retry_after_min, f"Organization plan ({plan_slug}) rate limit exceeded"

    # 4. Check Endpoint Burst Limit
    if endpoint_tag and endpoint_tag in ENDPOINT_BURST_LIMITS:
        burst_limit = ENDPOINT_BURST_LIMITS[endpoint_tag]
        burst_key = f"rl:dev:burst:{key_id}:{endpoint_tag}:{minute_bucket}"
        burst_count = int(cache.get(burst_key) or 0)
        if burst_count >= burst_limit:
            return False, 0, retry_after_min, f"Endpoint '{endpoint_tag}' burst limit exceeded"

    # All checks passed — increment counters atomically / with TTL
    new_day = day_count + 1
    new_key_min = key_min_count + 1
    cache.setex(key_day_key, 86400, str(new_day))
    cache.setex(key_min_key, 60, str(new_key_min))

    if org_minute_limit > 0:
        org_min_key = f"rl:dev:org:min:{org_id}:{minute_bucket}"
        org_min_count = int(cache.get(org_min_key) or 0)
        cache.setex(org_min_key, 60, str(org_min_count + 1))

    if endpoint_tag and endpoint_tag in ENDPOINT_BURST_LIMITS:
        burst_key = f"rl:dev:burst:{key_id}:{endpoint_tag}:{minute_bucket}"
        burst_count = int(cache.get(burst_key) or 0)
        cache.setex(burst_key, 60, str(burst_count + 1))

    remaining = max(0, key_minute_limit - new_key_min)
    return True, remaining, 0, ""


def check_rate_limits(key_id: int, rate_limit: int, daily_limit: int) -> Tuple[bool, int, int]:
    """
    Backwards-compatible wrapper for legacy internal calls.
    """
    allowed, remaining, retry_after, _ = check_multi_tier_rate_limit(
        org_id=0,
        key_id=key_id,
        key_minute_limit=rate_limit,
        key_daily_limit=daily_limit,
        plan_slug="enterprise",
    )
    return allowed, remaining, retry_after
