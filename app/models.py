"""Shared data shapes. Every source returns a list of `Item`."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Item(BaseModel):
    """One card on the page."""

    title: str
    url: str                                   # where clicking the card goes
    description: str | None = None
    metric: str | None = None                  # headline number, e.g. "1,204 stars today"
    details: list[str] = Field(default_factory=list)   # small facts: language, author, age...
    discussion_url: str | None = None          # optional secondary link (e.g. HN comments)
    discussion_label: str | None = None        # text for that link, e.g. "212 comments"


class SourceInfo(BaseModel):
    id: str
    name: str
    homepage: str
    color: str
    description: str = ""


class SourceFeed(BaseModel):
    source: SourceInfo
    items: list[Item] = Field(default_factory=list)
    fetched_at: datetime | None = None
    error: str | None = None
    stale: bool = False                        # True when showing cached items after a failed refresh
