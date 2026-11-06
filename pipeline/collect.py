"""Tahap discover & collect untuk pipeline scraper komentar Facebook.

LOGIN — BACA DULU:
Sama seperti fb_login_scrape.py: modul ini TIDAK menerima username /
password lewat argumen, file txt, environment, atau cara lain apa pun.
Login HANYA dilakukan user sendiri di jendela browser (headed) pada run
pertama; sesi disimpan lokal ke file state dan dipakai ulang. File state
itu setara akses akun: jangan dibagikan.

Perilaku: read-only, jeda antar aksi, batas postingan/komentar dari
config. Tidak posting, like, komentar, atau add friend.
"""

import json
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from envcheck import close_browser_quietly

LOGIN_URL = "https://www.facebook.com/"
SEARCH_POSTS_URL = "https://www.facebook.com/search/posts/?q={q}"
SEARCH_TOP_URL = "https://www.facebook.com/search/top/?q={q}"

MORE_COMMENTS_TEXT = [
    "View more comments",
    "Lihat komentar lainnya",
    "View previous comments",
    "Lihat komentar sebelumnya",
    "View all comments",
    "Lihat semua komentar",
    "View replies",
    "Lihat balasan",
    "View more replies",
    "Lihat balasan lainnya",
]

POST_LINK_MARKERS = ("/posts/", "/permalink/", "/story.php", "/videos/", "/reel/")


def _is_logged_in(context):
    try:
        return any(c.get("name") == "c_user" for c in context.cookies())
    except Exception:
        return False


def ensure_login(p, state_path, headed):
    """Buka browser + pastikan login. Kembalikan (browser, context, page)."""
    try:
        browser = p.chromium.launch(headless=not headed, args=["--no-sandbox"])
    except Exception:
        # Fallback: pakai Google Chrome sistem kalau chromium Playwright
        # belum terinstal (mis. download CDN gagal).
        browser = p.chromium.launch(
            headless=not headed, args=["--no-sandbox"], channel="chrome"
        )
    if os.path.exists(state_path):
        context = browser.new_context(storage_state=state_path)
    else:
        context = browser.new_context()
    page = context.new_page()
    if not _is_logged_in(context):
        page.goto(LOGIN_URL)
        print("Belum ada sesi login. Silakan login Facebook di jendela")
        print("browser yang terbuka (ketik sendiri kredensialmu di sana).")
        deadline = time.time() + 300
        while time.time() < deadline:
            if _is_logged_in(context):
                break
            time.sleep(5)
        else:
            close_browser_quietly(browser)
            raise RuntimeError("Login tidak terdeteksi dalam 300 detik.")
        context.storage_state(path=state_path)
        print("Sesi login tersimpan ke %s (jangan dibagikan)." % state_path)
    return browser, context, page


def _collect_post_links(page, limit):
    hrefs = page.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.href)"
    )
    links, seen = [], set()
    for href in hrefs:
        if not isinstance(href, str) or "facebook.com" not in href:
            continue
        if any(m in href for m in POST_LINK_MARKERS) and href not in seen:
            seen.add(href)
            links.append(href)
        if len(links) >= limit:
            break
    return links


def _scroll(page, rounds, delay):
    for _ in range(rounds):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(int(delay * 1000))


def discover_posts(page, config):
    """Cari postingan untuk tiap kata kunci x bentuk query x mode search.

    Mengembalikan list {"base_keyword", "query", "mode", "url"}.
    Juga menambahkan seed_post_urls dari config (base_keyword="seed").
    """
    delay = float(config.get("delay_seconds", 5.0))
    max_per_query = int(config.get("max_posts_per_query", 30))
    found, seen = [], set()

    for seed in config.get("seed_post_urls", []):
        if seed not in seen:
            seen.add(seed)
            found.append(
                {"base_keyword": "seed", "query": "", "mode": "seed", "url": seed}
            )

    for kw in config.get("keywords", []):
        queries = []
        for form in config.get("query_forms", ["plain"]):
            queries.append(kw if form == "plain" else '"%s"' % kw)
        for query in queries:
            for mode in config.get("search_modes", ["posts"]):
                template = (
                    SEARCH_POSTS_URL if mode == "posts" else SEARCH_TOP_URL
                )
                url = template.format(q=urllib.parse.quote(query))
                try:
                    page.goto(url)
                    page.wait_for_timeout(4000)
                    _scroll(page, 5, 2)
                    links = _collect_post_links(page, max_per_query)
                except Exception as exc:
                    print("[%s/%s] gagal: %s" % (kw, mode, exc))
                    links = []
                print(
                    "[%s | %s | %s] %d postingan"
                    % (kw, query, mode, len(links))
                )
                for link in links:
                    if link not in seen:
                        seen.add(link)
                        found.append(
                            {
                                "base_keyword": kw,
                                "query": query,
                                "mode": mode,
                                "url": link,
                            }
                        )
                time.sleep(delay)
    return found


