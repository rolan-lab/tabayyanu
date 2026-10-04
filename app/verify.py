"""Verification pipeline: text in, list of verified quotations out.

Everything here is deterministic. The verdict (status, reference, source text)
comes only from the matchers; explanations are fixed templates until the LLM
adapter exists, and the LLM will never be allowed to change a verdict.
"""
import json
import re
from pathlib import Path

import yaml

from app.hadith import COLLECTION_NAMES, HadithIndex, HadithMatch
from app.normalize import folded, strict
from app.quran import Quran, QuranMatch

ROOT = Path(__file__).resolve().parent.parent
STRINGS = json.loads((ROOT / "app" / "static" / "strings_ar.json").read_text(encoding="utf-8"))
CONFIG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
QURAN_URL = "https://qurancomplex.gov.sa/quran-dev/"

# Quotation brackets people use around verses and hadith.
_QUOTED = re.compile(r"﴿([^﴾]+)﴾|«([^»]+)»|“([^”]+)”|\"([^\"]+)\"|\{([^}]+)\}")
# Bracketed references such as "(البقرة: 255)" or "[رواه البخاري 1]": dropped before matching.
_REFERENCE = re.compile(r"[\(\[][^\)\]]*(?:\d|[٠-٩]|سورة|رواه|:)[^\)\]]*[\)\]]")
# Framing phrases around a quotation (not part of it). Compared after strict().
_FRAMING = [strict(p).split() for p in (
    "قال الله تعالى", "قال تعالى", "يقول الله تعالى", "قال الله عز وجل", "قال عز وجل",
    "أعوذ بالله من الشيطان الرجيم", "صدق الله العظيم",
    "قال رسول الله صلى الله عليه وسلم", "قال النبي صلى الله عليه وسلم",
    "عن النبي صلى الله عليه وسلم قال", "صلى الله عليه وسلم",
)]


# Strong punctuation that separates sentences (not the Arabic comma, which can sit inside a quote).
_SENTENCE_BREAK = re.compile(r"[:؟?!.\n]+")


def split_quotes(text: str) -> list[str]:
    """Candidate quotations, deterministically (the LLM extractor, when enabled, replaces this):
    bracketed quotations if there are any, otherwise sentence-like segments of the text."""
    min_words = CONFIG["segments"]["min_words"]
    found = [next(g for g in m.groups() if g) for m in _QUOTED.finditer(text)]
    found = [q for q in found if len(strict(q).split()) >= min_words]
    if found:
        return found
    parts = [p for p in _SENTENCE_BREAK.split(text) if len(strict(p).split()) >= min_words]
    return parts or [text]


def clean_quote(text: str) -> str:
    """Drop bracketed references and leading/trailing framing phrases."""
    text = _REFERENCE.sub(" ", text)
    raw = text.split()
    norm = [strict(w) for w in raw]

    def strip_edge(from_start: bool) -> bool:
        flat = [n for n in norm if n]
        for phrase in sorted(_FRAMING, key=len, reverse=True):
            edge = flat[:len(phrase)] if from_start else flat[-len(phrase):]
            if edge == phrase:
                # Remove raw words until the phrase's words are consumed.
                need = len(phrase)
                while need:
                    i = next(k for k, n in enumerate(norm) if n) if from_start else \
                        max(k for k, n in enumerate(norm) if n)
                    need -= len(norm[i].split())
                    del raw[i], norm[i]
                return True
        return False

    while strip_edge(True):
        pass
    while strip_edge(False):
        pass
    return " ".join(raw)


def quran_ref(surah_name: str, ayah_from: int, ayah_to: int) -> str:
    key = "quran_ref_one" if ayah_from == ayah_to else "quran_ref_range"
    return STRINGS[key].format(surah=surah_name, **{"from": ayah_from, "to": ayah_to})


def diff_notes(diff: list[dict]) -> list[str]:
    return [STRINGS["diff"][d["op"]].format(**d) for d in diff if d["op"] != "equal"]


def template_explanation(status: str, ref: str = "", n: int = 0) -> str:
    return STRINGS["explain_template"][status].format(ref=ref, n=n)


def hadith_ref(m: HadithMatch) -> str:
    parts = []
    for coll, number in m.citations:
        key = "hadith_citation" if number else "hadith_citation_no_number"
        parts.append(STRINGS[key].format(collection=COLLECTION_NAMES[coll], number=number))
    return "، ".join(parts)


def _markers(name: str) -> list[str]:
    return [folded(m) for m in CONFIG["levels"][name]]


PERSONAL, RULING, QUESTION = _markers("personal_markers"), _markers("ruling_markers"), _markers("question_markers")


