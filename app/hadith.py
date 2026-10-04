"""Hadith matcher over the HadeethEnc records that cite Sahih al-Bukhari or Sahih Muslim.

Quotes are usually fragments of a longer narration, so the score is containment
(how much of the quote is found, in order, inside a record), not whole-text
similarity. Candidates come from SQLite FTS5 ranked by bm25().

Statuses: exact (every quote word found contiguously, strict equality),
lexical_diff (same passage with a few different words), near_match (many of the
quote's word pairs occur in the record: possibly narrated by meaning).
"""
import sqlite3
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.normalize import fold, strict
from app.quran import Token, merge_equal, word_diff

COLLECTION_NAMES = {"bukhari": "صحيح البخاري", "muslim": "صحيح مسلم"}


@dataclass
class HadithMatch:
    status: str
    record_id: str
    text: str                       # matn exactly as given by HadeethEnc
    grade: str | None
    attribution: str | None
    citations: list                 # [(collection, number or None)]
    url: str
    diff: list = field(default_factory=list)
    similarity: float = 0.0
    containment: float = 0.0

    def rank(self):
        order = {"exact": 3, "lexical_diff": 2, "near_match": 1}
        return (order[self.status], self.similarity, self.containment)


class HadithIndex:
    def __init__(self, db_path: str, norm_flags: dict, cfg: dict):
        self.flags, self.cfg = norm_flags, cfg
        self.ignore = [fold(strict(p), **norm_flags).split() for p in cfg["ignore_phrases"]]
        self.con = sqlite3.connect(db_path, check_same_thread=False)
        self.records = {}
        rows = self.con.execute(
            "SELECT source_record_id, collection, number, text_raw, grade, attribution, source_url"
            " FROM hadith ORDER BY source_record_id, collection").fetchall()
        for rid, coll, number, text, grade, attribution, url in rows:
            rec = self.records.setdefault(rid, {
                "text": text, "grade": grade, "attribution": attribution, "url": url, "citations": []})
            rec["citations"].append((coll, number))
        self.tokens = {rid: self.content_tokens(rec["text"]) for rid, rec in self.records.items()}

    def content_tokens(self, text: str) -> list[Token]:
        """Tokens with the ignored phrases (salawat, radiya Allahu anhu...) removed."""
        tokens = []
        for raw in (text or "").replace("ﷺ", " ").split():
            for part in strict(raw).split():
                tokens.append(Token(raw, part, fold(part, **self.flags)))
        out, i = [], 0
        while i < len(tokens):
            for phrase in self.ignore:
                if [t.folded for t in tokens[i:i + len(phrase)]] == phrase:
                    i += len(phrase)
                    break
            else:
                out.append(tokens[i])
                i += 1
        return out

    def candidates(self, quote: list[Token]) -> list[str]:
        terms = sorted({t.folded for t in quote if len(t.folded) > 1})
        if not terms:
            return []
        query = " OR ".join(f'"{t}"' for t in terms)
        rows = self.con.execute(
            "SELECT source_record_id FROM hadith_fts WHERE hadith_fts MATCH ? ORDER BY bm25(hadith_fts) LIMIT ?",
            (query, self.cfg["fts_candidates"])).fetchall()
        return [r[0] for r in rows]

    def trim_partial_phrases(self, quote: list[Token]) -> list[Token]:
        """Drop the tail of an ignored phrase at the start of a quote and its head at the end
        (e.g. a quote pasted from the middle of «صلى الله عليه وسلم»)."""
        for phrase in self.ignore:
            for k in range(len(phrase) - 1, 0, -1):
                if [t.folded for t in quote[:k]] == phrase[-k:]:
                    quote = quote[k:]
                    break
            for k in range(len(phrase) - 1, 0, -1):
                if len(quote) > k and [t.folded for t in quote[-k:]] == phrase[:k]:
                    quote = quote[:-k]
                    break
        return quote

    def match(self, text: str) -> HadithMatch | None:
        quote = self.trim_partial_phrases(self.content_tokens(text))
        if len(quote) < self.cfg["min_words"]:
            return None
        best = None
        for rid in self.candidates(quote):
            cand = self._compare(quote, rid)
            if cand and (best is None or cand.rank() > best.rank()):
                best = cand
        return best

    def _compare(self, quote: list[Token], rid: str) -> HadithMatch | None:
        record = self.tokens[rid]
        sm = SequenceMatcher(None, [t.folded for t in quote], [t.folded for t in record], autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        matched = sum(b.size for b in blocks)
        containment = pair_containment(quote, record)
        status, diff, similarity = None, [], 0.0
        if matched >= self.cfg["min_matched_words"]:
            # Record span aligned with the quote, extended to pair with unmatched quote words at the ends.
            start = max(0, blocks[0].b - blocks[0].a)
            end = min(len(record), blocks[-1].b + blocks[-1].size + (len(quote) - blocks[-1].a - blocks[-1].size))
            span = record[start:end]
            similarity = matched / max(len(quote), len(span))
            diff = word_diff(quote, span)
            if all(d["op"] == "equal" for d in diff):
                status = "exact"
            elif similarity >= self.cfg["min_similarity"]:
                status = "lexical_diff"
        if status is None:
            shared = int(containment * max(1, len(quote) - 1))
            if containment >= self.cfg["near_min_containment"] and shared >= self.cfg["near_min_shared_pairs"]:
                status, diff = "near_match", []
            else:
                return None
        rec = self.records[rid]
        return HadithMatch(status=status, record_id=rid, text=rec["text"], grade=rec["grade"],
                           attribution=rec["attribution"], citations=rec["citations"], url=rec["url"],
                           diff=merge_equal(diff), similarity=round(similarity, 3),
                           containment=round(containment, 3))


def pair_containment(quote: list[Token], record: list[Token]) -> float:
    """Share of the quote's consecutive word pairs that occur anywhere in the record."""
    q_pairs = {(a.folded, b.folded) for a, b in zip(quote, quote[1:])}
    if not q_pairs:
        return 0.0
    r_pairs = {(a.folded, b.folded) for a, b in zip(record, record[1:])}
    return len(q_pairs & r_pairs) / len(q_pairs)
