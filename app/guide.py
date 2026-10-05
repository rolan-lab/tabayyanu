"""Learning-path guide: answers a visitor's question only by pointing to lessons.

Nothing here is generated for the visitor to read. The reply is: links to lessons,
a short excerpt of the team's own lesson text, a referral for ruling or personal
questions, and a "verify" hint when the question contains a verse or hadith.

The model (optional) has one narrow job here (docs/CHANGES.md, 2026-10-06): turn the
question into Arabic search keywords and pick up to three lessons from the search
results. Its output is validated: keywords must be Arabic words, picked ids must be
among the candidates. Without a model, plain keyword search is used.
"""
import re
import sqlite3

from app.normalize import folded, strict
from app.verify import STRINGS_BY_LANG, clean_quote, content_level

STOPWORDS = {folded(w) for w in (
    "ما ماذا هل كيف لماذا متى أين من عن في إلى على أريد اريد أتعلم تعلم أعرف معرفة شرح اشرح "
    "لي هو هي ذلك هذا هذه التي الذي و أو ثم مع كل بعض أن إن كان يكون عند"
).split()}
ARABIC_WORD = re.compile(r"^[ء-ي]{2,20}$")
MAX_RESULTS = 3


_PREFIXES = ("وال", "بال", "فال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "س")
_SUFFIXES = ("ون", "ين", "ات", "ان", "ها", "هم", "كم", "نا", "ه", "ي", "ا")


def stem(word: str) -> str:
    """Very light Arabic stem for the fallback search: drop common prefixes, a verb prefix and a
    suffix, keep at most 4 letters. Used only as a search prefix, never shown."""
    w = folded(word)
    for p in _PREFIXES:
        if w.startswith(p) and len(w) - len(p) >= 3:
            w = w[len(p):]
            break
    if w[:1] in ("ا", "ي", "ت", "ن") and len(w) >= 5:
        w = w[1:]
    if w[:1] in ("ت",) and len(w) >= 4:  # تفعّل forms: توضأ -> وضأ
        w = w[1:]
    for s in _SUFFIXES:
        if w.endswith(s) and len(w) - len(s) >= 3:
            w = w[:-len(s)]
            break
    w = w[:4]
    if len(w) == 3 and w[-1] in "اوي":  # weak final letter: وضا / وضو -> وض
        w = w[:2]
    return w


class Guide:
    def __init__(self, paths: list[dict], verifier):
        self.v = verifier
        self.llm = verifier.llm
        self.con = sqlite3.connect(":memory:", check_same_thread=False)
        self.con.execute("CREATE VIRTUAL TABLE lessons USING fts5(key UNINDEXED, text)")
        self.meta = {}
        for p in paths:
            for m in p["modules"]:
                for lesson in m["lessons"]:
                    key = f"{p['id']}/{m['id']}/{lesson['id']}"
                    body = "\n".join(b.get("body", "") for b in lesson["blocks"]
                                     if b["type"] in ("text", "heading", "cited"))
                    self.meta[key] = {
                        "path": p["title"], "module": m["title"], "lesson": lesson["title"],
                        "href": f"#/lesson/{p['id']}/{m['id']}/{lesson['id']}", "text": body}
                    words = folded(lesson["title"] + " " + m["title"] + " " + body)
                    # Words plus their light stems, so «أتوضأ» finds «الوضوء» (both stem to «وض»).
                    stems = " ".join(stem(w) for w in words.split() if len(stem(w)) >= 2)
                    self.con.execute("INSERT INTO lessons VALUES (?, ?)", (key, words + " " + stems))

    def keywords(self, question: str) -> list[str]:
        words = None
        if self.llm.name != "none":
            words = self.llm.search_keywords(question)
        if not words:  # no model, or its answer failed validation
            words = [w for w in folded(question).split() if w not in STOPWORDS]
        clean = [folded(w) for w in words if ARABIC_WORD.match(strict(w).replace(" ", ""))]
        return [w for w in dict.fromkeys(clean) if w and w not in STOPWORDS][:8]

    def excerpt(self, text: str, words: list[str], limit: int = 220) -> str:
        """The first sentence of the lesson that contains a search word (team's own text)."""
        for sentence in re.split(r"(?<=[.؟!\n])", text):
            if any(w in folded(sentence) for w in words):
                s = sentence.strip()
                return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"
        first = text.strip().split("\n")[0]
        return first if len(first) <= limit else first[:limit].rsplit(" ", 1)[0] + "…"

    def ask(self, question: str, lang: str = "ar") -> dict:
        S = STRINGS_BY_LANG[lang]
        question = (question or "").strip()
        if not strict(question) and not re.search(r"[A-Za-z]", question):
            return {"kind": "empty", "message": S["guide_empty"], "lessons": []}
        level = content_level(question)
        cleaned = clean_quote(question)
        has_text = any(m and m.status in ("exact", "lexical_diff") for m in (
            self.v.quran.match(cleaned), self.v.hadith.match(cleaned))) if len(cleaned.split()) >= 5 else False

        words = self.keywords(question)
        candidates = []
        if words:
            # Each word as typed, plus its light stem (indexed the same way).
            terms = [f'"{w}"' for w in words] + [f'"{stem(w)}"' for w in words if len(stem(w)) >= 2]
            query = " OR ".join(dict.fromkeys(terms))
            candidates = [r[0] for r in self.con.execute(
                "SELECT key FROM lessons WHERE lessons MATCH ? ORDER BY bm25(lessons) LIMIT 8", (query,))]
        picked = None
        if candidates and self.llm.name != "none":
            picked = self.llm.pick_lessons(question, [(k, self.meta[k]["lesson"], self.meta[k]["module"])
                                                      for k in candidates])
        keys = (picked or candidates)[:MAX_RESULTS]
        lessons = [{"path": self.meta[k]["path"], "module": self.meta[k]["module"], "lesson": self.meta[k]["lesson"],
                    "href": self.meta[k]["href"], "excerpt": self.excerpt(self.meta[k]["text"], words)}
                   for k in keys]
        return {
            "kind": "referral" if level in ("C", "D") else "lessons",
            "message": S["referral"] if level in ("C", "D") else (S["guide_found"] if lessons else S["guide_none"]),
            "lessons": lessons,
            "verify_hint": S["guide_verify_hint"] if has_text else None,
            "picked_by": "llm" if picked else "search",
        }
