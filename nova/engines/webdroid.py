"""WebDroid engine (OPTIONAL backend).

WebDroid (github.com/takafu/webdroid) is an Android WebView browser app with
an HTTP API on http://localhost:8765 (verified from its docs/API.md):
  GET  /ping /url /title /html
  POST /navigate {"url": ...}   POST /eval (JavaScript, returns result)

Limitations, honestly: the WebDroid repo ships NO prebuilt APK — the user
must build it (Gradle) and install it themselves. Login happens manually in
WebDroid's visible browser window; its session lives in the app's own
WebView storage. This adapter is code-complete against the documented API
but has NOT been device-tested by the NOVA author (no Android device in the
build environment); treat it as beta.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import AuthRequiredError, BrowserEngine, EngineError


class WebDroidEngine(BrowserEngine):
    name = "webdroid"

    def __init__(self, base_url: str = "http://localhost:8765", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _call(self, method: str, path: str, payload: dict | None = None):
        data = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.base_url + path, data=data,
                                     headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError) as exc:
            raise EngineError(
                f"WebDroid API unreachable at {self.base_url} ({exc}). "
                "Is the WebDroid app installed, running, and its HTTP server on?"
            )
        try:
            parsed = json.loads(body)
        except ValueError:
            return {"raw": body}
        if isinstance(parsed, dict) and parsed.get("success") is False:
            raise EngineError(f"WebDroid error: {parsed.get('error', 'unknown')}")
        return parsed

    def available(self) -> tuple[bool, str]:
        try:
            self._call("GET", "/ping")
            return True, ""
        except EngineError as exc:
            return False, str(exc)

    def start(self) -> None:
        ok, reason = self.available()
        if not ok:
            raise EngineError(
                "WebDroid is an Android app, not a daemon NOVA can start. "
                "Open the WebDroid app on the phone first. " + reason
            )

    def stop(self) -> None:
        # No documented stop endpoint; the user closes the app.
        pass

    def is_running(self) -> bool:
        ok, _ = self.available()
        return ok

    def navigate(self, url: str) -> None:
        self._call("POST", "/navigate", {"url": url})
        current = self.current_url()
        if "/login" in current or "checkpoint" in current:
            raise AuthRequiredError(
                f"Facebook is asking for login/verification ({current}). "
                "Log in manually in the WebDroid window, then resume."
            )

    def current_url(self) -> str:
        data = self._call("GET", "/url")
        return str(data.get("url", "")) if isinstance(data, dict) else ""

    def page_html(self) -> str:
        data = self._call("GET", "/html")
        if isinstance(data, dict):
            return str(data.get("html", data.get("raw", "")))
        return ""

    def eval_js(self, expression: str):
        data = self._call("POST", "/eval", {"script": expression})
        if isinstance(data, dict):
            return data.get("result", data.get("value"))
        return data

    def scroll_down(self, pixels: int = 800) -> None:
        # No dedicated scroll endpoint in the documented API; use JS eval.
        self._call("POST", "/execute",
                   {"script": f"window.scrollBy(0, {int(pixels)})"})

    def session_storage_hint(self) -> str:
        return ("WebDroid keeps its session inside the WebDroid app's own "
                "WebView storage. Log out from inside the app, or clear the "
                "app's data in Android Settings, to delete it.")