def content_level(text: str) -> str:
    """Organizers' A-D level by fixed word lists (config.yaml). D and C lead to a referral."""
    padded = f" {folded(text)} "
    if any(f" {m} " in padded for m in PERSONAL):
        return "D"
    if any(f" {m} " in padded for m in RULING):
        return "C"
    return "A"


def is_question(text: str) -> bool:
    padded = f" {folded(text)} "
    return "؟" in text or "?" in text or any(padded.startswith(f" {m} ") for m in QUESTION)


STATUS_ORDER = {"exact": 3, "lexical_diff": 2, "near_match": 1}


class Verifier:
    def __init__(self, db_path: str):
        self.quran = Quran(db_path, CONFIG["normalize"], CONFIG["quran"])
        self.hadith = HadithIndex(db_path, CONFIG["normalize"], CONFIG["hadith"])

    def verify(self, text: str) -> dict:
        text = (text or "").strip()
        if not strict(text):
            return {"items": [], "notice": "empty_input"}
        level = content_level(text)
        quotes = [self.verify_quote(q, level) for q in split_quotes(text)]
        found = [q for q in quotes if q["status"] != "not_found"]
        items = []
        if level in ("C", "D"):
            items.append(self.message_item("referral", level))
            items += found  # a misquoted ayah inside a question is still corrected
        elif found:
            items = found
        elif is_question(text):
            items.append(self.message_item("out_of_scope", level))
        elif len(quotes) == 1:
            items = quotes
        else:
            items = [self.verify_quote(text, level)]  # report the text once, not per segment
        return {"items": items, "level": level}

    def message_item(self, kind: str, level: str) -> dict:
        return {"kind": kind, "quote": None, "level": level, "status": None, "status_label": STRINGS[f"kind_{kind}"],
                "source": None, "diff": [], "diff_notes": [], "note": None,
                "explanation": STRINGS[kind], "explanation_origin": "template"}

    def verify_quote(self, quote: str, level: str = "A") -> dict:
        cleaned = clean_quote(quote)
        item = {"kind": "quote", "quote": quote.strip(), "level": level, "status": "not_found", "source": None,
                "diff": [], "diff_notes": [], "note": STRINGS["not_found_note"],
                "explanation": template_explanation("not_found"), "explanation_origin": "template",
                "status_label": STRINGS["status"]["not_found"]}
        if len(strict(cleaned).split()) < CONFIG["quran"]["min_words"]:
            item["note"] = STRINGS["too_short_note"]
            item["note_key"] = "too_short"
            return item
        q = self.quran.match(cleaned)
        h = self.hadith.match(cleaned)
        # The Quran wins ties: a verse quoted inside a narration is still a verse.
        if q and (not h or STATUS_ORDER[q.status] >= STATUS_ORDER[h.status]):
            item.update(self.quran_fields(q))
        elif h:
            item.update(self.hadith_fields(h))
        return item

    def quran_fields(self, m: QuranMatch) -> dict:
        ref = quran_ref(m.surah_name, m.ayah_from, m.ayah_to)
        notes = []
        if m.partial:
            notes.append(STRINGS["partial_note"])
        if m.also_in:
            refs = "، ".join(quran_ref(self.quran.surah_name(s), a, b) for s, a, b in m.also_in)
            notes.append(STRINGS["also_in"].format(refs=refs))
        return {
            "status": m.status, "status_label": STRINGS["status"][m.status], "note": " ".join(notes) or None,
            "partial": m.partial, "also_in": [list(k) for k in m.also_in],
            "source": {"type": "quran", "ref": ref, "text": m.source_text, "grade": None, "grade_source": None,
                       "name": STRINGS["quran_source_name"], "url": QURAN_URL,
                       "surah": m.surah, "ayah_from": m.ayah_from, "ayah_to": m.ayah_to},
            "diff": m.diff, "diff_notes": diff_notes(m.diff),
            "explanation": template_explanation(m.status, ref, sum(d["op"] != "equal" for d in m.diff)),
        }

    def hadith_fields(self, m: HadithMatch) -> dict:
        ref = hadith_ref(m)
        return {
            "status": m.status, "status_label": STRINGS["status"][m.status], "note": None,
            "source": {"type": "hadith", "ref": ref, "text": m.text, "grade": m.grade,
                       "grade_source": "HadeethEnc.com", "attribution": m.attribution,
                       "name": STRINGS["hadith_source_name"], "url": m.url, "record_id": m.record_id},
            "diff": m.diff, "diff_notes": diff_notes(m.diff),
            "explanation": template_explanation(m.status, ref, sum(d["op"] != "equal" for d in m.diff)),
        }
