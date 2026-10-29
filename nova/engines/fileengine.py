"""FileEngine — offline engine over saved page HTML.

Powers `nova extract --file page.html`, the unit tests, and fixture-based
verification with NO browser and NO Facebook login. Scrolling is simulated:
each scroll_down() advances to the next supplied HTML snapshot (if several
files were given), otherwise returns the same page (which correctly trips
the scroller's "no new content" stopping condition).
"""
from __future__ import annotations

from .base import BrowserEngine


class FileEngine(BrowserEngine):
    name = "file"

    def __init__(self, html_pages: list[str], url: str = "https://www.facebook.com/offline-fixture"):
        if not html_pages:
            raise ValueError("FileEngine needs at least one HTML page")
        self._pages = html_pages
        self._idx = 0
        self._url = url
        self._running = False

    def available(self) -> tuple[bool, str]:
        return True, ""

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def navigate(self, url: str) -> None:
        self._url = url

    def current_url(self) -> str:
        return self._url

    def page_html(self) -> str:
        return self._pages[min(self._idx, len(self._pages) - 1)]

    def eval_js(self, expression: str):
        # Offline: the session probe in session.py treats location queries.
        if "location.href" in expression:
            return self._url
        return None

    def scroll_down(self, pixels: int = 800) -> None:
        if self._idx < len(self._pages) - 1:
            self._idx += 1
