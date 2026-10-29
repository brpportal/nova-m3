"""Hybrid extraction: run M1 and M3, merge, deduplicate.

Neither method is assumed superior. A link found by both methods gets a
confidence boost; if M3 produces nothing (data format changed), M1 results
are retained and the M3 stats make the failure visible.
"""
from __future__ import annotations

from .m1 import extract_m1
from .m3 import extract_m3
from .urls import Candidate


def merge_candidates(*groups: list[Candidate]) -> tuple[list[Candidate], dict]:
    """Merge candidate lists, deduplicating by object id / normalized URL."""
    merged: dict[str, Candidate] = {}
    stats = {"input": 0, "duplicates": 0, "merged_pairs": 0}
    for group in groups:
        for cand in group:
            stats["input"] += 1
            key = cand.dedup_key
            existing = merged.get(key)
            if existing is None:
                merged[key] = cand
                continue
            stats["duplicates"] += 1
            if existing.method != cand.method:
                stats["merged_pairs"] += 1
                existing.method = "hybrid"
                existing.confidence = min(1.0, max(existing.confidence, cand.confidence) + 0.05)
                if cand.confidence > existing.confidence - 0.05 and cand.raw_url:
                    existing.raw_value = existing.raw_value or cand.raw_value
    return list(merged.values()), stats


def extract_hybrid(html: str, source_page: str = "") -> tuple[list[Candidate], dict]:
    m1_results, m1_stats = extract_m1(html, source_page)
    m3_results, m3_stats = extract_m3(html, source_page)
    merged, merge_stats = merge_candidates(m1_results, m3_results)
    stats = {"m1": m1_stats, "m3": m3_stats, "merge": merge_stats,
             "total_unique": len(merged)}
    return merged, stats
