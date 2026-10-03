"""Small helpers shared by sources."""
from __future__ import annotations

import time


def compact(n: int | float | None) -> str:
    """12345 -> '12.3k'"""
    if n is None:
        return "0"
    n = float(n)
    for unit, size in (("M", 1_000_000), ("k", 1_000)):
        if abs(n) >= size:
            return f"{n / size:.1f}".rstrip("0").rstrip(".") + unit
    return f"{int(n)}"


def ago(unix_ts: int | float | None) -> str | None:
    if not unix_ts:
        return None
    secs = max(0, int(time.time() - unix_ts))
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{secs // size}{unit} ago"
    return "just now"


def clip(text: str | None, length: int = 240) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    return text if len(text) <= length else text[: length - 1].rsplit(" ", 1)[0] + "…"
