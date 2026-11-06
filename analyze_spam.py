#!/usr/bin/env python3
"""Jalankan spam detector v2 di atas data/raw_comments.jsonl (offline).

Output:
- data/spam_comments.csv: satu baris per komentar UNIK (post_url +
  teks), dengan skor, label, sinyal, dan token brand. Komentar yang
  sama di postingan berbeda tetap baris terpisah (sinyal copy-paste).
- data/spam_summary.json: hitungan spam/candidate/other, daftar
  token brand spam + frekuensinya (per postingan berbeda, bukan per
  baris mentah, supaya satu komentar yang terduplikasi 16x di file
  mentah tidak menggelembungkan frekuensi).

Pakai: python3 analyze_spam.py
Lalu jalankan lagi setelah setiap batch live baru masuk raw_comments.
"""

import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spam_detector import classify_comment  # noqa: E402
from pipeline.collect import is_real_post_url  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main(base_dir=None):
    base = base_dir or HERE
    raw_path = os.path.join(base, "data", "raw_comments.jsonl")
    rows, seen = [], set()
    skipped_bogus = 0
    with open(raw_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            # v2.23: buang komentar dari URL yang bukan postingan
            # (halaman pencarian, tab Reels) — di run Colab
            # 2026-11-06, 354 dari 651 komentar berasal dari URL
            # seperti itu, termasuk 163 "promo" dari satu halaman
            # pencarian video. File mentah tidak diubah; yang
            # dibersihkan hanya output analisis ini.
            if not is_real_post_url(row.get("post_url", "")):
                skipped_bogus += 1
                continue
            key = (row.get("post_url", ""), row.get("comment_text", ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    out_rows = []
    label_counts = Counter()
    spam_token_posts = {}
    brand_context_counter = Counter()
    for row in rows:
        res = classify_comment(row.get("comment_text", ""))
        label_counts[res["label"]] += 1
        for w in res.get("brand_context_words", []):
            brand_context_counter[w] += 1
        if res["label"] == "spam":
            for tok in res["brand_tokens"]:
                spam_token_posts.setdefault(tok, set()).add(row.get("post_url", ""))
        out_rows.append({
            "post_url": row.get("post_url", ""),
            "base_keyword": row.get("base_keyword", ""),
            "label": res["label"],
            "score": res["score"],
            "brand_tokens": ",".join(res["brand_tokens"]),
            "families": ",".join(res["families"]),
            "signals": ";".join(res["signals"]),
            "comment_text": row.get("comment_text", ""),
        })

    csv_path = os.path.join(base, "data", "spam_comments.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()) if out_rows else [])
        w.writeheader()
        w.writerows(out_rows)

    # Dataset promo (koreksi user 2026-11-05): yang penting komentar
    # PROMOSI judi online masuk dataset, peduli label spam/candidate.
    # Jadi dataset promo = spam + candidate. "Other" (keluhan, peringatan,
    # diskusi tanpa ajakan/kontak/link/brand) tetap dibuang, karena itu
    # bukan promosi. Satu pengecualian yang diketahui: 1 komentar
    # peringatan penipuan yang lolos sebagai candidate karena mengandung
    # kata "daftar" di dalam daftar situs yang diperingatkan — noise
    # 1 dari 42, dicatat di sini supaya tidak dihitung sebagai bukti.
    promo_rows = [r for r in out_rows if r["label"] in ("spam", "candidate")]
    promo_path = os.path.join(base, "data", "promo_comments.csv")
    with open(promo_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()) if out_rows else [])
        w.writeheader()
        w.writerows(promo_rows)

    summary = {
        "distinct_comments": len(rows),
        "labels": dict(label_counts),
        "promo_comments": len(promo_rows),
        "skipped_bogus_urls": skipped_bogus,
        "spam_brand_tokens_by_posts": {
            tok: len(posts) for tok, posts in sorted(
                spam_token_posts.items(), key=lambda kv: -len(kv[1]))
        },
    }
    with open(os.path.join(base, "data", "spam_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print("Komentar unik: %d" % len(rows))
    if skipped_bogus:
        print("Dibuang (URL bukan postingan): %d komentar" % skipped_bogus)
    print("Label: %s" % dict(label_counts))
    print("Promo (spam+candidate): %d -> %s" % (len(promo_rows), promo_path))
    print("Calon brand baru dari pola 'main di / daftar di / coba di / "
          "cari / pindah ke X' (frekuensi, kata umum sudah dibuang): %s"
          % brand_context_counter.most_common(20))
    print("Token brand di komentar spam (per postingan): %s" % summary["spam_brand_tokens_by_posts"])
    print("-> %s" % csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
