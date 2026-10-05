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
from app.llm import get_llm
from app.meaning import Meanings
from app.normalize import folded, strict
from app.quran import Quran, QuranMatch

ROOT = Path(__file__).resolve().parent.parent
STRINGS_BY_LANG = {lang: json.loads((ROOT / "app" / "static" / f"strings_{lang}.json").read_text(encoding="utf-8"))
                   for lang in ("ar", "en")}
STRINGS = STRINGS_BY_LANG["ar"]
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


def bracketed_quotes(text: str) -> list[str]:
    """Quotations inside ﴿﴾ «» “” "" {} with enough words."""
    min_words = CONFIG["segments"]["min_words"]
    found = [next(g for g in m.groups() if g) for m in _QUOTED.finditer(text)]
    return [q for q in found if len(strict(q).split()) >= min_words]


def sentence_segments(text: str) -> tuple[list[str], bool]:
    """Sentence-like pieces with enough words, and whether any short piece was left out."""
    min_words = CONFIG["segments"]["min_words"]
    pieces = [p for p in _SENTENCE_BREAK.split(text) if strict(p)]
    kept = [p for p in pieces if len(strict(p).split()) >= min_words]
    return kept, len(kept) < len(pieces)


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


def quran_ref(surah_name: str, ayah_from: int, ayah_to: int, S: dict = STRINGS) -> str:
    key = "quran_ref_one" if ayah_from == ayah_to else "quran_ref_range"
    return S[key].format(surah=surah_name, **{"from": ayah_from, "to": ayah_to})


def diff_notes(diff: list[dict], S: dict = STRINGS) -> list[str]:
    return [S["diff"][d["op"]].format(**d) for d in diff if d["op"] != "equal"]


def template_explanation(status: str, ref: str = "", n: int = 0, S: dict = STRINGS) -> str:
    return S["explain_template"][status].format(ref=ref, n=n)


def hadith_ref(citations: list, S: dict = STRINGS) -> str:
    parts = []
    for coll, number in citations:
        key = "hadith_citation" if number else "hadith_citation_no_number"
        parts.append(S[key].format(collection=S["collections"][coll], number=number))
    return S["list_separator"].join(parts)


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
    def __init__(self, db_path: str, llm=None):
        self.quran = Quran(db_path, CONFIG["normalize"], CONFIG["quran"])
        self.hadith = HadithIndex(db_path, CONFIG["normalize"], CONFIG["hadith"])
        self.llm = llm or get_llm()
        self.meanings = Meanings(db_path)

    def verify(self, text: str, lang: str = "ar") -> dict:
        text = (text or "").strip()
        if not strict(text):
            return {"items": [], "notice": "empty_input"}
        level = content_level(text)
        quotes = self.find_quotes(text, level)
        found = [q for q in quotes if q["status"] != "not_found"]
        items = []
        if level in ("C", "D"):
            items.append(self.message_item("referral", level))
            items += found  # a misquoted ayah inside a question is still corrected
        elif found:
            items = found
        elif is_question(text):
            items.append(self.message_item("out_of_scope", level))
        else:
            items = [self.verify_quote(text, level)]  # report the text once, not per segment
        for item in items:
            self.add_meaning(item)
            if lang != "ar":
                self.localize(item, STRINGS_BY_LANG[lang], lang)
            self.add_explanation(item, lang)
        return {"items": items, "level": level, "lang": lang}

    def add_meaning(self, item: dict) -> None:
        """Approved explanation and translation from the database (never generated)."""
        src = item.get("source")
        if not src:
            return
        if src["type"] == "quran":
            item["meaning"] = self.meanings.quran(src["surah"], src["ayah_from"], src["ayah_to"])
        elif src["type"] == "hadith":
            item["meaning"] = self.meanings.hadith(src["record_id"], src["url"])

    def localize(self, item: dict, S: dict, lang: str) -> None:
        """Rebuild every user-facing string of an item in another language from its structured data.
        Status, references (numbers), grades and source texts are not changed."""
        if item["kind"] != "quote":
            item["status_label"] = S[f"kind_{item['kind']}"]
            item["explanation"] = S[item["kind"]]
            return
        item["status_label"] = S["status"][item["status"]]
        src = item.get("source")
        if not src:
            item["note"] = S["too_short_note"] if item.get("note_key") == "too_short" else S["not_found_note"]
            item["explanation"] = template_explanation("not_found", S=S)
            return
        if src["type"] == "quran":
            src["ref"] = quran_ref(self.quran.surah_name(src["surah"], lang), src["ayah_from"], src["ayah_to"], S)
            src["name"] = S["quran_source_name"]
            notes = [S["partial_note"]] if item.get("partial") else []
            if item.get("also_in"):
                refs = S["list_separator"].join(quran_ref(self.quran.surah_name(s, lang), a, b, S)
                                                for s, a, b in item["also_in"])
                notes.append(S["also_in"].format(refs=refs))
            item["note"] = " ".join(notes) or None
        else:
            src["ref"] = hadith_ref(src["citations"], S)
            src["name"] = S["hadith_source_name"]
        item["diff_notes"] = diff_notes(item["diff"], S)
        item["explanation"] = template_explanation(item["status"], src["ref"],
                                                   sum(d["op"] != "equal" for d in item["diff"]), S)

    def add_explanation(self, item: dict, lang: str = "ar") -> None:
        """LLM explanation for a found quotation; the template stays when the model is off or fails.
        The verdict fields are never touched here."""
        if item["kind"] != "quote" or item["status"] == "not_found":
            return
        text = self.llm.explain(item["source"], item["status"], item["diff"], item["quote"], lang)
        if text:
            item["explanation"] = text
            item["explanation_origin"] = "llm"

    def find_quotes(self, text: str, level: str) -> list[dict]:
        """Deterministic quotation finding (the LLM extractor, when enabled, comes first):
        bracketed quotations; else the whole text; else its sentence-like segments."""
        bracketed = bracketed_quotes(text)
        if bracketed:
            return [self.verify_quote(q, level) for q in bracketed]
        whole = self.verify_quote(text, level)
        if whole["status"] == "exact":
            return [whole]
        extracted = self.llm.extract_quotes(text)  # validated: literal substrings only
        if extracted:
            items = [self.verify_quote(q, level) for q in extracted]
            if any(i["status"] != "not_found" for i in items):
                return items
        segments, dropped_short = sentence_segments(text)
        if len(segments) < 2:
            return [whole]
        parts = [self.verify_quote(q, level) for q in segments]
        if whole["status"] == "not_found":
            return parts
        # The whole text matched with differences. Trust the sentence split only if it gives an
        # exact quotation and no short piece was dropped (a short piece could be part of an
        # altered quote, and dropping it would hide the change).
        if any(p["status"] == "exact" for p in parts) and not dropped_short:
            return parts
        return [whole]

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
        ref = hadith_ref(m.citations)
        return {
            "status": m.status, "status_label": STRINGS["status"][m.status], "note": None,
            "source": {"type": "hadith", "ref": ref, "text": m.text, "grade": m.grade,
                       "grade_source": "HadeethEnc.com", "attribution": m.attribution,
                       "name": STRINGS["hadith_source_name"], "url": m.url, "record_id": m.record_id,
                       "citations": [list(c) for c in m.citations]},
            "diff": m.diff, "diff_notes": diff_notes(m.diff),
            "explanation": template_explanation(m.status, ref, sum(d["op"] != "equal" for d in m.diff)),
        }
