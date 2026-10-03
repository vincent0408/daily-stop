"""Fetch every source once and write static/data/feed.json.

Used by the GitHub Actions workflow to publish a static site to GitHub Pages.
You can also run it locally:  python build.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.feed import FeedService, make_client
from app.sources import all_sources, discover

OUT = Path(__file__).resolve().parent / "static" / "data" / "feed.json"


def workflow_file() -> str:
    # e.g. "you/daily-stop/.github/workflows/refresh.yml@refs/heads/main"
    ref = os.getenv("GITHUB_WORKFLOW_REF", "")
    match = re.search(r"/workflows/([^@]+)@", ref)
    return match.group(1) if match else "refresh.yml"


async def main() -> int:
    discover()
    sources = all_sources()
    async with make_client() as client:
        feeds = await FeedService(client).get_many(sources, refresh=True)

    for f in feeds:
        print(f"{f.source.id:<12} {len(f.items):>3} items  {f.error or ''}")

    if not any(f.items for f in feeds):
        print("Every source failed, so the previous site stays live.", file=sys.stderr)
        return 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": os.getenv("GITHUB_REPOSITORY"),      # lets the page's refresh button find the workflow
        "ref": os.getenv("GITHUB_REF_NAME", "main"),
        "workflow": workflow_file(),
        "feeds": [f.model_dump(mode="json") for f in feeds],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
