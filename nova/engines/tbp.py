"""Termux Browser Pilot engine (PRIMARY).

Drives the real `tbp` CLI (github.com/salviz/termux-browser-pilot) as a
subprocess. Verified against TBP v0.17.1's CLI surface:
  tbp status | start | stop | goto URL | html | eval "JS" | scroll --amount N
All commands accept --json for structured output.

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
    def _run(self, *args: str, expect_json: bool = True):
        try:
            proc = subprocess.run(
                [self.binary, *args, "--json"] if expect_json else [self.binary, *args],
                capture_output=True, text=True, timeout=self.timeout,
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
        if proc.returncode != 0:
            raise EngineError(f"tbp {' '.join(args)} failed: {(proc.stderr or out)[:300]}")
        if not expect_json:
            return out
        try:
            return json.loads(out) if out else {}
        except ValueError:
            return {"raw": out}

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
            data = self._run("status")
        except EngineError:
            return False
        if isinstance(data, dict):
            return bool(data.get("running", data.get("status") == "running"))
        return False

    def navigate(self, url: str) -> None:
        self._run("goto", url)
        current = self.current_url()
        if "/login" in current or "checkpoint" in current:
            raise AuthRequiredError(
                f"Facebook is asking for login/verification ({current}). "
                "Log in manually in the browser window, then resume."
            )

    def current_url(self) -> str:
        data = self._run("eval", "window.location.href")
        if isinstance(data, dict):
            return str(data.get("result", data.get("value", "")))
        return str(data)

    def page_html(self) -> str:
        data = self._run("eval", "document.documentElement.outerHTML")
        if isinstance(data, dict):
            return str(data.get("result", data.get("value", "")))
        return str(data)

    def eval_js(self, expression: str):
        data = self._run("eval", expression)
        if isinstance(data, dict):
            return data.get("result", data.get("value"))
        return data

    def scroll_down(self, pixels: int = 800) -> None:
        self._run("scroll", "--down", "--amount", str(int(pixels)))

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
