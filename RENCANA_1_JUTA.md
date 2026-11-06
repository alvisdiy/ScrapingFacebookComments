# Rencana Skala Besar — Dataset 1.000.000 Komentar Promo Judol

> **Status: RENCANA SAJA, belum diimplementasi.** Dibuat 2026-11-06 atas
> permintaan Vi. Target dari dosen Vi: dataset berisi **1.000.000 komentar
> promo judi online** (komentar judol = total dataset; definisi "promo"
> tetap sama seperti sekarang: spam + candidate dari detektor v2.22).
> Semua angka di bawah ini adalah **perkiraan** dari hasil yang sudah
> terukur sejauh ini, bukan janji.

## 0. Posisi sekarang

- Dataset: **1.013 promo** (spam 530, candidate 483) dari **137 postingan**.
- Sisa ke target: **998.987 promo** (~99,9% masih kurang).
- Cara sekarang: 1 akun throwaway, 1 browser, berurutan, sengaja pelan
  supaya tidak kena checkpoint Facebook.

## 1. Hitungan dasar (dari data yang sudah terukur)

| Ukuran | Nilai | Sumber |
|---|---|---|
| Promo per postingan | ~5 (kisaran 3–7) | 1.013 promo / 137 postingan = 7,4 rata-rata, tapi cluster besar sudah ditambang; batch biasa ~2,6–5 |
| Postingan yang dibutuhkan | ~200.000 (kisaran 140rb–330rb) | 1.000.000 / 5 per postingan |
| Kecepatan per worker | ~20–25 postingan/jam | Setting best: 25 postingan/putaran, mode random ~1 jam/putaran, keywords ~80 mnt/putaran |
| Promo per jam per worker | ~100 (kisaran 60–125) | 5 promo × 20–25 postingan/jam |
| Promo per hari per worker | ~1.200 | 100/jam × 12 jam jalan |
| Total jam-worker untuk 1 juta | ~10.000 jam | 1.000.000 / 100 per jam |

Satu worker sendirian: ~10.000 jam = **~417 hari nonstop**. Jadi paralel
bukan pilihan — keharusan.

## 2. Berapa worker yang dibutuhkan

Satu **worker** = 1 akun Facebook throwaway + 1 runtime (Colab/Kaggle/PC)
yang menjalankan `auto.py` sendiri. Hitungan sudah termasuk cadangan
overhead duplikasi antar worker (~20%).

| Worker paralel | Perkiraan waktu ke 1 juta | Catatan |
|---|---|---|
| 10 | ~6–10 minggu | Paling gampang diatur, tapi lama |
| **25** | **~3–5 minggu** | **Rencana utama yang disarankan** |
| 50 | ~2 minggu | Cepat, tapi butuh 50 akun + 50 runtime + pengawasan ketat |

Angka di atas mengasumsikan tiap worker jalan ~12 jam/hari. Sesi Colab
gratis maksimal ~12 jam (dokumen resmi; meski tampilan Colab Vi sempat
menunjukkan estimasi sampai ~72 jam, itu tidak dijamin), jadi tiap worker
perlu di-restart ~1–2× sehari — sudah aman karena run bersifat resume-safe
(checkpoint per putaran, postingan yang sudah selesai tidak diulang).

## 3. Arsitektur: sharding (bagi kerja supaya tidak tumpang tindih)

Masalah utama paralel: dua worker bisa menemukan dan mengumpulkan
postingan yang sama. Solusinya bertahap:

**Tahap awal (tanpa infrastruktur baru) — sharding kata kunci:**
- 22 kata kunci dibagi ke dalam grup yang tidak saling tumpang tindih,
  mis. 5 grup × 4–5 kata kunci. Tiap worker hanya menjalankan grupnya.
- Worker terpisah untuk feed grup dan untuk mode random (postingan biasa).
- Tumpang tindih masih mungkin terjadi (satu postingan bisa mengandung
  dua kata kunci), tapi kecil. Sisa duplikasi dibersihkan saat merge.

