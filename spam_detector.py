#!/usr/bin/env python3
"""Detektor spam judol v2.23 - kenapa matcher lama kurang menangkap spam.

v2.23 (2026-11-06, dari analisis run Colab 651 komentar):
- keluarga brand baru auto/dapurpola/cici/swiftfrog (token kata+angka
  yang selama ini cuma +2); brand 2026 dan game+1000 sudah +3 lewat
  keluarga yang ada, tidak perlu tambahan;
- "coba" polos dan "login" dihapus dari daftar CTA ("coba" polos
  dihitung kondisional: +2 hanya kalau ada brand/link/kontak,
  supaya ajakan "coba sweetbonanza1000" tetap ketangkap tapi
  keluhan "coba buat grup... Semua slot itu nipu" tidak);
- teks UI Facebook ("Find friends", "Unread...", dsb) langsung
  other skor 0, bukan komentar.
Intinya tetap sama: yang harus ketangkap adalah komentar PROMOSI dan
spam AJAKAN main judi online — keluhan/peringatan dan teks UI bukan
promo dan tidak boleh masuk dataset.


Diagnosis dari 2 run terakhir (48 baris mentah, 15 postingan live):
1. Matcher frasa lama butuh frasa persis ("slot gacor", "maxwin").
   Tiga komentar live terakhir: 0 match frasa, padahal ketiganya
   konteks promo (DAFTAR + link, kontak Telegram/Viber, permintaan
   app link).
2. Matcher brand v1 cuma kenal token menempel persis stem+angka.
   Ia gagal di varian stem (maximumwin99 bukan "maxwin" persis),
   token + sufiks (taktik88live, angka di tengah), huruf fancy
   (DAFTAR ditulis dengan huruf mathematical bold, tidak dikenali),
   dan sinyal non-token (link URL dan kontak Telegram/Viber/WhatsApp
   sama sekali tidak dihitung, padahal itu ciri spam paling kuat).
3. Koleksi dangkal: komentar cuma dibuka beberapa putaran, postingan
   yang tampil "No comments yet" dilewati, dan pencarian live cuma
   3 kata kunci persis - bukan varian brand, bukan feed grup.

Detector ini memperbaiki ketiganya di sisi ANALISIS:
- normalisasi huruf fancy -> ascii, baru dicocokkan;
- token brand v2: menempel, terpisah (stem dikenal saja), dan
  token+huruf sufiks, dengan keluarga stem (family) bukan kesamaan
  persis - maxwin family mencakup maximumwin, toto family mencakup
  wintoto, cuan family mencakup bakricuan;
- sinyal kontak dan link dihitung sebagai bukti spam;
- skor transparan, dan klasifikasi spam vs candidate vs diskusi,
  supaya keluhan korban / peringatan penipuan (yang menyebut judi
  tapi tanpa ajakan promo) TIDAK masuk dataset spam.

Skor (sekali per jenis sinyal, bukan per kemunculan):
  brand token keluarga dikenal       +3
  brand token pola saja (tak dikenal) +2
  kontak (Telegram/Viber/WhatsApp/handle) +3
  link URL                            +3
  ajakan (CTA: daftar, gabung, cobain, main di, app link) +2
  konteks promo (wd, depo, gacor, rtp, slot)               +1
Klasifikasi: spam >= 5, candidate 2-4, other < 2.
Candidate BUKAN spam terbukti - ia butuh review / frekuensi ulang.

Yang TIDAK dilakukan detector ini:
- Tidak menyimpan nama/ID orang, tidak membuka link promo, tidak
  menebak identitas pemilik brand.
- Tidak menampilkan nomor kontak / URL lengkap di laporan ringkas:
  sinyalnya dicatat sebagai jenis (contact:telegram, link:present),
  teks komentar mentah tetap di file dataset lokal saja.
"""

import re
import unicodedata

AMOUNT_STEMS = {
    "depo", "deposit", "modal", "main", "menang", "kalah", "saldo",
    "bonus", "wd", "withdraw", "bayar", "transfer", "tarik",
    "bettingan", "taruhan",
}

