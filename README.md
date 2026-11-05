# Facebook Judol Comment Scraper

Kumpulan script untuk mengumpulkan dan mengklasifikasikan komentar
promosi judi online (judol) di Facebook — dari pencarian dan feed grup
— lalu menilainya dengan detektor spam/promosi berbasis aturan.

Hasil yang sudah dicapai dengan kode ini: **1.013 komentar promo unik**
(spam 530, kandidat 483) dari 137 postingan berbeda, dikumpulkan dalam
26 batch kecil (maks 15 postingan per batch), semuanya read-only dan
dengan akun throwaway khusus. Dataset-nya sendiri **tidak ikut di repo
ini** (lihat "Yang tidak ada di repo").

> ⚠️ Scraping saat login **melanggar aturan Facebook** dan bisa membuat
> akun dibatasi/dinonaktifkan. Pakai akun throwaway/khusus saja, jangan
> akun utama. Jangan dijalankan agresif atau 24/7. Script ini dibuat
> konservatif: jeda antar aksi, batas postingan per run kecil, dan
> read-only — tidak posting, like, komentar, follow, atau membuka
> tautan promo.

## Cara kerja (ringkas)

1. **Discover** — `search_retriever.py` mencari postingan lewat
   pencarian Facebook (istilah merek, mis. `zeus88`, `maxwin98`) atau
   feed grup. Satu run maks 25 postingan, default sekali jalan.
2. **Collect** — `details_retriever.py` membuka tiap postingan dan
   memuat komentarnya (klik "lihat komentar lainnya" + scroll, sampai
   6 putaran), lalu menyimpannya ke `data/raw_comments.jsonl`.
3. **Match / klasifikasi** — `spam_detector.py` menilai tiap komentar:
   token merek (huruf + 2–5 angka, mis. `zeus88`, `maxwin98`,
   `dones999`, termasuk varian leet/pisah/fancy unicode), tautan,
   kontak (WhatsApp/Telegram), ajakan (CTA), dan frasa promo.
   Skor: **spam ≥ 5, kandidat 2–4, lain < 2**. Dataset "promo" =
   spam + kandidat; keluhan korban dan peringatan scam tanpa unsur
   promo sengaja **tidak** masuk.
4. **Laporan** — `analyze_spam.py` menulis ringkasan ke
   `data/spam_summary.json` dan daftar promo ke `data/promo_comments.csv`;
   `to_csv.py` mengekspor postingan/komentar/token ke `csv_files/`.

Detail metode dan daftar sinyal promo: `SPAM_STRATEGY.md`,
`CARA_CARI_PROMO.md`. Adaptasi dari repo LinkedIn yang dipakai sebagai
kerangka: `LINKEDIN_ADAPT.md`.

## Instalasi

```bash
pip install -r requirements.txt
playwright install chromium   # butuh browser di mesin yang menjalankan
```

Kalau unduhan Chromium Playwright gagal, script otomatis fallback ke
Google Chrome sistem (`channel="chrome"`) bila tersedia.

## Login — dua cara

### Cara A (direkomendasikan): login manual, tanpa file password

Jalankan retriever pertama kali dengan `--headed`, login sendiri di
jendela browser yang terbuka, sesi tersimpan ke `auth_state.json`
(chmod 600). Run berikutnya pakai sesi itu, tanpa login ulang.

```bash
python3 search_retriever.py --headed
python3 details_retriever.py
```

Tidak ada username/password yang diterima script ini lewat argumen,
file txt, atau environment. `auth_state.json` masuk `.gitignore` —
**jangan pernah dibagikan**, isinya setara akses akun.

### Cara B (untuk teman): sekali login lewat `login.csv`

Kalau mau membagikan project ini ke teman supaya dia tidak perlu
login manual berulang, ada varian `login_csv.py`. Teman mengisi
`login.csv`-nya **sendiri di komputernya sendiri** (dari
`logins.csv.template`, isinya placeholder saja), lalu:

```bash
cp logins.csv.template login.csv   # lalu isi login.csv di editor
python3 login_csv.py --headed      # login + simpan sesi
python3 search_retriever.py        # berikutnya, pakai sesi, tanpa csv
python3 details_retriever.py
rm login.csv                       # disarankan setelah sesi tersimpan
```

Aturan varian ini (lengkapnya di `README_LOGIN_CSV.md`):

- Jangan pernah kirim `login.csv` ke siapa pun, termasuk ke Muse —
  password tidak pernah dicetak, dilog, atau disimpan script ini ke
  file lain; yang disimpan hanya sesi browser.
