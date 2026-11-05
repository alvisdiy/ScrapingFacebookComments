#!/usr/bin/env python3
"""Bangun data/raw_comments.jsonl dari hasil collect browser-task run 2.

Sumber: laporan browser-task 2026-11-03 (tahap A seed + tahap B discovery).
Hanya komentar yang lolos prefilter longgar yang ditranskrip ke sini;
komentar lain hanya tercatat lewat hitungan loaded, bukan teksnya.

Redaksi yang diterapkan di file ini (bukan di laporan asli):
- nomor telepon dihapus -> [nomor disensor]
- tautan situs judi dihapus -> [tautan dihapus]
- daftar nama situs di komentar peringatan dipersingkat -> [daftar nama situs dihapus]
Nama penulis komentar TIDAK disimpan di sini (hanya teks + URL postingan).
"""

import json
import os

OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "raw_comments.jsonl"
)

# (post_url, base_keyword, comment_text, jumlah_duplikat_identik)
ITEMS = [
    (
        "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
        "seed",
        "Emang depo brp bg, dan setelah lu depo lu mau berharap jp berapa iket",
        1,
    ),
    (
        "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
        "seed",
        "OTAK KAU ITU GIMANA... yeey saya menang dah wd tinggal tidur nyenyak deh",
        1,
    ),
    (
        "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
        "seed",
        "Depo berapa kali. Rungkad terus",
        1,
    ),
    (
        "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
        "seed",
        "Betul , dapat scatter bettingan 2000 isi ampas",
        1,
    ),
    (
        "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
        "seed",
        "Saya punya ratusan merek situs slot. Pakta semua slot nipu penguna. Lubang tanpa dasar.",
        1,
    ),
    (
        "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
        "seed",
        "Pindah aja bang, Hari ini gacor bgt emng , wajib cobain si main di STARXBOY akun baru enak bgt, coba",
        1,
    ),
    (
        "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
        "seed",
        "Open Freebet buat 10 orang tercepat Depo 50 bonus 20k Wa [nomor disensor]",
        1,
    ),
    (
        "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
        "seed",
        "cobain di apk aja bre wd juga satset tanpa nunggu [tautan dihapus]",
        1,
    ),
    (
        "https://www.facebook.com/groups/4154747314816376/permalink/4229629950661445/",
        "seed",
        "DEPOSIT=BAYAR PAJAK",
        1,
    ),
    (
        "https://www.facebook.com/permalink.php?story_fbid=pfbid09KUspSj4eknyYvJekNkbezxFXBh7FReQcgJEJmsgkGqz7tNuvGF3JdVLz5CLuFEQl&id=61594672211081",
        "seed",
        "Iseng coba 200rb, main di PACINKO88 wd 2jt , makasih atas info linknya, sangat membantu",
        9,
    ),
    (
        "https://www.facebook.com/permalink.php?story_fbid=pfbid0AR9hzbjftgQVb3WrkYJJzFmR5CWGvWZeLXnzCCGjU5tuERrurq41uePcvPgt54Z2l&id=61596385970194",
        "seed",
        "Iseng coba 200rb, main di PACINKO88 wd 2jt , makasih atas info linknya, sangat membantu",
        7,
    ),
    (
        "https://www.facebook.com/groups/1307335247318904/permalink/1965526194833136/",
        "seed",
        "Koitoto + nenektogel penipu situs bangsat",
        1,
    ),
    (
        "https://www.facebook.com/groups/1307335247318904/permalink/1965526194833136/",
        "seed",
        "Lintogel situs anjing penipu wd pun gak di proses",
        1,
    ),
    (
        "https://www.facebook.com/permalink.php?story_fbid=pfbid0oeft8vE3dgu8NNu4HUzvotA1CFpJZS2AQM7VRLUsQfFcbeXwimo9MEfd5UxrGdral&id=61595782994239",
        "seed",
        "Langsung WD tanpa basa basi gcorrr parah duduk BAKRICUAN22",
        1,
    ),
    (
        "https://www.facebook.com/permalink.php?story_fbid=pfbid0oeft8vE3dgu8NNu4HUzvotA1CFpJZS2AQM7VRLUsQfFcbeXwimo9MEfd5UxrGdral&id=61595782994239",
        "seed",
        "Baru main langsung di kasi wd aja tkp di BAKRICUAN22",
        1,
    ),
    (
        "https://www.facebook.com/permalink.php?story_fbid=pfbid0226SX6MGZECprmFZvPnwwR36TmDpNhRhFDEVsvsRbqqwo8WauZPNghDecAqTX8z9al&id=61595199393365",
        "slot gacor",
        "Turut Berduka Cita Selamat Pagi ... Tetap Semangat Pagi Ini. Yang Belum Mencoba, Masih Banyak Waktu Untuk Mencoba Sekarang Juga. Semoga WDnya Bisa Melimpah Ruah, Selamat Mencoba...",
        1,
    ),
    (
        "https://www.facebook.com/permalink.php?story_fbid=pfbid0LBJ8TEHLZYneyer9deYQyVWyLfr35R9H748fWWjA9MfZAWaeoAqYmw3XsVZBX3bol&id=61595859330997",
        "slot gacor",
        "Iseng coba main 200rb, main di Wintoto189, wd 2jt , makasih atas info linknya, sangat membantu",
        1,
    ),
    (
        "https://www.facebook.com/groups/1027152220961329/permalink/2970832773259921/",
        "judi online",
        "63jt om total depo saya dlm 3bln. Gara2 ikut2an..dpt scter hitam modal 500rb bsa wd 5jt..nyesek om r",
        1,
    ),
    (
        "https://www.facebook.com/groups/1027152220961329/permalink/2970832773259921/",
        "judi online",
        "Gua udah sering share bro. Kalo deposit sekarang sama aja kayak Transfer uang ke tukang tipu. Apa lagi sekarang banyak situs scam yang terus-terusan spam iklan di medsos [daftar nama situs dihapus] Selalu di ingat bro kalo lu depo berarti lu TF uang ke tukang tipu",
        1,
    ),
    (
        "https://www.facebook.com/groups/497256869560004/permalink/877600028192351/",
        "deposit pulsa",
        "rencana bonus kesbek main di RAFASL0T mau tak wd in,iseng tak mainin malah naik",
        1,
    ),
    (
        "https://www.facebook.com/groups/497256869560004/permalink/877600028192351/",
        "deposit pulsa",
        "Iya apa ya situs yg depo pulsa Smartfren",
        1,
    ),
    (
        "https://www.facebook.com/groups/497256869560004/permalink/877600028192351/",
        "deposit pulsa",
        "Depoh cacing jadi dragon",
        1,
    ),
    (
        "https://www.facebook.com/groups/497256869560004/permalink/877600028192351/",
        "deposit pulsa",
        "max win",
        1,
    ),
    (
        "https://www.facebook.com/groups/497256869560004/permalink/877600028192351/",
        "deposit pulsa",
        "maxwin",
        1,
    ),
]


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rows = []
    for url, base, text, count in ITEMS:
        for _ in range(count):
            rows.append(
                {
                    "post_url": url,
                    "base_keyword": base,
                    "query": "",
                    "comment_text": text,
                }
            )
    with open(OUT, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("Wrote %d rows to %s" % (len(rows), OUT))


if __name__ == "__main__":
    main()
