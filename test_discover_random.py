#!/usr/bin/env python3
"""Tes offline discover_random_posts dengan halaman palsu (tanpa browser).

Memastikan mode random hanya memakai istilah netral (tidak ada kata
judi), hanya mengembalikan tautan postingan Facebook, memberi label
base_keyword "random", dan mendedupe URL yang sama.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import collect as collect_mod


class FakePage:
    def __init__(self, hrefs):
        self.visited = []
        self._hrefs = hrefs

    def goto(self, url):
        self.visited.append(url)

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, js):
        pass

    def eval_on_selector_all(self, selector, js):
        return list(self._hrefs)


HREFS = [
    "https://www.facebook.com/groups/123/permalink/111/",
    "https://www.facebook.com/permalink.php?story_fbid=abc&id=123",
    "https://www.facebook.com/someone/posts/999/",
    "https://www.facebook.com/groups/123/permalink/111/",  # duplikat
    "https://example.com/bukan-facebook",
    "https://www.facebook.com/search/posts/?q=motor",
]


def main():
    failures = []

    def check(name, cond):
        print(("OK  " if cond else "FAIL") + " " + name)
        if not cond:
            failures.append(name)

    page = FakePage(HREFS)
    config = {"delay_seconds": 0, "max_random_posts_per_query": 10,
              "random_queries": ["motor bekas", "hp second"]}
    posts = collect_mod.discover_random_posts(page, config)
    check("hanya tautan postingan facebook",
          all("facebook.com" in p["url"] for p in posts))
    check("bukan tautan facebook dibuang",
          not any("example.com" in p["url"] for p in posts))
    check("duplikat URL dibuang", len({p["url"] for p in posts}) == len(posts))
    check("semua berlabel random",
          all(p["base_keyword"] == "random" and p["mode"] == "random"
              for p in posts))
    check("URL pencarian memakai istilah netral",
          all("motor%20bekas" in u or "hp%20second" in u
              for u in page.visited)
          and not any("judol" in u or "slot" in u or "togel" in u
                      for u in page.visited))
    check("satu URL pencarian per istilah", len(page.visited) == 2)

    page2 = FakePage(HREFS)
    posts2 = collect_mod.discover_random_posts(
        page2, {"delay_seconds": 0, "max_random_posts_per_query": 10})
    check("tanpa random_queries pakai default netral",
          len(page2.visited) == len(collect_mod.DEFAULT_RANDOM_QUERIES)
          and all("facebook.com/search/posts" in u for u in page2.visited))
    check("default tidak mengandung kata judi",
          not any(w in " ".join(collect_mod.DEFAULT_RANDOM_QUERIES)
                  for w in ("judol", "judi", "slot", "togel", "gacor")))

    print()
    if failures:
        print("%d kasus gagal: %s" % (len(failures), failures))
        return 1
    print("0 kasus gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