FAMILIES = [
    ("maxwin", re.compile(r"max\w{0,4}win")),
    ("zeus", re.compile(r"zeus")),
    ("toto", re.compile(r"toto")),
    ("togel", re.compile(r"togel")),
    ("slot", re.compile(r"slot")),
    ("gacor", re.compile(r"gacor")),
    ("cuan", re.compile(r"cuan")),
    ("olympus", re.compile(r"olympus")),
    ("pacinko", re.compile(r"pacinko")),
    ("jackpot", re.compile(r"jackpot")),
    ("casino", re.compile(r"casino")),
    ("pragmatic", re.compile(r"pragmatic")),
    # Perluasan 2026-11-05 (user: tambah kayak zeus777 dan sejenisnya,
    # biar semua ketangkap): keluarga dewa/mitos/raja dan stem brand
    # yang sudah terlihat di batch-batch sebelumnya. Keluarga ini
    # penting bukan cuma buat label spam, tapi buat bentuk PISAH:
    # "zeus 777" / "dewa 99" baru dihitung kalau stem-nya dikenal.
    ("dewa", re.compile(r"dewa|dewi")),
    ("naga", re.compile(r"naga|dragon")),
    ("raja", re.compile(r"raja|ratu|king")),
    ("bintang", re.compile(r"bintang|star")),
    ("mitos", re.compile(r"athena|hercules|thor|odin|poseidon|hades|apollo|ares|kratos")),
    ("win", re.compile(r"win")),
    ("kuat", re.compile(r"kuat")),
    ("tirai", re.compile(r"tirai")),
    ("ajaib", re.compile(r"ajaib")),
    ("nox", re.compile(r"nox")),
    # Perluasan v2.3 (user: pasti semua promo ketangkap): nama game
    # slot yang dipakai sebagai brand (bonanza88, mahjong77, dll)
    # dan kata hoki (wangi88, hoki99).
    ("bonanza", re.compile(r"bonanza")),
    ("mahjong", re.compile(r"mahjong")),
    ("princess", re.compile(r"princess")),
    ("gates", re.compile(r"gates")),
    ("wangi", re.compile(r"wangi")),
    ("hoki", re.compile(r"hoki")),
    # Perluasan v2.23 (dari run Colab 2026-11-06, 651 komentar):
    # brand yang selama ini cuma +2 (pola tak dikenal) padahal jelas
    # promo — auto30, dapurpola68, cici46, swiftfrog3176. Pola
    # ^...$ dipakai untuk "auto" dan "cici" supaya stem generik
    # itu hanya dihitung kalau stem tokennya persis itu (bukan
    # "automatic88" dsb). Keluarga ini HANYA berlaku untuk token
    # kata+angka — "cici" / "auto" polos tanpa angka TIDAK jadi
    # brand (cici adalah panggilan umum, auto kata umum), jadi
    # tidak masuk KNOWN_BRANDS_NO_DIGITS. Brand 2026
    # (slotgacor2026, jackpot2026) dan game+1000
    # (sweetbonanza1000, gatesofolympus1000, zeuss1000) TIDAK
    # perlu tambahan — sudah +3 lewat keluarga slot/gacor,
    # jackpot, bonanza, gates/olympus, zeus yang sudah ada.
    ("auto", re.compile(r"^auto$")),
    ("dapurpola", re.compile(r"dapurpola")),
    ("cici", re.compile(r"^cici$")),
    ("swiftfrog", re.compile(r"swiftfrog")),
    # Perluasan v2.4 (dari batch raja88): togel 4D/3D/2D.
    ("togel4d", re.compile(r"togel")),
    # Perluasan v2.5 (user: jangan sampai ada promo yang lolos):
    # bet (sbobet88, bet88, alamatbet) sebagai keluarga token.
    ("bet", re.compile(r"bet")),
]

CTA_PHRASES = [
    "daftar", "gabung", "join", "register", "cobain", "coba di",
    "main di", "mainnya di", "klik", "download", "apk", "app link",
    "link", "gas", "gasken", "langsung", "cobain di",
    # v2.23: "coba" polos dan "login" DIHAPUS dari daftar CTA
    # ini. "coba" polos bikin keluhan korban jadi candidate
    # ("Bos semua coba buat grup gimana cara nya slot di hapus
    # kan. Semua slot itu nipu" — skor 3, padahal itu peringatan,
    # bukan promo). Tapi ajakan promo "coba sweetbonanza1000"
    # harus tetap ketangkap — karena itu "coba" polos dihitung
    # secara kondisional di classify_comment: +2 hanya kalau ada
    # bukti promo lain (brand/link/kontak). "coba di X" /
    # "coba aja" / "cobalah" tetap ada di daftar ini.
    # "login" hanya muncul di teks UI Facebook ("UnreadWe noticed
    # a new login...") — 21 komentar UI-junk jadi candidate
    # gara-gara kata ini di run Colab 2026-11-06. Promo asli
    # yang pakai "login" ("login di zeus88") tetap ketangkap
    # lewat brand-nya.
    # Perluasan 2026-11-05 (user: jangan cuma token angka, tangkap
    # semua promosi): ajakan dan perintah promo lainnya.
    "klaim", "hubungi", "inbox", "daftar di", "nyoba", "cobain aja",
    "gas aja", "buruan", "join sekarang", "daftar sekarang",
    "cari di google", "cari aja", "pindah ke", "mainnya",
    "coba aja", "yuk", "chat",
    # Perluasan v2.3: rujukan link di bio dan ajakan rekomendasi.
    # Ini yang menangkap komentar "linknya cek dibio" yang lolos
    # di batch sebelumnya (tidak ada brand/link/CTA di teksnya).
    "cek bio", "cek dibio", "link di bio", "cek profil",
    "rekomendasi", "rekomen", "saran", "berbagi info",
    "info situs", "info link", "baru nemu", "baru nyoba",
    "baru nyobain", "coba pertimbangkan", "pertimbangkan",
    # Perluasan v2.4: testimoni togel "sudah lama main disana/
    # disitu", rujukan Google, dan typo download yang dipakai
    # promotor untuk lolos filter ("donwload").
    "main disana", "main disitu", "main disini",
    "ketik di google", "donwload", "dowload",
    # Perluasan v2.5: install/terekomendasi/silahkan/
    # buktikan — ajakan yang muncul di batch raja88/slot777
    # tapi belum ada di daftar CTA. ("login" dihapus di v2.23,
    # lihat catatan di atas.)
    "install", "terekomendasi", "silahkan", "buktikan",
    "download aplikasi",
    # Perluasan v2.7 dari batch feed grup 2026-11-05: "joki"
    # adalah jasa main judi untuk orang lain — promosi jasa,
    # bukan sekadar diskusi. "terima joki" / "jasa joki" juga.
    "joki", "terima joki", "jasa joki", "bantu jp",
    # Perluasan v2.9: ejaan slang "maen" (bukan "main") —
    # "Aku juga barusan ngasih maen disitu" lolos dengan skor
    # 0 karena CTA cuma kenal "main disitu". "cobalah" juga
    # ditambahkan (bukan cuma "coba").
    "maen di", "maen disitu", "maen disana", "maen disini",
    "cobalah",
    # Perluasan v2.10 dari batch lanjut-terus 2: "pm" (private
    # message) adalah ajakan kontak promo — "Yang mau saldo
    # geratis pm cuma kirim no rek aja sistem WD bagi dua"
    # lolos dengan skor 1 (cuma konteks WD) tanpa ini.
    "pm",
    # Perluasan v2.11: komentar promo berbahasa Portugis
    # (ditemukan lewat pencarian megawin777, di halaman slot
    # berbahasa Portugis) — ajakan promo dalam bahasa itu:
    # recomendo (rekomendasi), indico (saya rekomendasikan),
    # apostar (bertaruh), jogar (bermain).
    "recomendo", "indico", "apostar", "jogar",
    # Perluasan v2.12 dari batch rafa88: typo evasion
    # "dptar" (daftar) dan "nyobaiin" (nyobain dengan i ganda).
    "dptar", "nyobaiin",
    # Perluasan v2.13: "gaskan" (gas kan, satu kata) — balasan
    # "GASKAN KETUA" ke komentar DAFTAR VIP ber-tautan.
    "gaskan",
    # Perluasan v2.14: "merapat" (ajakan gabung — "mari
    # merapat" di promo togel leet) dan "beralih" (pindah
    # situs — "Gue mah udh kapok... beralih di MPO007").
    "merapat", "beralih",
    # Perluasan v2.15: "nyobak" (varian nyoba) dan "gass"
    # ("Broo gass truss ini user KOIPLAY...").
    "nyobak", "gass",
    # Perluasan v2.18: "mainkan" dan "daftarkan" ("MAINKAN DAN
    # DAFTARKAN SEKARANG ... DI Dapurbos77" — bentuk -kan dari
    # main/daftar, yang tidak cocok dengan \bmain\b/\bdaftar\b).
    "mainkan", "daftarkan",
    # Perluasan v2.21: "cek beranda" ("Tak kasih yang aman
    # amanah ... cek berandaq" — ajakan cek profil/beranda
    # promotor; "berandaq" adalah typo berandaku).
    "cek beranda", "cek berandaq",
]

