#!/usr/bin/env python3
"""Varian login lewat login.csv — untuk dibagikan ke teman, BUKAN untuk
dikirim ke Muse.

Bedanya dengan versi utama project ini:
- Versi utama (search_retriever.py / details_retriever.py): login
  manual oleh user di jendela browser, sesi disimpan ke auth_state.json.
  Tidak ada file password sama sekali. Ini yang tetap direkomendasikan.
- Varian ini: teman mengisi login.csv-nya SENDIRI di komputernya
  sendiri (dari logins.csv.template), script ini membaca file itu
  sekali, login lewat form Facebook, lalu menyimpan sesi ke
  auth_state.json. Setelah sesi tersimpan, login.csv TIDAK lagi
  dibutuhkan untuk run berikutnya — dan sebaiknya DIHAPUS.

ATURAN KEAMANAN VARIAN INI (baca sebelum dipakai / dibagikan):
1. JANGAN PERNAH kirim login.csv ke Muse, ke chat, atau ke siapa pun.
   Muse tidak butuh dan tidak boleh menerima password lewat file/chat.
2. JANGAN PERNAH commit login.csv atau auth_state.json ke GitHub.
   Keduanya sudah ada di .gitignore project ini. Sebelum push, cek
   `git status` dan pastikan tidak ada keduanya di daftar.
3. JANGAN pakai akun utama. Pakai akun throwaway/khusus saja, karena
   scraping login melanggar aturan Facebook dan akun bisa dibatasi /
   dinonaktifkan.
4. Password TIDAK PERNAH dicetak, dilog, atau disimpan oleh script ini
   ke file lain. Yang disimpan hanya sesi browser (auth_state.json) —
   dan file sesi itu sendiri setara akses akun, jadi jangan dibagikan.
5. Login otomatis tidak selalu berhasil: kalau Facebook menampilkan
   checkpoint / kode 2FA, script akan menunggu penyelesaian manual di
   jendela browser (mode headed) sampai 300 detik, lalu gagal dengan
   pesan jelas kalau tidak selesai. Jadi "tanpa login manual sama
   sekali" tidak bisa dijamin — yang dihemat adalah login manual
   BERULANG, karena sesi dipakai ulang setelahnya.

Format login.csv (salin dari logins.csv.template, satu baris saja):
    email,password
    akun-teman@example.com,GANTI_DENGAN_PASSWORD_ASLI

Penggunaan (di komputer teman, setelah pip install -r requirements.txt):
    cp logins.csv.template login.csv   # lalu isi login.csv di editor
    python3 login_csv.py --headed      # login + simpan sesi
    python3 search_retriever.py        # berikutnya, pakai sesi, tanpa csv
    python3 details_retriever.py
    rm login.csv                       # disarankan setelah sesi tersimpan
"""

import argparse
import csv
import os
import sys
import time

LOGIN_URLS = ("https://www.facebook.com/",
              "https://www.facebook.com/login")
EMAIL_SELECTORS = ("#email", "input[name='email']",
                   "[data-testid='royal_email']")
PASS_SELECTORS = ("#pass", "input[name='pass']",
                  "[data-testid='royal_pass']")
COOKIE_BUTTON_TEXTS = ("Allow all cookies",
                       "Allow essential and optional cookies",
                       "Terima semua cookie", "Izinkan semua cookie")
PLACEHOLDER_MARKERS = ("example", "ganti", "changeme", "password_here",
                       "isi_disini", "your_password")


def _dismiss_cookie_banner(page):
    """Klik tombol persetujuan cookie kalau muncul, abaikan kalau tidak."""
    for text in COOKIE_BUTTON_TEXTS:
        try:
            page.click("text=%s" % text, timeout=3000)
            print("Tombol cookie diklik: %s" % text)
            return
        except Exception:
            continue


def _wait_for_selector(page, selector, timeout_ms):
    try:
        page.wait_for_selector(selector, timeout=timeout_ms)
        return True
    except Exception:
        return False


