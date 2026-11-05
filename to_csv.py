#!/usr/bin/env python3
"""Ekspor SQLite ala LinkedIn to_csv.py, untuk Facebook.

LinkedIn: satu CSV per tabel + satu file gabungan job_postings.csv.
Di sini: posts.csv, comments.csv, brand_tokens.csv, plus satu file
yang paling berguna untuk pola ini — brand_token_counts.csv:
satu baris per token, dengan jumlah komentar, jumlah postingan,
jumlah yang strong, dan satu contoh link postingan. Token yang
paling sering diulang di banyak postingan itulah kandidat promo
copy-paste, bukan sekadar satu komentar iseng.

Tidak pakai pandas (LinkedIn pakai pandas); cukup sqlite3 + csv
stdlib supaya dependensinya tetap cuma playwright.
"""

import argparse
import csv
import os
import sqlite3


def _dump(conn, out_path, query):
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(rows)
    print("%s: %d baris" % (out_path, len(rows)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/fb_judol.db")
    parser.add_argument("--folder", default="csv_files")
    args = parser.parse_args()
    os.makedirs(args.folder, exist_ok=True)
    conn = sqlite3.connect(args.database)

    _dump(conn, os.path.join(args.folder, "posts.csv"),
          "SELECT * FROM posts ORDER BY post_url")
    _dump(conn, os.path.join(args.folder, "comments.csv"),
          "SELECT * FROM comments ORDER BY id")
    _dump(conn, os.path.join(args.folder, "brand_tokens.csv"),
          "SELECT * FROM brand_tokens ORDER BY token, id")
    _dump(conn, os.path.join(args.folder, "brand_token_counts.csv"),
          """
          SELECT bt.token, bt.stem, bt.digits, bt.form,
                 COUNT(DISTINCT bt.comment_id) AS n_comments,
                 COUNT(DISTINCT c.post_url) AS n_posts,
                 SUM(CASE WHEN bt.strength = 'strong' THEN 1 ELSE 0 END) AS n_strong,
                 MIN(c.post_url) AS example_post_url
          FROM brand_tokens bt
          JOIN comments c ON c.id = bt.comment_id
          GROUP BY bt.token, bt.stem, bt.digits, bt.form
          ORDER BY n_posts DESC, n_comments DESC, bt.token
          """)
    conn.close()
    return 0


if __name__ == "__main__":
    main()
