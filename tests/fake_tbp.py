#!/usr/bin/env python3
"""Fake `tbp` binary for engine tests.

Emulates the REAL Termux Browser Pilot v0.17.1 response envelope, copied
from its cli.py/src/daemon.py:
  {"id": 1, "success": true, "data": {...}}  /  {"success": false, "error": ...}
State (current URL) is kept in the file named by $FAKE_TBP_STATE.
"""
import json
import os
import sys

STATE = os.environ.get("FAKE_TBP_STATE", "/tmp/fake-tbp-state.json")
HTML = "<html><body><a href=\"https://www.facebook.com/P/posts/123456789\">x</a></body></html>"


def load():
    try:
        with open(STATE) as fh:
            return json.load(fh)
    except Exception:
        return {"url": "https://www.facebook.com/", "running": True}


def save(state):
    with open(STATE, "w") as fh:
        json.dump(state, fh)


def out(obj):
    print(json.dumps(obj))


def main(argv):
    args = []
    skip_next = False
    for a in argv:
        if skip_next:
            skip_next = False
            continue
        if a == "--timeout":
            skip_next = True
            continue
        if a != "--json":
            args.append(a)
    state = load()
    cmd = args[0] if args else ""
    if cmd == "status":
        if not state.get("running"):
            out({"success": False, "error": "No daemon running"})
        else:
            out({"id": 1, "success": True, "data": {
                "pid": 4242, "browser": "firefox", "url": state["url"],
                "title": "Facebook", "uptime": 12.5}})
        return 0
    if cmd == "start":
        state["running"] = True
        save(state)
        out({"id": 1, "success": True, "data": {}})
        return 0
    if cmd == "stop":
        state["running"] = False
        save(state)
        out({"id": 1, "success": True, "data": {}})
        return 0
    if cmd == "goto":
        state["url"] = args[1]
        save(state)
        if os.environ.get("FAKE_TBP_GOTO_TIMEOUT"):
            # Simulates the field case: client timed out, page still loaded.
            out({"success": False, "error": "Command timed out"})
        else:
            out({"id": 1, "success": True, "data": {}})
        return 0
    if cmd == "html":
        out({"id": 1, "success": True, "data": {"html": HTML, "truncated": False}})
        return 0
    if cmd == "eval":
        expr = args[1]
        if "loginForm" in expr:  # session probe (also mentions location.href)
            result = json.dumps({"href": state["url"], "loginForm": False,
                                 "accountUI": True})
        elif "location.href" in expr:
            result = state["url"]
        elif "outerHTML" in expr:
            result = HTML
        else:
            result = None
        out({"id": 1, "success": True, "data": {"result": result}})
        return 0
    if cmd == "scroll":
        out({"id": 1, "success": True, "data": {}})
        return 0
    out({"success": False, "error": f"unknown command {cmd}"})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