def _open_login_form(page):
    """Buka halaman login dan tunggu form email+password muncul.

    Facebook tidak selalu menampilkan form yang sama: dari IP datacenter
    (Colab/Kaggle) kadang yang muncul halaman lain, atau form-nya memakai
    selector berbeda. Jadi: coba dua URL, tutup banner cookie dulu, lalu
    coba beberapa selector. Kalau tetap tidak ketemu, simpan screenshot
    + HTML halaman (SEBELUM password diisi, jadi tidak ada kredensial
    di file itu) dan berhenti dengan pesan jelas, bukan traceback buta.
    Kembalikan (email_selector, pass_selector).
    """
    for url in LOGIN_URLS:
        try:
            page.goto(url, timeout=60000)
        except Exception as exc:
            print("Gagal membuka %s: %s" % (url, exc))
            continue
        page.wait_for_timeout(3000)
        _dismiss_cookie_banner(page)
        for email_sel in EMAIL_SELECTORS:
            if not _wait_for_selector(page, email_sel, 10000):
                continue
            for pass_sel in PASS_SELECTORS:
                if _wait_for_selector(page, pass_sel, 5000):
                    print("Form login ketemu di %s (%s / %s)"
                          % (url, email_sel, pass_sel))
                    return email_sel, pass_sel
            print("Kolom email ketemu tapi kolom password tidak (%s)."
                  % url)
            return email_sel, None
    # Tidak ada form di semua URL yang dicoba — simpan bukti diagnosis.
    try:
        print("Halaman yang tampil: %s" % page.url)
        print("Judul halaman: %s" % page.title())
    except Exception:
        pass
    try:
        page.screenshot(path="login_page.png")
        with open("login_page.html", "w", encoding="utf-8") as fh:
            fh.write(page.content())
        print("Diagnosis disimpan ke %s + %s "
              "(diambil SEBELUM password diisi)."
              % (os.path.abspath("login_page.png"),
                 os.path.abspath("login_page.html")))
    except Exception as exc:
        print("Gagal menyimpan diagnosis: %s" % exc)
    raise SystemExit(
        "Form login Facebook tidak muncul. Kemungkinan: Facebook "
        "menampilkan halaman pemeriksaan (checkpoint / verifikasi robot) "
        "untuk IP ini, atau halaman login berubah. Lihat login_page.png "
        "untuk melihat halaman apa yang tampil, lalu coba Opsi A "
        "(upload auth_state.json dari komputermu sendiri) di notebook.")


LOGIN_FAILURE_PHRASES = (
    # (frasa di halaman/URL, arti untuk user)
    ("you've entered is incorrect", "password salah"),
    ("you entered is incorrect", "password salah"),
    ("yang anda masukkan salah", "password salah"),
    ("yang kamu masukkan salah", "password salah"),
    ("checkpoint", "checkpoint / verifikasi identitas"),
    ("confirm your identity", "checkpoint / verifikasi identitas"),
    ("konfirmasi identitas", "checkpoint / verifikasi identitas"),
    ("verifikasi identitas", "checkpoint / verifikasi identitas"),
    ("perlu memverifikasi", "checkpoint / verifikasi identitas"),
    ("two-factor", "kode 2FA"),
    ("two factor", "kode 2FA"),
    ("two-step", "kode 2FA"),
    ("two_step_verification", "kode 2FA"),
    ("enter the code", "kode 2FA"),
    ("enter your code", "kode 2FA"),
    ("masukkan kode", "kode 2FA"),
    ("kode login", "kode 2FA"),
    ("suspicious", "login mencurigakan"),
    ("mencurigakan", "login mencurigakan"),
    ("unusual login", "login mencurigakan"),
    ("login tidak biasa", "login mencurigakan"),
    ("locked", "akun terkunci"),
    ("terkunci", "akun terkunci"),
    ("disabled", "akun dinonaktifkan"),
    ("dinonaktifkan", "akun dinonaktifkan"),
)


def _describe_login_failure(page):
    """Setelah submit login tapi sesi tidak terbentuk: laporkan kenapa.

    Mencetak URL + judul halaman terakhir, mendeteksi penyebab dari
    teks halaman (password salah / checkpoint / 2FA / terkunci), dan
    menyimpan login_failed.png + login_failed.txt sebagai bukti.
    Password TIDAK ada di keduanya: kolom password hanya menampilkan
    titik-titik, dan teks halaman tidak memuat nilai isian.
    Kembalikan set label penyebab yang terdeteksi (bisa kosong).
    """
    url, title, text = "", "", ""
    try:
        url = page.url or ""
    except Exception:
        pass
    try:
        title = page.title() or ""
    except Exception:
        pass
    try:
        text = page.locator("body").inner_text(timeout=5000)
    except Exception:
        text = ""
    print("Halaman terakhir: %s" % url)
    print("Judul: %s" % title)
    low_text, low_url = text.lower(), url.lower()
    hints = {label for phrase, label in LOGIN_FAILURE_PHRASES
             if phrase in low_text or phrase in low_url}
    if hints:
        print("Yang terdeteksi di halaman: %s" % ", ".join(sorted(hints)))
    else:
        print("Tidak ada pesan error yang dikenali di halaman.")
    try:
        page.screenshot(path="login_failed.png")
        with open("login_failed.txt", "w", encoding="utf-8") as fh:
            fh.write("URL: %s\nJudul: %s\n\n%s" % (url, title, text[:2000]))
        print("Bukti disimpan ke %s + %s."
              % (os.path.abspath("login_failed.png"),
                 os.path.abspath("login_failed.txt")))
    except Exception as exc:
        print("Gagal menyimpan bukti: %s" % exc)
    return hints


