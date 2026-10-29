# Compatibility matrix — researched 2026-10-29

All three referenced projects were cloned and inspected (source + docs), not
taken on faith. NOVA M3 v1.0.0 status:

| Project | What it actually is | Interface NOVA uses | Verdict |
|---|---|---|---|
| **Termux Browser Pilot** (salviz) v0.17.1 | Real browser automation for Termux: Firefox (default) or Chromium on Xvfb, persistent daemon, no root. Python CLI `tbp` with `--json` output, JS eval, page HTML, scrolling, tabs, persistent Firefox profile under `~/.tbp`. | Subprocess adapter over the documented CLI: `tbp status/start/stop/goto/html/eval/scroll` | **PRIMARY ENGINE.** Adapter implemented against the verified CLI surface. Needs an X display (Xvfb built in; view via Termux:X11/VNC). On-device run is the user's integration test — it was not device-tested by the author (no Android device in the build env). |
| **WebDroid** (takafu) | Android WebView browser app with a floating bubble UI and an HTTP API on `localhost:8765` (docs/API.md: `/ping /url /title /html /navigate /eval /execute`). | HTTP adapter (`nova/engines/webdroid.py`) implementing navigate, current URL, HTML, eval, JS scroll | **OPTIONAL / BETA.** Adapter is code-complete against the documented API. Blocker: the repo ships **no prebuilt APK** (checked: no GitHub releases) — you must build it with Gradle and install it yourself. Not device-tested. |
| **fbcli** (0xEnc0der) | Desktop-oriented Python CLI that injects **user-exported session cookies** into a headless Playwright Chromium and drives the Facebook UI (whoami/feed/post/comment/react/dm...). | — | **NOT INTEGRATED, deliberately.** (1) Its auth model requires exporting `c_user`/`xs` session cookies — NOVA's security policy never handles session tokens; login happens manually inside the engine's own browser instead. (2) Playwright Chromium is not a supported runtime on Termux/Android. Its command ideas (feed/timeline reading) are noted for a possible future, cookie-free engine feature. |

## REA (Reverse Engineer Anything)

REA is an analysis toolkit (binary/JS reverse engineering) installed separately
by the user. It provides **no** browser control and **no** Facebook session or
extraction capability, so NOVA does not pretend otherwise: see `docs/REA.md`
for the isolated, optional integration points.
