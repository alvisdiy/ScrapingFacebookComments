#!/usr/bin/env python3
"""Login manual lewat cookies — untuk Colab / Kaggle (Opsi C).

Kenapa ada varian ini: di Colab/Kaggle tidak ada jendela browser yang
bisa dipakai login manual, dan login form headless sering mentok di
checkpoint/2FA yang tidak bisa diselesaikan dari sana. Alurnya:

  1. Di notebook, klik link "Buka Facebook di tab baru" — Facebook
     terbuka di tab browser KAMU SENDIRI.
  2. Login manual di tab itu (checkpoint / 2FA bisa kamu selesaikan
     sendiri, seperti login biasa).
  3. Export cookies facebook.com dengan ekstensi gratis Cookie-Editor
     (Chrome/Firefox) sebagai JSON, simpan sebagai cookies.json.
  4. Upload cookies.json ke Colab/Kaggle, jalankan script ini.
  5. Script mengubah cookies itu menjadi auth_state.json (sesi
     Playwright) dan memverifikasi loginnya. Setelah itu hapus
     cookies.json — run berikutnya pakai sesi, tidak butuh file itu.

ATURAN KEAMANAN (sama seperti login.csv):
- Cookies itu SETARA AKSES AKUN: siapa pun yang punya file cookies
  ini bisa memakai sesimu. JANGAN kirim ke siapa pun / ke chat,
  jangan commit ke GitHub (sudah di .gitignore).
- Pakai akun throwaway/khusus saja, bukan akun utama.
- Format yang diterima: JSON export Cookie-Editor / EditThisCookie,
  atau format Netscape cookies.txt.

Pakai:
    python3 login_cookies.py --cookies cookies.json
    python3 login_cookies.py --cookies cookies.json --no-verify
"""

import argparse
import json
import os
import sys

from envcheck import close_browser_quietly

SAMESITE_MAP = {
    "no_restriction": "None",
    "none": "None",
    "lax": "Lax",
    "strict": "Strict",
}


def load_cookies(path):
    """Baca cookies dari JSON (Cookie-Editor) atau Netscape txt.

    Kembalikan list dict Playwright: name, value, domain, path,
    expires, httpOnly, secure, sameSite.
    """
    if not os.path.exists(path):
        raise SystemExit(
            "File %s tidak ditemukan. Export dulu cookies facebook.com "
            "dari browsermu (ekstensi Cookie-Editor, format JSON) lalu "
            "upload ke sini." % path)
    with open(path, encoding="utf-8") as fh:
        raw = fh.read().strip()
    if not raw:
        raise SystemExit("File %s kosong." % path)
    if raw[0] in "[{":
        data = json.loads(raw)
        items = data.get("cookies") if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise SystemExit("Format JSON tidak dikenali (bukan list cookies).")
        cookies = []
        for c in items:
            domain = (c.get("domain") or "").lstrip(".")
            if "facebook.com" not in domain:
                continue
            exp = c.get("expirationDate")
            cookies.append({
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
                "expires": int(exp) if exp else -1,
                "httpOnly": bool(c.get("httpOnly", False)),
                "secure": bool(c.get("secure", False)),
                "sameSite": SAMESITE_MAP.get(
                    str(c.get("sameSite", "lax")).lower(), "Lax"),
            })
        return cookies
    # Format Netscape: domain \t flag \t path \t secure \t expires \t name \t value
    cookies = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, cpath, secure, expires, name, value = parts[:7]
        if "facebook.com" not in domain:
            continue
        cookies.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": cpath,
            "expires": int(float(expires)) if expires else -1,
            "httpOnly": False,
            "secure": secure.upper() == "TRUE",
            "sameSite": "Lax",
        })
    return cookies


def build_storage_state(cookies):
    """Ubah list cookies menjadi dict storage_state Playwright.

    Menolak kalau tidak ada cookie sesi (c_user) — artinya export
    dilakukan sebelum login, atau cookies-nya bukan dari facebook.com.
    """
    names = {c.get("name") for c in cookies}
    if "c_user" not in names:
        raise SystemExit(
            "Cookies tidak berisi sesi login (c_user tidak ada). "
            "Pastikan kamu SUDAH login di tab Facebook itu sebelum "
            "export cookies, dan export-nya mencakup facebook.com.")
    if "xs" not in names:
        print("Peringatan: cookie xs tidak ada — sesi mungkin tidak "
              "bertahan lama. Coba export ulang sesudah login.")
    return {"cookies": cookies, "origins": []}


def verify_state(state_path, playwright_fn=None):
    """Cek sesi benar-benar login: buka facebook.com, lihat c_user.

    Kembalikan (logged_in, title). playwright_fn hanya untuk tes
    (stub); default-nya Playwright asli.
    """
    if playwright_fn is None:
        from envcheck import require_playwright
        playwright_fn = require_playwright()
    with playwright_fn() as p:
        try:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        except Exception:
            browser = p.chromium.launch(
                headless=True, args=["--no-sandbox"], channel="chrome")
        context = browser.new_context(storage_state=state_path)
        page = context.new_page()
        try:
            page.goto("https://www.facebook.com/", timeout=60000)
            page.wait_for_timeout(5000)
            logged_in = any(
                c.get("name") == "c_user" for c in context.cookies())
            try:
                title = page.title() or ""
            except Exception:
                title = ""
            return logged_in, title
        finally:
            close_browser_quietly(browser)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cookies", default="cookies.json")
    parser.add_argument("--state", default="auth_state.json")
    parser.add_argument("--no-verify", action="store_true",
                        help="Lewati verifikasi login (simpan sesi saja).")
    args = parser.parse_args()

    cookies = load_cookies(args.cookies)
    print("%d cookies facebook.com dibaca." % len(cookies))
    state = build_storage_state(cookies)
    with open(args.state, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    try:
        os.chmod(args.state, 0o600)
    except Exception:
        pass
    print("Sesi tersimpan ke %s (jangan dibagikan)." % args.state)
    print("Saran: hapus %s sekarang (rm %s) — run berikutnya sudah "
          "pakai sesi." % (args.cookies, args.cookies))
    if args.no_verify:
        return 0
    logged_in, title = verify_state(args.state)
    print("Verifikasi: halaman '%s', sesi login: %s"
          % (title, "YA" if logged_in else "TIDAK"))
    if not logged_in:
        print("Cookies tersimpan tapi sesi tidak terverifikasi login. "
              "Kemungkinan cookies sudah kedaluwarsa atau export-nya "
              "tidak lengkap — login ulang di tab baru, lalu export lagi.")
        return 1
    print("Login terverifikasi. Lanjut ke sel JALANKAN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
