import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config.settings import get_settings

# In-memory fallback when Redis is unavailable.
_buckets: dict[str, deque] = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter for auth and AI endpoints."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = get_settings().rate_limit_requests_per_minute or requests_per_minute
        self.window_seconds = 60
        self.protected_prefixes = ("/auth/", "/google/", "/email/", "/api/v1/ai/", "/tasks/")

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _allow(self, key: str) -> bool:
        now = time.time()
        bucket = _buckets[key]
        while bucket and bucket[0] <= now - self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.requests_per_minute:
            return False
        bucket.append(now)
        return True

    async def dispatch(self, request: Request, call_next):
        if get_settings().environment == "development":
            return await call_next(request)

        path = request.url.path
        if not any(path.startswith(prefix) for prefix in self.protected_prefixes):
            return await call_next(request)

        key = f"{self._client_key(request)}:{path}"
        if not self._allow(key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again shortly."},
            )
        return await call_next(request)
