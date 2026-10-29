"""M1 — visible-link extraction from rendered page HTML.

Reads links from accessible rendered elements (anchor hrefs), keeps only
Facebook post/photo/video links, and records what it skipped. M1 has no
dependency on structured data, so it keeps working when M3 data is absent.
"""
from __future__ import annotations

from html.parser import HTMLParser

from .urls import ALLOWED_HOSTS, Candidate, classify, normalize_url, validate_candidate
from urllib.parse import urlsplit


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.hrefs.append(value)


def extract_m1(html: str, source_page: str = "") -> tuple[list[Candidate], dict]:
    """Extract post/photo/video link candidates from rendered HTML.

    Returns (candidates, stats) where stats counts skipped hrefs by reason.
    Only validated post/photo/video candidates are returned; profile,
    comment, navigation and external links are counted as skipped.
    """
    parser = _LinkParser()
    parser.feed(html or "")
    stats = {"hrefs_seen": len(parser.hrefs), "skipped_external": 0,
             "skipped_non_post": 0, "skipped_invalid": 0, "candidates": 0}
    out: list[Candidate] = []
    seen_raw: set[str] = set()
    for href in parser.hrefs:
        if href in seen_raw:
            continue
        seen_raw.add(href)
        normalized = normalize_url(href, base=source_page)
        if normalized is None:
            stats["skipped_invalid"] += 1
            continue
        host = (urlsplit(normalized).hostname or "").lower()
        if host not in ALLOWED_HOSTS:
            stats["skipped_external"] += 1
            continue
        obj_type, _ = classify(normalized)
        if obj_type == "unknown":
            stats["skipped_non_post"] += 1
            continue
        cand = Candidate(raw_url=href, source_page=source_page, method="m1",
                         confidence=0.7)
        validate_candidate(cand, base=source_page)
        out.append(cand)
    stats["candidates"] = len(out)
    return out, stats