PROMO_CONTEXT = [
    "wd", "depo", "deposit", "gacor", "rtp", "scatter", "jp", "cuan",
    "slot", "togel", "judi", "judol", "bonus", "freebet", "pragmatic",
    "olympus", "zeus", "toto", "jackpot", "situs", "maxwin",
    # Perluasan konteks promo (bukan bukti sendiri, cuma +1):
    "terpercaya", "resmi", "alternatif", "hoki", "profit",
    "sensational", "pola", "bocoran", "server", "cair", "kilat",
    "lancar", "vip", "pro", "thailand", "jepang", "luar",
    "member", "baru", "akun", "withdraw", "taruhan", "game",
    # Perluasan v2.3: slang promo dari batch-batch terakhir.
    # Ini cuma +1, jadi keluhan "ketagihan judi, depo terus
    # rungkad" tetap other — konteks saja tidak cukup jadi promo.
    "wede", "narik", "jepe", "jepeh", "wangi", "ketagihan",
    "nagih", "nageh", "rekomendasi", "rekomen", "kemenangan",
    "hadiah", "dibayar", "membayar", "amanah", "saldo",
    "meledak", "provider", "mj", "mahjong", "bonanza",
    "princess", "gates", "sweet", "sugar", "receh", "tembus",
    "jutaan", "pelayanan", "mantap", "okee",
    # Perluasan v2.4: kata testimoni togel (aman/percaya/lunas
    # saja tidak cukup jadi promo, cuma +1).
    "aman", "percaya", "lunas",
    # Perluasan v2.5: konteks saja (+1, tidak cukup jadi promo
    # sendirian) — bo/bandar/agen, sensasional, modal, enak,
    # bagus, top, terbukti, cepat, iseng, pengalaman, bukti,
    # vvip, vpn, web, prediksi, pasaran, diskon, salam.
    # Sengaja tetap +1: kalau threshold diturunkan ke +1,
    # keluhan "depo terus rungkad" ikut jadi promo, padahal
    # itu bukan promosi. Jadi "semua promo ketangkap" dicapai
    # dengan memperbanyak kata, bukan dengan menurunkan ambang.
    "bo", "bandar", "agen", "sensasional", "sensasi",
    "bettingan", "bet", "modal", "enak", "bagus", "top",
    "terbukti", "cepat", "iseng", "pengalaman", "bukti",
    "vvip", "vpn", "web", "prediksi", "pasaran", "diskon",
    "prize", "gacorr", "mantapp", "salam",
    # Perluasan v2.11: konteks promo berbahasa Portugis
    # (cuma +1, bukan bukti sendiri) — plataforma (platform),
    # saque (penarikan/WD), pix (pembayaran), deposito, jogos.
    "plataforma", "saque", "pix", "deposito", "jogos",
]