def discover_group_posts(page, config):
    """Kumpulkan postingan dari feed grup-grup seed di config.

    Grup-grup ini adalah tempat komentar judol ditemukan pada run
    sebelumnya, jadi feed-nya adalah permukaan pencarian tambahan
    selain pencarian kata kunci. Mengembalikan list yang sama
    formatnya dengan discover_posts (base_keyword="group").
    """
    delay = float(config.get("delay_seconds", 5.0))
    max_per_group = int(config.get("max_posts_per_group", 20))
    found, seen = [], set()
    for gurl in config.get("seed_groups", []):
        try:
            page.goto(gurl)
            page.wait_for_timeout(4000)
            _scroll(page, 5, 2)
            links = _collect_post_links(page, max_per_group)
        except Exception as exc:
            print("[grup %s] gagal: %s" % (gurl, exc))
            links = []
        print("[grup %s] %d postingan" % (gurl, len(links)))
        for link in links:
            if link not in seen:
                seen.add(link)
                found.append(
                    {
                        "base_keyword": "group",
                        "query": gurl,
                        "mode": "group",
                        "url": link,
                    }
                )
        time.sleep(delay)
    return found


DEFAULT_RANDOM_QUERIES = [
    # Istilah netral sehari-hari, TANPA kata judi apa pun. Tujuannya
    # menemukan postingan biasa (random) yang komentarnya ternyata
    # ditempeli promosi judol — pola yang terbukti di pengumpulan
    # sebelumnya: spam AMAVI88/RAFA88/POA88 menempel di postingan
    # peringatan scam, keluhan WD, sampai postingan motor. Detektor
    # yang menyaring (komentar non-promo jadi "other"), jadi
    # permukaan yang berisik tidak masalah.
    "motor bekas", "hp second", "lowongan kerja", "viral hari ini",
    "jual beli", "sepak bola", "resep masakan", "kucing lucu",
    "info terbaru", "travel murah",
]


def discover_random_posts(page, config):
    """Cari postingan BIASA (random) lewat istilah netral, bukan judol.

    Sengaja TIDAK memakai kata kunci judi: yang dicari adalah
    postingan sehari-hari yang komentarnya bisa ditempeli promosi
    judol. Mengembalikan list {"base_keyword": "random", "query",
    "mode": "random", "url"}. Batas per query lebih kecil dari
    pencarian kata kunci (default 10) karena permukaan ini lebih
    berisik — detektor spam yang akan menyaringnya nanti.
    """
    delay = float(config.get("delay_seconds", 5.0))
    max_per_query = int(config.get("max_random_posts_per_query", 10))
    queries = config.get("random_queries") or DEFAULT_RANDOM_QUERIES
    found, seen = [], set()
    for query in queries:
        url = SEARCH_POSTS_URL.format(q=urllib.parse.quote(query))
        try:
            page.goto(url)
            page.wait_for_timeout(4000)
            _scroll(page, 5, 2)
            links = _collect_post_links(page, max_per_query)
        except Exception as exc:
            print("[random/%s] gagal: %s" % (query, exc))
            links = []
        print("[random | %s] %d postingan" % (query, len(links)))
        for link in links:
            if link not in seen:
                seen.add(link)
                found.append(
                    {
                        "base_keyword": "random",
                        "query": query,
                        "mode": "random",
                        "url": link,
                    }
                )
        time.sleep(delay)
    return found


