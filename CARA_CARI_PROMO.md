# Cara cari komentar promosi judi online (metode yang dipakai)

Definisi yang dipakai sekarang (koreksi user, 5 Nov 2026):
yang penting komentar PROMOSI judi online masuk dataset, tidak
peduli label spam/candidate. Jadi dataset promo = komentar spam +
komentar candidate dari detector v2. Yang dibuang hanya "other":
keluhan korban, peringatan penipuan, dan diskusi tanpa unsur
promosi — karena itu bukan promosi, meski terkait judi.

## 1. Apa itu komentar promosi? (tanda-tandanya)

Komentar dicatat sebagai promo kalau ada minimal satu dari ini:

1. **Brand kata+angka** — kata diikuti angka, mis. zeus88,
   maxwin98, dones999, pacinko88, dora77, tkp303, gogo77, pohon169.
   Termasuk varian dan sufiks: maximumwin99 (varian maxwin),
   taktik88live (taktik88 + sufiks), serta bentuk pisah (taktik 88).
   **Perluasan pola zeus777 (2026-11-05):** angka 2-5 digit (jadi
   zeus77777 / maxwin12345 ikut ketangkap; 1 digit sengaja tidak,
   supaya iphone7 / gta6 / ps5 tidak membanjiri dataset), keluarga
   dewa/mitos/raja (zeus, dewa/dewi, naga/dragon, raja/ratu/king,
   bintang/star, athena, hercules, thor, odin, poseidon, hades,
   apollo, plus stem batch sebelumnya: kuat, tirai, ajaib, nox,
   win), dan keluarga "lucky" untuk angka hoki 777/888/999 —
   jadi dewa99, raja88, naga888, slot777, gacor777, maxwin777,
   bintang88, dan bentuk pisah "zeus 777" / "dewa 99" semuanya
   ketangkap. Angka hoki berdiri sendiri ("777 gacor") juga
   sinyal, bukan cuma yang menempel ke kata.
   **Perluasan 2026-11-05: brand TANPA angka juga ditangkap** —
   SONITOTO, OPUNGWIN, GARUDAPLAY, YOKUBET, STARXBOY, LGOSULTAN,
   dan sejenisnya. Dulu nama tanpa angka sengaja diabaikan, sekarang
   tidak lagi: kalau nama itu muncul sebagai brand (apalagi setelah
   "main di / daftar di / coba di / cari / pindah ke"), itu sinyal
   promo. Calon brand baru juga dicari otomatis dari pola itu:
   kata setelah ajakan dihitung frekuensinya di analyze_spam.py
   (sekarang: sonitoto 2x, starxboy 1x, olympus 1x) — kata yang
   sering muncul setelah ajakan jadi pencarian batch berikutnya.
2. **Link** — URL apa pun di komentar, terutama shortlink /
   link bio yang mengarah ke situs. Di laporan, link tidak ditulis
   lengkap, cukup "link:present".
3. **Kontak** — Telegram, Viber, WhatsApp, atau @handle yang
   dipakai buat menghubungi bandar. Nomornya tidak ditulis di
   laporan, cukup jenisnya.
4. **Ajakan + konteks judi** — daftar, gabung, cobain, main di,
   app link, klik, download, apk, gas — bersamaan dengan wd, depo,
   gacor, rtp, slot, togel, bonus, freebet.
   **Perluasan frasa promo utuh:** situs gacor, web gacor, link
   gacor, link alternatif, link daftar, situs terpercaya, situs
   resmi, server luar / thailand / jepang, rtp live, pola gacor,
   bocoran pola, bonus new member, member baru, akun baru,
   wd lancar / cepat, cair kilat, gacor parah, klaim bonus,
   free spin, buy spin, scatter hitam, jam gacor. Frasa-frasa ini
   yang membuat komentar seperti "situs terpercaya dan gampang WD"
   atau "coba server luar, RTP di atas 90%" ketangkap, padahal
   tidak ada token angka dan tidak ada link di teksnya.
   Catatan jujur perluasan ini: recall naik, presisi turun sedikit
   — frasa positif bisa juga muncul di peringatan, tapi user
   memilih recall (tangkap semua promo) daripada presisi, dan
   label candidate tetap menandai komentar yang buktinya lebih
   lemah.
   **Perluasan v2.3 (2026-11-05, user: pasti semua ketangkap):**
   frasa testimoni (lagi wangi, player baru, modal receh, depo
   kecil, situs/tempat enak, jangan salah pilih, paling mantap/
   okee, emang beda, gak ada obat, saldo tebal, hadiah besar,
   taruhan kecil, rtp terlengkap, all provider, provider ternama,
   aura kemenangan), disclaimer promo (bukan sales, bukan
   promosi), rujukan link di bio (cek bio, cek dibio, link di
   bio, cek profil, info situs, info link, berbagi info,
   rekomendasi, rekomen, saran), slang konteks (wede, narik,
   jepe/jepeh, wangi, ketagihan, nagih, kemenangan, hadiah,
   dibayar, membayar, amanah, saldo, meledak, provider, mj,
   mahjong, bonanza, princess, gates, receh, tembus, jutaan,
   pelayanan, mantap, okee), dan keluarga game (bonanza,
   mahjong, princess, gates, wangi, hoki). Konteks saja (+1)
   tidak cukup jadi promo — keluhan "ketagihan judi, depo
   terus rungkad" tetap other. Bukti v2.3: 2 komentar batch
   sebelumnya yang lolos detector (balasan depo/profit ke
   utas bintang88 dan komentar "link di bio") sekarang
   ketangkap, dan dari 41 komentar browser batch promo
   terakhir, **0 yang masih lolos** dari dataset promo.
