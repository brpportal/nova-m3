"""Export manager: CSV, JSON and TXT exports of stored records."""
from __future__ import annotations

import csv
import io
import json
import time

_FIELDS = ["record_id", "source_page", "post_url", "object_type", "object_id",
           "extraction_method", "first_seen_at", "last_seen_at",
           "validation_status", "confidence", "error_reason"]


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))


def render(records: list[dict], fmt: str) -> str:
    fmt = fmt.lower()
    if fmt == "txt":
        seen: list[str] = []
        for r in records:
            if r["post_url"] not in seen:
                seen.append(r["post_url"])
        return "\n".join(seen) + ("\n" if seen else "")
    if fmt == "json":
        out = []
        for r in records:
            row = {k: r.get(k) for k in _FIELDS}
            row["first_seen_at"] = _iso(r["first_seen_at"])
            row["last_seen_at"] = _iso(r["last_seen_at"])
            out.append(row)
        return json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_FIELDS)
        writer.writeheader()
        for r in records:
            row = {k: r.get(k) for k in _FIELDS}
            row["first_seen_at"] = _iso(r["first_seen_at"])
            row["last_seen_at"] = _iso(r["last_seen_at"])
            writer.writerow(row)
        return buf.getvalue()
    raise ValueError(f"unsupported export format: {fmt}")


def export(records: list[dict], fmt: str, out_path: str) -> str:
    content = render(records, fmt)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return out_path
