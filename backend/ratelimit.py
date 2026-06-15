"""Tiny in-memory per-IP rate limiter, used as a FastAPI dependency.

In-process and best-effort — exactly right for a single-instance free-tier
deploy. (Multi-instance would need a shared store like Redis; overkill here.)

Used via Depends so it composes cleanly with Pydantic request bodies — unlike a
decorator, it never interferes with FastAPI's signature introspection.

NB: no `from __future__ import annotations` here on purpose — FastAPI must see a
real `Request` annotation (not the stringized forward-ref) to special-case it
for this callable-instance dependency.
"""
import time
from collections import defaultdict, deque
from typing import Dict, Deque

from fastapi import HTTPException, Request


class RateLimiter:
    """Sliding-window limiter: at most `limit` requests per `window_s` per IP."""

    def __init__(self, limit: int, window_s: float):
        self.limit = limit
        self.window = window_s
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    async def __call__(self, request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits[ip]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            retry_after = int(self.window - (now - hits[0])) + 1
            raise HTTPException(
                status_code=429,
                detail="Too many requests — please slow down a moment.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        # Opportunistic cleanup so idle IPs don't accumulate forever.
        if not hits:
            self._hits.pop(ip, None)
