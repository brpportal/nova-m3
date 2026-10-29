"""Scroll-and-collect engine.

Loop: read page -> extract (m1/m3/hybrid) -> validate/dedupe/store ->
scroll -> wait -> repeat, until a stopping condition fires:
  - maximum posts reached
  - maximum scroll duration reached
  - N consecutive rounds with no new content
  - login/checkpoint encountered (AuthRequiredError or session state)
  - user stops (KeyboardInterrupt handled by the CLI)

The wait between scrolls is deliberate and configurable: NOVA uses polite,
human-paced collection, never aggressive request rates.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .engines.base import AuthRequiredError, BrowserEngine
from .extract.hybrid import extract_hybrid
from .extract.m1 import extract_m1
from .extract.m3 import extract_m3
from .extract.urls import VALID_FORMAT
from .store import Store


@dataclass
class CollectResult:
    stored_new: int = 0
    duplicates: int = 0
    rejected: int = 0
    rounds: int = 0
    stop_reason: str = ""
    extract_stats: dict = field(default_factory=dict)


def _extract(mode: str, html: str, page_url: str):
    if mode == "m1":
        results, stats = extract_m1(html, page_url)
        return results, {"m1": stats}
    if mode == "m3":
        results, stats = extract_m3(html, page_url)
        return results, {"m3": stats}
    return extract_hybrid(html, page_url)


def collect(engine: BrowserEngine, store: Store, *, mode: str = "hybrid",
            max_posts: int = 200, max_seconds: int = 600, idle_rounds: int = 5,
            scroll_pixels: int = 900, wait_seconds: float = 2.5,
            progress=None, sleep=time.sleep, clock=time.monotonic) -> CollectResult:
    """Run the collection loop against a live engine. `progress` is an
    optional callable receiving (round, new_total, duplicates, rejected)."""
    result = CollectResult()
    started = clock()
    idle = 0
    while True:
        result.rounds += 1
        try:
            html = engine.page_html()
            page_url = engine.current_url()
        except AuthRequiredError as exc:
            result.stop_reason = f"auth: {exc}"
            break
        candidates, stats = _extract(mode, html, page_url)
        result.extract_stats = stats
        new_this_round = 0
        for cand in candidates:
            if cand.validation_status != VALID_FORMAT:
                result.rejected += 1
                continue
            if store.upsert(cand):
                result.stored_new += 1
                new_this_round += 1
                if result.stored_new >= max_posts:
                    result.stop_reason = f"max posts reached ({max_posts})"
                    if progress:
                        progress(result.rounds, result.stored_new,
                                 result.duplicates, result.rejected)
                    return result
            else:
                result.duplicates += 1
        if progress:
            progress(result.rounds, result.stored_new, result.duplicates,
                     result.rejected)
        if result.stored_new >= max_posts:
            result.stop_reason = f"max posts reached ({max_posts})"
            break
        if clock() - started >= max_seconds:
            result.stop_reason = f"max scroll duration reached ({max_seconds}s)"
            break
        if new_this_round == 0:
            idle += 1
            if idle >= idle_rounds:
                result.stop_reason = f"no new content after {idle_rounds} rounds"
                break
        else:
            idle = 0
        try:
            engine.scroll_down(scroll_pixels)
        except AuthRequiredError as exc:
            result.stop_reason = f"auth: {exc}"
            break
        sleep(wait_seconds)
    return result
