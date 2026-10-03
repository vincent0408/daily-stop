"""Base class every source inherits from."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

import httpx

from app.models import Item, SourceInfo


class Source(ABC):
    # --- Required: describe the source -------------------------------------
    id: ClassVar[str]               # unique, url-safe, e.g. "github"
    name: ClassVar[str]             # shown as the section title
    homepage: ClassVar[str]         # "Open site" link in the section header
    color: ClassVar[str] = "#5B6675"  # card accent colour

    # --- Optional knobs -----------------------------------------------------
    description: ClassVar[str] = ""
    order: ClassVar[int] = 100      # lower numbers appear first
    limit: ClassVar[int] = 15       # max cards kept per fetch
    ttl_seconds: ClassVar[int] = 30 * 60   # how long results are cached
    enabled: ClassVar[bool] = True

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[Item]:
        """Download and return items, best first. Raise on failure."""

    def info(self) -> SourceInfo:
        return SourceInfo(
            id=self.id,
            name=self.name,
            homepage=self.homepage,
            color=self.color,
            description=self.description,
        )