GROUP_SEARCH_URL = "https://www.facebook.com/search/groups/?q={q}"


def extract_group_urls(post_urls):
    """Ambil URL grup dari URL postingan (pola /groups/<id-atau-nama>/)."""
    groups, seen = [], set()
    for url in post_urls:
        m = re.search(r"facebook\.com/groups/([^/?#]+)/", url)
        if m:
            g = "https://www.facebook.com/groups/%s/" % m.group(1)
            if g not in seen:
                seen.add(g)
                groups.append(g)
    return groups


def _collect_group_links(page):
    """Kumpulkan link profil grup dari halaman hasil pencarian."""
    try:
        hrefs = page.evaluate(
            "() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
        )
    except Exception:
        return []
    groups, seen = [], set()
    for href in hrefs:
        if "facebook.com/groups/" not in href:
            continue
        if any(x in href for x in ("/permalink/", "/posts/", "/search/", "/feed/")):
            continue
        clean = href.split("?")[0].rstrip("/") + "/"
        if clean not in seen and re.search(r"/groups/[^/]+/$", clean):
            seen.add(clean)
            groups.append(clean)
    return groups


def discover_groups_from_search(page, config):
    """Cari grup baru lewat tab Groups di pencarian Facebook.

    Ini permukaan discovery dinamis: grup yang ditemukan di sini
    dipromosikan ke seed_groups pada run berikutnya, jadi jangkauan
    membesar sendiri (efek bola salju), tidak terpaku pada seed awal.
    """
    delay = float(config.get("delay_seconds", 5.0))
    found, seen = [], set()
    for kw in config.get("keywords", []):
        try:
            page.goto(GROUP_SEARCH_URL.format(q=urllib.parse.quote(kw)))
            page.wait_for_timeout(4000)
            _scroll(page, 5, 2)
            links = _collect_group_links(page)
        except Exception as exc:
            print("[cari grup %s] gagal: %s" % (kw, exc))
            links = []
        print("[cari grup %s] %d grup" % (kw, len(links)))
        for link in links:
            if link not in seen:
                seen.add(link)
                found.append(link)
        time.sleep(delay)
    return found


def _click_more_comments(page):
    """Klik tombol 'lihat komentar lainnya' yang terlihat. Kembalikan jumlah klik."""
    clicked = 0
    for text in MORE_COMMENTS_TEXT:
        try:
            locator = page.locator("div[role='button']").filter(
                has_text=re.compile(re.escape(text), re.I)
            )
            count = locator.count()
            for i in range(min(count, 3)):
                try:
                    if locator.nth(i).is_visible():
                        locator.nth(i).click(timeout=3000)
                        clicked += 1
                        page.wait_for_timeout(1500)
                except Exception:
                    continue
        except Exception:
            continue
    return clicked


def extract_comment_texts(page):
    texts = page.eval_on_selector_all(
        '[dir="auto"]', "els => els.map(e => e.textContent)"
    )
    out, seen = [], set()
    for raw in texts:
        if not isinstance(raw, str):
            continue
        text = " ".join(raw.split())
        if 10 <= len(text) <= 2000 and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def collect_comments_deep(page, post_url, config):
    """Buka satu postingan dan muat komentar sedalam mungkin.

    Ulangi klik 'komentar lainnya' + scroll sampai jumlah komentar
    stabil 2 putaran, atau sampai batas config. Mengembalikan list teks.
    """
    max_comments = int(config.get("max_comments_per_post", 500))
    rounds = int(config.get("scroll_rounds", 12))
    delay = float(config.get("delay_seconds", 5.0))
    page.goto(post_url)
    page.wait_for_timeout(4000)
    texts, stable = [], 0
    for _ in range(rounds):
        _click_more_comments(page)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        new_texts = extract_comment_texts(page)
        if len(new_texts) == len(texts):
            stable += 1
        else:
            stable = 0
        texts = new_texts
        if len(texts) >= max_comments or stable >= 2:
            break
        time.sleep(delay)
    return texts[:max_comments]


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return default


def append_jsonl(path, rows):
    with open(path, "a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
