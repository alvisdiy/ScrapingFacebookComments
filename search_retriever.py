#!/usr/bin/env python3
"""Tahap 1 ala LinkedIn search_retriever.py, untuk Facebook.

LinkedIn: loop tanpa henti, panggil Voyager API, simpan job_id baru ke
SQLite, tidur adaptif.
Facebook: TIDAK ada API Voyager yang setara, dan loop tanpa henti itu
yang paling berisiko buat akun. Jadi di sini:
  - discovery lewat pencarian Facebook di browser (pipeline/collect.py,
    sudah teruji di project ini), bukan API;
  - default SEKALI jalan (--once, implisit), bukan while True;
  - --loop hanya kalau user memintanya eksplisit, dengan jeda tetap
    dari config, bukan tidur adaptif yang makin agresif;
  - dedupe persis seperti LinkedIn: post_url yang sudah ada di DB
    tidak dimasukkan lagi, dan laporan "X/Y NEW POSTS" dipertahankan.

Login: sama seperti project ini dari awal — TIDAK ada logins.csv,
tidak ada password di argumen/file/env. Sesi dibuat user sendiri di
jendela browser pada run pertama (pipeline/collect.ensure_login).

Contoh:
    python3 search_retriever.py --headed          # pertama kali (login manual)
    python3 search_retriever.py                   # run berikutnya, pakai sesi
    python3 search_retriever.py --loop --sleep 600  # hanya kalau diminta
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fb_database  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="pipeline/config.json")
    parser.add_argument("--db", default="data/fb_judol.db")
    parser.add_argument("--state", default="auth_state.json")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--loop", action="store_true",
                        help="Ulangi discovery sampai dihentikan (Ctrl+C).")
    parser.add_argument("--sleep", type=float, default=600.0,
                        help="Jeda antar putaran --loop, detik (default 600).")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as fh:
        config = json.load(fh)
    os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    conn = fb_database.connect(args.db)

    from playwright.sync_api import sync_playwright
    from pipeline import collect as collect_mod

    with sync_playwright() as p:
        browser, context, page = collect_mod.ensure_login(
            p, args.state, headed=args.headed
        )
        try:
            while True:
                posts = collect_mod.discover_posts(page, config)
                posts += collect_mod.discover_group_posts(page, config)
                seen, deduped = set(), []
                for post in posts:
                    if post["url"] not in seen:
                        seen.add(post["url"])
                        deduped.append(post)
                new = fb_database.insert_posts(conn, deduped)
                print("%d/%d NEW POSTS" % (new, len(deduped)))
                if not args.loop:
                    break
                print("Sleeping for %s seconds..." % args.sleep)
                time.sleep(args.sleep)
                print("Resuming...")
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