# Frasa promo utuh (+2 sekali, bukan per frasa): klaim positif yang
# hampir selalu promo, bukan sekadar menyebut judi. Sengaja TIDAK
# ada "situs slot" di sini — frasa itu juga muncul di peringatan
# penipuan, jadi terlalu generik untuk +2.
PHRASE_SIGNALS = [
    "situs gacor", "web gacor", "link gacor", "link alternatif",
    "link daftar", "situs terpercaya", "situs resmi",
    "tempat terpercaya",
    "server luar", "server thailand", "server jepang",
    "rtp live", "pola gacor", "bocoran pola",
    "bonus new member", "member baru", "akun baru",
    "wd lancar", "wd cepat", "cair kilat", "gacor parah",
    "daftar sekarang", "cari di google", "free spin", "buy spin",
    "scatter hitam", "jam gacor", "klaim bonus",
    # Perluasan v2.3: frasa testimoni promo dari batch terakhir.
    # "bukan sales" / "bukan promosi" adalah disclaimer yang
    # dipakai promotor supaya kelihatan autentik — di dataset
    # ini muncul di testimoni promo, bukan di keluhan korban.
    "lagi wangi", "player baru", "modal receh", "depo kecil",
    "bukan sales", "bukan promosi", "situs enak", "tempat enak",
    "jangan salah pilih", "paling mantap", "paling okee",
    # Perluasan v2.21: "paling mantep" (typo paling mantap —
    # "terbaik dan paling mantep ... AMAVI" di batch 10).
    "paling mantep",
    "emang beda", "gak ada obat", "nggak ada obat",
    "saldo tebal", "hadiah besar", "taruhan kecil",
    "rtp terlengkap", "all provider", "provider ternama",
    "aura kemenangan",
    # "cek bio" / "link di bio" sengaja TIDAK di sini — sudah ada
    # di CTA, jadi tidak dihitung dua kali untuk bukti yang sama.
    # Perluasan v2.5: frasa ajakan/testimoni togel.
    "jangan ragu", "jangan bimbang", "atm penuh",
    "angka jitu", "bocoran angka", "salam hoki", "salam jp",
    # Perluasan v2.13 dari batch merek baru: "situs paling
    # gacor" dan "new member" (komentar "Situs paling gacor
    # bwt new member min" lolos dengan skor 1 — tanpa brand,
    # tanpa CTA, tanpa frasa yang cocok), "hadiah togel
    # paling besar" (varian dari "hadiah togel terbesar").
    "situs paling gacor", "new member",
    "hadiah togel paling besar",
    # Perluasan v2.14: "paling aman" (frasa kepercayaan promo
    # togel leet "tog 3ll dan sl 0tt paling aman" — komentar
    # itu lolos dengan skor 1 tanpa ini) dan "id baru"
    # (akun baru, varian dari "akun baru"/"member baru").
    "paling aman", "id baru",
    # Perluasan dari batch tkp variants: "lahan mabar" adalah
    # sebutan promotor untuk tempat bermain (situs).
    "lahan mabar",
    # Perluasan v2.7 dari batch feed grup 2026-11-05: "freebet"
    # / "free bet" adalah tawaran promo langsung (bonus gratis),
    # sebelumnya cuma +1 sebagai konteks ("bonus"/"freebet" di
    # PROMO_CONTEXT) sehingga komentar freebet tanpa brand/link
    # bisa lolos.
    "freebet", "free bet", "open freebet",
    # Perluasan v2.21: "freee bet" (typo "Freee bet dong" —
    # bentuk "free bet" dengan e ganda, di batch 10).
    "freee bet",
]

