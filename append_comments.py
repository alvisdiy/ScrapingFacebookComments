#!/usr/bin/env python3
"""Tambah komentar hasil collect ke data/raw_comments.jsonl tanpa duplikat.

Ini jalur masuk komentar ke dataset: hasil collect browser-task
ditranskrip ke JSON lalu ditambahkan lewat skrip ini.

Pakai: python3 append_comments.py new_comments.json [data_path]
Format new_comments.json: list {"post_url", "base_keyword", "comment_text"}.
Baris yang (post_url, comment_text)-nya sudah ada dilewati; teks yang
sama di postingan BERBEDA tetap disimpan, karena itu sinyal copy-paste.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "data", "raw_comments.jsonl")


def main():
    src = sys.argv[1]
    data_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DATA
    existing = set()
    if os.path.exists(data_path):
        with open(data_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                existing.add((row.get("post_url"), row.get("comment_text")))
    new = json.load(open(src, encoding="utf-8"))
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    added = 0
    with open(data_path, "a", encoding="utf-8") as fh:
        for row in new:
            key = (row.get("post_url"), row.get("comment_text"))
            if key in existing:
                continue
            existing.add(key)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            added += 1
    print(
        "Ditambahkan %d baris baru, %d duplikat dilewati"
        % (added, len(new) - added)
    )


if __name__ == "__main__":
    main()
