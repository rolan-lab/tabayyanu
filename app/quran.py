"""Quran matcher: finds where a quote sits in the Quran and how it differs.

Two indexes are built: one on the KFGQPC plain-spelling text (text_emlaey), close
to how people type verses, and one on the Uthmani text (text_raw), for quotes
copied from a Mushaf app. The better match wins. The whole Quran is one token sequence, so a quote can
span consecutive ayat, but never two surahs.

Every word of the quote counts. A quote is `exact` only if all its words equal
the source words under strict normalization; any other difference, including a
spelling-only one (ى/ي, ة/ه, hamza), makes it `lexical_diff`.
"""
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.normalize import fold, strict


@dataclass
class Token:
    display: str   # word as written in the source (or the user's text)
    strict: str    # strict() form
    folded: str    # folded form, used to find candidates
    ayah_idx: int = -1  # index into QuranIndex.ayat (source tokens only)


@dataclass
class QuranMatch:
    status: str                     # "exact" | "lexical_diff"
    surah: int
    surah_name: str
    ayah_from: int
    ayah_to: int
    source_text: str                # Uthmani text of the matched ayat, as given
    diff: list = field(default_factory=list)   # [{"op", "quote", "source"}]
    similarity: float = 0.0
    coverage: float = 1.0           # share of the matched ayat's words the quote covers
    position: int = 0               # token offset in the index (earlier = smaller)
    also_in: list = field(default_factory=list)  # other places with the same exact text

    @property
    def key(self):
        return (self.surah, self.ayah_from, self.ayah_to)

    @property
    def partial(self) -> bool:
        return self.coverage < 1.0

    def rank(self):
        # Exact first, then closest wording, then the place the quote covers most fully
        # (a whole-ayah quote should point to that ayah, not to a longer ayah containing it).
        return (self.status == "exact", self.similarity, self.coverage, -self.position)


def tokenize(text: str, flags: dict) -> list[Token]:
    """Split text into tokens; a raw word may yield several tokens after strict()."""
    tokens = []
    for raw in (text or "").split():
        for part in strict(raw).split():
            tokens.append(Token(raw, part, fold(part, **flags)))
    return join_vocative(tokens, flags)


def join_vocative(tokens: list[Token], flags: dict) -> list[Token]:
    """The Mushaf texts always write vocative يا joined to the next word (ياأيها، ياقوم), and
    people usually type it apart («يا أيها»). A standalone يا never occurs in the Quran data,
    so joining it to the next word cannot create a false match."""
    out = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.strict == "يا" and i + 1 < len(tokens):
            nxt = tokens[i + 1]
            joined = t.strict + nxt.strict
            out.append(Token(f"{t.display} {nxt.display}", joined, fold(joined, **flags)))
            i += 2
        else:
            out.append(t)
            i += 1
    return out


