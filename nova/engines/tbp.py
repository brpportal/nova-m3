"""Termux Browser Pilot engine (PRIMARY).

Drives the real `tbp` CLI (github.com/salviz/termux-browser-pilot) as a
subprocess. Verified against TBP v0.17.1's source (cli.py + src/daemon.py):

- Every daemon-backed command answers `--json` with the daemon envelope:
      {"id": 1, "success": true,  "data": {...}}
      {"id": 1, "success": false, "error": "..."}
  Note: failures can arrive with process exit code 0, so the envelope's
  "success" flag — not the exit code — decides success.
- `tbp status` data: {"pid", "browser", "url", "title", "uptime"};
  with no daemon: {"success": false, "error": "No daemon running"}.
- `tbp eval` data: {"result": <value>}.

The user logs into Facebook manually in TBP's real Firefox window. TBP keeps
its own persistent profile under ~/.tbp (its documented storage); NOVA never
reads the cookie files — `session delete` only removes them on explicit
user request, after stopping the daemon.

NOVA deliberately does NOT use TBP's Cloudflare-bypass (-cf), stealth, geo
spoofing, user-agent spoofing or cookie-injection features: extraction runs
on the user's own visible, logged-in session only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

from .base import AuthRequiredError, BrowserEngine, EngineError

_TBP_DIR = os.path.expanduser("~/.tbp")


class TbpEngine(BrowserEngine):
    name = "tbp"

    def __init__(self, binary: str = "tbp", timeout: int = 60):
        self.binary = binary
        self.timeout = timeout

    # -- internals ---------------------------------------------------------
    def _run(self, *args: str, tbp_timeout: int | None = None) -> dict:
        """Run a tbp command, return the daemon envelope dict.

        `tbp_timeout` is forwarded as tbp's own --timeout (its client waits
        that long for the daemon; page loads on a phone can be slow, so
        navigation/content calls get minutes, not the 45s default).

        Raises EngineError on spawn failure, timeout, non-zero exit, or an
        envelope with success=false.
        """
        cmd = [self.binary, *args]
        if tbp_timeout:
            cmd += ["--timeout", str(tbp_timeout)]
        cmd.append("--json")
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=(tbp_timeout + 30) if tbp_timeout else self.timeout,
            )
        except FileNotFoundError:
            raise EngineError(
                "tbp command not found. Install Termux Browser Pilot first: "
                "bash setup.sh (NOVA installer sets it up), or see "
                "https://github.com/salviz/termux-browser-pilot"
            )
        except subprocess.TimeoutExpired:
            raise EngineError(f"tbp {' '.join(args)} timed out after {self.timeout}s")
        out = (proc.stdout or "").strip()
        envelope: dict = {}
        if out:
            try:
                parsed = json.loads(out)
                if isinstance(parsed, dict):
                    envelope = parsed
            except ValueError:
                envelope = {"raw": out}
        if isinstance(envelope, dict) and envelope.get("success") is False:
            raise EngineError(
                f"tbp {' '.join(args)}: {envelope.get('error', 'unknown error')}")
        if proc.returncode != 0 and not envelope:
            raise EngineError(
                f"tbp {' '.join(args)} failed: {(proc.stderr or out)[:300]}")
        return envelope

    @staticmethod
    def _data(envelope: dict) -> dict:
        data = envelope.get("data")
        return data if isinstance(data, dict) else {}

    # -- interface ----------------------------------------------------------
    def available(self) -> tuple[bool, str]:
        path = shutil.which(self.binary)
        if not path:
            return False, ("Termux Browser Pilot (tbp) not found on PATH. "
                           "Run NOVA's setup.sh, which installs it.")
        return True, ""

    def start(self) -> None:
        self._run("start")

    def stop(self) -> None:
        self._run("stop")

    def is_running(self) -> bool:
        try:
            envelope = self._run("status")
        except EngineError:
            return False
        return envelope.get("success") is True

    def status_data(self) -> dict:
        """Raw TBP status data (pid, browser, url, title, uptime)."""
        return self._data(self._run("status"))

    def navigate(self, url: str) -> str | None:
        """Navigate; returns a warning string if the goto command itself
        timed out but the page demonstrably loaded anyway (the tbp client
        gives up waiting before a slow phone browser finishes, while the
        navigation continues in the browser). Raises on real failures."""
        warning = None
        try:
            self._run("goto", url, tbp_timeout=180)
        except EngineError as exc:
            current = ""
            try:
                current = str(self.status_data().get("url", ""))
            except EngineError:
                pass
            target_hint = url.rstrip("/").rsplit("/", 1)[-1]
            if current and target_hint and target_hint in current:
                warning = (f"goto command timed out ({exc}) but the browser "
                           f"is on {current} — continuing")
            else:
                raise
        current = self.current_url()
        if "/login" in current or "checkpoint" in current:
            raise AuthRequiredError(
                f"Facebook is asking for login/verification ({current}). "
                "Log in manually in the browser window, then resume."
            )
        return warning

    def current_url(self) -> str:
        data = self._data(self._run("eval", "window.location.href"))
        if data.get("result"):
            return str(data["result"])
        return str(self.status_data().get("url", ""))

    def page_html(self) -> str:
        # Prefer tbp's dedicated html command; fall back to a raw eval.
        data = self._data(self._run("html", tbp_timeout=180))
        html = data.get("html")
        if html:
            return str(html)
        data = self._data(self._run(
            "eval", "document.documentElement.outerHTML", tbp_timeout=180))
        return str(data.get("result", ""))

    def eval_js(self, expression: str):
        return self._data(self._run("eval", expression, tbp_timeout=120)).get("result")

    def scroll_down(self, pixels: int = 800) -> None:
        self._run("scroll", "--down", "--amount", str(int(pixels)),
                  tbp_timeout=60)

    def session_storage_hint(self) -> str:
        return ("TBP keeps its Firefox profile and auto-saved cookies under "
                "~/.tbp (its own documented storage). NOVA never reads them. "
                "'nova session delete' stops TBP and removes "
                "~/.tbp/firefox_profile and ~/.tbp/auto_cookies.json.")

    def delete_session_data(self) -> list[str]:
        """Explicit user-requested logout: stop daemon + delete TBP profile."""
        removed = []
        try:
            self.stop()
        except EngineError:
            pass
        for path in (os.path.join(_TBP_DIR, "firefox_profile"),
                     os.path.join(_TBP_DIR, "auto_cookies.json")):
            if os.path.isdir(path):
                shutil.rmtree(path)
                removed.append(path)
            elif os.path.isfile(path):
                os.remove(path)
                removed.append(path)
        return removed
