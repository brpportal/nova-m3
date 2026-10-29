"""NOVA M3 command line + interactive task manager.

Commands:
  nova status                     engine + session + database summary
  nova browser open|stop          start/stop the browser engine
  nova session status             detect login state (no credentials handled)
  nova session delete             log out: remove the engine's session data
  nova extract --mode hybrid      collect post links from the current page
  nova extract --file page.html   offline extraction from a saved page
  nova export --format txt        export stored records
  nova logs [--tail N]            show recent log lines
  nova diagnose                   environment checks
  nova stop                       stop the browser engine
  nova                            interactive mode (natural-language tasks)

Interactive examples:
  open https://www.facebook.com/SomePage and collect up to 200 post links
  extract links from the current page using m1 and m3, then merge
  continue scrolling until 5 attempts produce no new links
  export unique links into a txt file
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time

from . import __version__
from .config import exports_dir, load_config
from .diagnostics import format_diagnostics, run_diagnostics
from .engines.base import AuthRequiredError, BrowserEngine, EngineError
from .engines.fileengine import FileEngine
from .engines.tbp import TbpEngine
from .engines.webdroid import WebDroidEngine
from .exporter import export as export_file
from .logs import get_logger
from .scroller import collect
from .session import check_session
from .store import Store

log = get_logger()


def make_engine(cfg: dict, name: str | None = None) -> BrowserEngine:
    engine_name = (name or cfg.get("engine", "tbp")).lower()
    if engine_name == "tbp":
        return TbpEngine(cfg.get("tbp_binary", "tbp"))
    if engine_name == "webdroid":
        return WebDroidEngine(cfg.get("webdroid_url", "http://localhost:8765"))
    raise EngineError(f"unknown engine '{engine_name}' (use tbp or webdroid)")


def _print_session(engine: BrowserEngine) -> str:
    state, detail = check_session(engine)
    print(f"Session: {state} — {detail}")
    return state


def cmd_status(cfg, _args) -> int:
    engine = make_engine(cfg)
    ok, reason = engine.available()
    print(f"NOVA M3 v{__version__}")
    print(f"Engine: {engine.name} — {'available' if ok else 'NOT available: ' + reason}")
    print(f"Browser running: {engine.is_running()}")
    if engine.is_running():
        _print_session(engine)
    store = Store(__import__("nova.config", fromlist=["db_path"]).db_path())
    print(f"Stored records: {store.count()}")
    store.close()
    return 0


def cmd_browser(cfg, args) -> int:
    engine = make_engine(cfg, args.engine)
    if args.action == "open":
        ok, reason = engine.available()
        if not ok:
            print(f"Cannot start: {reason}")
            return 1
        engine.start()
        print(f"{engine.name} browser started. Log into Facebook manually in "
              "the browser window if asked — NOVA never handles your password.")
        return 0
    engine.stop()
    print(f"{engine.name} browser stopped.")
    return 0


def cmd_session(cfg, args) -> int:
    engine = make_engine(cfg, args.engine)
    if args.action == "status":
        _print_session(engine)
        print(engine.session_storage_hint())
        return 0
    # delete
    if isinstance(engine, TbpEngine):
        answer = input("This stops TBP and deletes its saved Facebook session "
                       "(profile + auto cookies under ~/.tbp). Type DELETE to confirm: ")
        if answer.strip() != "DELETE":
            print("Cancelled.")
            return 0
        removed = engine.delete_session_data()
        print("Removed:", *removed, sep="\n  ") if removed else print("Nothing to remove.")
        return 0
    print("For this engine, log out inside the browser app (or clear its app "
          "data in Android Settings). " + engine.session_storage_hint())
    return 0


def _run_extract(engine: BrowserEngine, cfg, *, mode: str, url: str | None,
                 limit: int | None) -> int:
    store = Store(__import__("nova.config", fromlist=["db_path"]).db_path())
    try:
        if url:
            print(f"Target page: {url}")
            engine.navigate(url)
        state, detail = check_session(engine)
        print(f"Session: {state} — {detail}")
        if state in ("LOGIN_REQUIRED", "CHECKPOINT"):
            print("Paused: resolve the login/verification manually in the "
                  "browser window, then run extract again.")
            return 2
        print(f"Mode: {mode} | limit: {limit or cfg['max_posts']} posts | "
              f"idle rounds: {cfg['idle_rounds']} | "
              f"DB: {store.db_path}")

        def progress(round_no, total, dups, rejected):
            print(f"  round {round_no}: {total} stored, {dups} duplicates, "
                  f"{rejected} rejected", flush=True)

        result = collect(
            engine, store, mode=mode,
            max_posts=limit or cfg["max_posts"],
            max_seconds=cfg["max_scroll_seconds"],
            idle_rounds=cfg["idle_rounds"],
            scroll_pixels=cfg["scroll_pixels"],
            wait_seconds=cfg["scroll_wait_seconds"],
            progress=progress,
        )
        print(f"Done: {result.stored_new} new links stored, "
              f"{result.duplicates} duplicates, {result.rejected} rejected. "
              f"Stop reason: {result.stop_reason}")
        print(f"Total in database: {store.count()}")
        return 0
    finally:
        store.close()


def cmd_extract(cfg, args) -> int:
    if args.file:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            html = fh.read()
        engine = FileEngine([html], url=args.url or "https://www.facebook.com/offline-fixture")
        engine.start()
        print(f"Offline mode: extracting from {args.file} (no browser, no login)")
        return _run_extract(engine, cfg, mode=args.mode, url=None, limit=args.limit)
    engine = make_engine(cfg, args.engine)
    ok, reason = engine.available()
    if not ok:
        print(f"Engine unavailable: {reason}")
        return 1
    if not engine.is_running():
        print("Browser is not running. Start it first: nova browser open")
        return 1
    try:
        return _run_extract(engine, cfg, mode=args.mode, url=args.url,
                            limit=args.limit)
    except AuthRequiredError as exc:
        print(f"Paused: {exc}")
        return 2
    except EngineError as exc:
        print(f"Engine error: {exc}")
        return 1


def cmd_export(cfg, args) -> int:
    from .config import db_path

    store = Store(db_path())
    records = store.all_records()
    store.close()
    if not records:
        print("No records stored yet — run an extract first.")
        return 0
    out = args.out
    if not out:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        out = os.path.join(exports_dir(), f"nova-export-{stamp}.{args.format}")
    export_file(records, args.format, out)
    print(f"Exported {len(records)} records -> {out}")
    return 0


def cmd_logs(_cfg, args) -> int:
    from .config import nova_home

    path = os.path.join(nova_home(), "logs", "nova.log")
    if not os.path.isfile(path):
        print("No log file yet.")
        return 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    for line in lines[-args.tail:]:
        print(line, end="")
    return 0


def cmd_diagnose(_cfg, _args) -> int:
    print(format_diagnostics(run_diagnostics()))
    return 0


# --------------------------------------------------------------------------
# Interactive mode: a small, honest natural-language parser for the
# documented instruction shapes. Anything unrecognized is reported, never
# silently reinterpreted.
# --------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://[^\s\"']+")
_LIMIT_RE = re.compile(r"(?:up to|maximum|max)\s+(\d+)", re.I)
_IDLE_RE = re.compile(r"until\s+(\d+)\s+(?:consecutive\s+)?attempts?\s+produce\s+no\s+new", re.I)


def interactive(cfg) -> int:
    print("NOVA M3 interactive mode. Type 'help' or 'quit'.")
    print("Example: open https://www.facebook.com/SomePage and collect up to "
          "200 post links")
    engine_holder: dict[str, BrowserEngine] = {}

    def get_engine() -> BrowserEngine:
        if "engine" not in engine_holder:
            engine_holder["engine"] = make_engine(cfg)
        return engine_holder["engine"]

    while True:
        try:
            line = input("nova> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        low = line.lower()
        if low in ("quit", "exit", "q"):
            return 0
        if low == "help":
            print(__doc__)
            continue
        if low == "status":
            cmd_status(cfg, None)
            continue
        if "session" in low and "status" in low:
            _print_session(get_engine())
            continue
        if low.startswith("export"):
            fmt = "txt" if "txt" in low else "csv" if "csv" in low else "json"
            ns = argparse.Namespace(format=fmt, out=None)
            cmd_export(cfg, ns)
            continue
        if "stop" in low and "scroll" not in low:
            get_engine().stop()
            print("Browser stopped.")
            continue
        url_match = _URL_RE.search(line)
        limit_match = _LIMIT_RE.search(line)
        idle_match = _IDLE_RE.search(line)
        if url_match or "extract" in low or "collect" in low or "scroll" in low:
            mode = "hybrid"
            if "m1" in low and "m3" in low:
                mode = "hybrid"
            elif re.search(r"\bm1\b", low):
                mode = "m1"
            elif re.search(r"\bm3\b", low):
                mode = "m3"
            engine = get_engine()
            ok, reason = engine.available()
            if not ok:
                print(f"Engine unavailable: {reason}")
                continue
            if not engine.is_running():
                print("Starting browser… (log in manually if Facebook asks)")
                engine.start()
            if idle_match:
                cfg = {**cfg, "idle_rounds": int(idle_match.group(1))}
            ns_limit = int(limit_match.group(1)) if limit_match else None
            try:
                _run_extract(engine, cfg, mode=mode,
                             url=url_match.group(0) if url_match else None,
                             limit=ns_limit)
            except (AuthRequiredError, EngineError) as exc:
                print(f"Paused/stopped: {exc}")
            continue
        print("I don't recognize that instruction. Type 'help' for examples.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nova", description="NOVA M3 — Termux browser & Facebook post intelligence agent")
    parser.add_argument("--version", action="version", version=f"nova {__version__}")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="engine, session and database summary")
    sub.add_parser("diagnose", help="environment checks")
    sub.add_parser("stop", help="stop the browser engine")

    p_browser = sub.add_parser("browser", help="browser control")
    p_browser.add_argument("action", choices=["open", "stop"])
    p_browser.add_argument("--engine", choices=["tbp", "webdroid"])

    p_session = sub.add_parser("session", help="session management")
    p_session.add_argument("action", choices=["status", "delete"])
    p_session.add_argument("--engine", choices=["tbp", "webdroid"])

    p_extract = sub.add_parser("extract", help="collect post links")
    p_extract.add_argument("--mode", choices=["m1", "m3", "hybrid"], default="hybrid")
    p_extract.add_argument("--url", help="Facebook page/profile/group URL to open first")
    p_extract.add_argument("--limit", type=int, help="maximum posts to collect")
    p_extract.add_argument("--file", help="offline mode: extract from a saved HTML file")
    p_extract.add_argument("--engine", choices=["tbp", "webdroid"])

    p_export = sub.add_parser("export", help="export stored records")
    p_export.add_argument("--format", choices=["csv", "json", "txt"], required=True)
    p_export.add_argument("--out", help="output path (default: ~/.nova/exports/)")

    p_logs = sub.add_parser("logs", help="show recent log lines")
    p_logs.add_argument("--tail", type=int, default=50)
    return parser


def main(argv: list[str] | None = None) -> int:
    cfg = load_config()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            return interactive(cfg)
        if args.command == "status":
            return cmd_status(cfg, args)
        if args.command == "diagnose":
            return cmd_diagnose(cfg, args)
        if args.command == "stop":
            make_engine(cfg).stop()
            print("Browser engine stopped.")
            return 0
        if args.command == "browser":
            return cmd_browser(cfg, args)
        if args.command == "session":
            return cmd_session(cfg, args)
        if args.command == "extract":
            return cmd_extract(cfg, args)
        if args.command == "export":
            return cmd_export(cfg, args)
        if args.command == "logs":
            return cmd_logs(cfg, args)
    except EngineError as exc:
        print(f"Error: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nStopped by user. Progress so far is saved in the database.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
