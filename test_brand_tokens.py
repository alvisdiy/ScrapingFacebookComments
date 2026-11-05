#!/usr/bin/env python3
"""Tes offline matcher brand+angka. Jalankan: python3 test_brand_tokens.py

Kasus: 3 contoh user, 3 token nyata dari dataset lama, 3 negatif yang
tidak boleh diklaim sebagai promo (iphone15, tahun, depo 50).
"""

import sys

from brand_tokens import find_brand_tokens


def tokens(text):
    return [(t["token"], t["strength"]) for t in find_brand_tokens(text)]


CASES = [
    ("coba di zeus88 gacor banget", [("zeus88", "strong")]),
    ("maxwin98 wd 2jt makasih infonya", [("maxwin98", "strong")]),
    ("main di dones999 langsung wd", [("dones999", "strong")]),
    ("Iseng coba 200rb, main di PACINKO88 wd 2jt", [("pacinko88", "strong")]),
    ("Baru main langsung di kasi wd aja tkp di BAKRICUAN22", [("bakricuan22", "strong")]),
    ("main di Wintoto189, wd 2jt", [("wintoto189", "strong")]),
    ("coba zeus 88 linknya dong", [("zeus88", "strong")]),
    ("iphone15 bagus banget kameranya", [("iphone15", "candidate")]),
    ("tahun 2026 masih aja rame", []),
    ("depo 50 bonus 20k buat 10 orang", []),
]


def main():
    failed = 0
    for text, expected in CASES:
        got = tokens(text)
        ok = got == expected
        failed += not ok
        print("%s %-55s -> %s (harap %s)" % ("OK " if ok else "FAIL", text, got, expected))
    print("\n%d/%d lulus" % (len(CASES) - failed, len(CASES)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
