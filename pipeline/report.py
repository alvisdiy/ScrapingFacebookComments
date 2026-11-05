"""Tahap match & report: dari komentar mentah menjadi hasil yang bisa dibaca."""

import csv
import json
import os
from collections import Counter, defaultdict

from .textutil import match_comment


def build_matches(raw_rows, config):
    """Jalankan pencocokan untuk semua baris komentar mentah.

    raw_rows: {"post_url", "base_keyword", "query", "comment_text"}.
    Mengembalikan (match_rows, summary).
    """
    match_rows = []
    per_keyword = defaultdict(
        lambda: {
            "posts_checked": set(),
            "comments_checked": 0,
            "matches": 0,
            "by_type": Counter(),
        }
    )
    total_comments = 0
    for row in raw_rows:
        text = row.get("comment_text", "")
        if not text:
            continue
        total_comments += 1
        base = row.get("base_keyword", "")
        stats = per_keyword[base]
        stats["posts_checked"].add(row.get("post_url", ""))
        stats["comments_checked"] += 1
        for m in match_comment(text, config):
            stats["matches"] += 1
            stats["by_type"][m["match_type"]] += 1
            match_rows.append(
                {
                    "keyword": base,
                    "match_type": m["match_type"],
                    "matched_term": m["term"],
                    "matched_base": m["base_keyword"] or "",
                    "post_url": row.get("post_url", ""),
                    "comment_text": text,
                }
            )
    summary = {
        "total_comments_checked": total_comments,
        "total_matches": len(match_rows),
        "per_keyword": {
            kw: {
                "posts_checked": len(v["posts_checked"]),
                "comments_checked": v["comments_checked"],
                "matches": v["matches"],
                "by_type": dict(v["by_type"]),
            }
            for kw, v in sorted(per_keyword.items())
        },
    }
    return match_rows, summary


def write_matches_csv(path, match_rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "keyword",
                "match_type",
                "matched_term",
                "matched_base",
                "post_url",
                "comment_text",
            ],
        )
        writer.writeheader()
        writer.writerows(match_rows)


def write_summary_json(path, summary):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)


def print_summary(summary):
    print("\n===== RINGKASAN =====")
    print("Komentar dicek: %d" % summary["total_comments_checked"])
    print("Total match: %d" % summary["total_matches"])
    for kw, v in summary["per_keyword"].items():
        print(
            "- %s: %d postingan, %d komentar, %d match %s"
            % (
                kw,
                v["posts_checked"],
                v["comments_checked"],
                v["matches"],
                v["by_type"],
            )
        )
