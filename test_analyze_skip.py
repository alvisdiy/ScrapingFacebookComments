#!/usr/bin/env python3
"""Tes offline analyze_spam.py (v2.23): komentar dari URL yang bukan
postingan (halaman pencarian, tab Reels) dibuang dari output analisis,
bukan dari file mentah. File mentah tidak diubah; yang dibersihkan
hanya CSV + ringkasan hasil analisis.
"""
import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze_spam

ROWS = [
    # postingan asli, promo
    {"post_url": "https://www.facebook.com/groups/123/permalink/111/",
     "base_keyword": "slot gacor",
     "comment_text": "main di zeus88 gacor wd lancar"},
    # postingan asli, bukan promo
    {"post_url": "https://www.facebook.com/groups/123/permalink/111/",
     "base_keyword": "slot gacor",
     "comment_text": "situs ini nipu, depo gw ga balik"},
    # URL bogus: halaman pencarian video (dulu menyumbang 163 "promo")
    {"post_url": "https://www.facebook.com/search/videos/?q=slot%20gacor",
     "base_keyword": "slot gacor",
     "comment_text": "main di zeus88 gacor wd lancar"},
    # URL bogus: tab Reels
    {"post_url": "https://www.facebook.com/reel/?s=tab",
     "base_keyword": "slot gacor",
     "comment_text": "Find friends"},
    # URL bogus: halaman pencarian postingan
    {"post_url": "https://www.facebook.com/search/posts/?__cft__[0]=abc",
     "base_keyword": "slot gacor",
     "comment_text": "main di pacinko88 wd"},
    # postingan asli, teks UI Facebook (bukan komentar)
    {"post_url": "https://www.facebook.com/groups/123/permalink/222/",
     "base_keyword": "slot gacor",
     "comment_text": "UnreadWe noticed a new login from a device"},
]


def main():
    failures = []

    def check(name, cond):
        print(("OK  " if cond else "FAIL") + " " + name)
        if not cond:
            failures.append(name)

    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, "data"))
    with open(os.path.join(tmp, "data", "raw_comments.jsonl"),
              "w", encoding="utf-8") as fh:
        for r in ROWS:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    rc = analyze_spam.main(tmp)
    check("analyze selesai (rc 0)", rc == 0)

    summary = json.load(open(os.path.join(tmp, "data", "spam_summary.json"),
                             encoding="utf-8"))
    check("komentar unik hanya dari postingan asli (3)",
          summary["distinct_comments"] == 3)
    check("3 komentar URL bogus dibuang",
          summary["skipped_bogus_urls"] == 3)
    check("promo bersih 1 (zeus88 dari postingan asli)",
          summary["promo_comments"] == 1)
    check("teks UI 'Unread...' jadi other, bukan candidate",
          summary["labels"].get("other", 0) == 2)

    with open(os.path.join(tmp, "data", "spam_comments.csv"),
              encoding="utf-8") as fh:
        out = list(csv.DictReader(fh))
    check("CSV tidak mengandung URL pencarian/Reels",
          not any("/search/" in r["post_url"] or "/reel/" in r["post_url"]
                  for r in out))
    with open(os.path.join(tmp, "data", "promo_comments.csv"),
              encoding="utf-8") as fh:
        promo = list(csv.DictReader(fh))
    check("CSV promo hanya 1 baris dari postingan asli",
          len(promo) == 1
          and "/permalink/" in promo[0]["post_url"])

    # File mentah tidak diubah.
    with open(os.path.join(tmp, "data", "raw_comments.jsonl"),
              encoding="utf-8") as fh:
        check("file mentah tetap 6 baris", len(fh.readlines()) == 6)

    print()
    if failures:
        print("%d kasus gagal: %s" % (len(failures), failures))
        return 1
    print("0 kasus gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
