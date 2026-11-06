#!/usr/bin/env python3
"""Tes offline envcheck.py (tanpa mengubah environment nyata)."""
import io
import sys
from contextlib import redirect_stderr
from unittest import mock

sys.path.insert(0, __import__("os").path.dirname(
    __import__("os").path.abspath(__file__)))

import envcheck


def main():
    failures = []

    def check(name, cond):
        print(("OK  " if cond else "FAIL") + " " + name)
        if not cond:
            failures.append(name)

    # 1. Playwright ada (lingkungan ini) -> kembalikan fungsinya.
    fn = envcheck.require_playwright()
    check("playwright ada -> sync_playwright dikembalikan",
          callable(fn) and fn.__name__ == "sync_playwright")

    # 2. Playwright tidak ada -> SystemExit + petunjuk venv/python.
    real_import = __import__("builtins").__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("playwright"):
            raise ImportError("No module named 'playwright'")
        return real_import(name, *args, **kwargs)

    err = io.StringIO()
    with mock.patch("builtins.__import__", side_effect=fake_import):
        with redirect_stderr(err):
            try:
                envcheck.require_playwright()
                raised = False
            except SystemExit as exc:
                raised = exc.code == 1
    msg = err.getvalue()
    check("playwright hilang -> berhenti (exit 1)", raised)
    check("pesan menyebut venv", "venv" in msg)
    check("pesan menyebut python, bukan python3",
          "BUKAN `python3`" in msg)
    check("pesan menyebut interpreter yang dipakai",
          "Cek interpreter" in msg)

    print()
    if failures:
        print("%d kasus gagal: %s" % (len(failures), failures))
        return 1
    print("0 kasus gagal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
