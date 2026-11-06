#!/usr/bin/env python3
"""Tes offline auto.py dengan halaman/browser palsu (tanpa login nyata).

Memastikan mode otomatis: putaran berulang sampai --max-rounds, batas
per putaran BUKAN batas total (putaran berikut mengambil postingan
baru berikutnya), postingan yang sudah selesai tidak diulang, dan
ringkasan promo dihitung dari raw file.
"""
import json
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import auto

PROMO = "main di zeus88 gacor wd lancar https://bit.ly/abc123"
COMPLAINT = "situs ini penipu, depo gw ga balik"

HREFS = [
    "https://www.facebook.com/groups/123/permalink/111/",
    "https://www.facebook.com/groups/456/permalink/222/",
    "https://www.facebook.com/someone/posts/999/",
]


class FakePage:
    def goto(self, url):
        pass

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, js):
        pass

    def eval_on_selector_all(self, selector, js):
        return list(HREFS)


class FakeCtx:
    def __init__(self, page):
        self.page = page


class FakeBrowser:
    def close(self):
        pass


def fake_login(p, state, headed=False):
    return FakeBrowser(), FakeCtx(FakePage()), FakePage()


def fake_collect(page, url, config):
    return [PROMO, COMPLAINT]


def main():
    failures = []

    def check(name, cond):
        print(("OK  " if cond else "FAIL") + " " + name)
        if not cond:
            failures.append(name)

    tmp = tempfile.mkdtemp()
    config_path = os.path.join(tmp, "config.json")
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump({
            "keywords": ["motor bekas"],
            "query_forms": ["plain"],
            "search_modes": ["posts"],
            "seed_groups": ["https://www.facebook.com/groups/123/"],
            "random_queries": ["hp second"],
            "max_posts_per_query": 10,
            "max_posts_per_group": 10,
            "max_random_posts_per_query": 10,
            "delay_seconds": 0,
        }, fh)
    db_path = os.path.join(tmp, "test.db")
    raw_path = os.path.join(tmp, "raw.jsonl")

    summary = auto.run_auto(
        config_path, db_path, raw_path, os.path.join(tmp, "state.json"),
        headed=False, mode="all", max_posts_per_round=2, sleep_s=0,
        max_rounds=2, max_minutes=0, analyze=False,
        login_fn=fake_login, collect_fn=fake_collect)

    check("2 putaran jalan", summary["rounds"] == 2)
    check("batas per putaran bukan batas total (2+1=3 postingan)",
          summary["posts"] == 3)
    check("komentar masuk raw file (3 postingan x 2)",
          summary["comments"] == 6)
    total, labels = auto.summarize_raw(raw_path)
    check("raw file 6 unik", total == 6)
    check("promo 3 (satu per postingan)", labels["spam"] + labels["candidate"] == 3)
    check("keluhan 3 other", labels["other"] == 3)

    conn = sqlite3.connect(db_path)
    done = conn.execute("SELECT COUNT(*) FROM posts WHERE status='done'").fetchone()[0]
    check("semua postingan ditandai selesai", done == 3)

    # Putaran ketiga: tidak ada postingan baru lagi.
    summary2 = auto.run_auto(
        config_path, db_path, raw_path, os.path.join(tmp, "state.json"),
        headed=False, mode="all", max_posts_per_round=2, sleep_s=0,
        max_rounds=1, max_minutes=0, analyze=False,
        login_fn=fake_login, collect_fn=fake_collect)
    check("putaran tanpa postingan baru: 0 dikumpulkan",
          summary2["posts"] == 0 and summary2["comments"] == 0)
    total2, _ = auto.summarize_raw(raw_path)
    check("raw file tidak bertambah", total2 == 6)

    # Checkpoint: DB + raw tersalin tiap putaran, tanpa mengganggu run.
    ckpt = os.path.join(tmp, "ckpt")
    summary3 = auto.run_auto(
        config_path, db_path, raw_path, os.path.join(tmp, "state.json"),
        headed=False, mode="all", max_posts_per_round=2, sleep_s=0,
        max_rounds=1, max_minutes=0, analyze=False,
        login_fn=fake_login, collect_fn=fake_collect,
        checkpoint_dir=ckpt)
    check("checkpoint: run tetap selesai", summary3["rounds"] == 1)
    check("checkpoint: DB tersalin",
          os.path.exists(os.path.join(ckpt, "test.db")))
    check("checkpoint: raw tersalin",
          os.path.exists(os.path.join(ckpt, "raw.jsonl")))
    # Folder checkpoint rusak (berupa file, bukan folder): run tidak
    # boleh mati.
    bad = os.path.join(tmp, "bukan-folder")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("x")
    summary4 = auto.run_auto(
        config_path, db_path, raw_path, os.path.join(tmp, "state.json"),
        headed=False, mode="all", max_posts_per_round=2, sleep_s=0,
        max_rounds=1, max_minutes=0, analyze=False,
        login_fn=fake_login, collect_fn=fake_collect,
        checkpoint_dir=bad)
    check("checkpoint gagal tidak mematikan run", summary4["rounds"] == 1)

    print()
    if failures:
        print("%d kasus gagal: %s" % (len(failures), failures))
        return 1
    print("0 kasus gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
