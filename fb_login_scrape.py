#!/usr/bin/env python3
"""Scraper komentar Facebook berbasis kata kunci, memakai sesi login
akun milik user sendiri.

KEAMANAN — BACA DULU:
- Script ini TIDAK menerima username/password lewat argumen, file txt,
  variabel environment, atau cara lain apa pun.
- Login HANYA dilakukan user sendiri di jendela browser (mode headed)
  saat sesi belum ada. Setelah login berhasil, sesi disimpan lokal ke
  file state (default auth_state.json) dan dipakai ulang di run
  berikutnya. File state itu setara akses akun: jangan dibagikan.
- Data yang dikumpulkan: teks komentar yang mengandung kata kunci,
  link postingan sumber, dan waktu pengambilan. Script ini sengaja
  TIDAK mengumpulkan ID profil atau daftar orang.

Penggunaan:
    python3 fb_login_scrape.py --keywords-file keywords.txt --out hasil.csv
    python3 fb_login_scrape.py --keywords-file keywords.txt --out hasil.csv --headed
"""
import argparse
import csv
import os
import sys
import time
import urllib.parse
from datetime import datetime, timezone

SEARCH_URL = "https://www.facebook.com/search/posts/?q={q}"
LOGIN_URL = "https://www.facebook.com/"


def load_keywords(path):
    keywords = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            kw = line.strip()
            if kw and not kw.startswith("#"):
                keywords.append(kw)
    return keywords


def is_logged_in(context):
    try:
        return any(c.get("name") == "c_user" for c in context.cookies())
    except Exception:
        return False


def wait_for_login(page, context, timeout=300):
    """Tunggu user login manual di jendela browser (maks `timeout` detik)."""
    print("Belum ada sesi login. Silakan login Facebook di jendela browser")
    print("yang terbuka (ketik sendiri kredensialmu di sana), lalu tunggu.")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_logged_in(context):
            return True
        time.sleep(5)
    return False


def collect_post_links(page, limit):
    hrefs = page.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.href)"
    )
    links = []
    seen = set()
    for href in hrefs:
        if not isinstance(href, str):
            continue
        if (
            ("facebook.com" in href)
            and (
                "/posts/" in href
                or "/permalink/" in href
                or "/story.php" in href
                or "/videos/" in href
                or "/reel/" in href
            )
            and href not in seen
        ):
            seen.add(href)
            links.append(href)
        if len(links) >= limit:
            break
    return links


def collect_comments(page, keywords, limit):
    texts = page.eval_on_selector_all(
        '[dir="auto"]', "els => els.map(e => e.textContent)"
    )
    found = []
    seen = set()
    lowered_keywords = [k.lower() for k in keywords]
    for raw in texts:
        if not isinstance(raw, str):
            continue
        text = " ".join(raw.split())
        if len(text) < 10 or len(text) > 2000:
            continue
        low = text.lower()
        if any(kw in low for kw in lowered_keywords) and text not in seen:
            seen.add(text)
            found.append(text)
        if len(found) >= limit:
            break
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords-file", default="keywords.txt")
    parser.add_argument("--out", default="hasil.csv")
    parser.add_argument("--state", default="auth_state.json")
    parser.add_argument("--max-posts-per-keyword", type=int, default=10)
    parser.add_argument("--max-comments-per-post", type=int, default=20)
    parser.add_argument("--delay", type=float, default=5.0)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    keywords = load_keywords(args.keywords_file)
    if not keywords:
        print(f"Tidak ada kata kunci di {args.keywords_file}")
        return 1

    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as p:
        headed = args.headed or not os.path.exists(args.state)
        browser = p.chromium.launch(headless=not headed, args=["--no-sandbox"])
        if os.path.exists(args.state):
            context = browser.new_context(storage_state=args.state)
        else:
            context = browser.new_context()
        page = context.new_page()

        if not is_logged_in(context):
            page.goto(LOGIN_URL)
            if not wait_for_login(page, context):
                print("Login tidak terdeteksi dalam batas waktu. Berhenti.")
                browser.close()
                return 1
            context.storage_state(path=args.state)
            print(f"Sesi login tersimpan ke {args.state} (jangan dibagikan).")

        for kw in keywords:
            url = SEARCH_URL.format(q=urllib.parse.quote(kw))
            print(f"\n[{kw}] mencari: {url}")
            try:
                page.goto(url)
                page.wait_for_timeout(4000)
                for _ in range(4):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                post_links = collect_post_links(page, args.max_posts_per_keyword)
            except Exception as exc:
                print(f"[{kw}] gagal memuat hasil pencarian: {exc}")
                continue
            print(f"[{kw}] {len(post_links)} postingan ditemukan")
            for post_url in post_links:
                try:
                    page.goto(post_url)
                    page.wait_for_timeout(4000)
                    for _ in range(3):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(1500)
                    comments = collect_comments(
                        page, keywords, args.max_comments_per_post
                    )
                except Exception as exc:
                    print(f"  gagal membuka {post_url}: {exc}")
                    continue
                print(f"  {post_url[:80]}... -> {len(comments)} komentar cocok")
                now = datetime.now(timezone.utc).isoformat()
                for text in comments:
                    rows.append(
                        {
                            "keyword": kw,
                            "post_url": post_url,
                            "comment_text": text,
                            "scraped_at": now,
                        }
                    )
                time.sleep(args.delay)
            time.sleep(args.delay)
        browser.close()

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["keyword", "post_url", "comment_text", "scraped_at"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSelesai. {len(rows)} komentar tersimpan ke {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
