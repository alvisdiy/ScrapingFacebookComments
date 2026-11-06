#!/usr/bin/env python3
"""Cek dependensi Playwright dengan pesan error yang membantu.

Masalah yang sering terjadi (khususnya Windows): `pip install -r
requirements.txt` sukses, tapi script gagal dengan
`ModuleNotFoundError: No module named 'playwright'` — karena
interpreter yang menjalankan script BUKAN interpreter tempat pip
menginstall. Di Windows, `python3` biasanya menunjuk ke Python lain,
sementara venv yang aktif memakai `python`. Alih-alih traceback buta,
script-script repo ini memanggil require_playwright() dan user
mendapat petunjuk yang bisa langsung diikuti.
"""

import sys


def close_browser_quietly(browser):
    """Tutup browser tanpa traceback kalau koneksi driver-nya sudah
    mati — yang biasa terjadi habis Ctrl+C: interrupt menutup koneksi
    dulu, lalu browser.close() di blok finally ikut gagal dan
    traceback-nya menutupi Ctrl+C yang sebenarnya tidak apa-apa."""
    try:
        browser.close()
    except Exception:
        pass


def require_playwright():
    """Kembalikan playwright.sync_api.sync_playwright, atau berhenti
    dengan petunjuk instalasi kalau modulnya tidak ditemukan."""
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        print(
            "Playwright tidak ditemukan di Python yang menjalankan "
            "script ini.\n"
            "Kemungkinan besar kamu menjalankan script dengan interpreter "
            "yang salah (bukan venv tempat pip menginstall).\n"
            "Perbaiki:\n"
            "  1. Aktifkan venv dulu:\n"
            "       Windows (PowerShell): .\\venv\\Scripts\\Activate.ps1\n"
            "       Linux/Mac:            source venv/bin/activate\n"
            "  2. Install di venv itu:\n"
            "       python -m pip install -r requirements.txt\n"
            "       python -m playwright install chromium\n"
            "  3. Jalankan script dengan `python` (BUKAN `python3` di "
            "Windows):\n"
            "       python login_csv.py --headed\n"
            "  Atau pakai launcher Windows: setup_windows.bat sekali, "
            "lalu run_windows.bat <script> [argumen...]\n"
            "Cek interpreter yang sedang dipakai: %s" % sys.executable,
            file=sys.stderr)
        raise SystemExit(1)