5. **Testimoni brand** — brand disebut positif tanpa ajakan
   eksplisit pun tetap promo, mis. "dapat tambahan dari JUNIOR88"
   atau "iseng tes hoki di TKP303". Ini yang membuat banyak
   komentar jadi candidate, bukan spam — tapi tetap promo, jadi
   tetap masuk dataset promo.

Huruf yang disamarkan ikut ditangkap: huruf fancy diubah jadi
huruf biasa dulu, leet (dep0, sl0t) dan spasi-spasi juga, sebelum
dicocokkan. Jadi "DAFTAR" huruf fancy + link tetap ketahuan.

## 2. Dari mana komentar itu dicari? (sumbernya)

1. **Pencarian brand** — cari nama brand yang sudah diketahui
   (kata+angka) di pencarian Postingan Facebook. Brand baru yang
   muncul di komentar langsung jadi pencarian berikutnya
   (snowball): mis. dari komentar maximumwin99 ketemu brand
   DORA77, dari DORA77 ketemu brand lain lagi.
2. **Pencarian frasa promo** — "slot gacor", "daftar slot",
   "link slot gacor", bentuk biasa + kutip, mode Posts + Top.
3. **Feed grup** — buka feed 1 grup per batch, bukan semua grup
   sekaligus. Grup yang isinya korban anti-judol biasanya 0 promo
   (itu hasil, bukan gagal), grup jual-beli / umum biasanya
   banyak promo nyangkut di komentar.
4. **Postingan video / reel ramai** — 1 postingan video bisa
   menyumbang 18 komentar promo sekaligus (terjadi di batch 1),
   jadi postingan ramai diprioritaskan, bukan postingan sepi.
5. **Postingan biasa / random (tanpa kata kunci judol)** — promosi
   judol sering menempel di postingan yang isinya bukan judol
   sama sekali: postingan peringatan scam, keluhan WD tidak
   dibayar, jual beli, sampai postingan motor. Buktinya dari
   pengumpulan: klaster AMAVI88 38 komentar menempel di 1
   postingan peringatan penipuan, klaster RAFA88 11 komentar di
   postingan keluhan, spam MEGA177/NABATIBET di postingan motor.
   Jadi pencariannya tidak boleh cuma kata kunci judol — ada mode
   `--mode random` di `search_retriever.py` yang mencari
   postingan lewat istilah netral sehari-hari (motor bekas, hp
   second, lowongan kerja, ...) plus feed grup, tanpa kata judi
   apa pun. Hit rate-nya memang lebih rendah dari pencarian
   brand, tapi detektor yang menyaring: komentar biasa jadi
   "other" dan tidak masuk dataset promo.

## 2b. Mode otomatis (auto.py)

Kalau mau jalan terus tanpa per run manual: `python3 auto.py`
menjalankan putaran discover -> collect -> analyze berulang sampai
dihentikan (Ctrl+C), atau sampai `--max-rounds N` / `--minutes M`.
Per putaran maks 25 postingan BARU (bukan batas total — putaran
berikutnya mengambil 25 baru lagi), jeda antar putaran default 10
menit. Kalau login/checkpoint gagal, run berhenti sendiri, tidak
mencoba lagi agresif; lanjutkan lain kali, postingan yang sudah
selesai tidak diulang karena statusnya tersimpan di DB.

## 3. Cara koleksinya (supaya tidak hilang di tengah jalan)

- Per batch MAKS 15 postingan. Batch besar dulu pernah gagal
  total dan laporannya hilang, jadi kecil tapi selesai itu
  lebih baik daripada besar tapi hilang.
- Per postingan: coba filter "All comments", klik "view more
  comments" + balasan sampai 6 putaran + scroll. Kalau Facebook
  berhenti memuat (mis. postingan 260 komentar cuma kebuka
  puluhan pertama), catat sebagai batas, pindah postingan
  berikutnya — jangan dipaksa.
- Setelah batch selesai, hasil LANGSUNG dimasukkan ke dataset
  (append + analyze) sebelum batch berikutnya. Jadi kalau batch
  berikutnya gagal, batch sebelumnya sudah aman.
- Dedupe per pasangan postingan + teks. Teks sama di postingan
  BERBEDA tetap disimpan, karena itu sinyal copy-paste promo.
  Frekuensi dihitung per postingan berbeda, bukan per baris
  mentah — satu komentar yang terduplikasi 16x di file mentah
  tidak boleh menggelembungkan hitungan brand.

## 4. Cara tahu itu promo atau bukan (skor, untuk transparansi)

Detector v2 memberi skor: brand keluarga +3, brand pola +2,
kontak +3, link +3, ajakan +2, konteks promo +1. Spam >= 5,
candidate 2-4, other < 2. Dataset promo = spam + candidate.
Candidate itu artinya "promo kemungkinan besar, tapi buktinya
tidak sekuat spam" — mis. brand doang tanpa ajakan/link. Bukan
berarti bukan promo, makanya tetap masuk dataset promo.

## 5. Batasan yang jujur

- Facebook tidak memuat semua komentar, jadi angka yang
  dilaporkan adalah yang benar-benar terlihat, bukan total
  Facebook.
- Postingan yang tampil "No comments yet" padahal di pencarian
  ada hitungan komentarnya tetap dicatat sebagai 0, bukan
  dikarang.
- Akun yang dipakai hanya akun throwaway khusus. Berhenti di
  checkpoint/blokir, tanpa posting/like/komen, tanpa membuka
  link promo, tanpa nama/ID profil.
- Sebelum dataset dishare / diupload, sensor nomor kontak dan
  link di file ekspor (lihat README_LOGIN_CSV.md).
