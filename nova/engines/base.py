"""Common browser-engine adapter interface for NOVA M3.

Every engine (Termux Browser Pilot, WebDroid, offline FileEngine) implements
this interface so extraction code never depends on one backend. Engines
control a browser the USER logs into manually; no engine reads, stores, or
prints cookies, tokens, or passwords.
"""
from __future__ import annotations

import abc


class EngineError(Exception):
    """A browser-control operation failed; message must be actionable."""


class AuthRequiredError(EngineError):
    """Login, verification, or a checkpoint blocks the task. User resolves it
    manually in the browser; NOVA never tries to bypass it."""


class BrowserEngine(abc.ABC):
    name = "base"

    @abc.abstractmethod
    def available(self) -> tuple[bool, str]:
        """(True, '') if usable, else (False, exact reason + install hint)."""

    @abc.abstractmethod
    def start(self) -> None:
        """Start or attach to the browser."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the browser/daemon (session data stays in the engine's own
        private storage unless the user explicitly deletes it)."""

    @abc.abstractmethod
    def is_running(self) -> bool:
        ...

    @abc.abstractmethod
    def navigate(self, url: str) -> None:
        ...

    @abc.abstractmethod
    def current_url(self) -> str:
        ...

    @abc.abstractmethod
    def page_html(self) -> str:
        ...

    @abc.abstractmethod
    def eval_js(self, expression: str):
        """Evaluate JS in the page and return its JSON-serializable result."""

    @abc.abstractmethod
    def scroll_down(self, pixels: int = 800) -> None:
        ...

    def session_storage_hint(self) -> str:
        """Human-readable note about where this engine keeps its own session
        data and how the user deletes it. Never returns secret material."""
        return "Session data is managed by the browser engine itself."
