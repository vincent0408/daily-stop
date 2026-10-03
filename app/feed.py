"""Fetches sources concurrently with a per-source cache.

A failing source never breaks the page: it returns its last good items
(marked stale) or an error message for that one section.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

import httpx

from app.models import SourceFeed
from app.sources.base import Source

log = logging.getLogger(__name__)
FETCH_TIMEOUT = 25  # seconds per source


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers={"User-Agent": "daily-stop/1.0 (personal news dashboard)"},
        limits=httpx.Limits(max_connections=30),
    )


class FeedService:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self._cache: dict[str, tuple[float, SourceFeed]] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def get(self, source: Source, refresh: bool = False) -> SourceFeed:
        async with self._locks[source.id]:  # avoids duplicate fetches on parallel requests
            cached = self._cache.get(source.id)
            if cached and not refresh and time.monotonic() - cached[0] < source.ttl_seconds:
                return cached[1]
            try:
                items = await asyncio.wait_for(source.fetch(self.client), FETCH_TIMEOUT)
            except Exception as exc:
                log.warning("Source %s failed: %r", source.id, exc)
                message = _describe(exc)
                if cached:
                    return cached[1].model_copy(update={"error": message, "stale": True})
                return SourceFeed(source=source.info(), error=message)

            feed = SourceFeed(
                source=source.info(),
                items=items[: source.limit],
                fetched_at=datetime.now(timezone.utc),
            )
            self._cache[source.id] = (time.monotonic(), feed)
            return feed

    async def get_many(self, sources: list[Source], refresh: bool = False) -> list[SourceFeed]:
        return list(await asyncio.gather(*(self.get(s, refresh) for s in sources)))


def _describe(exc: Exception) -> str:
    if isinstance(exc, asyncio.TimeoutError):
        return f"Timed out after {FETCH_TIMEOUT}s."
    if isinstance(exc, httpx.HTTPStatusError):
        return f"The site answered with HTTP {exc.response.status_code}."
    if isinstance(exc, httpx.RequestError):
        return "Couldn't reach the site. Check your connection."
    return str(exc) or exc.__class__.__name__