**Kalau nanti perlu (opsional) — antrean pusat:**
- Satu tempat bersama (server kecil / database gratis) berisi daftar
  postingan yang sudah ditemukan; tiap worker "mengambil" sekelompok
  postingan dan menandainya sedang dikerjakan. Menghilangkan duplikasi
  hampir sepenuhnya, tapi butuh server yang selalu hidup.
- Keputusan: mulai dengan sharding kata kunci dulu. Antrean pusat hanya
  kalau duplikasi saat merge ternyata di atas ~30%.

**Merge (penggabungan):**
- Tiap worker menulis ke foldernya sendiri: `workers/w03/` berisi
  `fb_judol.db` + `raw_comments.jsonl` + `promo_comments.csv`
  (checkpoint otomatis ke Drive tiap putaran — sudah dibangun).
- Pekerjaan merge (di mesin utama, sekali jalan): kumpulkan semua
  `raw_comments.jsonl` → dedupe berdasarkan (post_url, comment_text)
  → jalankan `analyze_spam.py` (detektor v2.22) → `promo_comments.csv`
  final 1 juta baris + laporan sebaran (jumlah postingan, brand).
- Merge murah: Python biasa, hitungan menit–jam, dan bisa diulang kapan
  saja karena file mentah tiap worker disimpan utuh.

## 4. Akun & keamanan

- **1 worker = 1 akun Facebook.** Jangan pernah satu akun dipakai dua
  worker bersamaan (login bersamaan dari IP berbeda = checkpoint).
- Semua akun **throwaway**, bukan akun utama. Siapkan **cadangan +20%**
  (mis. 30 akun untuk 25 worker) karena sebagian akun pasti kena
  checkpoint/ban di tengah jalan.
- Pace per akun tetap seperti sekarang (delay 5 detik, jeda 300 detik
  antar putaran, maks 25 postingan/putaran). Paralelnya datang dari
  banyak akun, **bukan** dari menggeber satu akun.
- Login tiap akun: Opsi C (login manual di tab sendiri + export cookies)
  atau headed login. Headless `login.csv` sudah terbukti mati untuk akun
  yang punya 2FA + reCAPTCHA dari IP datacenter.
- Aturan yang tetap berlaku: read-only (tanpa posting/like/komentar),
  jangan buka link promo judi, jangan kumpulkan nama/ID pribadi
  komentator, berhenti saat checkpoint (jangan retry agresif).

## 5. Mesin / runtime

- **Colab gratis:** 1 runtime per akun Google. Butuh 25 akun Google
  untuk 25 worker (atau campuran dengan Kaggle/PC).
- **Kaggle:** maks 9 jam/sesi, Internet harus diaktifkan manual.
- **PC rumah (Windows):** 1 worker per PC (atau beberapa, dengan profil
  browser terpisah). IP rumah lebih "aman" di mata Facebook daripada IP
  datacenter, tapi jumlah PC terbatas.
- Checkpoint tiap worker ke subfolder Drive-nya sendiri
  (`fb-judol/workers/w03/`), supaya satu folder Drive tidak jadi
  rebutan dan gampang dipantau.
- Biaya: semuanya bisa jalan di tier gratis. Kalau nanti butuh yang
  dijamin (bukan gratis), Colab Pro+ sekitar $50/bulan per akun — itu
  opsi, bukan keharusan.

## 6. Kualitas data (jangan sampai 1 juta baris sampah)

- Definisi tidak berubah: **promo = spam + candidate**; konteks promo
  saja (+1) tetap `other`; keluhan/peringatan tanpa unsur promo tidak
  masuk dataset.
- Detektor tetap v2.22. Kalau brand baru muncul, tambah kata promo —
  jangan pernah turunkan threshold.
- **Sebaran wajib dipantau**, bukan cuma total: target 1 juta harus
  datang dari banyak postingan dan banyak brand. Laporan merge harus
  selalu mencantumkan jumlah postingan distinct dan brand teratas,
  seperti laporan 1.013 dulu (137 postingan, 30 postingan 10+ = 73%).
- Spot-check: tiap worker diambil ~20 komentar acak per minggu untuk
  dicek manual — kalau satu worker ternyata mengumpulkan komentar
  yang salah sasaran (mis. bukan judol), matikan dan perbaiki dulu.
