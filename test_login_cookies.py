#!/usr/bin/env python3
"""Tes offline login_cookies.py (tanpa browser / tanpa login nyata)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import login_cookies

COOKIE_EDITOR_JSON = json.dumps([
    {"domain": ".facebook.com", "expirationDate": 1790000000,
     "hostOnly": False, "httpOnly": True, "name": "c_user",
     "path": "/", "sameSite": "no_restriction", "secure": True,
     "session": False, "storeId": "0", "value": "12345"},
    {"domain": ".facebook.com", "httpOnly": True, "name": "xs",
     "path": "/", "sameSite": "lax", "secure": True,
     "session": True, "storeId": "0", "value": "abc%3Adef"},
    {"domain": ".google.com", "name": "NID", "path": "/",
     "secure": True, "session": True, "value": "xyz"},
])

NETSCAPE_TXT = """# Netscape HTTP Cookie File
.facebook.com\tTRUE\t/\tTRUE\t1790000000\tc_user\t12345
.facebook.com\tTRUE\t/\tTRUE\t1790000000\txs\tabc%3Adef
.google.com\tTRUE\t/\tFALSE\t1790000000\tNID\txyz
"""


class FakePage:
    def __init__(self, title="Facebook"):
        self._title = title

    def goto(self, url, timeout=60000):
        pass

    def wait_for_timeout(self, ms):
        pass

    def title(self):
        return self._title


class FakeContext:
    def __init__(self, cookies):
        self._cookies = cookies

    def cookies(self):
        return self._cookies

    def new_page(self):
        return FakePage()


class FakeBrowser:
    def __init__(self, cookies):
        self._cookies = cookies

    def new_context(self, storage_state=None):
        return FakeContext(self._cookies)

    def close(self):
        pass


class FakeChromium:
    def __init__(self, cookies):
        self._cookies = cookies

    def launch(self, **kwargs):
        return FakeBrowser(self._cookies)


class FakePW:
    def __init__(self, cookies):
        self.chromium = FakeChromium(cookies)

    def __call__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def main():
    failures = []

    def check(name, cond):
        print(("OK  " if cond else "FAIL") + " " + name)
        if not cond:
            failures.append(name)

    tmp = tempfile.mkdtemp()
    p_json = os.path.join(tmp, "cookies.json")
    with open(p_json, "w", encoding="utf-8") as fh:
        fh.write(COOKIE_EDITOR_JSON)
    cookies = login_cookies.load_cookies(p_json)
    check("JSON Cookie-Editor: hanya cookies facebook.com",
          len(cookies) == 2
          and {c["name"] for c in cookies} == {"c_user", "xs"})
    c_user = next(c for c in cookies if c["name"] == "c_user")
    check("expirationDate -> expires", c_user["expires"] == 1790000000)
    check("no_restriction -> sameSite None",
          c_user["sameSite"] == "None")
    xs = next(c for c in cookies if c["name"] == "xs")
    check("cookie sesi -> expires -1", xs["expires"] == -1)

    p_txt = os.path.join(tmp, "cookies.txt")
    with open(p_txt, "w", encoding="utf-8") as fh:
        fh.write(NETSCAPE_TXT)
    cookies2 = login_cookies.load_cookies(p_txt)
    check("Netscape txt: 2 cookies facebook.com",
          len(cookies2) == 2
          and {c["name"] for c in cookies2} == {"c_user", "xs"})
    check("Netscape: secure TRUE -> True",
          next(c for c in cookies2 if c["name"] == "c_user")["secure"] is True)

    state = login_cookies.build_storage_state(cookies)
    check("storage_state berisi cookies + origins",
          state["origins"] == [] and len(state["cookies"]) == 2)

    try:
        login_cookies.build_storage_state(
            [{"name": "sb", "value": "x"}])
        no_c_user_raised = False
    except SystemExit as exc:
        no_c_user_raised = "c_user" in str(exc)
    check("tanpa c_user ditolak dengan pesan jelas", no_c_user_raised)

    state_path = os.path.join(tmp, "auth_state.json")
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    logged_in, title = login_cookies.verify_state(
        state_path,
        playwright_fn=lambda: FakePW([{"name": "c_user", "value": "12345"}]))
    check("verifikasi lolos saat c_user ada", logged_in is True)
    logged_in2, _ = login_cookies.verify_state(
        state_path, playwright_fn=lambda: FakePW([{"name": "sb"}]))
    check("verifikasi gagal saat c_user tidak ada", logged_in2 is False)

    print()
    if failures:
        print("%d kasus gagal: %s" % (len(failures), failures))
        return 1
    print("0 kasus gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
