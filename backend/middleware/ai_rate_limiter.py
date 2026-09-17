"""
AI Generate-Reply Rate Limiter
==============================
Sliding-window rate limiter scoped to the authenticated *user account*.

Limit: AI_REPLY_LIMIT requests per AI_REPLY_WINDOW_SECONDS  (default: 5 / hour)

Storage strategy (with graceful fallback):
  1. Redis  — atomic INCR + EXPIRE (survives restarts, shared across workers)
  2. In-memory deque — used automatically when Redis is unreachable

Returns standard rate-limit headers on every request so the frontend can
display remaining quota and reset time without an extra round-trip.
"""

import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from math import ceil
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
from config.settings import get_settings
from auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

# ── configuration ──────────────────────────────────────────────────────────────
REPLY_LIMIT: int = 5          # max requests
REPLY_WINDOW: int = 3600      # seconds (1 hour)
REDIS_KEY_PREFIX = "rl:ai_reply:"

# ── in-memory fallback ─────────────────────────────────────────────────────────
_mem_buckets: dict[str, deque] = defaultdict(deque)


# ── Redis helper (optional) ─────────────────────────────────────────────────────
def _get_redis():
    """Return a Redis client or None if unavailable."""
    try:
        import redis as redis_lib
        settings = get_settings()
        r = redis_lib.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
        r.ping()
        return r
    except Exception:
        return None


# ── sliding-window logic ────────────────────────────────────────────────────────
def _check_redis(r, key: str) -> tuple[bool, int, int]:
    """
    Atomic sliding-window check via a Redis sorted set.
    Returns (allowed, count_used, reset_ts).
    """
    now = time.time()
    window_start = now - REPLY_WINDOW
    reset_ts = ceil(now) + REPLY_WINDOW  # conservative upper bound

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)          # evict old entries
    pipe.zadd(key, {str(now): now})                           # record this attempt (always add first)
    pipe.zcard(key)                                           # count in window
    pipe.expire(key, REPLY_WINDOW + 60)                       # ttl cleanup
    results = pipe.execute()

    count = results[2]  # int from ZCARD
    if count > REPLY_LIMIT:
        # We already wrote; remove the entry we just added to be non-destructive
        pipe2 = r.pipeline()
        pipe2.zrem(key, str(now))
        pipe2.execute()
        # compute precise reset from oldest entry
        oldest = r.zrange(key, 0, 0, withscores=True)
        if oldest:
            reset_ts = ceil(oldest[0][1] + REPLY_WINDOW)
        return False, count - 1, reset_ts

    return True, count, reset_ts


def _check_memory(key: str) -> tuple[bool, int, int]:
    """
    Sliding-window check against the in-process deque.
    Returns (allowed, count_used, reset_ts).
    """
    now = time.time()
    bucket = _mem_buckets[key]
    # evict expired timestamps
    while bucket and bucket[0] <= now - REPLY_WINDOW:
        bucket.popleft()

    count = len(bucket)
    reset_ts = ceil(bucket[0] + REPLY_WINDOW) if bucket else ceil(now + REPLY_WINDOW)

    if count >= REPLY_LIMIT:
        return False, count, reset_ts

    bucket.append(now)
    return True, count + 1, reset_ts


# ── FastAPI dependency ──────────────────────────────────────────────────────────
def ai_reply_rate_limit(
    response: Response,
    current_user: dict = Depends(get_current_user),
):
    """
    Inject into the generate-reply endpoint with `Depends(ai_reply_rate_limit)`.
    Raises HTTP 429 when the user has exceeded their hourly quota.
    Always attaches X-RateLimit-* headers so the UI can show remaining quota.
    """
    user_id = current_user.get("user_id") or current_user.get("sub", "anon")
    key = f"{REDIS_KEY_PREFIX}{user_id}"

    redis = _get_redis()
    if redis:
        try:
            allowed, used, reset_ts = _check_redis(redis, key)
        except Exception as e:
            logger.warning(f"Redis rate-limit error, falling back to memory: {e}")
            allowed, used, reset_ts = _check_memory(key)
    else:
        allowed, used, reset_ts = _check_memory(key)

    remaining = max(REPLY_LIMIT - used, 0)
    reset_dt = datetime.fromtimestamp(reset_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Standard rate-limit headers (RFC 6585 style)
    response.headers["X-RateLimit-Limit"] = str(REPLY_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_ts)
    response.headers["X-RateLimit-Window"] = f"{REPLY_WINDOW}s"

    if not allowed:
        retry_after = max(reset_ts - int(time.time()), 1)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": (
                    f"You have used all {REPLY_LIMIT} AI reply generations allowed per hour. "
                    f"Your quota resets at {reset_dt} UTC."
                ),
                "limit": REPLY_LIMIT,
                "used": used,
                "remaining": 0,
                "reset_at": reset_dt,
                "retry_after_seconds": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(REPLY_LIMIT),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_ts),
            },
        )

    return {"used": used, "remaining": remaining, "reset_at": reset_dt}
