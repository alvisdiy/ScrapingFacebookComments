# Adaptasi LinkedIn-Job-Scraper -> Facebook Judol

Sumber: https://github.com/ArshKA/LinkedIn-Job-Scraper
(196 stars, Selenium + LinkedIn Voyager API + SQLite + CSV, 2 script
paralel: search_retriever + details_retriever.)

## Yang dipakai (strukturnya, bukan kodenya mentah-mentah)

| LinkedIn | Adaptasi Facebook di project ini |
|---|---|
| `search_retriever.py`: loop, API, simpan job_id baru, dedupe, laporan X/Y NEW | `search_retriever.py`: discovery via pencarian FB di browser (`pipeline/collect.py`), simpan post_url baru ke SQLite, laporan X/Y NEW POSTS |
| `details_retriever.py`: job_id scraped=0, maks 25/putaran, API detail, tidur 60 dtk | `details_retriever.py`: post status='new', maks 25/run, `collect_comments_deep`, jeda dari config (5 dtk) |
| `scripts/create_db.py` + `database_scripts.py`: jobs/companies/salaries/... | `fb_database.py`: posts / comments / brand_tokens |
| `to_csv.py`: satu CSV per tabel + gabungan | `to_csv.py`: posts/comments/brand_tokens + `brand_token_counts.csv` (frekuensi brand) |
| `json_paths/*.csv`: jalur atribut JSON | `pipeline/config.json`: keywords/varian/related (sudah ada) |

## Yang sengaja TIDAK disalin

1. **`logins.csv` (email + password di file).** Ini pola paling berbahaya
   di repo LinkedIn. Project ini dari awal menolaknya: login hanya
   manual oleh user di jendela browser, sesi di `auth_state.json`
   (lihat README.md). Tidak ada argumen/file/env password di script baru.
2. **Loop tanpa henti + API.** Facebook tidak punya API Voyager yang
   setara untuk pencarian komentar, jadi discovery tetap lewat DOM
   browser — dan defaultnya sekali jalan, bukan `while True`. `--loop`
   ada tapi harus diminta eksplisit, dan tetap bukan 24/7.
3. **Tabel orang/perusahaan.** LinkedIn menyimpan companies; di sini
   tidak ada tabel profil/penulis. Yang disimpan: teks komentar +
   link postingan + token brand.

## Yang baru: pola kata+angka (brand_tokens.py)

Promo judol sering bukan frasa ("slot gacor") tapi satu token:
`zeus88`, `maxwin98`, `dones999` — kata + 2-4 angka, kadang dipisah
(`zeus 88`, `zeus-88`). Matcher frasa lama tidak mencatat tokennya:
di dataset lama, PACINKO88 / BAKRICUAN22 / Wintoto189 cuma tercatat
sebagai sinyal "related: wd".

Aturan baru:
- Menempel (`zeus88`): stem >= 3 huruf + 2-4 angka.
- Terpisah (`zeus 88`): HANYA kalau stem-nya dikenal — kalau tidak,
  "depo 50", "buat 10 orang", "mau 2027" ikut kena (ini sempat
  gagal di tes pertama, lalu diperbaiki).
- Label: `strong` kalau stem dikenal ATAU ada konteks promo
  (wd/depo/link/main/cobain/...), `candidate` kalau cuma polanya.
  `candidate` (mis. `iphone15`) disimpan, bukan diklaim promo.
- Frekuensi dihitung per postingan + komentar yang berbeda, bukan
  per baris mentah — penting karena di dataset lama, satu komentar
  PACINKO88 yang sama muncul 16x di file mentah.

## Verifikasi (tanpa live run, tanpa login)

```
python3 test_brand_tokens.py        # 10/10, termasuk 3 contoh user
python3 details_retriever.py --offline   # dataset lama, tanpa browser
python3 to_csv.py --database data/fb_judol.db --folder csv_files
```

Hasil offline di dataset lama (45 baris mentah -> 31 komentar unik
per postingan, 13 postingan): 3 brand strong, 5 token total —
pacinko88 (2 komentar, 2 postingan), bakricuan22 (2 komentar,
1 postingan), wintoto189 (1 komentar, 1 postingan). Tidak ada
zeus88/maxwin98/dones999 di dataset lama itu — wajar, datasetnya
kecil dan dari November 2026, bukan bukti brand itu tidak ada.

## Live run berikutnya (belum dijalankan, butuh persetujuan user)

```
python3 search_retriever.py --headed   # pertama kali: login manual
python3 search_retriever.py            # berikutnya: pakai sesi
python3 details_retriever.py           # maks 25 postingan baru
python3 to_csv.py
```

Risiko tetap sama seperti project ini dari awal: scraping login
melanggar aturan Facebook dan bisa membatasi akun — makanya batas
kecil, jeda 5 detik, dan cron lama tetap PAUSED sampai user bilang
lanjut.
