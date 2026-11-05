# Varian login.csv (untuk teman)

Ini varian terpisah dari versi utama. Versi utama tetap yang
direkomendasikan (login manual di browser, tanpa file password).
Varian ini ada karena satu alasan praktis: supaya teman bisa
menjalankan project ini di komputernya sendiri tanpa harus
mengulang login manual setiap kali — sesi disimpan sekali, lalu
dipakai ulang.

## Alur untuk teman (di komputer teman sendiri)

```bash
pip install -r requirements.txt
cp logins.csv.template login.csv
# buka login.csv di editor, isi 1 baris dengan akunnya sendiri
python3 login_csv.py --headed
python3 search_retriever.py
python3 details_retriever.py
python3 to_csv.py
rm login.csv   # disarankan, setelah sesi tersimpan
```

Setelah `login_csv.py` berhasil, file `login.csv` sudah tidak
dibutuhkan lagi. Run berikutnya (`search_retriever.py`,
`details_retriever.py`) memakai `auth_state.json`, bukan csv.

## Yang harus temanmu tahu sebelum pakai

1. **Pakai akun throwaway/khusus, bukan akun utama.** Scraping
   dengan login melanggar aturan Facebook; akun bisa dibatasi atau
   dinonaktifkan.
2. **Checkpoint / 2FA masih bisa muncul.** Kalau Facebook minta
   verifikasi tambahan, selesaikan manual di jendela browser yang
   terbuka (`--headed`). Kalau tidak selesai dalam 300 detik,
   script gagal dengan jelas dan sesi tidak disimpan. Jadi janji
   "tanpa login manual sama sekali" tidak berlaku untuk kasus itu —
   yang dihemat adalah login manual berulang.
3. **Hanya teks komentar + link postingan yang dikumpulkan.**
   Tidak ada nama/ID profil yang disimpan, tidak ada posting/like/
   komen yang dilakukan script.

## Checklist sebelum upload ke GitHub (penting)

File ini **tidak boleh** ikut ter-push, dalam keadaan apa pun:

- `login.csv` — berisi password plaintext
- `auth_state.json` — berisi sesi login (setara akses akun)
- `data/` dan `*.db` — dataset hasil scrape
- `csv_files/` — hasil ekspor

Keduanya (`login.csv`, `auth_state.json`) sudah ada di `.gitignore`.
Sebelum push, selalu cek:

```bash
git status
```

Kalau `login.csv` atau `auth_state.json` muncul di daftar, JANGAN
push. Kalau terlanjur ter-push, anggap password/sesi itu bocor:
ganti password akun itu segera dan logout semua sesi di Facebook.

Yang aman di-push: semua file `.py`, `logins.csv.template`,
`keywords.txt`, `pipeline/config.json`, README, dan file ini.
File `logins.csv.template` sengaja hanya berisi placeholder, bukan
kredensial asli.

## Yang TIDAK berubah

- **Jangan kirim `login.csv` ke Muse / ke chat.** Varian ini untuk
  teman menjalankan di komputernya sendiri. Muse tidak menerima,
  menyimpan, atau membutuhkan password siapa pun lewat file/chat.
- Script ini tidak pernah mencetak password ke terminal/log, dan
  tidak menulis password ke file lain. Yang ditulis hanya
  `auth_state.json` (sesi browser, chmod 600).
