# Strategi dataset spam judol v2

Target "jadi" yang konkret (bukan sekadar "banyak"):
- minimal 50 komentar spam UNIK (postingan + teks berbeda),
- minimal 10 token brand berbeda di komentar spam,
- dari minimal 3 permukaan berbeda (pencarian brand, pencarian
  frasa, feed grup).

Posisi sekarang (5 Nov 2026, setelah detector v2):
- 34 komentar unik di dataset, 7 spam, 5 candidate, 22 other.
- Token brand di spam: pacinko88, bakricuan22, wintoto189,
  taktik88, maximumwin99 (5 token).
- Jadi masih jauh dari target: butuh +43 spam unik dan +5 token.

## Kenapa batch lama sedikit hasilnya

1. Prefilter browser cuma frasa persis + token persis, jadi komentar
   DAFTAR+link, kontak Telegram/Viber, dan varian maximumwin99
   lolos dari hitungan (atau cuma candidate).
2. Koleksi dangkal (beberapa putaran saja), postingan "No comments
   yet" dilewati, pencarian cuma 3 kata kunci persis.
3. Dataset lama mencampur keluhan korban / peringatan penipuan
   dengan promo — tanpa label spam, "banyak" tidak berarti "spam".

## Yang diubah di v2

- `spam_detector.py`: fancy unicode -> ascii, token family
  (maximumwin = maxwin family, wintoto = toto family, taktik88live
  = taktik88 + sufiks), sinyal kontak dan link (+3 masing-masing),
  CTA (+2), skor spam >= 5, candidate 2-4, other < 2.
- `analyze_spam.py`: output `data/spam_comments.csv` +
  `data/spam_summary.json`, frekuensi dihitung per postingan
  berbeda, bukan per baris mentah.
- Prefilter batch live baru: pakai kriteria v2 di atas, BUKAN
  daftar frasa lama. Keluhan tanpa CTA/kontak/link/brand TIDAK
  dicatat sebagai spam (masuk other, tidak masuk dataset spam).

## Pola batch live (diulang sampai target tercapai)

- Ukuran per batch: MAKS 15 postingan, supaya laporan selesai
  dan tidak hilang seperti batch 7 grup dulu. Setelah tiap batch,
  hasil langsung dimasukkan ke dataset (append + analyze_spam)
  sebelum batch berikutnya dimulai.
- Permukaan per batch, bergantian:
  a. Pencarian brand varian: maximumwin, taktik88, zeus, toto,
     dan brand baru yang muncul di batch sebelumnya.
  b. Pencarian frasa promo: "slot gacor", "daftar slot", "link
     slot gacor" (bentuk biasa + kutip, mode Posts + Top).
  c. Feed 1 grup seed per batch (mulai jualbelihpbebas, grup yang
     dulu memuat 207 komentar dalam 1 run).
- Expand komentar lebih dalam dari batch lama: coba filter
  "All comments" bila ada, klik "view more comments" + balasan
  sampai 6 putaran + scroll, bukan cuma beberapa klik. Kalau
  Facebook berhenti memuat, catat itu sebagai batas, pindah
  postingan berikutnya — jangan dipaksa berulang.
- Akun: hanya Yukii Ad (throwaway). Berhenti di checkpoint/blokir,
  tanpa posting/like/komen, tanpa membuka link promo, tanpa nama/ID
  profil.

## Aturan presentasi

- Di chat, nomor kontak dan URL promo TIDAK ditulis lengkap:
  cukup jenis sinyalnya (contact:telegram, link:present) + token
  brand-nya. Teks mentah hanya di file dataset lokal.
- Sebelum dataset dishare / diupload ke GitHub, sensor kontak dan
  link di file ekspor (lihat README_LOGIN_CSV.md).
