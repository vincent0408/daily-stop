"""GitHub Trending (scraped — GitHub has no official trending API)."""
from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from app.models import Item
from app.sources import register
from app.sources._util import clip
from app.sources.base import Source


def _num(text: str | None) -> int:
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else 0


@register
class GitHubTrending(Source):
    id = "github"
    name = "GitHub Trending"
    homepage = "https://github.com/trending"
    color = "#2DA44E"
    description = "Repos gaining the most stars today"
    order = 10
    limit = 20

    since = "daily"      # "daily" | "weekly" | "monthly"
    language = ""        # e.g. "python" to narrow it down

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        path = f"/{self.language}" if self.language else ""
        resp = await client.get(f"https://github.com/trending{path}", params={"since": self.since})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items: list[Item] = []
        for row in soup.select("article.Box-row"):
            link = row.select_one("h2 a")
            if not link or not link.get("href"):
                continue
            repo = link["href"].strip("/")
            desc = row.select_one("p")
            lang = row.select_one('[itemprop="programmingLanguage"]')
            stars = row.select_one('a[href$="/stargazers"]')
            gained = row.select_one("span.float-sm-right")

            details = []
            if lang:
                details.append(lang.get_text(strip=True))
            if stars:
                details.append(f"{_num(stars.get_text()):,} total stars")

            items.append(
                Item(
                    title=repo.replace("/", " / "),
                    url=f"https://github.com/{repo}",
                    description=clip(desc.get_text() if desc else None),
                    metric=f"+{_num(gained.get_text()):,} stars" if gained else None,
                    details=details,
                )
            )
        if not items:
            raise RuntimeError("GitHub page layout changed — no repos found")
        return items
