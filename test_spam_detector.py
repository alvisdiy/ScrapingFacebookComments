#!/usr/bin/env python3
"""Tes offline spam detector v2. Jalankan: python3 test_spam_detector.py"""

import sys

from spam_detector import classify_comment, normalize_text


def label(text):
    r = classify_comment(text)
    return r["label"], r["score"], r["brand_tokens"]


CASES = [
    # (teks, label yang diharapkan)
    ("coba di zeus88 gacor banget daftar sekarang", "spam"),
    ("main di PACINKO88 wd 2jt", "spam"),
    ("Baru main langsung di kasi wd aja tkp di BAKRICUAN22", "spam"),
    ("main di Wintoto189, wd 2jt", "spam"),
    ("Iseng coba 200rb, main di PACINKO88 wd 2jt", "spam"),
    ("situs slot nipu, depo berkali-kali rungkad terus", "other"),
    ("iphone15 bagus banget kameranya", "candidate"),
    ("tahun 2026 masih aja rame", "other"),
    ("depo 50 bonus 20k buat 10 orang", "other"),
    ("App link please", "candidate"),
    # Perluasan 2026-11-05: brand tanpa angka + frasa promo.
    ("Bisa di coba di SONITOTO lagi gacor nya ini", "spam"),
    ("cari aja OPUNGWIN yang lagi rame ini", "spam"),
    ("Pindah ke GARUDAPLAY, cairnya kilat", "spam"),
    ("wajib cobain si main di STARXBOY akun baru enak bgt, coba", "spam"),
    ("Link alternatif baru, situs terpercaya dan gampang WD", "spam"),
    # v2.23: "coba" polos dihapus dari CTA (keluhan korban salah jadi
    # candidate gara-gara "coba"), jadi komentar ini turun dari spam
    # ke candidate — tetap promo (candidate masuk dataset), cuma
    # labelnya bukan spam lagi.
    ("Coba pake server luar, RTP nya di atas 90%, JP terus", "candidate"),
    ("situs slot nipu, depo berkali-kali rungkad terus", "other"),
    # Perluasan pola zeus777 2026-11-05.
    ("zeus777 gacor banget daftar sekarang", "spam"),
    ("zeus 777 main di sini", "spam"),
    ("dewa99 lagi gacor", "candidate"),
    ("naga888 wd lancar", "spam"),
    ("main di bintang88", "spam"),
    ("slot777 gacor", "candidate"),
    ("gacor777", "candidate"),
    ("maxwin777", "candidate"),
    ("zeus77777", "candidate"),
    ("raja88 terpercaya", "candidate"),
    ("777 gacor", "candidate"),
    ("tahun 2026 masih aja rame", "other"),
    # Perluasan v2.3: 2 komentar batch sebelumnya yang lolos.
    ("info situs enak nih sesama pemain wd brpa pun dibayar info linknya cek dibio profil gua", "spam"),
    ("asli bang bagus saya bukan sales berbagai pengalaman soalnya kemarin saya depo 2 jt profit 13 jt aman lumayan enak situs nya", "candidate"),
    ("berbagi info aja nih mumpung sesama pemain, ajaib76 lagi wangi buat akun baru", "spam"),
    ("lagi wangi", "candidate"),
    ("ketagihan main di kuat46", "spam"),
    ("cek bio profil gua buat linknya", "candidate"),
    ("gw ketagihan judi, depo terus rungkad", "other"),
    ("bonanza88 lagi wangi", "spam"),
    # Perluasan v2.4: pola batch raja88.
    ("Jne aman bos. Gua udah lama main disana.", "candidate"),
    ("sorry yaa alamatbet..jp selalu di bayar..thanksss", "candidate"),
    ("#kubutogel aman2 aja sih", "candidate"),
    ("Maaf untuk #zara4d saya masih percaya soalnya saya pernah dapat togel 1jutaan wd dibayar lunas", "candidate"),
    ("Rog777,lampung4d,bogor4d,malang4d pokok nya banyak pinter pinter milih bo yg pasti pasti aja kaya Vegas", "candidate"),
    ("Donwload VPN", "candidate"),
    ("Cair BG WD lagi emang top JANGAN RAGU JANGAN BIMBANG BUKTIKAN SENDIRI SENSASI ATM PENUH GUYS KETIK DI GOOGLE : KUY19", "spam"),
    ("Togelon bagus saya sudah join disana sudah hampir 2th, pernah kena berapa saja dibayar kok.. lancar2 saja..", "spam"),
    # Perluasan v2.5.
    ("Jangan ragu jangan bimbang buktikan sendiri sensasi atm penuh", "spam"),
    ("INSTALL APK", "candidate"),
    ("salam hoki dan salam jp dari CUN4D", "spam"),
    ("prediksi angka jitu togel hari ini", "candidate"),
    ("bo yg pasti pasti aja", "other"),
    ("gw ketagihan judi, depo terus rungkad", "other"),
    ("Lahan Mabar ELANGGAME KLIK", "spam"),
    ("Server Thailand terbaik Di situs KIU77", "spam"),
    ("Super bagus LOGO303", "candidate"),
    ("Very aesthetic really like the style of BENDERA88", "candidate"),
]


