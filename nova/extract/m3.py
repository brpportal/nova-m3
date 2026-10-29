"""M3 — structured-data extraction from accessible page data.

Sources: embedded JSON inside <script> tags / page HTML, or raw JSON text.
Parsing uses a real JSON parser (json.JSONDecoder.raw_decode) — never regex
extraction of JSON values. Candidate fields are treated as candidates, not
guarantees; every result carries its extraction method and confidence.

Rules:
- A valid direct permalink_url on a post-like object wins (high confidence).
- ID-based URL construction happens ONLY for a verified format: a post
  object that carries both a story/top-level post id AND its owner id,
  producing https://www.facebook.com/{owner_id}/posts/{story_fbid}.
- Bare numeric IDs (user ids, comment ids, reaction ids...) are rejected:
  a number alone never identifies a post.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser

from .urls import Candidate, validate_candidate

_POST_ID_KEYS = ("story_fbid", "top_level_post_id", "post_id", "feedback_id")
_OWNER_KEYS = ("owner_id", "page_id", "profile_id", "actor_id", "author_id")
_POST_TYPENAMES = ("story", "post", "feedback", "video", "photo")
_MAX_JSON_BLOBS = 4000  # safety bound against pathological pages


class _ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scripts: list[str] = []
        self._in_script = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            self._in_script = True
            self._buf = []

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._in_script:
            self._in_script = False
            self.scripts.append("".join(self._buf))

    def handle_data(self, data):
        if self._in_script:
            self._buf.append(data)


def _iter_json_objects(text: str):
    """Yield every decodable JSON object/array found in text."""
    decoder = json.JSONDecoder()
    idx = 0
    made = 0
    n = len(text)
    while idx < n and made < _MAX_JSON_BLOBS:
        ch = text[idx]
        if ch in "{[":
            try:
                obj, end = decoder.raw_decode(text, idx)
            except (ValueError, RecursionError):
                idx += 1
                continue
            yield obj
            made += 1
            idx = max(end, idx + 1)
        else:
            idx += 1


def _walk(node, out: list[dict]):
    if isinstance(node, dict):
        out.append(node)
        for value in node.values():
            _walk(value, out)
    elif isinstance(node, list):
        for item in node:
            _walk(item, out)


def _first_str(node: dict, keys) -> str | None:
    for key in keys:
        value = node.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, int) and value > 0:
            return str(value)
    return None


def _looks_like_post_object(node: dict) -> bool:
    typename = str(node.get("__typename", "")).lower()
    if any(t in typename for t in _POST_TYPENAMES):
        return True
    # A permalink plus a creation/post context is a strong signal.
    if "permalink_url" in node and (
        "creation_time" in node or "created_time" in node or "story_fbid" in node
        or "top_level_post_id" in node or "post_id" in node
    ):
        return True
    return False


def _candidates_from_object(node: dict, source_page: str) -> list[Candidate]:
    results: list[Candidate] = []
    permalink = node.get("permalink_url")
    if isinstance(permalink, str) and "facebook.com" in permalink or isinstance(permalink, str) and "fb.watch" in permalink:
        cand = Candidate(raw_url=permalink, source_page=source_page, method="m3",
                         confidence=0.95, raw_value=permalink)
        validate_candidate(cand, base=source_page)
        if cand.validation_status != "INVALID_URL":
            results.append(cand)
        return results
    # ID-based construction — only the verified owner/posts format.
    post_id = _first_str(node, _POST_ID_KEYS)
    owner_id = _first_str(node, _OWNER_KEYS)
    if post_id and owner_id and post_id.isdigit() and owner_id.isdigit() \
            and len(post_id) >= 5 and _looks_like_post_object(node):
        url = f"https://www.facebook.com/{owner_id}/posts/{post_id}"
        cand = Candidate(raw_url=url, source_page=source_page, method="m3",
                         confidence=0.6, raw_value=f"constructed from post_id={post_id} owner_id={owner_id}")
        validate_candidate(cand, base=source_page)
        results.append(cand)
    return results


def extract_m3(data: str, source_page: str = "") -> tuple[list[Candidate], dict]:
    """Extract post candidates from structured data in HTML or raw JSON text.

    Returns (candidates, stats). Stats report how many JSON objects were
    inspected and how many post-like objects were rejected, so an M3 failure
    mode (format changed) is visible instead of silent.
    """
    stats = {"json_blobs": 0, "objects_seen": 0, "post_objects": 0,
             "rejected_id_only": 0, "candidates": 0}
    texts: list[str] = []
    if data and "<script" in data.lower():
        parser = _ScriptParser()
        try:
            parser.feed(data)
        except Exception:
            pass
        texts.extend(parser.scripts)
    elif data:
        texts.append(data)

    out: list[Candidate] = []
    for text in texts:
        for blob in _iter_json_objects(text):
            stats["json_blobs"] += 1
            dicts: list[dict] = []
            _walk(blob, dicts)
            stats["objects_seen"] += len(dicts)
            for node in dicts:
                has_id = _first_str(node, _POST_ID_KEYS) is not None
                has_permalink = isinstance(node.get("permalink_url"), str)
                if not (has_id or has_permalink):
                    continue
                if not _looks_like_post_object(node) and not has_permalink:
                    if has_id:
                        stats["rejected_id_only"] += 1
                    continue
                stats["post_objects"] += 1
                out.extend(_candidates_from_object(node, source_page))
    stats["candidates"] = len(out)
    return out, stats