class QuranIndex:
    COLUMNS = {"emlaey": 4, "uthmani": 3}  # position of the text column in self.ayat rows

    def __init__(self, db_path: str, norm_flags: dict, cfg: dict, column: str = "emlaey"):
        self.flags = norm_flags
        self.cfg = cfg
        con = sqlite3.connect(db_path)
        self.ayat = con.execute(
            "SELECT surah, surah_name_ar, ayah, text_raw, text_emlaey FROM quran_ayat ORDER BY id"
        ).fetchall()
        con.close()
        self.tokens: list[Token] = []
        col = self.COLUMNS[column]
        for idx, row in enumerate(self.ayat):
            for tok in tokenize(row[col], norm_flags):
                tok.ayah_idx = idx
                self.tokens.append(tok)
        self.ayah_len = Counter(t.ayah_idx for t in self.tokens)
        self.n = cfg["ngram"]
        self.ngrams = defaultdict(list)
        for pos in range(len(self.tokens) - self.n + 1):
            key = tuple(t.folded for t in self.tokens[pos:pos + self.n])
            self.ngrams[key].append(pos)

    def surah_of(self, pos: int) -> int:
        return self.ayat[self.tokens[pos].ayah_idx][0]

    def match(self, quote: list[Token]) -> QuranMatch | None:
        """Best match for the quote tokens, or None if nothing passes the thresholds."""
        if len(quote) < self.cfg["min_words"]:
            return None
        votes = Counter()
        for i in range(len(quote) - self.n + 1):
            for pos in self.ngrams.get(tuple(t.folded for t in quote[i:i + self.n]), ()):
                votes[pos - i] += 1
        found = {}
        for offset, _ in votes.most_common(self.cfg["candidates"]):
            cand = self._align(quote, offset)
            if cand and (cand.key not in found or cand.rank() > found[cand.key].rank()):
                found[cand.key] = cand
        return pick_best(list(found.values()))

    def _align(self, quote: list[Token], offset: int) -> QuranMatch | None:
        pad = max(3, len(quote) // 4)
        lo, hi = max(0, offset - pad), min(len(self.tokens), offset + len(quote) + pad)
        window = self.tokens[lo:hi]
        sm = SequenceMatcher(None, [t.folded for t in quote], [t.folded for t in window], autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        matched = sum(b.size for b in blocks)
        if matched < self.cfg["min_matched_words"]:
            return None
        # Source span covers the matched source words, extended to pair with any
        # unmatched quote words at either end, but only inside the same ayah.
        start = lo + blocks[0].b
        end = lo + blocks[-1].b + blocks[-1].size  # exclusive
        lead = blocks[0].a
        trail = len(quote) - (blocks[-1].a + blocks[-1].size)
        while lead and start > 0 and self.tokens[start - 1].ayah_idx == self.tokens[start].ayah_idx:
            start, lead = start - 1, lead - 1
        while trail and end < len(self.tokens) and self.tokens[end].ayah_idx == self.tokens[end - 1].ayah_idx:
            end, trail = end + 1, trail - 1
        if self.surah_of(start) != self.surah_of(end - 1):
            return None
        source = self.tokens[start:end]
        similarity = matched / max(len(quote), len(source))
        if similarity < self.cfg["min_similarity"]:
            return None
        diff = word_diff(quote, source)
        exact = all(d["op"] == "equal" for d in diff)
        first, last = self.ayat[source[0].ayah_idx], self.ayat[source[-1].ayah_idx]
        span_words = sum(self.ayah_len[i] for i in range(source[0].ayah_idx, source[-1].ayah_idx + 1))
        ayat_text = " ".join(self.ayat[i][3] for i in range(source[0].ayah_idx, source[-1].ayah_idx + 1))
        return QuranMatch(
            status="exact" if exact else "lexical_diff",
            surah=first[0], surah_name=first[1], ayah_from=first[2], ayah_to=last[2],
            source_text=ayat_text, diff=diff, similarity=round(similarity, 3),
            coverage=round(len(source) / span_words, 3), position=start,
        )


def word_diff(quote: list[Token], source: list[Token]) -> list[dict]:
    """Word-level diff. Ops: equal, spelling (same word after folding), replace, insert, delete.

    'insert' = word in the quote but not in the source; 'delete' = source word missing from the quote.
    """
    sm = SequenceMatcher(None, [t.folded for t in quote], [t.folded for t in source], autojunk=False)
    out = []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            for q, s in zip(quote[a1:a2], source[b1:b2]):
                kind = "equal" if q.strict == s.strict else "spelling"
                out.append({"op": kind, "quote": q.display, "source": s.display})
        elif op == "replace":
            out.append({"op": "replace", "quote": " ".join(t.display for t in quote[a1:a2]),
                        "source": " ".join(t.display for t in source[b1:b2])})
        elif op == "insert":
            out.append({"op": "delete", "quote": "", "source": " ".join(t.display for t in source[b1:b2])})
        elif op == "delete":
            out.append({"op": "insert", "quote": " ".join(t.display for t in quote[a1:a2]), "source": ""})
    return merge_equal(out)


def merge_equal(diff: list[dict]) -> list[dict]:
    """Join runs of consecutive 'equal' words so the diff stays short."""
    merged = []
    for d in diff:
        if merged and d["op"] == "equal" and merged[-1]["op"] == "equal":
            merged[-1] = {"op": "equal", "quote": merged[-1]["quote"] + " " + d["quote"],
                          "source": merged[-1]["source"] + " " + d["source"]}
        else:
            merged.append(d)
    return merged


class Quran:
    """Both indexes; returns the better match (exact first, then similarity)."""

    def __init__(self, db_path: str, norm_flags: dict, cfg: dict):
        self.flags = norm_flags
        self.indexes = [QuranIndex(db_path, norm_flags, cfg, col) for col in QuranIndex.COLUMNS]
        self.surah_names = {row[0]: row[1] for row in self.indexes[0].ayat}
        con = sqlite3.connect(db_path)
        self.surah_names_en = dict(con.execute("SELECT DISTINCT surah, surah_name_en FROM quran_ayat"))
        con.close()

    def surah_name(self, surah: int, lang: str = "ar") -> str:
        return self.surah_names_en[surah] if lang == "en" else self.surah_names[surah]

    def match(self, text: str) -> QuranMatch | None:
        quote = tokenize(text, self.flags)
        results = [m for m in (ix.match(quote) for ix in self.indexes) if m]
        if not results:
            return None
        best = max(results, key=QuranMatch.rank)
        others = {key for m in results for key in [m.key] + m.also_in if m.status == "exact"}
        best.also_in = sorted(others - {best.key}) if best.status == "exact" else []
        return best


def pick_best(cands: list[QuranMatch]) -> QuranMatch | None:
    """Best candidate; for an exact match, record the other exact places too."""
    if not cands:
        return None
    best = max(cands, key=QuranMatch.rank)
    if best.status == "exact":
        best.also_in = sorted(c.key for c in cands if c.status == "exact" and c.key != best.key)
    return best