def load_login(path):
    """Baca baris pertama yang valid dari login.csv. Kembalikan (email, password).

    Password dikembalikan hanya ke pemanggil di proses ini, tidak
    pernah dicetak. File yang hilang / kosong / masih placeholder
    ditolak dengan pesan, bukan ditebak.
    """
    if not os.path.exists(path):
        raise SystemExit(
            "login.csv tidak ditemukan. Salin dulu:\n"
            "  cp logins.csv.template login.csv\n"
            "lalu isi login.csv di komputermu sendiri (jangan dikirim ke siapa pun)."
        )
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise SystemExit("login.csv kosong / tanpa header email,password.")
        # Terima header gaya LinkedIn (emails,passwords) maupun email,password.
        email_key = "email" if "email" in reader.fieldnames else (
            "emails" if "emails" in reader.fieldnames else None)
        pass_key = "password" if "password" in reader.fieldnames else (
            "passwords" if "passwords" in reader.fieldnames else None)
        if email_key is None or pass_key is None:
            raise SystemExit(
                "Header login.csv harus email,password (ditemukan: %s)."
                % ",".join(reader.fieldnames))
        for row in reader:
            email = (row.get(email_key) or "").strip()
            password = (row.get(pass_key) or "").strip()
            if not email or not password:
                continue
            low = (email + " " + password).lower()
            if any(m in low for m in PLACEHOLDER_MARKERS):
                raise SystemExit(
                    "login.csv masih berisi placeholder. Isi dulu dengan "
                    "akunmu sendiri di komputermu, jangan kirim file ini "
                    "ke siapa pun.")
            return email, password
    raise SystemExit("login.csv tidak berisi baris login yang valid.")


def _is_logged_in(context):
    try:
        return any(c.get("name") == "c_user" for c in context.cookies())
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="login.csv")
    parser.add_argument("--state", default="auth_state.json")
    parser.add_argument("--headed", action="store_true",
                        help="Tampilkan browser (disarankan, supaya checkpoint/2FA bisa diselesaikan manual).")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    email, password = load_login(args.csv)
    # Password hanya dipakai untuk mengisi form login di proses ini;
    # tidak dicetak, tidak dilog, dan tidak ditulis ke file lain.

    from playwright.sync_api import sync_playwright

    headed = args.headed or not args.headless
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=not headed, args=["--no-sandbox"])
        except Exception:
            browser = p.chromium.launch(
                headless=not headed, args=["--no-sandbox"], channel="chrome")
        context = browser.new_context()
        page = context.new_page()
        try:
            email_sel, pass_sel = _open_login_form(page)
            if pass_sel is None:
                raise SystemExit(
                    "Kolom password tidak ditemukan setelah kolom email. "
                    "Lihat login_page.png untuk halaman yang tampil.")
            page.fill(email_sel, email)
            page.fill(pass_sel, password)
            # Tombol login Facebook: name="login", fallback tekan Enter.
            try:
                page.click('button[name="login"]', timeout=10000)
            except Exception:
                page.keyboard.press("Enter")
            # Tunggu sesi: cookie c_user, atau penyelesaian manual
            # checkpoint/2FA di jendela browser (maks 300 detik).
            # URL dicetak hanya saat berubah, supaya log tidak berisik.
            deadline = time.time() + 300
            last_url = ""
            while time.time() < deadline:
                if _is_logged_in(context):
                    break
                try:
                    url = page.url or ""
                except Exception:
                    url = ""
                if url != last_url:
                    last_url = url
                    print("Halaman: %s" % url)
                    if "checkpoint" in url or "two_factor" in url:
                        print("Facebook meminta verifikasi tambahan. "
                              "Selesaikan di jendela browser (kalau headed), "
                              "lalu tunggu...")
                time.sleep(5)
            else:
                hints = _describe_login_failure(page)
                print("Login tidak terdeteksi dalam 300 detik. "
                      "Sesi TIDAK disimpan.")
                if ("checkpoint / verifikasi identitas" in hints
                        or "kode 2FA" in hints):
                    print("Penyebab paling mungkin: Facebook meminta "
                          "verifikasi tambahan yang tidak bisa diselesaikan "
                          "headless. Login sekali di komputermu sendiri "
                          "(--headed), lalu upload auth_state.json (Opsi A "
                          "di notebook).")
                elif "password salah" in hints:
                    print("Facebook bilang password salah — cek lagi penulisan "
                          "password di login.csv (spasi di ujung? huruf "
                          "besar/kecil?).")
                elif "akun terkunci" in hints or "akun dinonaktifkan" in hints:
                    print("Akun tampaknya terkunci/dinonaktifkan. Coba login "
                          "biasa di browser dulu untuk memastikannya.")
                else:
                    print("Coba login biasa di browser dulu: kalau di sana "
                          "bisa login, berarti yang gagal hanya jalur "
                          "headless ini — pakai Opsi A (auth_state.json dari "
                          "komputermu sendiri).")
                return 1
            context.storage_state(path=args.state)
            try:
                os.chmod(args.state, 0o600)
            except Exception:
                pass
            print("Login berhasil. Sesi tersimpan ke %s (jangan dibagikan)." % args.state)
            print("Saran: hapus %s sekarang (rm %s) — run berikutnya sudah "
                  "pakai sesi, tidak butuh file itu lagi." % (args.csv, args.csv))
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