def main():
    failed = 0
    for text, expected in CASES:
        got, score, toks = label(text)
        ok = got == expected
        failed += not ok
        print("%s %-55s -> %s (%d) %s (harap %s)" % (
            "OK " if ok else "FAIL", text[:55], got, score, toks, expected))
    # Kasus khusus yang tidak bisa ditulis persis di daftar di atas:
    # huruf fancy DAFTAR + link, dan kontak Telegram/Viber.
    fancy = "".join(chr(0x1D400 + ord(c) - 65) if "A" <= c <= "Z" else c for c in "DAFTAR")
    # Double-struck capital D (code point, bukan literal) harus jadi "d".
    assert normalize_text(chr(0x1D53B)) == "d", normalize_text(chr(0x1D53B))
    r = classify_comment(fancy + " https://example.pages.dev/")
    print("fancy DAFTAR+link -> %s (%d) %s ; normalisasi=%s" % (
        r["label"], r["score"], r["signals"], normalize_text(fancy)))
    if r["label"] != "spam":
        failed += 1
    r2 = classify_comment("Telegram @maximumwin99 Viber contact please")
    print("maximumwin99+kontak -> %s (%d) %s" % (r2["label"], r2["score"], r2["brand_tokens"]))
    if r2["label"] != "spam" or "maximumwin99" not in r2["brand_tokens"]:
        failed += 1
    # v2.23: keluarga brand baru (auto/dapurpola/cici/swiftfrog naik
    # dari +2 pola tak dikenal menjadi +3 keluarga dikenal).
    v23_scores = [
        ("auto30", 3),
        ("SwiftFrog3176", 3),
        ("cici46", 3),
        ("main di dapurpola68", 5),
        ("daftar auto30 gacor", 6),
        ("main di slotgacor2026 gacor wd lancar", 10),
        ("coba sweetbonanza1000 gacor hari ini", 6),
        ("main di zeuss1000 wd", 6),
    ]
    for text, expected_score in v23_scores:
        r = classify_comment(text)
        ok = r["score"] == expected_score
        failed += not ok
        print("%s %-55s -> skor %d (harap %d) %s" % (
            "OK " if ok else "FAIL", text[:55], r["score"],
            expected_score, r["brand_tokens"]))
    # v2.23: "coba di" tetap CTA, tapi "coba" polos bukan lagi.
    v23_labels = [
        # (teks, label yang diharapkan)
        ("coba di zeus88", "spam"),
        ("Bos semua coba buat grup gimana cara nya slot di hapus kan. Semua slot itu nipu.", "other"),
        ("login di zeus88", "candidate"),
        # Teks UI Facebook — bukan komentar, langsung other skor 0.
        ("Find friends", "other"),
        ("Notifications", "other"),
        ("New See all", "other"),
        ("UnreadWe noticed a new login from a device or location that you don't usually use. Please review.", "other"),
        ("UnreadSee who's also on Facebook. Tap here to get help finding friends.", "other"),
        ("Marketplace", "other"),
    ]
    for text, expected in v23_labels:
        r = classify_comment(text)
        ok = r["label"] == expected
        failed += not ok
        print("%s %-55s -> %s (%d) (harap %s)" % (
            "OK " if ok else "FAIL", text[:55], r["label"], r["score"], expected))
    print("\n%d kasus gagal" % failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
