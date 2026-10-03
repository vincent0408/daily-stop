"""Hacker News front page via the official Firebase API."""
from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

import httpx

from app.models import Item
from app.sources import register
from app.sources._util import ago
from app.sources.base import Source

API = "https://hacker-news.firebaseio.com/v0"


@register
class HackerNews(Source):
    id = "hackernews"
    name = "Hacker News"
    homepage = "https://news.ycombinator.com"
    color = "#FF6600"
    description = "Top stories on the front page"
    order = 20
    limit = 20
    ttl_seconds = 15 * 60

    scan = 40            # how many top stories to look at
    # Only keep stories whose title contains one of these words (case-insensitive).
    # Leave empty for the full front page. Example for an AI-only feed:
    # keywords = ("ai", "llm", "gpt", "claude", "model", "agent", "openai", "anthropic")
    keywords: tuple[str, ...] = ()

    def _matches(self, title: str) -> bool:
        words = "|".join(re.escape(k) for k in self.keywords)
        return re.search(rf"\b({words})\b", title, re.IGNORECASE) is not None

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        resp = await client.get(f"{API}/topstories.json")
        resp.raise_for_status()
        ids = resp.json()[: self.scan]

        async def one(story_id: int) -> dict | None:
            r = await client.get(f"{API}/item/{story_id}.json")
            return r.json() if r.status_code == 200 else None

        stories = await asyncio.gather(*(one(i) for i in ids), return_exceptions=True)

        items: list[Item] = []
        for s in stories:
            if not isinstance(s, dict) or s.get("type") != "story" or s.get("dead"):
                continue
            title = s.get("title", "")
            if self.keywords and not self._matches(title):
                continue
            hn_url = f"https://news.ycombinator.com/item?id={s['id']}"
            url = s.get("url") or hn_url
            domain = urlparse(url).netloc.removeprefix("www.") if s.get("url") else "news.ycombinator.com"
            details = [domain]
            if (when := ago(s.get("time"))):
                details.append(when)
            items.append(
                Item(
                    title=title,
                    url=url,
                    metric=f"{s.get('score', 0)} points",
                    details=details,
                    discussion_url=hn_url,
                    discussion_label=f"{s.get('descendants', 0)} comments",
                )
            )
        return items
