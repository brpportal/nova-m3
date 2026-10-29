# Troubleshooting

Run `nova diagnose` first — it checks Python, Termux, the workspace, config,
both engines, Firefox/Xvfb, and the database, with the exact fix for each
failure.

| Symptom | Cause / fix |
|---|---|
| `tbp command not found` | Termux Browser Pilot not installed. Re-run `bash setup.sh`, or install TBP manually from its repo. |
| Browser starts but you see no window | TBP runs Firefox on Xvfb. View it with the Termux:X11 app (DISPLAY=:0) or a VNC viewer — see TBP's README for display options. |
| `session status` says LOGIN_REQUIRED | Open the browser (`nova browser open`) and log into Facebook manually in the window. NOVA cannot and will not log in for you. |
| Extraction stops with "auth: … checkpoint" | Facebook wants a verification step. Resolve it manually in the browser window, then re-run extract. |
| M3 returns 0 candidates but M1 works | Facebook changed its embedded-JSON shape. This is expected over time: hybrid mode keeps M1 results, and `extract_stats` in the logs show M3's rejected counts. |
| Everything extracts but all are "duplicates" | Those posts are already in `~/.nova/nova.db` from an earlier run. Exports always reflect the full stored set. |
| WebDroid API unreachable | The WebDroid app must be installed (you build it yourself — no prebuilt APK) and open, with its HTTP server running on port 8765. |
| Slow collection | Raise `scroll_wait_seconds` lower bound is discouraged; instead raise `scroll_pixels` in `~/.nova/config.json`. Keep waits polite. |
| Database grows large | It stores one row per unique post. Delete `~/.nova/nova.db` to start fresh (exports are separate files). |
