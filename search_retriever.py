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

Mode discovery (--mode):
    all       kata kunci judol + feed grup + postingan random (default)
    keywords  kata kunci judol + feed grup (perilaku lama)
    random    HANYA feed grup + postingan random, tanpa kata kunci
              judol sama sekali — untuk menangkap promosi judol yang
              menempel di postingan biasa (keluhan, peringatan scam,
              jual beli, motor, dll). Detektor spam yang menyaring
              komentarnya nanti, jadi permukaan yang berisik tidak
              masalah.

Contoh:
    python3 search_retriever.py --headed          # pertama kali (login manual)
    python3 search_retriever.py                   # run berikutnya, pakai sesi
    python3 search_retriever.py --mode random     # hanya postingan biasa
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
    parser.add_argument("--mode", choices=["all", "keywords", "random"],
                        default="all",
                        help="Permukaan discovery: all (default), "
                        "keywords saja, atau random saja (tanpa kata "
                        "kunci judol).")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as fh:
        config = json.load(fh)
    os.makedirs(os.path.dirname(args.db) or ".", exist_ok=True)
    conn = fb_database.connect(args.db)

    from envcheck import close_browser_quietly, require_playwright
    sync_playwright = require_playwright()
    from pipeline import collect as collect_mod

    def _insert(posts):
        """Simpan postingan ke DB langsung (dedupe per URL), kembalikan
        (baru, total). Dipanggil per tahap supaya Ctrl+C di tengah
        jalan tidak menghilangkan postingan yang sudah ditemukan."""
        seen, deduped = set(), []
        for post in posts:
            if post["url"] not in seen:
                seen.add(post["url"])
                deduped.append(post)
        return fb_database.insert_posts(conn, deduped), len(deduped)

    with sync_playwright() as p:
        browser, context, page = collect_mod.ensure_login(
            p, args.state, headed=args.headed
        )
        try:
            while True:
                total_new, total_found = 0, 0
                try:
                    if args.mode in ("all", "keywords"):
                        n, f = _insert(collect_mod.discover_posts(page, config))
                        total_new += n
                        total_found += f
                    if args.mode in ("all", "keywords", "random"):
                        n, f = _insert(collect_mod.discover_group_posts(page, config))
                        total_new += n
                        total_found += f
                    if args.mode in ("all", "random"):
                        n, f = _insert(collect_mod.discover_random_posts(page, config))
                        total_new += n
                        total_found += f
                except KeyboardInterrupt:
                    print("\nDihentikan (Ctrl+C). %d/%d postingan baru "
                          "tetap tersimpan di DB." % (total_new, total_found))
                    break
                print("%d/%d NEW POSTS" % (total_new, total_found))
                if not args.loop:
                    break
                print("Sleeping for %s seconds..." % args.sleep)
                try:
                    time.sleep(args.sleep)
                except KeyboardInterrupt:
                    print("\nDihentikan (Ctrl+C).")
                    break
                print("Resuming...")
        finally:
            close_browser_quietly(browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