- Jangan pernah commit `login.csv` / `auth_state.json` ke GitHub.
  Keduanya sudah ada di `.gitignore`; cek `git status` sebelum push.
- Kalau Facebook menampilkan checkpoint / kode 2FA, script menunggu
  penyelesaian manual di jendela browser sampai 300 detik. Jadi
  "tanpa login manual sama sekali" tidak dijamin — yang dihemat adalah
  login manual **berulang**.

## Cara pakai

```bash
# 1. Cari postingan (maks 25/run, satu kali jalan)
python3 search_retriever.py --help

# 2. Ambil komentar dari postingan yang ditemukan
python3 details_retriever.py --help

# 3. Analisis offline dari data yang sudah terkumpul (tanpa browser/login)
python3 details_retriever.py --offline
python3 to_csv.py
python3 analyze_spam.py
```

Alur tanpa browser yang dipakai setelah tiap batch: transkrip komentar
ke JSON → `append_comments.py` (tambah ke `data/raw_comments.jsonl`,
dedupe per pasangan postingan+teks; teks sama di postingan berbeda
tetap disimpan sebagai sinyal copy-paste) → `details_retriever.py
--offline` → `to_csv.py` → `analyze_spam.py`.

Pipeline lama (tahap discover → collect → match → report) masih ada
di `pipeline/` + `run_pipeline.py`:

```bash
python3 run_pipeline.py --stage all --headed   # pertama kali (login manual)
python3 run_pipeline.py --stage collect        # lanjutkan collect saja
python3 run_pipeline.py --stage match          # cocokkan ulang tanpa browser
```

## Tes

```bash
python3 test_spam_detector.py    # harus: 0 kasus gagal
python3 test_brand_tokens.py     # harus: 10/10
python3 -m py_compile *.py pipeline/*.py
```

## File

- `search_retriever.py` — discovery postingan (pencarian/feed grup).
- `details_retriever.py` — pengambilan komentar (+ mode `--offline`).
- `spam_detector.py` — detektor spam/promosi v2.22 (+ aturan skor).
- `brand_tokens.py` — pencocok token merek (huruf + angka).
- `analyze_spam.py` — ringkasan label + `data/promo_comments.csv`.
- `append_comments.py` — ingest komentar baru (dedupe postingan+teks).
- `to_csv.py` — ekspor CSV postingan/komentar/token.
- `fb_database.py` — penyimpanan SQLite (`data/fb_judol.db`).
- `login_csv.py` + `logins.csv.template` — varian login sekali (Cara B).
- `pipeline/` + `run_pipeline.py` — pipeline staged lama.
- `fb_login_scrape.py` — script utama awal (Playwright, login manual).
- `keywords.txt` — daftar kata kunci awal.
- `data/search_queue_1000.json` — antrean istilah pencarian (diabaikan
  git karena di dalam `data/`; lihat "Yang tidak ada di repo").

## Yang tidak ada di repo (sengaja)

- `data/` — dataset mentah (komentar berisi tautan promo verbatim).
- `csv_files/`, `*.db` — ekspor dan database lokal.
- `login.csv`, `logins.csv`, `auth_state.json` — kredensial / sesi.
- `hasil.csv` — output run lama.

Semua itu sudah ada di `.gitignore`. Kalau salah satunya pernah
ter-push, anggap password/sesi itu bocor: ganti password dan logout
semua sesi. Tautan promo di dataset mentah harus disensor sebelum
dibagikan ke siapa pun, dan nomor telepon tidak pernah disimpan —
hanya marker `[nomor telepon dihapus]`.

## Cakupan data

Yang dikumpulkan: teks komentar yang mengandung sinyal promo, tautan
postingan sumber, dan waktu pengambilan. Script ini **sengaja tidak**
mengumpulkan nama profil, ID profil, atau data pribadi komentator —
fokusnya ke konten komentar, bukan ke orangnya.

## Catatan

- DOM Facebook sering berubah, jadi selector komentar bersifat
  heuristik dan mungkin perlu disesuaikan sewaktu-waktu.
- Facebook sering berhenti memuat daftar komentar di postingan besar;
  angka yang dilaporkan adalah yang benar-benar terlihat, bukan total
  yang diklaim Facebook.
- Reels umumnya bukan permukaan pengumpulan (beberapa komentar reel
  tercatat kalau muncul di hasil pencarian).
- Script mencatat apa adanya: kalau tidak ada komentar yang ditemukan
  untuk satu kata kunci, itu dilaporkan, bukan dikarang.
