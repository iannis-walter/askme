"""Tiny in-memory abuse protection, used as FastAPI dependencies.

Two layers:

  * `RateLimiter`  — sliding window per visitor (see `security.client_ip` for how
    a visitor is identified behind the front-end proxy).
  * `DailyBudget`  — one service-wide cap on LLM-backed requests per UTC day, so
    no amount of traffic can run the API bill past a known ceiling.

In-process and best-effort — exactly right for a single-instance free-tier
deploy. (Multi-instance would need a shared store like Redis; overkill here.)

Used via Depends so it composes cleanly with Pydantic request bodies — unlike a
decorator, it never interferes with FastAPI's signature introspection.

NB: no `from __future__ import annotations` here on purpose — FastAPI must see a
real `Request` annotation (not the stringized forward-ref) to special-case it
for this callable-instance dependency.
"""
import os
import time
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from typing import Deque, Dict, Optional

from fastapi import HTTPException, Request

from security import client_ip


class RateLimiter:
    """Sliding-window limiter: at most `limit` requests per `window_s` per visitor."""

    def __init__(self, limit: int, window_s: float):
        self.limit = limit
        self.window = window_s
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._last_sweep = time.monotonic()

    async def __call__(self, request: Request) -> None:
        ip = client_ip(request)
        now = time.monotonic()
        self._sweep(now)
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

    def _sweep(self, now: float) -> None:
        """Once per window, drop visitors with no recent hit so the table stays small."""
        if now - self._last_sweep < self.window:
            return
        self._last_sweep = now
        stale = [ip for ip, hits in self._hits.items() if not hits or now - hits[-1] > self.window]
        for ip in stale:
            del self._hits[ip]


def _today() -> date:
    return datetime.now(timezone.utc).date()


class DailyBudget:
    """Service-wide cap on LLM-backed requests per UTC day.

    `DAILY_REQUEST_BUDGET` sets the number of units; each endpoint charges what
    it roughly costs (`charge(1)` for a chat turn, more for multi-call routes).
    The count lives in memory, so a restart resets it — fine as a ceiling, and
    the provider-side spend limit remains the hard stop.
    """

    def __init__(self, default_limit: int = 1500):
        self._default = default_limit
        self._day: Optional[date] = None
        self._spent = 0

    @property
    def limit(self) -> int:
        try:
            return int(os.getenv("DAILY_REQUEST_BUDGET", "") or self._default)
        except ValueError:
            return self._default

    def charge(self, cost: int = 1):
        async def dependency() -> None:
            today = _today()
            if today != self._day:
                self._day, self._spent = today, 0
            if self._spent + cost > self.limit:
                raise HTTPException(
                    status_code=429,
                    detail="The assistant has reached its daily limit — please come back tomorrow.",
                )
            self._spent += cost

        return dependency
