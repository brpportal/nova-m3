"""Diagnostics: environment checks with actionable messages."""
from __future__ import annotations

import os
import platform
import shutil
import sqlite3
import sys

from .config import config_path, db_path, load_config, nova_home
from .engines.tbp import TbpEngine
from .engines.webdroid import WebDroidEngine


def run_diagnostics() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    checks.append(("Python >= 3.10", sys.version_info >= (3, 10),
                   f"python {platform.python_version()}"))
    in_termux = "com.termux" in os.environ.get("PREFIX", "") or \
        os.path.isdir("/data/data/com.termux")
    checks.append(("Running in Termux", in_termux,
                   "PREFIX=" + os.environ.get("PREFIX", "(unset)") +
                   ("" if in_termux else " — NOVA targets Termux on Android")))

    home = nova_home()
    checks.append(("NOVA workspace writable", os.access(home, os.W_OK), home))

    cfg_file = config_path()
    if os.path.isfile(cfg_file):
        try:
            import json
            with open(cfg_file, encoding="utf-8") as fh:
                json.load(fh)
            checks.append(("config.json valid", True, cfg_file))
        except ValueError as exc:
            checks.append(("config.json valid", False, f"{cfg_file}: {exc}"))
    else:
        checks.append(("config.json valid", True,
                       "no config file yet; defaults in use"))

    cfg = load_config()
    tbp_ok, tbp_reason = TbpEngine(cfg["tbp_binary"]).available()
    checks.append(("Termux Browser Pilot (tbp)", tbp_ok,
                   tbp_reason or shutil.which(cfg["tbp_binary"]) or ""))
    checks.append(("Firefox (TBP browser)", bool(shutil.which("firefox")),
                   shutil.which("firefox") or "pkg install firefox"))
    checks.append(("Xvfb (TBP display)", bool(shutil.which("Xvfb")),
                   shutil.which("Xvfb") or "pkg install xorg-server-xvfb"))

    wd_ok, wd_reason = WebDroidEngine(cfg["webdroid_url"]).available()
    checks.append(("WebDroid API (optional)", wd_ok,
                   wd_reason or cfg["webdroid_url"]))

    path = db_path()
    if os.path.isfile(path):
        try:
            conn = sqlite3.connect(path)
            count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            conn.close()
            checks.append(("SQLite database", True, f"{path} ({count} records)"))
        except sqlite3.Error as exc:
            checks.append(("SQLite database", False, f"{path}: {exc}"))
    else:
        checks.append(("SQLite database", True, "not created yet (first extract creates it)"))
    return checks


def format_diagnostics(checks: list[tuple[str, bool, str]]) -> str:
    lines = ["NOVA diagnostics:"]
    for name, ok, detail in checks:
        mark = "OK " if ok else "!! "
        lines.append(f"  [{mark}] {name}: {detail}")
    return "\n".join(lines)
