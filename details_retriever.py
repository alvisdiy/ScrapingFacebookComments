#!/usr/bin/env python3
"""Tahap 2 ala LinkedIn details_retriever.py, untuk Facebook.

LinkedIn: ambil job_id yang scraped=0 (maks 25 per putaran), panggil
API detail per job, simpan atribut lengkap, tidur 60 detik.
Facebook: ambil post_url yang status='new' (maks 25 per run, sama),
buka postingannya, kumpulkan komentar sedalam mungkin
(pipeline/collect.collect_comments_deep), lalu untuk tiap komentar
jalankan DUA matcher: matcher frasa lama (textutil, tidak diubah) dan
matcher token brand+angka baru (brand_tokens). Hasilnya masuk SQLite,
bukan cuma CSV, supaya frekuensi brand bisa dihitung di to_csv.

Mode --offline dipakai untuk verifikasi tanpa browser dan tanpa login:
membaca data/raw_comments.jsonl yang sudah ada, memasukkannya ke DB,
dan menjalankan matcher yang sama. Mode ini yang dipakai untuk
membuktikan matcher baru di dataset lama sebelum ada live run baru.

Contoh:
    python3 details_retriever.py --offline
    python3 details_retriever.py --headed   # live, maks 25 postingan baru
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import brand_tokens  # noqa: E402
import fb_database  # noqa: E402

MAX_UPDATES = 25


def _store_comments(conn, post_url, texts):
    from pipeline import textutil
    config = json.load(open("pipeline/config.json", encoding="utf-8")) \
        if os.path.exists("pipeline/config.json") else {}
    total_tokens = 0
    for text in texts:
        tokens = brand_tokens.find_brand_tokens(text)
        total_tokens += fb_database.insert_comment_with_tokens(
            conn, post_url, text, tokens)
        # Matcher frasa lama tetap dijalankan untuk konsistensi, tapi
        # hasilnya tidak diduplikasi ke DB: laporan frasa lama tetap
        # lewat run_pipeline.py --stage match (matches.csv).
        _ = textutil.match_comment(text, config) if config else []
    fb_database.mark_post_done(conn, post_url, len(texts))
    return total_tokens


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/fb_judol.db")
    parser.add_argument("--config", default="pipeline/config.json")
    parser.add_argument("--state", default="auth_state.json")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--max-posts", type=int, default=MAX_UPDATES)
    parser.add_argument("--offline", action="store_true",
                        help="Pakai data/raw_comments.jsonl, tanpa browser.")
    parser.add_argument("--offline-input", default="data/raw_comments.jsonl")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as fh:
        config = json.load(fh)
    os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    conn = fb_database.connect(args.db)
    delay = float(config.get("delay_seconds", 5.0))

    if args.offline:
        posts = {}
        with open(args.offline_input, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    posts.setdefault(row["post_url"], []).append(row["comment_text"])
        fb_database.insert_posts(conn, [
            {"url": url, "base_keyword": "", "query": "", "mode": "offline"}
            for url in posts
        ])
        total = 0
        for url, texts in posts.items():
            total += _store_comments(conn, url, texts)
        print("OFFLINE: %d postingan, %d komentar, %d token brand+angka"
              % (len(posts), sum(len(v) for v in posts.values()), total))
        return 0

    cur = conn.cursor()
    cur.execute("SELECT post_url FROM posts WHERE status = 'new' LIMIT ?",
                (args.max_posts,))
    urls = [r[0] for r in cur.fetchall()]
    if not urls:
        print("Tidak ada postingan baru di DB. Jalankan search_retriever.py dulu.")
        return 0

    from playwright.sync_api import sync_playwright
    from pipeline import collect as collect_mod

    with sync_playwright() as p:
        browser, context, page = collect_mod.ensure_login(
            p, args.state, headed=args.headed
        )
        try:
            for url in urls:
                try:
                    texts = collect_mod.collect_comments_deep(page, url, config)
                except Exception as exc:
                    print("Gagal %s: %s" % (url[:80], exc))
                    continue
                n_tokens = _store_comments(conn, url, texts)
                print("%s -> %d komentar, %d token" % (url[:80], len(texts), n_tokens))
                time.sleep(delay)
        finally:
            browser.close()
    print("UPDATED %d POSTS" % len(urls))
    return 0


if __name__ == "__main__":
    sys.exit(main())
