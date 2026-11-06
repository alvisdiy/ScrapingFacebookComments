#!/usr/bin/env python3
"""Tes offline Ctrl+C di search_retriever.py (browser palsu).

Kasus nyata: user menekan Ctrl+C di tengah discovery. Sebelum
perbaikan, dua hal buruk terjadi: (1) browser.close() di blok finally
ikut gagal ("Connection closed while reading from the driver") dan
traceback-nya menutupi Ctrl+C; (2) semua postingan yang sudah
ditemukan hilang, karena insert ke DB baru dilakukan setelah SEMUA
tahap discovery selesai.
"""
import io
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import envcheck  # noqa: E402
import fb_database  # noqa: E402


class ExplodingBrowser:
    def close(self):
        raise Exception("Connection closed while reading from the driver")


class FakePW:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


POSTS = [
    {"url": "https://www.facebook.com/groups/1/permalink/1/",
     "base_keyword": "slot gacor", "query": "slot gacor", "mode": "posts"},
    {"url": "https://www.facebook.com/groups/1/permalink/2/",
     "base_keyword": "slot gacor", "query": "slot gacor", "mode": "posts"},
]


def main():
    failures = []

    def check(name, cond):
        print(("OK  " if cond else "FAIL") + " " + name)
        if not cond:
            failures.append(name)

    # 1. close_browser_quietly menelan error tutup browser.
    try:
        envcheck.close_browser_quietly(ExplodingBrowser())
        check("tutup browser yang sudah mati tidak traceback", True)
    except Exception:
        check("tutup browser yang sudah mati tidak traceback", False)

    # 2. Ctrl+C di tengah discovery: berhenti bersih, yang sudah
    #    ditemukan tahap pertama tetap tersimpan.
    tmp = tempfile.mkdtemp()
    config_path = os.path.join(tmp, "config.json")
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump({"delay_seconds": 0}, fh)
    db_path = os.path.join(tmp, "test.db")

    import search_retriever
    argv = ["search_retriever.py", "--db", db_path, "--config", config_path,
            "--mode", "all"]
    out = io.StringIO()
    with mock.patch.object(sys, "argv", argv), \
            mock.patch("playwright.sync_api.sync_playwright",
                       return_value=FakePW()), \
            mock.patch("pipeline.collect.ensure_login",
                       return_value=(ExplodingBrowser(), mock.Mock(),
                                     mock.Mock())), \
            mock.patch("pipeline.collect.discover_posts",
                       return_value=list(POSTS)), \
            mock.patch("pipeline.collect.discover_group_posts",
                       side_effect=KeyboardInterrupt), \
            mock.patch("pipeline.collect.discover_random_posts",
                       return_value=[]), \
            redirect_stdout(out):
        rc = search_retriever.main()
    check("Ctrl+C: main kembali 0 tanpa traceback", rc == 0)
    check("Ctrl+C: pesan berhenti bersih dicetak",
          "Dihentikan (Ctrl+C)" in out.getvalue())
    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    check("postingan tahap pertama tetap tersimpan di DB", n == 2)
    conn.close()

    print()
    if failures:
        print("%d kasus gagal: %s" % (len(failures), failures))
        return 1
    print("0 kasus gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
