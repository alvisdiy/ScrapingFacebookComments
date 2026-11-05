#!/usr/bin/env python3
"""Percobaan scraping MENTAH Facebook (tanpa login) untuk kata kunci judi online.

Hanya mengakses endpoint publik, tanpa kredensial, tanpa bypass login.
Kalau Facebook mengarahkan ke halaman login, skrip melaporkannya apa adanya
dan berhenti untuk URL itu (tidak mencoba mengakali login wall).

Penggunaan:
    python3 fb_scrape.py "slot gacor" "togel online"
    python3 fb_scrape.py --out hasil.json "slot gacor"

Output: JSON berisi status tiap URL, deteksi login wall, dan cuplikan teks
yang berhasil diambil (kalau ada).
"""
import argparse
import json
import re
import sys
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

SEARCH_URLS = [
    "https://mbasic.facebook.com/search/posts/?q={q}",
    "https://m.facebook.com/search/posts/?q={q}",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

LOGIN_MARKERS = [
    "log in", "login", "masuk ke facebook", "create new account",
    "buat akun baru", "login.php", "checkpoint",
]


def fetch(session, url):
    try:
        resp = session.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException as exc:
        return {"url": url, "error": str(exc)}
    final_url = resp.url
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    lowered = (final_url + " " + text[:2000]).lower()
    login_wall = any(m in lowered for m in LOGIN_MARKERS) or "login" in final_url
    snippets = []
    if not login_wall:
        for el in soup.select("p, div"):
            t = el.get_text(" ", strip=True)
            if len(t) > 40:
                snippets.append(t)
            if len(snippets) >= 10:
                break
    return {
        "url": url,
        "final_url": final_url,
        "status": resp.status_code,
        "bytes": len(resp.content),
        "login_wall": login_wall,
        "snippets": snippets,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("keywords", nargs="+")
    parser.add_argument("--out", default="")
    parser.add_argument("--delay", type=float, default=3.0)
    args = parser.parse_args()

    session = requests.Session()
    results = []
    for kw in args.keywords:
        q = urllib.parse.quote(kw)
        for template in SEARCH_URLS:
            url = template.format(q=q)
            result = fetch(session, url)
            result["keyword"] = kw
            results.append(result)
            print(
                f"[{kw}] {url} -> status={result.get('status')} "
                f"login_wall={result.get('login_wall')} bytes={result.get('bytes')}"
            )
            time.sleep(args.delay)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
        print(f"Hasil disimpan ke {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
