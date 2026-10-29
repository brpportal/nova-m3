"""NOVA M3 — Termux Browser & Facebook Post Intelligence Agent.

Modular, honest tooling:
- Browser engines behind one adapter interface (Termux Browser Pilot primary,
  WebDroid optional, offline FileEngine for fixtures/tests).
- M1 visible-link extraction, M3 structured-data extraction, hybrid merge.
- URL validation, SQLite storage, CSV/JSON/TXT export.

NOVA never asks for a Facebook password, never reads or prints cookies or
tokens, and never bypasses login, CAPTCHA, MFA, or checkpoints. The user logs
in manually inside the browser engine's own browser window.
"""

__version__ = "1.0.3"