- Batas yang sudah diketahui dan tetap berlaku: Facebook sering hanya
  menampilkan puluhan komentar padahal tertulis ratusan — jadi angka
  per postingan adalah yang terlihat, bukan total Facebook.

## 7. Fase & perkiraan waktu (rencana 25 worker)

| Fase | Isi | Perkiraan |
|---|---|---|
| **0 — Persiapan** | Bangun sharding + merge + monitoring; uji 2–3 worker 1–2 hari; ukur promo/jam/worker yang sebenarnya; validasi merge | ~1 minggu |
| **1 — Pilot** | 5 worker jalan 3–5 hari; ukur yield asli, ketahanan akun, keandalan checkpoint | ~1 minggu |
| **2 — Skala penuh** | Naik ke 25 worker; pantau harian (total promo, yield per worker, akun mati); ganti akun yang mati | ~3–5 minggu |
| **3 — Penutup** | Merge final, dedupe, jalankan detektor, verifikasi 1 juta, laporan sebaran, serahkan CSV + kode | ~2–3 hari |

**Total perkiraan: ~5–7 minggu** untuk 25 worker (termasuk persiapan
dan pilot). Dengan 10 worker: ~9–12 minggu. Dengan 50 worker: ~3–4
minggu. Semua dengan ketidakpastian ±50% — angka pastinya baru ketahuan
setelah pilot.

## 8. Risiko & mitigasi

| Risiko | Mitigasi |
|---|---|
| Akun kena checkpoint/ban | Akun cadangan +20%; pace pelan per akun; login Opsi C; jangan akun utama |
| Runtime Colab/Kaggle mati | Checkpoint ke Drive tiap putaran (sudah dibangun); resume-safe; restart ~1–2×/hari |
| Duplikasi antar worker | Sharding kata kunci; dedupe saat merge; terima overhead ~20% |
| Facebook mengubah tampilan / membatasi komentar | Sebar ke banyak postingan; jangan andalkan postingan raksasa |
| Detektor ketinggalan brand baru | Tinjau `other` yang hampir promo tiap minggu; tambah kata promo |
| Data hilang / merge salah | File mentah tiap worker tidak pernah dihapus; merge bisa diulang |
| Scraping melanggar ToS Facebook | Tetap read-only, akun throwaway, tanpa data pribadi; risiko ini ada sejak awal dan tidak berubah dengan skala — yang berubah hanya jumlah akunnya |

## 9. Yang harus dibangun (backlog implementasi — BELUM dikerjakan)

1. **Sharding di `auto.py` / `search_retriever.py`:** flag `--shard` atau
   config per worker (subset kata kunci / mode), supaya tiap worker
   hanya mengerjakan bagiannya.
2. **Worker ID & folder output:** tiap worker menulis ke foldernya
   sendiri (`--db`, `--raw`, `--state`, `--checkpoint-dir` per worker —
   sebagian argumennya sudah ada).
3. **`merge_workers.py`:** kumpulkan semua raw → dedupe → analisis →
   CSV final + laporan sebaran.
4. **Monitoring:** skrip kecil yang membaca semua checkpoint worker dan
   mencetak total promo, yield per worker, dan worker yang mati.
5. **Notebook varian worker:** sel run dengan parameter shard +
   `CHECKPOINT_DIR` per worker.
6. **Runbook:** langkah demi langkah menyalakan satu worker baru
   (siapkan akun → login Opsi C → jalankan → pantau → ganti kalau mati).

## 10. Keputusan yang masih dibutuhkan dari Vi (dan dosen)

1. **Deadline:** kapan 1 juta harus selesai? Ini yang menentukan jumlah
   worker (lihat tabel §2).
2. **Berapa akun & mesin yang bisa didapat?** (akun Google untuk Colab,
   akun Facebook throwaway, PC — sendiri, teman, lab?)
3. **Konfirmasi:** 1 juta = komentar promo, dataset = promo saja. Sudah
   dikonfirmasi Vi 2026-11-06: "1 juta itu komentar judolnya dan menjadi
   total semua komentarnya".
4. **Milestone perantara:** apakah boleh menyerahkan bertahap (mis.
   100 ribu dulu sebagai bukti jalan, lalu lanjut ke 1 juta)?
