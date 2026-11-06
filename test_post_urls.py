#!/usr/bin/env python3
"""Tes offline filter URL postingan (v2.23).

Kasus nyata (run Colab 2026-11-06): 12 dari 25 "postingan" yang
dikumpulkan ternyata bukan postingan — halaman pencarian dan tab
Reels lolos karena penanda lama ("/posts/", "/videos/", "/reel/")
juga cocok dengan URL pencarian ("/search/posts/?q=...",
"/search/videos/?q=..."). Akibatnya 354 dari 651 komentar (54%)
berasal dari URL bogus, termasuk 163 "promo" dari satu halaman
pencarian video.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import collect as collect_mod

# URL asli dari run Colab 2026-11-06.
REAL = [
    "https://www.facebook.com/groups/jualbelihpbebas/permalink/4348343795386397/",
    "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
    "https://www.facebook.com/permalink.php?story_fbid=pfbid0zkuFJTQa5oop4yC35wsg8ME3",
    "https://www.facebook.com/someone/posts/999/",
    "https://www.facebook.com/61595789443887/videos/pcb.122102916699526314/1115886488035952",
]
BOGUS = [
    "https://www.facebook.com/search/videos/?q=slot%20gacor&__rsidv2__=c4d39e59",
    "https://www.facebook.com/search/posts/?__cft__[0]=AZgJ_JPvrJt2KNXIg0CY-_WJifx3ox",
    "https://www.facebook.com/search/posts/?q=motor",
    "https://www.facebook.com/search/top/?q=slot%20gacor",
    "https://www.facebook.com/reel/?s=tab",
    "https://www.facebook.com/groups/123/",
    "https://www.facebook.com/someone",
    "https://example.com/groups/123/permalink/111/",
    "",
]


class FakePage:
    def __init__(self, hrefs):
        self._hrefs = hrefs

    def goto(self, url):
        pass

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, js):
        pass

    def eval_on_selector_all(self, selector, js):
        return list(self._hrefs)


def main():
    failures = []

    def check(name, cond):
        print(("OK  " if cond else "FAIL") + " " + name)
        if not cond:
            failures.append(name)

    for url in REAL:
        check("postingan asli diterima: %s" % url[:60],
              collect_mod.is_real_post_url(url))
    for url in BOGUS:
        check("URL bogus ditolak: %s" % (url[:60] or "(kosong)"),
              not collect_mod.is_real_post_url(url))

    # _collect_post_links: dari campuran href, hanya postingan asli
    # yang keluar (termasuk URL pencarian yang dulu lolos).
    page = FakePage(REAL + BOGUS + [REAL[0]])
    links = collect_mod._collect_post_links(page, 30)
    check("collect hanya kembalikan postingan asli",
          sorted(links) == sorted(set(REAL)))
    check("URL pencarian tidak ikut",
          not any("/search/" in u or "/reel/?" in u for u in links))

    print()
    if failures:
        print("%d kasus gagal: %s" % (len(failures), failures))
        return 1
    print("0 kasus gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
