#!/usr/bin/env python3
"""Mode otomatis: cari + kumpulkan + analisis terus sampai dihentikan.

Satu putaran = discover (mode all/keywords/random) -> kumpulkan
komentar dari postingan BARU (maks --max-posts-per-round, default 25)
-> masukkan ke data/raw_comments.jsonl -> analisis detektor -> laporan.
Lalu tidur --sleep detik (default 600) dan ulangi sampai Ctrl+C,
--max-rounds N, atau --minutes M.

Kenapa masih ada batas 25 per putaran padahal "otomatis terus": batas
itu BUKAN batas total. Tiap putaran mengambil 25 postingan baru
berikutnya, jadi totalnya tidak terbatas selama masih ada postingan
baru. Batas per putaran menjaga tiap putaran selesai dan terlapor
(batch besar dulu pernah gagal total dan laporannya hilang), dan jeda
antar putaran menjaga akun tidak kena checkpoint.

Berhenti aman: Ctrl+C menutup browser dan mencetak ringkasan akhir.
Kalau login/checkpoint gagal, run berhenti sendiri, tidak mencoba
lagi secara agresif. Lanjutkan lain kali tanpa kehilangan apa-apa:
DB (status per postingan) dan raw_comments.jsonl bersifat append,
postingan yang sudah selesai tidak diulang.

Pakai:
    python3 auto.py --headed            # pertama kali (login manual)
    python3 auto.py                      # run berikutnya, pakai sesi
    python3 auto.py --mode random        # hanya postingan biasa
    python3 auto.py --max-rounds 10 --sleep 300
    python3 auto.py --minutes 120        # berhenti setelah 2 jam
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fb_database  # noqa: E402
from spam_detector import classify_comment  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def discover(page, config, mode):
    """Kumpulkan postingan baru sesuai mode. Kembalikan list dict."""
    from pipeline import collect as collect_mod
    posts = []
    if mode in ("all", "keywords"):
        posts += collect_mod.discover_posts(page, config)
    if mode in ("all", "keywords", "random"):
        posts += collect_mod.discover_group_posts(page, config)
    if mode in ("all", "random"):
        posts += collect_mod.discover_random_posts(page, config)
    seen, deduped = set(), []
    for post in posts:
        if post["url"] not in seen:
            seen.add(post["url"])
            deduped.append(post)
    return deduped


def summarize_raw(raw_path):
    """Hitung komentar unik + label promo dari raw_comments.jsonl."""
    seen, labels = set(), {"spam": 0, "candidate": 0, "other": 0}
    if not os.path.exists(raw_path):
        return 0, labels
    with open(raw_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            key = (row.get("post_url", ""), row.get("comment_text", ""))
            if key in seen:
                continue
            seen.add(key)
            labels[classify_comment(row.get("comment_text", ""))["label"]] += 1
    total = sum(labels.values())
    return total, labels


def append_raw(raw_path, rows):
    """Tambah komentar ke raw_comments.jsonl (dedupe postingan+teks)."""
    existing = set()
    if os.path.exists(raw_path):
        with open(raw_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                existing.add((row.get("post_url"), row.get("comment_text")))
    os.makedirs(os.path.dirname(raw_path) or ".", exist_ok=True)
    added = 0
    with open(raw_path, "a", encoding="utf-8") as fh:
        for row in rows:
            key = (row.get("post_url"), row.get("comment_text"))
            if key in existing:
                continue
            existing.add(key)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            added += 1
    return added


def run_auto(config_path, db_path, raw_path, state_path, headed, mode,
             max_posts_per_round=25, sleep_s=600.0, max_rounds=0,
             max_minutes=0, analyze=True, login_fn=None, collect_fn=None):
    """Jalankan putaran otomatis. Kembalikan ringkasan akhir (dict)."""
    from pipeline import collect as collect_mod
    import details_retriever as details_mod

    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = fb_database.connect(db_path)
    delay = float(config.get("delay_seconds", 5.0))
    if login_fn is None:
        login_fn = collect_mod.ensure_login
    if collect_fn is None:
        collect_fn = collect_mod.collect_comments_deep

    from envcheck import require_playwright
    sync_playwright = require_playwright()
    deadline = time.time() + max_minutes * 60 if max_minutes else None
    total_rounds = 0
    total_collected_posts = 0
    total_added_comments = 0
    summary = {"rounds": 0, "posts": 0, "comments": 0, "promo": 0}
    try:
        with sync_playwright() as p:
            browser, context, page = login_fn(p, state_path, headed=headed)
            try:
                while True:
                    total_rounds += 1
                    print("\n=== Putaran %d (mode %s) ===" % (total_rounds, mode))
                    posts = discover(page, config, mode)
                    new = fb_database.insert_posts(conn, posts)
                    print("Discovery: %d postingan, %d BARU"
                          % (len(posts), new))
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT post_url FROM posts WHERE status = 'new' "
                        "LIMIT ?", (max_posts_per_round,))
                    urls = [r[0] for r in cur.fetchall()]
                    base_kw = {p["url"]: p.get("base_keyword", "")
                               for p in posts}
                    round_comments = []
                    for url in urls:
                        try:
                            texts = collect_fn(page, url, config)
                        except Exception as exc:
                            print("Gagal %s: %s" % (url[:80], exc))
                            continue
                        details_mod._store_comments(conn, url, texts)
                        round_comments.extend(
                            {"post_url": url,
                             "base_keyword": base_kw.get(url, ""),
                             "comment_text": t} for t in texts)
                        total_collected_posts += 1
                        print("%s -> %d komentar"
                              % (url[:80], len(texts)))
                        time.sleep(delay)
                    added = append_raw(raw_path, round_comments)
                    total_added_comments += added
                    total, labels = summarize_raw(raw_path)
                    promo = labels["spam"] + labels["candidate"]
                    print("Putaran %d: %d postingan dikumpulkan, "
                          "+%d komentar baru. Total unik: %d, promo: %d "
                          "(spam %d, candidate %d, other %d)"
                          % (total_rounds, len(urls), added, total, promo,
                             labels["spam"], labels["candidate"],
                             labels["other"]))
                    if analyze:
                        import analyze_spam
                        analyze_spam.main()
                    summary = {"rounds": total_rounds,
                               "posts": total_collected_posts,
                               "comments": total_added_comments,
                               "promo": promo}
                    if max_rounds and total_rounds >= max_rounds:
                        print("Batas putaran tercapai (%d)." % max_rounds)
                        break
                    if deadline and time.time() >= deadline:
                        print("Batas waktu tercapai.")
                        break
                    print("Tidur %s detik (Ctrl+C untuk berhenti)..."
                          % sleep_s)
                    time.sleep(sleep_s)
            finally:
                browser.close()
    except KeyboardInterrupt:
        print("\nDihentikan pengguna (Ctrl+C).")
    except RuntimeError as exc:
        # ensure_login gagal (login/checkpoint tidak selesai): berhenti
        # sendiri, jangan coba lagi secara agresif.
        print("Berhenti: %s" % exc)
        return dict(summary, stopped=str(exc))
    print("\n=== Ringkasan akhir: %d putaran, %d postingan, "
          "+%d komentar, promo total %d ==="
          % (summary["rounds"], summary["posts"], summary["comments"],
             summary["promo"]))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="pipeline/config.json")
    parser.add_argument("--db", default="data/fb_judol.db")
    parser.add_argument("--raw", default="data/raw_comments.jsonl")
    parser.add_argument("--state", default="auth_state.json")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--mode", choices=["all", "keywords", "random"],
                        default="all")
    parser.add_argument("--max-posts-per-round", type=int, default=25,
                        help="Postingan baru per putaran (default 25). "
                        "Bukan batas total: putaran berikutnya mengambil "
                        "25 baru lagi.")
    parser.add_argument("--sleep", type=float, default=600.0,
                        help="Jeda detik antar putaran (default 600).")
    parser.add_argument("--max-rounds", type=int, default=0,
                        help="Berhenti setelah N putaran (0 = tanpa batas).")
    parser.add_argument("--minutes", type=float, default=0,
                        help="Berhenti setelah N menit (0 = tanpa batas).")
    args = parser.parse_args()
    run_auto(args.config, args.db, args.raw, args.state, args.headed,
             args.mode, args.max_posts_per_round, args.sleep,
             args.max_rounds, args.minutes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