# Brand tanpa angka yang sudah terlihat di batch-batch sebelumnya.
# Dulu aturan browser sengaja mengabaikan nama tanpa angka (OPUNGWIN,
# SONITOTO saja, GARUDAPLAY saja, YOKUBET saja) — user minta itu
# ditangkap juga sekarang, jadi nama-nama ini jadi sinyal brand.
KNOWN_BRANDS_NO_DIGITS = {
    "sonitoto", "opungwin", "garudaplay", "yokubet", "starxboy",
    "lgosultan", "lgohoky", "ugdewa", "mpowin", "taktik",
    "olympus", "pragmatic",
    # Snowball dari batch promo 2026-11-05 (DORA77/TKP303/grup):
    # brand tanpa angka yang muncul sebagai testimoni positif.
    "agustoto", "registertoto", "kusumatoto",
    # Perluasan pola zeus777: nama dewa/mitos/raja tanpa angka pun
    # dihitung brand, karena user memilih recall di atas presisi.
    # Catatan: stem generik (dewa, raja, bintang, kuat) bisa muncul
    # di bahasa sehari-hari — di dataset ini mereka tetap masuk
    # sebagai candidate (bukan spam) kalau berdiri sendiri, dan
    # jadi spam kalau ada ajakan/konteks promo juga.
    "zeus", "dewa", "dewi", "naga", "raja", "ratu", "bintang",
    "kuat", "tirai", "ajaib", "nox", "athena", "hercules", "thor",
    "odin", "poseidon", "hades", "apollo", "dragon", "king",
    # Perluasan v2.4: brand togel tanpa angka dari batch raja88.
    # "jne" sengaja TIDAK dimasukkan — JNE juga nama kurir, jadi
    # terlalu ambigu sebagai brand; komentar Jne itu ketangkap
    # lewat "main disana" + "aman", bukan lewat nama brand.
    "luxtogel", "togelon", "kubutogel", "alamatbet",
    # Perluasan dari batch tkp variants: ELANGGAME (tanpa digit,
    # disebut berulang sebagai lahan bermain). LOGO/BENDERA/
    # OMBAK/OPA sengaja TIDAK dimasukkan sebagai brand tanpa
    # angka — kata-kata itu terlalu umum (logo, bendera, ombak,
    # opa) — komentar-komentar itu ketangkap lewat token
    # berangkanya (LOGO303, BENDERA88, OMBAK126, OPA89).
    "elanggame",
    # Perluasan v2.6 dari batch diverse-brands 2026-11-05
    # (dora88/junior77/mpo77/kuat77/tirai77): 5 komentar browser
    # yang lolos dari detektor v2.5 karena nama brand tanpa
    # angka ini belum dikenal — hokbet, sogoslot, gilalitoto,
    # mpogacor, corgacor. Semua adalah nama brand spesifik
    # yang muncul di konteks judi (aman, wd, situs, testimoni),
    # bukan kata umum, jadi ditambahkan sebagai brand tanpa
    # angka (candidate sendiri, spam dengan ajakan/konteks).
    "hokbet", "sogoslot", "gilalitoto", "mpogacor", "corgacor",
    # Perluasan v2.7 dari batch feed grup 2026-11-05: "gengtoto"
    # muncul sendirian sebagai brand togel (tanpa angka) di
    # postingan grup 1 — sebelumnya skor 0 dan lolos.
    "gengtoto",
    # Perluasan v2.13 dari batch merek baru 2026-11-05.
    # "lgohoki" (ejaan benar) — daftar v2.1 menulis "lgohoky"
    # (typo huruf y), jadi komentar LGOHOKI selama ini lolos
    # dengan skor 0; keduanya sekarang ada. "x5oosl0t" (leet:
    # huruf x + 5 + oosl + 0 + t, token biasa tidak menangkap
    # karena stem-nya cuma 1 huruf + angka di tengah).
    # "dewigaming", "kipaswin", "pajerowin", "omtotgel",
    # "inatogel", "mahkotaslot", "mawatoto", "cyberslot"
    # adalah nama brand spesifik dari batch ini.
    "lgohoki", "dewigaming", "kipaswin",
    "pajerowin", "omtogel", "inatogel", "mahkotaslot",
    "mawatoto", "cyberslot",
    # Perluasan v2.14 dari batch merek baru 2: "lingkarwin"
    # ("Pindah ke LINGKARWIN...") dan "jawaraliga" (4 komentar
    # di postingan SATSET189).
    "lingkarwin", "jawaraliga",
    # Perluasan v2.15 dari batch merek baru 3: "koiplay"
    # (tanpa angka — 19 komentar testimoni polos lolos
    # dengan skor 0 karena cuma nama merek tanpa CTA).
    "koiplay",
    # Perluasan v2.18 dari batch merek baru 6: "mahaspin"
    # ("gacor kali ahk mahaspin aku tadi jp jp" lolos skor 1),
    # "marettoto" (togel, aturan lomba + tautan) dan
    # "kapalslot" (situs judi terpercaya + tautan/WA/Telegram).
    "mahaspin", "marettoto", "kapalslot",
    # Perluasan v2.20 dari batch merek baru 9: "wongtoto"
    # ("Wongtoto aman bray" lolos skor 1), "alexistoto"
    # ("Paling enak main di alexistoto"), "cupangcuan" /
    # "ligacuan" / "rajacuan" (keluarga cuan tanpa angka),
    # "indoseven" (nama merek tanpa angka).
    "wongtoto", "alexistoto", "cupangcuan", "ligacuan",
    "rajacuan", "indoseven",
    # Perluasan v2.21 dari batch merek baru 10: "amavi"
    # ("terbaik dan paling mantep ... AMAVI" tanpa angka lolos
    # skor 1) dan "nabatibet" (tautan + kontak WA, tanpa angka).
    "amavi", "nabatibet",
    # Perluasan v2.22 dari batch merek baru 11: "sicepattoto"
    # (ditulis pisah "SICEPAT TOTO", lolos skor 1 — ditangkap
    # lewat cek merek pisah), "gwinbola" dan "pastiprofit"
    # (merek tanpa angka yang sejauh ini ketangkap lewat
    # tautan/frasa, tapi perlu dikenal sendiri).
    "sicepattoto", "gwinbola", "pastiprofit",
    # Perluasan v2.8 dari batch campuran 2026-11-05: "ybowin"
    # adalah nama brand spesifik tanpa angka ("Situs yg
    # terpercaya menurut saya YBOWIN") — sebelumnya cuma +1
    # konteks dan lolos sebagai other.
    "ybowin",
    # Perluasan v2.9 dari batch lanjut-terus 2026-11-05:
    # "RAFASL0T" ditulis dengan angka 0 pengganti huruf O
    # (leet evasion), jadi token angka biasa tidak menangkapnya:
    # kata "rafasl0t" terpecah jadi "rafasl" + "t" saat
    # diekstrak, jadi "rafasl" (dan "rafaslot" untuk ejaan
    # normal) ditambahkan sebagai brand tanpa angka. 27 dari
    # 29 komentar batch ini yang lolos adalah testimoni
    # RAFASL0T polos tanpa CTA — semuanya jadi candidate
    # dengan tambahan ini, bukan spam.
    "rafasl", "rafaslot",
    # Perluasan v2.12 dari batch rafa88 2026-11-05: "gendut"
    # (disebut "Gendut 188" — bentuk pisah, stem belum dikenal)
    # dan "pgbet" ("Pgbet aku WD 30jt dibayar bosku" — testimoni
    # wd dibayar). Catatan: "Gendut 188" muncul di utas yang
    # meminta tambahan nama situs penipu, jadi konteksnya
    # ambigu — tetap dihitung candidate (bukan spam), sesuai
    # definisi pencatatan browser untuk komentar itu.
    "gendut", "pgbet",
}

# Kata yang TIDAK boleh dianggap brand dari pola "main di X" /
# "daftar di X" — kata umum, bukan nama brand.
_BRAND_CONTEXT_STOPWORDS = {
    "situs", "web", "link", "google", "gugel", "sana", "sini", "di",
    "yang", "dan", "itu", "ini", "bang", "bos", "bro", "kak", "mas",
    "akun", "server", "luar", "dalam", "semua", "orang", "apk",
    "aja", "ajaib",
}

