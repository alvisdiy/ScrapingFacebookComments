# Facebook Judol Comment Scraper

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/alvisdiy/ScrapingFacebookComments/blob/main/ScrapingFacebookComments_Colab.ipynb)

Mengumpulkan komentar promosi judi online di Facebook, lalu menilai
mana yang promo dan mana yang bukan. Hasilnya jadi file CSV.

Kode ini sudah dipakai mengumpulkan **1.013 komentar promo unik**
dari 137 postingan berbeda.

> ⚠️ Pakai akun Facebook **throwaway/khusus, jangan akun utama**.
> Scraping login melanggar aturan Facebook, akun bisa dibatasi.

## 1. Install (sekali saja)

**Windows (paling gampang):** double-klik `setup_windows.bat`,
tunggu sampai selesai.

**Linux / Mac:**

```bash
pip install -r requirements.txt
playwright install chromium
```

## 2. Login (pilih satu cara)

**Cara A — login manual (disarankan).** Browser terbuka, login
sendiri di sana. Captcha dan kode 2FA bisa kamu selesaikan sendiri.
Sesi tersimpan otomatis, jadi cukup sekali:

```bash
python search_retriever.py --headed
```

**Cara B — pakai file `login.csv`.** Isi `login.csv` dari
`logins.csv.template` dengan akunmu sendiri, lalu:

```bash
python login_csv.py --headed
rm login.csv
```

**Cara C — di Colab / Kaggle.** Login manual di tab browsermu
sendiri, export cookies pakai ekstensi gratis Cookie-Editor,
upload `cookies.json` ke notebook:

```bash
python login_cookies.py --cookies cookies.json
```

Detail ketiga cara ini ada di `README_LOGIN_CSV.md`, dan langkah
demi langkah untuk Colab ada di notebook
(`ScrapingFacebookComments_Colab.ipynb`).

## 3. Jalankan

Mode otomatis — cari postingan, ambil komentarnya, analisis,
ulangi terus sampai kamu tekan **Ctrl+C**:

```bash
python auto.py --mode random
```

Per putaran maks 25 postingan baru (itu batas per putaran, bukan
batas total — putaran berikutnya mengambil 25 baru lagi).

Simpan otomatis ke Drive tiap putaran (supaya runtime Colab mati pun
datanya aman): tambah `--checkpoint-dir /content/drive/MyDrive/fb-judol/data`.
Tanpa flag itu, data hanya tersimpan di dalam runtime dan hilang kalau
runtime mati sebelum disimpan manual.

**Mode — mau cari postingan apa:**

| Mode | Yang dicari | Kapan dipakai |
|---|---|---|
| `all` (default) | Kata kunci judol + feed grup + postingan biasa | Mau semuanya |
| `keywords` | Kata kunci judol + feed grup | Mau fokus ke postingan judol |
| `random` | Feed grup + postingan biasa, tanpa kata kunci judol | Mau menangkap promo yang menempel di postingan biasa (peringatan scam, keluhan, jual beli, motor) |

Contoh:

```bash
python auto.py --mode all       # semuanya
python auto.py --mode keywords  # hanya postingan judol
python auto.py --mode random    # hanya postingan biasa
```

Mode ini sama untuk `search_retriever.py`.

Sekali jalan saja juga bisa:

```bash
python search_retriever.py --mode random
python details_retriever.py
python analyze_spam.py
```

(`details_retriever` menyimpan komentar ke database DAN ke
`data/raw_comments.jsonl`, jadi `analyze_spam` langsung melihat
komentar yang baru dikumpulkan.)

**Windows:** ganti `python` dengan `run_windows.bat`, contoh:
`run_windows.bat auto.py --mode random`

## 4. Lihat hasil

- `data/promo_comments.csv` — daftar komentar promo (ini dataset-nya)
- `data/spam_summary.json` — ringkasan jumlah (spam, kandidat, lain)

## Yang tidak ada di repo (sengaja)

Dataset, `login.csv`, `auth_state.json`, `cookies.json` — jangan
pernah kirim file-file itu ke siapa pun. Kalau salah satunya pernah
ter-push ke GitHub, anggap bocor: ganti password dan logout semua sesi.

## Kalau error

- **`No module named 'playwright'`** — kamu menjalankan script dengan
  Python yang salah. Aktifkan venv dulu, lalu pakai `python`
  (bukan `python3` di Windows), atau pakai `run_windows.bat`.
  Script sekarang memberi tahu ini langsung, bukan traceback buta.
- **Login gagal / captcha / 2FA** — login form tidak bisa
  menyelesaikannya sendiri. Pakai Cara A atau Cara C (login manual).
- **Komentar tidak ketemu / postingan tidak termuat** — itu normal,
  Facebook sering berhenti memuat daftar komentar di postingan besar.
  Angka yang dilaporkan adalah yang benar-benar terlihat.

## Mau tahu lebih dalam?

- `CARA_CARI_PROMO.md` — dari mana komentar dicari dan cara tahunya
  itu promo atau bukan
- `SPAM_STRATEGY.md` — cara kerja detektor (skor, label, aturan)
- `README_LOGIN_CSV.md` — semua cara login, lengkap dengan aturan
  keamanannya
- `LINKEDIN_ADAPT.md` — asal-usul kerangka kode ini
