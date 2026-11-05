"""Mesin pencocokan teks untuk pipeline scraper.

Tujuan: run pertama hanya memakai pencocokan frasa persis pada batch
komentar pertama yang kelihatan, sehingga banyak yang lolos. Modul ini
menangkap lebih banyak dengan cara yang tetap bisa dijelaskan:

- exact: frasa kata kunci persis (setelah normalisasi huruf/punktuasi).
- variant: frasa varian yang dipetakan ke kata kunci dasar (lihat
  config.json). Dilaporkan variannya, jadi noise-nya kelihatan.
- deobfuscated: frasa yang cocok setelah mengubah leet-speak umum
  (mis. sl0t -> slot, g4cor -> gacor).
- compact: frasa yang cocok kalau semua spasi dihapus (menangkap
  penulisan spasi-spasi seperti "s l o t g a c o r").
- fuzzy: kata komentar yang mirip kata kunci (difflib >= threshold)
  tapi tidak sama persis — mis. typo. Dilaporkan terpisah, bukan
  dianggap bukti sekuat exact.
- related: istilah terkait judi (rtp, scatter, wd, ...) — sinyal
  konteks saja, bukan hit utama.

Tidak ada data orang yang diekstrak di sini: hanya teks komentar.
"""

import difflib
import re
import unicodedata

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def normalize(text):
    """Lowercase, buang aksen, ganti punktuasinya jadi spasi."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def deobfuscate(normalized_text):
    """Ubah leet-speak umum kembali ke huruf biasa."""
    return re.sub(r"\s+", " ", normalized_text.translate(_LEET)).strip()


def _phrase_forms(phrase):
    norm = normalize(phrase)
    return norm, deobfuscate(norm), deobfuscate(norm).replace(" ", "")


def match_comment(text, config):
    """Kembalikan daftar match untuk satu teks komentar.

    Setiap match: {"match_type", "term", "base_keyword"}.
    base_keyword None untuk related terms.
    """
    norm = normalize(text)
    deob = deobfuscate(norm)
    compact = deob.replace(" ", "")
    keywords = config.get("keywords", [])
    variants = config.get("variants", {})
    related = config.get("related_terms", [])
    threshold = float(config.get("fuzzy_threshold", 0.85))

    matches = []
    seen = set()

    def add(match_type, term, base):
        key = (match_type, term, base)
        if key not in seen:
            seen.add(key)
            matches.append(
                {"match_type": match_type, "term": term, "base_keyword": base}
            )

    # exact + deobfuscated + compact untuk kata kunci dasar
    for kw in keywords:
        norm_kw, deob_kw, compact_kw = _phrase_forms(kw)
        if norm_kw and norm_kw in norm:
            add("exact", kw, kw)
        elif deob_kw and deob_kw in deob:
            add("deobfuscated", kw, kw)
        elif compact_kw and len(compact_kw) >= 4 and compact_kw in compact:
            add("compact", kw, kw)

    # varian -> dipetakan ke kata kunci dasar
    for base, variant_list in variants.items():
        for var in variant_list:
            norm_var, deob_var, _ = _phrase_forms(var)
            if norm_var and (norm_var in norm or norm_var in deob):
                add("variant", var, base)

    # fuzzy per kata (typo), hanya kata >= 4 huruf, dibatasi 3 per komentar
    words = [w for w in norm.split() if len(w) >= 4]
    keyword_words = {}
    for kw in keywords:
        for w in normalize(kw).split():
            if len(w) >= 4:
                keyword_words.setdefault(w, kw)
    fuzzy_count = 0
    for w in words:
        if fuzzy_count >= 3:
            break
        for kw_word, base in keyword_words.items():
            if w == kw_word:
                continue
            if difflib.SequenceMatcher(None, w, kw_word).ratio() >= threshold:
                add("fuzzy", "%s~%s" % (w, kw_word), base)
                fuzzy_count += 1
                break

    # istilah terkait (sinyal konteks saja)
    for term in related:
        norm_term = normalize(term)
        if norm_term and (norm_term in norm or norm_term in deob):
            add("related", term, None)

    return matches