# v2.16: TLD diperluas dengan shortener dan domain promo yang
# umum dipakai di komentar judi — bit.ly, mez.ink, heylink.me,
# lingkarwin.store, e55.group — yang tanpa skema "https://" tidak
# ketangkap regex lama (hanya com/net/dev/...). "bit.ly/..." dan
# "mez.ink/..." tanpa skema sebelumnya lolos dengan skor 0 tautan.
# v2.17: "ke" ditambahkan untuk shortener msha.ke (tautan resmi
# RAJA189) — sebelumnya "Rama Aditya https://msha.ke/raja189.official"
# hanya skor token +2 (candidate), padahal ada tautan.
# v2.19: "page" ditambahkan untuk shortener desty.page
# ("LINK JALUR CEPAT https://desty.page/maxwin288.official"
# di batch merek baru 8 — dengan skema sih ketangkap, tapi
# tanpa skema akan lolos).
# v2.20: "iy" ditambahkan — "https//rebrand.Iy/..." di batch
# merek baru 9 ditulis dengan huruf I besar (kemungkinan
# salah baca glyph "rebrand.ly" di tampilan Facebook);
# TLD ".iy" sendiri tidak ada, jadi risiko false positive
# praktis nol.
_URL_RE = re.compile(r"https?://\S+|www\.\S+|\b[\w-]+\.(com|net|dev|site|xyz|top|live|vip|cc|id|co|ly|ink|me|link|click|store|group|app|io|gg|to|su|pw|fun|online|bet|casino|slot|pro|win|asia|ke|page|iy)\b", re.I)
# v2.7: "nomor telepon dihapus" adalah penanda redaksi di
# transkripsi lokal — artinya nomor WA/telepon ASLI ada di
# komentar aslinya tapi sengaja tidak disimpan/dikutip.
# Penanda itu sendiri adalah bukti kontak (+3), bukan nomornya.
_CONTACT_RE = re.compile(r"(@[a-z0-9_]{4,}|telegram|viber|whatsapp|\bwa\b\s*[:\d]|nomor telepon dihapus)", re.I)
# Digit 2-5 (dulu 2-4): zeus777 sudah ketangkap dari dulu (3 digit),
# sekarang zeus77777 / maxwin12345 juga ketangkap. Sengaja TIDAK
# diperluas ke 1 digit — iphone7, gta6, ps5 dan sejenisnya akan
# membanjiri dataset dengan produk teknologi, bukan promo judi.
_ATTACHED_RE = re.compile(r"\b([a-z]{3,20})(\d{2,5})([a-z]{0,12})\b")
_SEPARATED_RE = re.compile(r"\b([a-z]{3,20})[\s\-_]+(\d{2,5})(?![a-z0-9])")
_LUCKY_RE = re.compile(r"\b(777|888|999)\b")
# Togel 4D/3D/2D: zara4d, lampung4d, bogor4d, malang4d, cun4d.
# Angka tunggal saja (zara4) sengaja TIDAK dihitung — "4" di sini
# bukan angka brand, tapi format togel (4D), jadi polanya
# stem + digit + "d", bukan stem + digit saja.
_FOURD_RE = re.compile(r"\b([a-z]{3,20})([234])d\b")

# v2.23: teks chrome/UI Facebook, BUKAN komentar — ikut terkumpul
# karena extract_comment_texts mengambil semua elemen [dir="auto"]
# di halaman, termasuk navigasi dan notifikasi. Di run Colab
# 2026-11-06, 117 dari 651 "komentar" (18%) adalah teks seperti
# ini, dan 21 di antaranya kehitung promo. Dicek di teks yang
# sudah dinormalisasi: cocok persis (seluruh komentar memang cuma
# label UI itu) atau diawali "unread" (notifikasi "UnreadWe noticed
# a new login..." / "UnreadSee who's also on Facebook...").
_UI_JUNK_EXACT = {
    "find friends", "notifications", "see all", "new see all",
    "marketplace", "log in", "log in or sign up",
    "create new account", "forgot password", "forgot account",
    "home", "watch", "groups", "reels", "menu", "search",
    "see more", "see less", "like", "comment", "share", "follow",
    "following", "send", "save", "view more comments",
    "view previous comments", "view all comments", "view replies",
    "view more replies", "lihat komentar lainnya",
    "lihat komentar sebelumnya", "lihat semua komentar",
    "lihat balasan", "lihat balasan lainnya",
}
_UI_JUNK_PREFIXES = (
    "unread",
    "see who's also on facebook",
    "tap here to get help",
)


def _is_ui_junk(norm):
    n = norm.strip()
    if n in _UI_JUNK_EXACT:
        return True
    return any(n.startswith(p) for p in _UI_JUNK_PREFIXES)


def _fancy_to_ascii(ch):
    """Huruf fancy (mathematical bold/double-struck/dll) -> huruf biasa."""
    if ch.isascii():
        return ch
    try:
        name = unicodedata.name(ch, "")
    except Exception:
        return ch
    m = re.search(r"(CAPITAL|SMALL).* ([A-Z0-9])$", name)
    if m and ("LATIN" in name or "MATHEMATICAL" in name or "DIGIT" in name):
        letter = m.group(2)
        return letter.lower() if m.group(1) == "SMALL" else letter
    decomposed = unicodedata.normalize("NFKD", ch)
    return decomposed[0] if decomposed and decomposed[0].isascii() else ch


def normalize_text(text):
    """Lowercase + fancy->ascii. Angka dipertahankan (penting buat token)."""
    if not text:
        return ""
    out = "".join(_fancy_to_ascii(ch) for ch in text)
    # v2.17: underscore diganti spasi — "_kaisar189official_"
    # (di dalam URL heylink) tidak ketangkap _ATTACHED_RE karena
    # "_" adalah karakter kata, jadi tidak ada batas kata (\b)
    # sebelum "kaisar". Tanpa ini tokennya lolos dengan skor 0.
    return out.lower().replace("_", " ")


def _family(stem):
    for name, pattern in FAMILIES:
        if pattern.search(stem):
            return name
    return None


