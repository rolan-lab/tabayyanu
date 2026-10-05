"""Approved meaning and translation for a verified text, read from the database.

Nothing here is generated. Sources (SOURCES.md):
  Quran   Arabic explanation: Tafsir Muyassar (KFGQPC developer platform)
          English translation: QuranEnc.com, Saheeh International (key and version stored)
  Hadith  Arabic explanation and English translation: HadeethEnc.com
Texts are returned exactly as stored; the only processing is splitting the tafsir's
<span class='aya'> markup into segments so the page can style quoted verses.
"""
import re
import sqlite3

_AYA_SPAN = re.compile(r"<span class='aya'>(.*?)</span>", re.S)
QURANENC_URL = "https://quranenc.com/en/browse/{key}"
TAFSIR_URL = "https://qurancomplex.gov.sa/quran-dev/"


def tafsir_segments(raw: str) -> list[dict]:
    """[{"text", "aya": bool}] with the markup removed and the text unchanged."""
    out, pos = [], 0
    for m in _AYA_SPAN.finditer(raw):
        if m.start() > pos:
            out.append({"text": raw[pos:m.start()], "aya": False})
        out.append({"text": m.group(1), "aya": True})
        pos = m.end()
    if pos < len(raw):
        out.append({"text": raw[pos:], "aya": False})
    return out


class Meanings:
    def __init__(self, db_path: str):
        self.con = sqlite3.connect(db_path, check_same_thread=False)

    def quran(self, surah: int, ayah_from: int, ayah_to: int) -> dict:
        tafsir = self.con.execute(
            "SELECT ayah, tafsir_raw FROM quran_tafsir WHERE surah = ? AND ayah BETWEEN ? AND ? ORDER BY ayah",
            (surah, ayah_from, ayah_to)).fetchall()
        trans = self.con.execute(
            "SELECT ayah, translation, footnotes, translation_key, version FROM quran_translation"
            " WHERE surah = ? AND ayah BETWEEN ? AND ? ORDER BY ayah", (surah, ayah_from, ayah_to)).fetchall()
        key, version = (trans[0][3], trans[0][4]) if trans else (None, None)
        return {
            "explanation_ar": {
                "items": [{"ayah": a, "segments": tafsir_segments(t)} for a, t in tafsir],
                "source": "التفسير الميسر — مجمع الملك فهد لطباعة المصحف الشريف", "url": TAFSIR_URL},
            "translation_en": {
                "items": [{"ayah": a, "text": t, "footnotes": f or ""} for a, t, f, _, _ in trans],
                "source": f"QuranEnc.com — Saheeh International ({key}, version {version})",
                "url": QURANENC_URL.format(key=key) if key else None},
        }

    def hadith(self, record_id: str, url: str) -> dict:
        row = self.con.execute(
            "SELECT explanation_ar, title_en, text_en, explanation_en FROM hadith_extra WHERE source_record_id = ?",
            (record_id,)).fetchone()
        if not row:
            return {}
        explanation_ar, title_en, text_en, explanation_en = row
        en_url = url.replace("/ar/", "/en/") if url else None
        out = {}
        if explanation_ar:
            out["explanation_ar"] = {"text": explanation_ar, "source": "موسوعة الأحاديث النبوية (HadeethEnc.com)",
                                     "url": url}
        if text_en:
            out["translation_en"] = {"title": title_en, "text": text_en, "explanation": explanation_en or "",
                                     "source": "HadeethEnc.com — The Encyclopedia of Translated Prophetic Hadiths",
                                     "url": en_url}
        return out
