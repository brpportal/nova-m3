"""Session manager: detect login state WITHOUT touching credentials.

States: LOGGED_IN, LOGIN_REQUIRED, CHECKPOINT, NOT_RUNNING, UNKNOWN.
Detection is heuristic by necessity (Facebook's DOM changes often), so
UNKNOWN is an honest possible answer; NOVA pauses instead of guessing.
Nothing here reads cookies or storage values.
"""
from __future__ import annotations

from .engines.base import BrowserEngine

LOGGED_IN = "LOGGED_IN"
LOGIN_REQUIRED = "LOGIN_REQUIRED"
CHECKPOINT = "CHECKPOINT"
NOT_RUNNING = "NOT_RUNNING"
UNKNOWN = "UNKNOWN"

_PROBE_JS = """
(function () {
  var href = window.location.href;
  var hasLoginForm = !!document.querySelector('form[action*=\"login\"], input[name=\"email\"], input[name=\"pass\"]');
  var hasAccountUI = !!document.querySelector('a[href*=\"/me/\"], a[href*=\"profile.php?id=\"], [aria-label=\"Account\"], [data-testid=\"account-menu\"]');
  return JSON.stringify({href: href, loginForm: hasLoginForm, accountUI: hasAccountUI});
})()
"""


def check_session(engine: BrowserEngine) -> tuple[str, str]:
    """Return (state, detail). Never raises for auth problems."""
    import json

    if not engine.is_running():
        return NOT_RUNNING, "browser engine is not running"
    try:
        url = engine.current_url()
    except Exception as exc:  # engine-level diagnostics, not auth
        return UNKNOWN, f"could not read current URL: {exc}"
    if "checkpoint" in url:
        return CHECKPOINT, f"Facebook checkpoint page: {url}"
    if "/login" in url:
        return LOGIN_REQUIRED, f"Facebook login page: {url}"
    try:
        raw = engine.eval_js(_PROBE_JS)
    except Exception:
        return UNKNOWN, "page probe failed; cannot confirm login state"
    probe = {}
    if isinstance(raw, str):
        try:
            probe = json.loads(raw)
        except ValueError:
            probe = {}
    elif isinstance(raw, dict):
        probe = raw
    href = str(probe.get("href", url))
    if "checkpoint" in href:
        return CHECKPOINT, f"Facebook checkpoint page: {href}"
    if probe.get("loginForm") and not probe.get("accountUI"):
        return LOGIN_REQUIRED, "login form visible; not logged in"
    if probe.get("accountUI"):
        return LOGGED_IN, "account UI visible in the page"
    if "facebook.com" in href:
        return UNKNOWN, ("on a Facebook page but login markers are unclear; "
                         "if you can see your account UI, you are logged in")
    return UNKNOWN, f"current page is not Facebook: {href}"