def extract_brand_tokens_v2(text):
    """Token brand v2 dari teks (setelah normalisasi fancy)."""
    norm = normalize_text(text)
    out, seen = [], set()

    def add(token, stem, digits, form, family):
        if token in seen:
            return
        seen.add(token)
        out.append({
            "token": token, "stem": stem, "digits": digits,
            "form": form, "family": family,
        })

    for stem, digits, suffix in _ATTACHED_RE.findall(norm):
        if stem in AMOUNT_STEMS:
            continue
        family = _family(stem)
        if not family and (digits.startswith("777")
                           or digits.startswith("888")
                           or digits.startswith("999")):
            # Angka hoki sendiri adalah sinyal brand: bigwin777,
            # slot777, gacor888 — stem-nya tidak dikenal pun tetap
            # keluarga "lucky", jadi bentuk pisahnya pun ikut dihitung
            # di bawah (karena family sudah ada).
            family = "lucky"
        add(stem + digits, stem, digits,
            "attached+suffix" if suffix else "attached", family)
    for m in _SEPARATED_RE.finditer(norm):
        stem, digits = m.group(1), m.group(2)
        if stem in AMOUNT_STEMS:
            continue
        family = _family(stem)
        if not family:
            continue
        add(stem + digits, stem, digits, "separated", family)
    for stem, digit in _FOURD_RE.findall(norm):
        if stem in AMOUNT_STEMS:
            continue
        add(stem + digit + "d", stem, digit + "d", "togel4d", "togel")
    # v2.12: token dengan stem 2 huruf — hanya "jp" (jackpot),
    # yang memang singkatan judi. _ATTACHED_RE butuh stem
    # minimal 3 huruf, jadi "Jp139" lolos dengan skor 0.
    # Dibatasi ke "jp" saja supaya "wd88"/"bo99" dan sejenisnya
    # tidak ikut kebuka (terlalu rawan false positive).
    for m in re.finditer(r"\bjp(\d{2,5})\b", norm):
        add("jp" + m.group(1), "jp", m.group(1),
            "attached-short", None)
    return out


def _contains_phrase(norm, phrase):
    return re.search(r"\b" + re.escape(phrase) + r"\b", norm) is not None


def _known_brands_in_text(norm):
    """Brand tanpa angka yang muncul sebagai kata utuh."""
    words = set(re.findall(r"[a-z]+", norm))
    return sorted(KNOWN_BRANDS_NO_DIGITS & words)


def _brand_context_words(norm):
    """Kata setelah ajakan 'main di / daftar di / coba di / cari /
    pindah ke' — calon brand baru. Kata umum dibuang di sini, sisanya
    dipakai analyze_spam untuk mengusulkan brand baru, bukan langsung
    jadi bukti (supaya 'main di sana' tidak jadi brand)."""
    found = []
    for m in re.finditer(
            r"\b(?:main di|daftar di|coba di|cobain di|cari(?: aja)?|pindah ke)\s+([a-z]{3,20})\b",
            norm):
        w = m.group(1)
        if w not in _BRAND_CONTEXT_STOPWORDS and w not in found:
            found.append(w)
    return found


