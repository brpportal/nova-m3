# NOVA M3 — Advanced Termux Browser & Facebook Post Intelligence Agent

A modular, production-oriented tool that runs on Android through **Termux**:
it operates a real browser session **you log into manually**, inspects
accessible Facebook pages, extracts post/photo/video permalinks (M1 visible
links + M3 structured data + hybrid), validates and deduplicates them, and
exports structured data (SQLite → CSV / JSON / TXT).

**Honesty first:** NOVA never asks for your Facebook password, never reads or
prints cookies/tokens, never bypasses CAPTCHA/MFA/checkpoints, and never
fabricates results. What is tested and what is not is listed at the bottom.

---

## Install (Android Termux)

Prerequisite: Termux installed on the phone (F-Droid or GitHub build).

```bash
pkg update && pkg install -y git
git clone https://github.com/brpportal/nova-m3.git
cd nova-m3
bash setup.sh
```

`setup.sh` checks the environment, installs the primary browser engine
(**Termux Browser Pilot**, via its own installer: Firefox + Xvfb + tools),
creates the private workspace `~/.nova`, installs the `nova` command, and
runs a self-test (unit tests + an offline extraction that must store 7
records from the bundled fixture).

## Quick start

```bash
nova browser open        # opens TBP's Firefox window (view via Termux:X11 / VNC)
                         # → log into YOUR Facebook account manually in that window
nova session status      # expect: LOGGED_IN
nova extract --mode hybrid --url https://www.facebook.com/<page-or-profile-or-group>
nova export --format txt # → ~/.nova/exports/nova-export-<time>.txt
```

## Commands

| Command | What it does |
|---|---|
| `nova status` | Engine availability, browser state, session state, record count |
| `nova browser open` / `nova stop` | Start / stop the browser engine |
| `nova session status` | Detect login state (LOGGED_IN / LOGIN_REQUIRED / CHECKPOINT / UNKNOWN) |
| `nova session delete` | Log out: stop TBP + delete its own session files under `~/.tbp` (asks you to type DELETE) |
| `nova extract --mode m1\|m3\|hybrid` | Collect from the current page, scrolling until a stop condition |
| `nova extract --file page.html` | Offline extraction from a saved page (no browser, no login) |
| `nova export --format csv\|json\|txt` | Export stored records to `~/.nova/exports/` |
| `nova logs [--tail N]` | Recent log lines (URLs/counts/states only — never secrets) |
| `nova diagnose` | Environment checks with actionable fixes |
| `nova` | Interactive mode: natural-language tasks (type `help`) |

Interactive examples:

```
open https://www.facebook.com/SomePage and collect up to 200 post links
extract links from the current page using m1 and m3, then merge
continue scrolling until 5 attempts produce no new links
export unique links into a txt file
```

Before a live extraction starts, NOVA prints the target page, mode, limit and
database path, and pauses if Facebook asks for login or verification.

## How it works

- **Engines** (`nova/engines/`) — one adapter interface, three backends:
  **TBP** (primary; drives the real `tbp` CLI), **WebDroid** (optional;
  HTTP API on `localhost:8765`), **FileEngine** (offline fixtures/tests).
  Adding an engine never touches extraction code.
- **M1** (`nova/extract/m1.py`) — mines rendered anchor links; keeps only
  post/photo/video URLs; profile, comment, navigation and external links are
  counted as skipped, never stored as posts.
- **M3** (`nova/extract/m3.py`) — parses embedded JSON with a real JSON
  parser; prefers a genuine `permalink_url`; constructs a URL **only** from
  the verified `{owner_id}/posts/{story_fbid}` format on post-like objects;
  bare numeric IDs (users, comments) are rejected and counted.
- **URL engine** (`nova/extract/urls.py`) — Facebook-host allowlist, tracking
  parameter removal that preserves destinations, classification
  (post/photo/video), and validation states: `VALID_FORMAT`, `DUPLICATE`,
  `INVALID_URL`, `UNVERIFIED_DESTINATION`, `ACCESS_RESTRICTED`,
  `VERIFIED_ACCESSIBLE`. A well-formed URL is never claimed to be accessible
  without an actual check.
- **Scroller** (`nova/scroller.py`) — collect → dedupe → scroll loop with
  stopping conditions: max posts, max duration, N idle rounds, auth walls,
  Ctrl-C. Default scroll wait is a polite 2.5 s.
- **Storage** — SQLite at `~/.nova/nova.db`: source page, post URL, object
  type/id, method, confidence, validation state, first/last seen. No
  credentials or session data, ever.

Configuration: `~/.nova/config.json` (see `config.example.json`) — engine,
limits, idle rounds, scroll distance/wait.

## Docs

- [Compatibility matrix](docs/COMPATIBILITY.md) — Browser Pilot vs fbcli vs WebDroid, researched from source
- [Security notes](docs/SECURITY.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [REA integration scope](docs/REA.md)

## Tests

```bash
python3 -m unittest discover -s tests
```

35 unit tests over sanitized fixtures (no Facebook login needed): URL
normalization/classification, invalid-ID rejection, M1, M3, hybrid merge,
duplicate detection, exports, scroll stopping conditions, session states.

## Tested / not tested — the honest list

✅ **Verified by the author (Linux VM, 2026-10-29):** all 35 unit tests pass;
full offline pipeline (`extract --file` → SQLite → TXT export) works;
`nova diagnose` reports accurately; TBP/WebDroid/fbcli interfaces above were
read from their actual source and docs at the pinned versions.

⚠️ **Not device-tested (no Android device in the build environment):** the
live TBP run on a phone (Firefox on Xvfb + manual Facebook login + live
extraction) and the WebDroid adapter against a running WebDroid app. These
are the manual integration tests: follow *Quick start* and report issues
with `nova logs` output.

## Unsupported / deliberately not included

- No Facebook password login (manual login only), no cookie import/export.
- **fbcli is not integrated** — it needs exported session cookies and
  Playwright, which conflict with this project's security policy and with
  Termux. See the compatibility matrix.
- WebDroid has **no prebuilt APK upstream**; you must build it yourself to
  use that backend.
- No CAPTCHA/MFA/checkpoint bypass, no stealth/spoofing features, no
  rate-limit evasion, no private-content access beyond what your own
  logged-in account can already see.
- `VERIFIED_ACCESSIBLE` link checking (actually opening each post) is a
  state the validator supports but v1.0 does not perform automatically —
  format validation and accessibility are kept separate by design.
- REA: no adapter ships in v1.0 (REA provides no browser/session capability);
  documented integration points only.

## Uninstall

```bash
bash uninstall.sh   # removes the nova command; asks before deleting data/session
```

License: MIT
