# Catatan cek jalur indeks mesin pencari (2026-11-03, ~17:40 WIB)

Konteks: setelah scraping mentah Facebook gagal (lihat fb_scrape.py dan
test-slot-gacor.json), jalur 1 yang ditawarkan ke Vi adalah mencari postingan
Facebook yang sudah terindeks mesin pencari, tanpa login.

Hasil cek cepat ini (belum dijawab Vi, jadi JANGAN dikirim sebagai pesan
proaktif — ini hanya catatan kerja untuk agen utama saat Vi menjawab):
- Pencarian `site:facebook.com "slot gacor" komentar` → tidak ada hasil.
- Pencarian umum `facebook "slot gacor" postingan` → hasilnya mayoritas
  halaman non-Facebook yang sekadar menyebut Facebook (situs promo slot,
  blog, forum), bukan komentar Facebook yang bisa diambil isinya.

Kesimpulan sementara: jalur indeks mesin pencari tampaknya lemah untuk
mendapatkan komentar Facebook itu sendiri, bukan hanya menyebut-nyebutnya.
Kalau Vi memilih jalur 1, perlu diuji dulu dengan kata kunci dan operator
yang lebih spesifik, atau langsung dikombinasikan dengan jalur 2 (API resmi
ke postingan/halaman tertentu) — bukan diasumsikan langsung jalan.
