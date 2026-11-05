# Target dataset: 1000 komentar promo dulu, baru 10.000

Target user, 5 Nov 2026: **1000 komentar promo dulu**. Kalau 1000
ini benar-benar berhasil, baru target berikutnya **10.000**.
Target lama (50 promo) sudah lewat dan tidak dipakai lagi.

## Definisi yang dihitung

- **Komentar promo** = komentar unik (dedupe postingan + teks)
  yang diklasifikasi detector sebagai spam ATAU candidate.
  Komentar "other" (keluhan, peringatan, diskusi tanpa unsur
  promo) tidak dihitung, meski terkait judi.
- **Berhasil untuk 1000** (usulan, bukan keputusan user):
  1000 promo unik, dari banyak postingan dan banyak brand
  (bukan 1 klaster copy-paste), dengan proses batch + ingest
  yang stabil (selesai dan dilaporkan tiap batch, tanpa
  checkpoint/blokir berulang). Kalau 1000 tercapai tapi
  isinya cuma 1-2 klaster, itu belum berhasil — harus
  diperbaiki dulu sebelum naik ke 10.000.

## Posisi sekarang (5 Nov 2026, setelah batch merek baru 11 + detektor v2.22)

- Raw: 1063 baris
- Komentar unik: 1049
- **Promo unik: 1013** (spam 530, candidate 483, other 36)
- Postingan berbeda dengan promo: 137
- **Target 1000 TERCAPAI: 1013 promo unik (lebih 13)**

## Hitungan kasar ke 1000

- Batch promo terakhir (15 postingan): 41 komentar browser,
  39 masuk promo detector = **2,6 promo per postingan**.
- Dengan laju itu: 916 / 39 ≈ **24 batch lagi, ≈ 360 postingan**.
- Kalau dicampur feed grup (hasil grup terakhir 25 promo dari
  5 postingan = 5 per postingan), lajunya bisa lebih cepat:
  **≈ 18 batch, ≈ 270 postingan**.
- Waktu browser per batch ≈ 5-6 menit, jadi total kerja
  browser ≈ **2-2,5 jam**, ditambah ingest tiap batch.
  Ini TIDAK bisa dipaksakan dalam satu maraton: risiko
  checkpoint/blokir dan token cap naik kalau dipaksa, dan
  batch besar yang gagal akan kehilangan laporannya (sudah
  terjadi 2x pada 3 Nov). Jadi jalannya bertahap: batch
  15 postingan, ingest langsung, lapor, lanjut batch berikut.

## Hitungan kasar ke 10.000 (untuk gambaran saja, bukan janji)

- Setelah 1000: sisa 9.000 promo unik.
- Dengan laju 39 promo per batch: ≈ 230 batch lagi,
  ≈ 3.500 postingan, ≈ 23 jam kerja browser.
- Kesimpulan: 10.000 butuh proses yang sudah terbukti stabil
  di 1000 dulu, plus antrean pencarian yang jauh lebih besar
  dan cara kerja yang lebih otomatis — bukan sekadar
  mengulang batch manual yang sama 230x. Keputusan naik ke
  10.000 diambil SETELAH 1000 berhasil, bukan sekarang.

## Antrean pencarian (data/search_queue_1000.json)

- Total antrean: **284 istilah** (147 varian brand terbukti,
  107 brand baru, 20 frasa promo, 10 feed grup).
- Varian brand terbukti: stem brand yang sudah ada di dataset
  (tkp, dora, junior, mpo, kuat, tirai, ajaib, bintang, nox,
  dewa, zeus, maxwin, taktik, pacinko, bakricuan, wintoto,
  gogo, pohon, dewaslot) x angka (77, 88, 99, 777, 888, 999,
  123, 69) — istilah yang sudah dipakai dibuang.
- Brand baru: stem dewa/mitos/raja/slot (olympus, naga, raja,
  ratu, garuda, dragon, athena, hercules, thor, odin,
  poseidon, hades, apollo, kratos, slot, gacor, toto, cuan,
  jackpot, casino, vip, pro) x angka hoki (777, 888, 999,
  88, 99).
- Frasa: situs gacor, link alternatif, link daftar, situs
  terpercaya, server luar, rtp live, pola gacor, bonus new
  member, dan sejenisnya.
- Feed grup: 10 grup seed + grup yang terbukti ada promo di
  batch sebelumnya (bukan grup anti-judol yang sudah
  terbukti 0 promo).
- Aturan batch: **5 istilah x 3 postingan = 15 postingan**,
  atau 3 istilah x 5 postingan, atau 3 feed grup x 5 postingan.
  Postingan yang sudah ada di DB dilewati (dedupe), istilah
  yang sudah dipakai ditandai, brand baru dari hasil batch
  langsung ditambahkan ke antrean (snowball).

## Rencana lanjut sampai dataset jadi (user, 5 Nov 2026)

- Lanjutkan batch bertahap (15 postingan per batch, ingest
  langsung, lapor, batch berikutnya) sampai **1000 promo unik**
  tercapai. Setelah itu, baru upload kode ke GitHub (lihat
  bawah) — bukan sekarang, dan bukan datasetnya.
- Batch berikutnya yang sedang berjalan: varian tkp
  (tkp77, tkp88, tkp99, tkp777, tkp888, masing-masing
  3 postingan, total 15) dengan prefilter v2.4. Antrean
  tersisa 279 istilah pending setelah 5 istilah ini ditandai
  in_progress.
- Setelah 1000 tercapai: upload **kode saja** ke GitHub —
  varian login.csv (lihat README_LOGIN_CSV.md), bukan
  dataset, bukan file berisi kredensial.

## Paket GitHub (disiapkan, belum diupload)

- Yang DIUPLOAD nanti (kode saja): search_retriever.py,
  details_retriever.py, fb_database.py, to_csv.py,
  brand_tokens.py, spam_detector.py, analyze_spam.py,
  test_*.py, login_csv.py, logins.csv.template (placeholder
  saja), README.md, README_LOGIN_CSV.md, LINKEDIN_ADAPT.md,
  CARA_CARI_PROMO.md, SPAM_STRATEGY.md, PROGRESS_1000.md,
  requirements.txt, keywords.txt, pipeline/ (bila relevan).
- Yang TIDAK BOLEH diupload: login.csv / logins.csv berisi
  akun asli, auth_state.json, data/ (dataset mentah berisi
  link promo dan nomor kontak verbatim), csv_files/, *.db.
  Saat ini di project: login.csv TIDAK ADA, logins.csv
  TIDAK ADA, auth_state.json TIDAK ADA — jadi tidak ada
  kredensial yang bisa ikut terupload secara tidak sengaja.
  .gitignore sudah menutupi ketiganya plus data/, csv_files/,
  *.db. Project ini belum menjadi repo git, jadi upload
  nanti butuh tujuan repo (nama repo / akun GitHub user)
  yang akan ditanyakan saat dataset sudah jadi — tidak
  ditebak sekarang.
- Teman user nanti: salin logins.csv.template jadi login.csv
  di komputernya sendiri, isi 1 baris akun throwaway-nya
  sendiri, jalankan login_csv.py --headed, lalu hapus
  login.csv setelah sesi tersimpan. Muse tidak menerima
  password lewat chat/file.
