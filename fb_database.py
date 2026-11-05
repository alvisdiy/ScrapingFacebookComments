#!/usr/bin/env python3
"""Skema SQLite adaptasi LinkedIn-Job-Scraper untuk Facebook.

Pemetaan dari LinkedIn:
  jobs (job_id, title, scraped)      -> posts (post_url, status)
  companies/salaries/dll (per job)   -> comments + brand_tokens (per post)
  insert_job_postings (dedupe by id) -> insert_posts (dedupe by post_url)
  details_retriever (scraped=0)      -> details_retriever (status='new')

Yang sengaja TIDAK ada di skema ini, padahal ada di LinkedIn:
  - tidak ada tabel orang/profil (LinkedIn punya companies; di sini
    fokusnya teks komentar + link postingan, bukan siapa yang nulis).
  - tidak ada kolom login/password apa pun.
"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    post_url TEXT PRIMARY KEY,
    base_keyword TEXT,
    query TEXT,
    mode TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    comments_checked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_url TEXT NOT NULL REFERENCES posts(post_url),
    comment_text TEXT NOT NULL,
    UNIQUE(post_url, comment_text)
);
CREATE TABLE IF NOT EXISTS brand_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id INTEGER NOT NULL REFERENCES comments(id),
    token TEXT NOT NULL,
    stem TEXT NOT NULL,
    digits TEXT NOT NULL,
    form TEXT NOT NULL,
    strength TEXT NOT NULL,
    context_terms TEXT NOT NULL DEFAULT '',
    UNIQUE(comment_id, token)
);
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def insert_posts(conn, posts):
    """Masukkan postingan baru saja. Kembalikan jumlah yang benar-benar baru."""
    cur = conn.cursor()
    new = 0
    for p in posts:
        cur.execute(
            "INSERT OR IGNORE INTO posts (post_url, base_keyword, query, mode)"
            " VALUES (?, ?, ?, ?)",
            (p["url"], p.get("base_keyword", ""), p.get("query", ""), p.get("mode", "")),
        )
        new += cur.rowcount
    conn.commit()
    return new


def insert_comment_with_tokens(conn, post_url, text, tokens):
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO comments (post_url, comment_text) VALUES (?, ?)",
        (post_url, text),
    )
    cur.execute(
        "SELECT id FROM comments WHERE post_url = ? AND comment_text = ?",
        (post_url, text),
    )
    comment_id = cur.fetchone()[0]
    inserted = 0
    for t in tokens:
        cur.execute(
            "INSERT OR IGNORE INTO brand_tokens"
            " (comment_id, token, stem, digits, form, strength, context_terms)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (comment_id, t["token"], t["stem"], t["digits"], t["form"],
             t["strength"], ",".join(t["context_terms"])),
        )
        inserted += cur.rowcount
    return inserted


def mark_post_done(conn, post_url, comments_checked):
    conn.execute(
        "UPDATE posts SET status = 'done', comments_checked = ? WHERE post_url = ?",
        (comments_checked, post_url),
    )
    conn.commit()