def classify_comment(text):
    """Kembalikan skor, klasifikasi, dan sinyal untuk satu komentar."""
    norm = normalize_text(text)
    if _is_ui_junk(norm):
        return {
            "score": 0, "label": "other", "signals": ["ui_junk"],
            "brand_tokens": [], "families": [], "known_brands": [],
            "brand_context_words": [],
        }
    tokens = extract_brand_tokens_v2(text)
    known_brands = _known_brands_in_text(norm)
    signals = []
    score = 0

    if tokens:
        known = any(t["family"] for t in tokens)
        score += 3 if known else 2
        signals.append("brand:%s" % ",".join(sorted({t["token"] for t in tokens})))
    # Jangan double-hitung brand yang sudah ada di token: "raja88"
    # memberi kata "raja" di _known_brands_in_text, tapi itu bukti
    # yang sama dengan token raja88, bukan bukti kedua.
    token_stems = {t["stem"] for t in tokens}
    known_brands = [b for b in known_brands if b not in token_stems]
    if known_brands:
        score += 3
        signals.append("brand_name:%s" % ",".join(known_brands))
    # v2.11: brand dengan pola yang tidak ditangkap token
    # biasa — "P0A88" (angka 0 pengganti O, jadi pecahan kata
    # "p"/"a" tidak cocok) dan "1388bet" (angka dulu baru
    # huruf). Dicek sebagai substring, bukan kata utuh.
    # "x5oosl0t" sengaja di sini, bukan di KNOWN_BRANDS_NO_DIGITS:
    # _known_brands_in_text hanya mengambil kata huruf saja
    # ([a-z]+), jadi brand berangka tidak pernah cocok di sana.
    _leet_brands = [b for b in ("p0a88", "poa88", "1388bet",
                               "17mabar", "x5oosl0t", "mp007")
                    if b in norm and b not in token_stems]
    if _leet_brands:
        score += 3
        signals.append("brand_name:%s" % ",".join(_leet_brands))
    # v2.13: "C A D A S 138" — brand ditulis dengan spasi
    # antar huruf (evasion seperti dotted P.I.X.E.L.1.3.8).
    # Dicek di teks tanpa spasi; jangan double-hitung kalau
    # token cadas138 sudah ketangkap dari ejaan normal.
    if "cadas138" in norm.replace(" ", ""):
        if not any(t["token"] == "cadas138" for t in tokens):
            score += 3
            signals.append("brand_name:cadas138")
    # v2.18: generalisasi cek spasi untuk semua brand tanpa
    # angka yang panjang (>= 6 huruf) — "M A H A S P I N"
    # di batch merek baru 6 lolos karena hurufnya dipisah spasi.
    # Dibatasi ke brand panjang supaya "win"/"toto"/"raja"
    # tidak kebentuk secara tidak sengaja dari kata sebelah
    # (mis. "kawin" mengandung "win"). Hanya dihitung kalau
    # brand-nya belum ketangkap dari ejaan normal.
    # Guard: jangan double-hitung kalau brand-nya sudah ketangkap
    # dari ejaan normal — dicek dengan batas kata (\b), bukan
    # spasi, karena "alamatbet..jp" dan "#kubutogel" juga
    # ejaan normal (diikuti titik / diawali #) tapi tidak
    # dikelilingi spasi.
    _squashed = norm.replace(" ", "")
    _spaced = [b for b in KNOWN_BRANDS_NO_DIGITS
               if len(b) >= 6 and b in _squashed
               and not re.search(r"\b" + re.escape(b) + r"\b", norm)]
    if _spaced:
        score += 3
        signals.append("brand_name_spaced:%s" % ",".join(_spaced))
    # v2.21: merek berangka yang ditulis terpisah — "POA 88"
    # dan "Gopek 178" di batch merek baru 10 lolos karena
    # bentuk pisah hanya dihitung kalau stem-nya keluarga
    # yang dikenal. Dicek di teks tanpa spasi, sama seperti
    # cadas138; jangan double-hitung kalau tokennya sudah
    # ketangkap dari ejaan normal.
    _spaced_digit = [b for b in ("p0a88", "poa88", "1388bet",
                                 "17mabar", "x5oosl0t", "mp007",
                                 "gopek178")
                     if b in _squashed
                     and not any(t["token"] == b for t in tokens)]
    if _spaced_digit:
        score += 3
        signals.append("brand_name_spaced_digit:%s"
                       % ",".join(_spaced_digit))
    if _CONTACT_RE.search(norm):
        score += 3
        if "telegram" in norm:
            signals.append("contact:telegram")
        elif "viber" in norm:
            signals.append("contact:viber")
        elif "whatsapp" in norm or re.search(r"\bwa\b", norm):
            signals.append("contact:whatsapp")
        elif "@" in norm:
            signals.append("contact:handle")
        else:
            signals.append("contact:present")
    # v2.11: penanda "[tautan ...]" di transkripsi lokal
    # artinya tautan ASLI ada di komentar aslinya tapi URL-nya
    # tidak disalin (mis. tautan share Facebook yang tidak
    # tercantum lengkap di laporan browser) — penanda itu
    # sendiri adalah bukti tautan (+3), sama seperti penanda
    # redaksi nomor telepon untuk kontak.
    # v2.18: domain yang disamarkan — titik diganti "*" atau ","
    # ("logincnn303*com", "bisaklikaja,com") — evasion yang
    # muncul dua kali di batch merek baru 6. Pola ini hanya
    # cocok kalau diikuti TLD yang dikenal, jadi "5*4" tidak
    # ikut ketangkap.
    _OBFUSCATED_URL_RE = re.compile(
        r"\b[a-z]{3,}[*,](com|net|id|me|co|xyz|top|site|live|vip|cc|ly|ink|link|click|store|group|app|io|gg|to|su|pw|fun|online|bet|casino|slot|pro|win|asia|ke)\b", re.I)
    if _URL_RE.search(norm) or _OBFUSCATED_URL_RE.search(norm) or "[tautan" in norm:
        score += 3
        signals.append("link:present")
    # v2.16: frasa tanpa spasi di dalam tagar — "#slotgacorhariini"
    # tidak cocok dengan frasa "slot gacor" (butuh batas kata),
    # padahal "slotgacor" sebagai substring jelas sinyal promo.
    if "slotgacor" in norm:
        score += 2
        signals.append("phrase:slotgacor")
    cta_found = [p for p in CTA_PHRASES if _contains_phrase(norm, p)]
    if cta_found:
        score += 2
        signals.append("cta:%s" % ",".join(cta_found[:3]))
    # v2.23: "coba" polos hanya dihitung sebagai ajakan kalau ada
    # bukti promo lain (brand/link/kontak). "coba sweetbonanza1000
    # gacor hari ini" adalah ajakan promo (brand + coba = spam),
    # tapi "Bos semua coba buat grup... Semua slot itu nipu"
    # adalah keluhan tanpa bukti promo (tetap other). Guard
    # startswith("coba") mencegah hitung ganda kalau "coba di" /
    # "cobain" / "cobalah" sudah dihitung di atas.
    if (re.search(r"\bcoba\b", norm)
            and not any(p.startswith("coba") for p in cta_found)
            and (tokens or _CONTACT_RE.search(norm)
                 or _URL_RE.search(norm) or "[tautan" in norm)):
        score += 2
        signals.append("cta:coba")
    phrase_found = [p for p in PHRASE_SIGNALS if p in norm]
    if phrase_found:
        score += 2
        signals.append("phrase:%s" % ",".join(phrase_found[:3]))
    # Angka hoki berdiri sendiri ("777 gacor", "888 lagi wangi"):
    # \b di sini sengaja, supaya zeus777 tidak dihitung dua kali
    # (di zeus777, 777 menempel ke huruf, jadi bukan \b777\b).
    if _LUCKY_RE.search(norm):
        score += 2
        signals.append("lucky:present")
    if any(_contains_phrase(norm, p) for p in PROMO_CONTEXT):
        score += 1
        signals.append("promo_context:present")

    if score >= 5:
        label = "spam"
    elif score >= 2:
        label = "candidate"
    else:
        label = "other"
    return {
        "score": score, "label": label, "signals": signals,
        "brand_tokens": [t["token"] for t in tokens],
        "families": sorted({t["family"] for t in tokens if t["family"]}),
        "known_brands": known_brands,
        "brand_context_words": _brand_context_words(norm),
    }
