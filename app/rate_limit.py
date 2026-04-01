"""
In-memory rate limiting for public endpoints.

Single-instance only. Move to Redis if scaling to multiple replicas.
"""

import math
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> int:
        """
        Check rate limit. Returns remaining requests.
        Raises HTTPException(429) if limit exceeded.
        """
        if limit <= 0:
            return 0
        now = time.time()
        with self._lock:
            bucket = self._buckets[key]
            cutoff = now - window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry = max(1, math.ceil((bucket[0] + window_seconds) - now))
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests",
                    headers={"Retry-After": str(retry)},
                )
            bucket.append(now)
            return max(0, limit - len(bucket))


_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    cf_ip = request.headers.get("CF-Connecting-IP", "")
    if cf_ip:
        return cf_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_chat(request: Request, client_id: str):
    """30 requests/minute per IP+client combo."""
    key = f"chat:{get_client_ip(request)}:{client_id}"
    _limiter.check(key, limit=30, window_seconds=60)


def rate_limit_callback(request: Request, client_id: str):
    """5 callback requests/minute per IP."""
    key = f"callback:{get_client_ip(request)}:{client_id}"
    _limiter.check(key, limit=5, window_seconds=60)
