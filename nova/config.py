"""NOVA configuration: ~/.nova/config.json (created from config.example.json).

The NOVA workspace lives in the user's Termux home (private app storage):
  ~/.nova/           config, database, logs
  ~/.nova/exports/   CSV/JSON/TXT exports
"""
from __future__ import annotations

import json
import os

DEFAULTS = {
    "engine": "tbp",               # tbp | webdroid | file
    "webdroid_url": "http://localhost:8765",
    "tbp_binary": "tbp",
    "max_posts": 200,
    "max_scroll_seconds": 600,
    "idle_rounds": 5,              # stop after N rounds with no new links
    "scroll_pixels": 900,
    "scroll_wait_seconds": 2.5,    # polite wait between scrolls
}


def nova_home() -> str:
    home = os.environ.get("NOVA_HOME", os.path.expanduser("~/.nova"))
    os.makedirs(home, exist_ok=True)
    os.makedirs(os.path.join(home, "exports"), exist_ok=True)
    os.makedirs(os.path.join(home, "logs"), exist_ok=True)
    return home


def config_path() -> str:
    return os.path.join(nova_home(), "config.json")


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    path = config_path()
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                user_cfg = json.load(fh)
            if isinstance(user_cfg, dict):
                cfg.update(user_cfg)
        except (ValueError, OSError):
            pass  # a broken config falls back to defaults; diagnostics reports it
    return cfg


def db_path() -> str:
    return os.path.join(nova_home(), "nova.db")


def exports_dir() -> str:
    return os.path.join(nova_home(), "exports")
