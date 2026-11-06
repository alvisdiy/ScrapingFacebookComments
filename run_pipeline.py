#!/usr/bin/env python3
"""Runner pipeline scraping komentar Facebook (tahap-tahap + checkpoint).

Tahapan:
  discover  cari postingan per kata kunci (plus seed URL) -> discovered_posts.json
  collect   kumpulkan komentar sedalam mungkin per postingan -> raw_comments.jsonl
  match     cocokkan komentar dengan kata kunci/varian -> matches.csv + summary.json
  report    tampilkan ringkasan dari summary.json
  all       jalankan semua tahap berurutan

Checkpoint: collect mencatat postingan yang sudah dikumpulkan di
collected_posts.json, jadi run yang terputus bisa dilanjut tanpa
mengulang postingan yang sama. File state disimpan di --state-dir
(default: data/).

Login: tidak ada password di argumen/file/env. Lihat pipeline/collect.py:
sesi dibuat user sendiri di jendela browser pada run pertama.

Contoh:
    python3 run_pipeline.py --stage all --headed
    python3 run_pipeline.py --stage collect
    python3 run_pipeline.py --stage match --state-dir data
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import collect as collect_mod  # noqa: E402
from pipeline import report as report_mod  # noqa: E402


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def stage_discover(page, config, state_dir):
    posts = collect_mod.discover_posts(page, config)
    posts += collect_mod.discover_group_posts(page, config)
    seen, deduped = set(), []
    for post in posts:
        if post["url"] not in seen:
            seen.add(post["url"])
            deduped.append(post)
    out = os.path.join(state_dir, "discovered_posts.json")
    collect_mod.save_json(out, deduped)
    print("Discovered %d postingan -> %s" % (len(deduped), out))
    # Snowball: grup baru dari URL postingan + pencarian grup.
    groups = sorted(
        set(config.get("seed_groups", []))
        | set(collect_mod.extract_group_urls([p["url"] for p in deduped]))
        | set(collect_mod.discover_groups_from_search(page, config))
    )
    gout = os.path.join(state_dir, "discovered_groups.json")
    collect_mod.save_json(gout, groups)
    print("Discovered %d grup (seed + snowball) -> %s" % (len(groups), gout))
    return deduped


def stage_collect(page, config, state_dir):
    posts = collect_mod.load_json(
        os.path.join(state_dir, "discovered_posts.json"), []
    )
    done = set(
        collect_mod.load_json(
            os.path.join(state_dir, "collected_posts.json"), []
        )
    )
    raw_path = os.path.join(state_dir, "raw_comments.jsonl")
    delay = float(config.get("delay_seconds", 5.0))
    import time

    new_done = []
    for post in posts:
        url = post["url"]
        if url in done:
            continue
        try:
            texts = collect_mod.collect_comments_deep(page, url, config)
        except Exception as exc:
            print("Gagal mengumpulkan %s: %s" % (url[:80], exc))
            continue
        rows = [
            {
                "post_url": url,
                "base_keyword": post.get("base_keyword", ""),
                "query": post.get("query", ""),
                "comment_text": t,
            }
            for t in texts
        ]
        collect_mod.append_jsonl(raw_path, rows)
        done.add(url)
        new_done.append(url)
        print("%s -> %d komentar" % (url[:80], len(rows)))
        time.sleep(delay)
    collect_mod.save_json(
        os.path.join(state_dir, "collected_posts.json"), sorted(done)
    )
    print("Collect selesai. %d postingan baru." % len(new_done))


def stage_match(config, state_dir):
    raw_path = os.path.join(state_dir, "raw_comments.jsonl")
    raw_rows = []
    if os.path.exists(raw_path):
        with open(raw_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    raw_rows.append(json.loads(line))
    match_rows, summary = report_mod.build_matches(raw_rows, config)
    report_mod.write_matches_csv(
        os.path.join(state_dir, "matches.csv"), match_rows
    )
    report_mod.write_summary_json(
        os.path.join(state_dir, "summary.json"), summary
    )
    report_mod.print_summary(summary)
    return summary


def stage_report(state_dir):
    summary = collect_mod.load_json(
        os.path.join(state_dir, "summary.json"), None
    )
    if summary is None:
        print("Belum ada summary.json. Jalankan --stage match dulu.")
        return
    report_mod.print_summary(summary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=["discover", "collect", "match", "report", "all"],
        default="all",
    )
    parser.add_argument("--config", default="pipeline/config.json")
    parser.add_argument("--state-dir", default="data")
    parser.add_argument("--state", default="auth_state.json")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    os.makedirs(args.state_dir, exist_ok=True)

    if args.stage in ("discover", "collect", "all"):
        from envcheck import close_browser_quietly, require_playwright
        sync_playwright = require_playwright()

        with sync_playwright() as p:
            browser, context, page = collect_mod.ensure_login(
                p, args.state, headed=args.headed
            )
            try:
                if args.stage in ("discover", "all"):
                    stage_discover(page, config, args.state_dir)
                if args.stage in ("collect", "all"):
                    stage_collect(page, config, args.state_dir)
            finally:
                close_browser_quietly(browser)

    if args.stage in ("match", "all"):
        stage_match(config, args.state_dir)
    if args.stage in ("report", "all"):
        stage_report(args.state_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
