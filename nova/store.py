"""SQLite storage for extraction records.

Never stores passwords, session cookies, or access tokens — only post link
records and their extraction metadata.
"""
from __future__ import annotations

import sqlite3
import time

from .extract.urls import Candidate

_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_page TEXT NOT NULL DEFAULT '',
    post_url TEXT NOT NULL,
    object_type TEXT NOT NULL DEFAULT 'unknown',
    object_id TEXT,
    extraction_method TEXT NOT NULL DEFAULT '',
    first_seen_at REAL NOT NULL,
    last_seen_at REAL NOT NULL,
    validation_status TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0,
    error_reason TEXT NOT NULL DEFAULT '',
    dedup_key TEXT NOT NULL UNIQUE
);
"""


class Store:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(_SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert(self, cand: Candidate) -> bool:
        """Insert a candidate; returns True if it was new, False if duplicate."""
        now = time.time()
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO records (source_page, post_url, object_type,"
            " object_id, extraction_method, first_seen_at, last_seen_at,"
            " validation_status, confidence, error_reason, dedup_key)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (cand.source_page, cand.normalized_url or cand.raw_url, cand.object_type,
             cand.object_id, cand.method, now, now, cand.validation_status,
             cand.confidence, cand.error_reason, cand.dedup_key),
        )
        if cur.rowcount == 0:
            self.conn.execute(
                "UPDATE records SET last_seen_at=? WHERE dedup_key=?",
                (now, cand.dedup_key),
            )
            self.conn.commit()
            return False
        self.conn.commit()
        return True

    def all_records(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM records ORDER BY record_id").fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
