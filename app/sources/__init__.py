"""Source registry.

Any module in this package (except base.py and files starting with "_")
is imported automatically. Decorate a Source subclass with @register and
it shows up on the page — no other wiring needed.
"""
from __future__ import annotations

import importlib
import logging
import os
import pkgutil

from app.sources.base import Source

log = logging.getLogger(__name__)
_REGISTRY: dict[str, Source] = {}


def register(cls: type[Source]) -> type[Source]:
    if cls.id in _REGISTRY:
        raise ValueError(f"Duplicate source id: {cls.id!r}")
    _REGISTRY[cls.id] = cls()
    return cls


def discover() -> None:
    for mod in pkgutil.iter_modules(__path__):
        if mod.name == "base" or mod.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"{__name__}.{mod.name}")
        except Exception:  # one broken source must not take down the app
            log.exception("Could not load source module %s", mod.name)


def all_sources() -> list[Source]:
    """Enabled sources, sorted by `order`.

    Set DAILY_STOP_SOURCES=github,hackernews to show only those ids.
    """
    only = {s.strip() for s in os.getenv("DAILY_STOP_SOURCES", "").split(",") if s.strip()}
    sources = [s for s in _REGISTRY.values() if s.enabled and (not only or s.id in only)]
    return sorted(sources, key=lambda s: (s.order, s.name))


def get_source(source_id: str) -> Source | None:
    src = _REGISTRY.get(source_id)
    return src if src in all_sources() else None
