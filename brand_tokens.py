#!/usr/bin/env python3
"""Deteksi token promo judol berpola kata+angka, mis. zeus88, maxwin98,
dones999, pacinko88, bakricuan22, wintoto189.

Kenapa ini modul baru, bukan sekadar kata kunci lama:
- Matcher lama (pipeline/textutil.py) bekerja per frasa, mis. "maxwin".
  Ia memang akan kena "maxwin98" secara substring, tapi tidak bisa
  membedakan itu dari kata "maxwin" biasa, dan tidak mencatat token
  brand-nya sendiri. Akibatnya di dataset lama, PACINKO88 / BAKRICUAN22 /
  Wintoto189 cuma tercatat sebagai sinyal "related: wd", bukan sebagai
  brand promo.
- Modul ini mencatat tokennya persis (stem + angka + bentuk penulisan)
  dan memberi label kekuatan, supaya frekuensi brand bisa dihitung
  (brand yang diulang di banyak komentar = pola copy-paste promo).

PENTING soal false positive:
Token kata+angka SAJA bukan bukti promo. "iphone15" juga berpola sama.
Karena itu setiap token diberi:
  - known_stem: stem-nya mengandung stem judi yang dikenal, atau
  - promo_context: komentarnya juga mengandung kata konteks promo
    (wd, depo, link, daftar, main, cobain, ...).
  - strength "strong" kalau salah satu dari dua itu ada,
    "candidate" kalau cuma polanya saja.
Token "candidate" tetap disimpan, tapi jangan dihitung sebagai promo
terbukti sampai frekuensi / konteksnya diperiksa di to_csv.

Yang TIDAK dilakukan modul ini:
- Tidak mengumpulkan nama/ID orang, tidak menebak identitas pemilik
  brand, tidak membuka link promo apa pun.
- Tidak memakai daftar brand hasil tebakan sebagai kebenaran mutlak:
  KNOWN_STEMS adalah stem yang sudah terlihat di dataset lama + contoh
  user, dan token baru yang belum dikenal tetap tercatat sebagai
  candidate, bukan dibuang.
"""

import re

# Stem judi yang sudah terlihat di dataset lama / contoh user.
# "contains" dipakai, bukan "sama persis", supaya wintoto (mengandung
# toto) dan bakricuan (mengandung cuan) ikut kena.
KNOWN_STEMS = (
    "zeus", "maxwin", "dones", "pacinko", "toto", "togel", "slot",
    "gacor", "cuan", "olympus", "pragmatic", "scatter", "jackpot",
    "casino", "bet", "judi", "judol", "sultan", "raja", "emas",
)

# Stem yang polanya kata+angka tapi hampir selalu berarti jumlah /
# satuan, bukan brand. Dipakai untuk bentuk terpisah ("depo 50").
AMOUNT_STEMS = {
    "depo", "deposit", "modal", "main", "menang", "kalah", "saldo",
    "bonus", "wd", "withdraw", "bayar", "transfer", "tarik",
}

# Kata konteks promo di dalam komentar yang sama.
PROMO_CONTEXT = (
    "wd", "depo", "deposit", "link", "daftar", "main", "cobain",
    "coba", "freebet", "bonus", "rtp", "gacor", "jp", "cuan",
    "withdraw", "situs", "apk", "gas", "gasken", "langsung",
)

_ATTACHED = re.compile(r"\b([a-z]{3,20})(\d{2,4})\b")
_SEPARATED = re.compile(r"\b([a-z]{3,20})[\s\-_]+(\d{2,4})(?![a-z0-9])")


def _known(stem):
    return any(k in stem for k in KNOWN_STEMS)


def _context_terms(text_lower):
    found = []
    for term in PROMO_CONTEXT:
        if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
            found.append(term)
    return found


def find_brand_tokens(text):
    """Kembalikan list token untuk satu teks komentar.

    Tiap item: token, stem, digits, form (attached/separated/hyphen/
    underscore), known_stem, context_terms, strength.
    Satu token yang sama di satu komentar hanya dicatat sekali.
    """
    if not text:
        return []
    lowered = text.lower()
    context = _context_terms(lowered)
    out, seen = [], set()

    for stem, digits in _ATTACHED.findall(lowered):
        if stem in AMOUNT_STEMS:
            continue
        token = stem + digits
        if token in seen:
            continue
        seen.add(token)
        known = _known(stem)
        out.append({
            "token": token,
            "stem": stem,
            "digits": digits,
            "form": "attached",
            "known_stem": known,
            "context_terms": context,
            "strength": "strong" if (known or context) else "candidate",
        })

    # Bentuk terpisah jauh lebih berisik daripada menempel: "depo 50",
    # "buat 10 orang", "mau 2027" semuanya cocok polanya tapi bukan
    # brand. Karena itu bentuk terpisah HANYA dihitung kalau stem-nya
    # dikenal (zeus 88, maxwin 98) — kata umum + angka dibuang.
    # Pengecualian: "bettingan 2000" itu jumlah taruhan, bukan brand,
    # meski mengandung "bet".
    for m in _SEPARATED.finditer(lowered):
        stem, digits = m.group(1), m.group(2)
        if stem in AMOUNT_STEMS or stem in ("bettingan", "taruhan"):
            continue
        if not _known(stem):
            continue
        token = stem + digits
        if token in seen:
            continue
        sep = m.group(0)[len(stem)]
        form = {" ": "separated", "-": "hyphen", "_": "underscore"}.get(sep, "separated")
        seen.add(token)
        known = _known(stem)
        out.append({
            "token": token,
            "stem": stem,
            "digits": digits,
            "form": form,
            "known_stem": known,
            "context_terms": context,
            "strength": "strong" if (known or context) else "candidate",
        })

    return out
