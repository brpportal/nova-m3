"""URL engine for NOVA M3: normalization, classification, validation.

Design rules (from the project spec):
- Hostname must be on an explicit Facebook allowlist.
- Tracking parameters are removed only when the destination is preserved.
- Syntactic validity is NOT proof of accessibility; states keep them separate.
- Profile links, comment links and navigation links are never post links.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

ALLOWED_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "mbasic.facebook.com",
    "web.facebook.com",
    "fb.watch",
}

# Parameters that never change the destination and are safe to drop.
TRACKING_PARAMS = {
    "fbclid", "__tn__", "__cft__", "__xts__", "mibextid", "rdid", "share_url",
    "ref", "ref_src", "refsrc", "h", "notif_id", "notif_t", "__nodl",
    "sfnsn", "wtsid", "ru", "rid", "psc", "locale",
}

# Validation states
VALID_FORMAT = "VALID_FORMAT"
DUPLICATE = "DUPLICATE"
INVALID_URL = "INVALID_URL"
UNVERIFIED_DESTINATION = "UNVERIFIED_DESTINATION"
ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
VERIFIED_ACCESSIBLE = "VERIFIED_ACCESSIBLE"

_POST_PATH = re.compile(r"/posts/(pfbid[0-9A-Za-z]+|\d{5,})/?$")
_GROUP_POST_PATH = re.compile(r"/groups/\d+/posts/(pfbid[0-9A-Za-z]+|\d{5,})/?$")
_GROUP_PERMALINK = re.compile(r"/groups/\d+/permalink/(\d{5,})/?$")
_PHOTO_PATH = re.compile(r"/photos?/(?:[^/]+/)?(\d{5,})/?$")
_VIDEO_PATH = re.compile(r"/videos/(?:[^/]+/)?(\d{5,})/?$")
_REEL_PATH = re.compile(r"/reel/(\d{5,})/?$")
_FBWATCH_PATH = re.compile(r"^/([0-9A-Za-z_-]{5,})/?$")


@dataclass
class Candidate:
    """One extracted link candidate before/after validation."""

    raw_url: str
    source_page: str = ""
    method: str = ""  # "m1" | "m3" | "hybrid"
    object_id: str | None = None
    object_type: str = "unknown"  # post | photo | video | unknown
    confidence: float = 0.0
    normalized_url: str = ""
    validation_status: str = UNVERIFIED_DESTINATION
    error_reason: str = ""
    raw_value: str = ""  # original structured value (M3 debugging, no secrets)
    extra: dict = field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        if self.object_type in ("post", "photo", "video") and self.object_id:
            return f"{self.object_type}:{self.object_id}"
        return f"url:{self.normalized_url or self.raw_url}"


def _is_tracking(key: str) -> bool:
    # Facebook emits indexed variants like __cft__[0], __xts__[0].
    return key in TRACKING_PARAMS or key.startswith(("__cft__", "__xts__"))


def _clean_query(pairs):
    kept = [(k, v) for k, v in pairs if not _is_tracking(k)]
    kept.sort()
    return kept


def normalize_url(raw: str, base: str = "") -> str | None:
    """Return a normalized absolute URL, or None if the input is unusable."""
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip().replace("&amp;", "&")
    if raw.startswith("#") or raw.lower().startswith(("javascript:", "mailto:", "tel:")):
        return None
    if base:
        raw = urljoin(base, raw)
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https"):
        return None
    host = (parts.hostname or "").lower()
    if not host:
        return None
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    query = urlencode(_clean_query(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit(("https", host, path, query, ""))


def classify(url: str) -> tuple[str, str | None]:
    """Classify a normalized URL. Returns (object_type, object_id|None)."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = parts.path or ""
    params = dict(parse_qsl(parts.query))

    if host == "fb.watch":
        m = _FBWATCH_PATH.match(path)
        return ("video", m.group(1)) if m else ("unknown", None)

    # Comment links are never post links.
    if "comment_id" in params:
        return ("unknown", None)

    if path.endswith("/permalink.php") and params.get("story_fbid"):
        return ("post", params["story_fbid"])
    if path.endswith("/story.php") and params.get("story_fbid"):
        return ("post", params["story_fbid"])
    if path.endswith("/photo.php") and params.get("fbid"):
        if params["fbid"].isdigit() and len(params["fbid"]) >= 5:
            return ("photo", params["fbid"])
        return ("unknown", None)
    if path in ("/watch", "/watch/") and params.get("v"):
        v = params["v"]
        return ("video", v) if (v.isdigit() and len(v) >= 5) else ("unknown", None)

    for regex, kind in (
        (_GROUP_POST_PATH, "post"),
        (_GROUP_PERMALINK, "post"),
        (_POST_PATH, "post"),
        (_PHOTO_PATH, "photo"),
        (_VIDEO_PATH, "video"),
        (_REEL_PATH, "video"),
    ):
        m = regex.search(path)
        if m:
            return (kind, m.group(1))

    return ("unknown", None)


def validate_candidate(cand: Candidate, base: str = "") -> Candidate:
    """Fill normalized_url, object_type, object_id and validation_status."""
    normalized = normalize_url(cand.raw_url, base=base)
    if normalized is None:
        cand.validation_status = INVALID_URL
        cand.error_reason = "unparseable or non-http(s) URL"
        return cand
    cand.normalized_url = normalized
    host = (urlsplit(normalized).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        cand.validation_status = INVALID_URL
        cand.error_reason = f"host not on Facebook allowlist: {host}"
        return cand
    obj_type, obj_id = classify(normalized)
    if cand.object_id and obj_id and cand.object_id != obj_id:
        # Conflicting identifiers: trust the URL, flag the mismatch.
        cand.error_reason = "object_id mismatch between source and URL"
    cand.object_type = obj_type if obj_type != "unknown" else cand.object_type
    if obj_id:
        cand.object_id = obj_id
    if obj_type == "unknown":
        cand.validation_status = UNVERIFIED_DESTINATION
        if not cand.error_reason:
            cand.error_reason = "allowlisted host but not a recognized post/photo/video URL"
    else:
        cand.validation_status = VALID_FORMAT
    return cand
