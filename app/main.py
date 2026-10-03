"""Daily Stop — run with:  uvicorn app.main:app --reload"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.feed import FeedService, make_client
from app.models import SourceFeed, SourceInfo
from app.sources import all_sources, discover, get_source

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    discover()
    async with make_client() as client:
        app.state.feeds = FeedService(client)
        logging.getLogger("daily-stop").info(
            "Loaded sources: %s", ", ".join(s.id for s in all_sources()) or "none"
        )
        yield


app = FastAPI(title="Daily Stop", lifespan=lifespan)


@app.get("/api/sources", response_model=list[SourceInfo])
async def list_sources():
    return [s.info() for s in all_sources()]


@app.get("/api/feed", response_model=list[SourceFeed])
async def feed(refresh: bool = False):
    return await app.state.feeds.get_many(all_sources(), refresh)


@app.get("/api/feed/{source_id}", response_model=SourceFeed)
async def feed_one(source_id: str, refresh: bool = False):
    source = get_source(source_id)
    if not source:
        raise HTTPException(404, f"No source called {source_id!r}")
    return await app.state.feeds.get(source, refresh)


# The front end. Mounted last so /api routes win.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
