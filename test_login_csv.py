#!/usr/bin/env python3
"""Tes offline _open_login_form di login_csv.py (halaman palsu).

Kasus nyata yang diperbaiki: di Colab, facebook.com/login tidak
menampilkan kolom #email dalam 30 detik (TimeoutError) — form-nya
bisa memakai selector lain, URL lain, atau tertutup banner cookie.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import login_csv


class FakePage:
    def __init__(self, ok_selectors, fail_urls=(), banner=False):
        self.ok = set(ok_selectors)
        self.fail_urls = set(fail_urls)
        self.banner = banner
        self.visited = []
        self.clicked = []
        self.shot = None
        self._url = "https://www.facebook.com/"

    def goto(self, url, timeout=60000):
        self.visited.append(url)
        self._url = url
        if url in self.fail_urls:
            raise Exception("navigasi gagal")

    def wait_for_timeout(self, ms):
        pass

    def click(self, selector, timeout=3000):
        if self.banner and "Allow all cookies" in selector:
            self.clicked.append(selector)
            return
        raise Exception("tidak ada tombol itu")

    def wait_for_selector(self, selector, timeout=10000):
        if selector in self.ok:
            return object()
        raise Exception("Timeout %s exceeded" % timeout)

    @property
    def url(self):
        return self._url

    def title(self):
        return "Facebook"

    def screenshot(self, path):
        self.shot = path
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("fake-png")

    def content(self):
        return "<html>fake</html>"


def main():
    failures = []

    def check(name, cond):
        print(("OK  " if cond else "FAIL") + " " + name)
        if not cond:
            failures.append(name)

    # 1. #email gagal, input[name='email'] + #pass berhasil.
    page = FakePage({"input[name='email']", "#pass"})
    got = login_csv._open_login_form(page)
    check("selector cadangan dipakai saat #email tidak muncul",
          got == ("input[name='email']", "#pass"))

    # 2. URL pertama gagal dibuka, URL kedua berhasil.
    page = FakePage({"#email", "#pass"},
                    fail_urls={"https://www.facebook.com/"})
    got = login_csv._open_login_form(page)
    check("URL cadangan dicoba saat URL pertama gagal",
          got == ("#email", "#pass")
          and page.visited == ["https://www.facebook.com/",
                               "https://www.facebook.com/login"])

    # 3. Banner cookie diklik kalau ada.
    page = FakePage({"#email", "#pass"}, banner=True)
    login_csv._open_login_form(page)
    check("tombol cookie diklik", len(page.clicked) == 1)

    # 4. Tidak ada form sama sekali -> berhenti jelas + simpan diagnosis.
    tmp = tempfile.mkdtemp()
    old = os.getcwd()
    os.chdir(tmp)
    try:
        page = FakePage(set())
        try:
            login_csv._open_login_form(page)
            raised = False
        except SystemExit as exc:
            raised = True
            msg = str(exc)
        check("berhenti dengan pesan jelas (bukan traceback buta)",
              raised and "tidak muncul" in msg)
        check("screenshot diagnosis disimpan",
              os.path.exists("login_page.png"))
        check("html diagnosis disimpan",
              os.path.exists("login_page.html"))
    finally:
        os.chdir(old)

    print()
    if failures:
        print("%d kasus gagal: %s" % (len(failures), failures))
        return 1
    print("0 kasus gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
