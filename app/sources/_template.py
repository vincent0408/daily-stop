"""Copy this file to add a new source.

1. cp app/sources/_template.py app/sources/my_source.py   (no leading underscore!)
2. Fill in the class below.
3. Restart the server. The new section appears automatically.
"""
from __future__ import annotations

import httpx

from app.models import Item
from app.sources import register
from app.sources.base import Source


@register
class MySource(Source):
    id = "my-source"                       # unique, url-safe
    name = "My Source"                     # section title
    homepage = "https://example.com"
    color = "#3B82F6"                      # card accent
    description = "What this feed shows"
    order = 50                             # position on the page

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        resp = await client.get("https://example.com/api/top.json")
        resp.raise_for_status()
        return [
            Item(
                title=row["title"],
                url=row["link"],
                description=row.get("summary"),
                metric=f"{row.get('score', 0)} points",
                details=[row.get("author", "")],
            )
            for row in resp.json()
        ]
