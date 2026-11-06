#!/usr/bin/env python3
"""Tes offline details_retriever.py live: komentar masuk DB + raw file.

Menangkap celah yang pernah ada: mode live dulu hanya menyimpan ke
SQLite, sementara analyze_spam.py membaca data/raw_comments.jsonl —
jadi urutan manual search -> details -> analyze tidak menambah promo
sama sekali. Sekarang details live juga append ke raw file.
"""
import json
import os
import sqlite3
import sys
import tempfile
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fb_database  # noqa: E402

PROMO = "main di zeus88 gacor wd lancar https://bit.ly/abc123"
COMPLAINT = "situs ini penipu, depo gw ga balik"


class FakePW:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def main():
    failures = []

    def check(name, cond):
        print(("OK  " if cond else "FAIL") + " " + name)
        if not cond:
            failures.append(name)

    tmp = tempfile.mkdtemp()
    config_path = os.path.join(tmp, "config.json")
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump({"delay_seconds": 0}, fh)
    db_path = os.path.join(tmp, "test.db")
    raw_path = os.path.join(tmp, "raw.jsonl")

    conn = fb_database.connect(db_path)
    fb_database.insert_posts(conn, [{
        "url": "https://www.facebook.com/groups/123/permalink/111/",
        "base_keyword": "random", "query": "motor bekas", "mode": "random",
    }])
    conn.close()

    import details_retriever
    argv = ["details_retriever.py", "--db", db_path, "--config", config_path,
            "--raw", raw_path, "--max-posts", "5"]
    with mock.patch.object(sys, "argv", argv), \
            mock.patch("playwright.sync_api.sync_playwright",
                       return_value=FakePW()), \
            mock.patch("pipeline.collect.ensure_login",
                       return_value=(mock.Mock(), mock.Mock(), mock.Mock())), \
            mock.patch("pipeline.collect.collect_comments_deep",
                       return_value=[PROMO, COMPLAINT]):
        rc = details_retriever.main()
    check("main selesai OK", rc == 0)

    conn = sqlite3.connect(db_path)
    done = conn.execute(
        "SELECT COUNT(*) FROM posts WHERE status='done'").fetchone()[0]
    check("postingan ditandai selesai di DB", done == 1)
    n_db = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    check("2 komentar di DB", n_db == 2)
    conn.close()

    rows = []
    with open(raw_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    check("2 komentar di raw file", len(rows) == 2)
    check("raw berisi promo + keluhan",
          {r["comment_text"] for r in rows} == {PROMO, COMPLAINT})
    check("raw menyimpan base_keyword postingan",
          all(r["base_keyword"] == "random" for r in rows))

    # Jalankan lagi: tidak ada postingan baru, raw tidak bertambah.
    with mock.patch.object(sys, "argv", argv), \
            mock.patch("playwright.sync_api.sync_playwright",
                       return_value=FakePW()), \
            mock.patch("pipeline.collect.ensure_login",
                       return_value=(mock.Mock(), mock.Mock(), mock.Mock())), \
            mock.patch("pipeline.collect.collect_comments_deep",
                       return_value=[PROMO]):
        rc2 = details_retriever.main()
    check("run kedua: tidak ada postingan baru", rc2 == 0)
    with open(raw_path, encoding="utf-8") as fh:
        n_raw2 = sum(1 for line in fh if line.strip())
    check("raw tidak bertambah di run kedua", n_raw2 == 2)

    # append_rows langsung: duplikat dilewati, teks sama di postingan
    # beda tetap disimpan.
    import append_comments
    added = append_comments.append_rows(raw_path, [
        {"post_url": "https://www.facebook.com/groups/123/permalink/111/",
         "base_keyword": "random", "comment_text": PROMO},
        {"post_url": "https://www.facebook.com/groups/999/permalink/222/",
         "base_keyword": "random", "comment_text": PROMO},
    ])
    check("append_rows: duplikat dilewati, postingan beda disimpan",
          added == 1)

    print()
    if failures:
        print("%d kasus gagal: %s" % (len(failures), failures))
        return 1
    print("0 kasus gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
