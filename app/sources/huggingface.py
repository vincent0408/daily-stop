"""Hugging Face: trending models and today's papers (public Hub API)."""
from __future__ import annotations

import httpx

from app.models import Item
from app.sources import register
from app.sources._util import clip, compact
from app.sources.base import Source


@register
class HFTrendingModels(Source):
    id = "hf-models"
    name = "Hugging Face Models"
    homepage = "https://huggingface.co/models?sort=trending"
    color = "#E8A400"
    description = "Models trending on the Hub"
    order = 30
    limit = 20

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        resp = await client.get(
            "https://huggingface.co/api/models",
            params={"sort": "trendingScore", "direction": -1, "limit": self.limit},
        )
        resp.raise_for_status()
        items: list[Item] = []
        for m in resp.json():
            model_id = m.get("id") or m.get("modelId")
            if not model_id:
                continue
            details = [d for d in (m.get("pipeline_tag"), m.get("library_name")) if d]
            details.append(f"{compact(m.get('downloads'))} downloads")
            items.append(
                Item(
                    title=model_id,
                    url=f"https://huggingface.co/{model_id}",
                    metric=f"{compact(m.get('likes'))} likes",
                    details=details,
                )
            )
        return items


@register
class HFDailyPapers(Source):
    id = "hf-papers"
    name = "Hugging Face Papers"
    homepage = "https://huggingface.co/papers"
    color = "#7C5CFA"
    description = "Today's most upvoted research papers"
    order = 40
    limit = 15

    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        resp = await client.get("https://huggingface.co/api/daily_papers", params={"limit": 40})
        resp.raise_for_status()
        rows = []
        for entry in resp.json():
            paper = entry.get("paper", entry)
            if paper.get("id"):
                rows.append(paper)
        rows.sort(key=lambda p: p.get("upvotes", 0), reverse=True)

        items: list[Item] = []
        for p in rows:
            authors = [a.get("name") for a in p.get("authors", []) if a.get("name")]
            details = []
            if authors:
                details.append(authors[0] + (" et al." if len(authors) > 1 else ""))
            details.append(f"arXiv {p['id']}")
            items.append(
                Item(
                    title=p.get("title", p["id"]),
                    url=f"https://huggingface.co/papers/{p['id']}",
                    description=clip(p.get("summary"), 220),
                    metric=f"{p.get('upvotes', 0)} upvotes",
                    details=details,
                )
            )
        return items
