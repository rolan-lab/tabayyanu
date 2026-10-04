"""Hadith matcher and routing tests. Hadith text comes from the database only."""
import pytest

from app.normalize import fold, strict
from app.verify import content_level


@pytest.fixture(scope="module")
def records(verifier):
    h = verifier.hadith
    return [(rid, rec["text"]) for rid, rec in sorted(h.records.items()) if len(rec["text"].split()) >= 20]


def fragment(text, rng, n=10):
    words = text.split()
    i = rng.randrange(3, len(words) - n - 1)
    return words, i, words[i:i + n]


def same_text(verifier, rid_a, rid_b):
    recs = verifier.hadith.records
    return rid_a == rid_b or recs[rid_a]["text"] == recs[rid_b]["text"]


def test_verbatim_fragment_is_exact(verifier, records, rng):
    checked = 0
    for rid, text in rng.sample(records, 60):
        _, _, frag = fragment(text, rng)
        # Skip fragments made mostly of salawat / narrator formulas (too few content words to verify).
        if len(verifier.hadith.content_tokens(" ".join(frag))) < 6:
            continue
        m = verifier.hadith.match(" ".join(frag))
        assert m and m.status == "exact", rid
        checked += 1
    assert checked >= 30


def test_content_word_change_is_never_exact(verifier, records, rng):
    """Critical-error guard for hadith: one content word replaced."""
    ignore = {w for p in verifier.hadith.ignore for w in p}
    vocab = sorted({w for _, t in records for w in t.split() if strict(w)})
    for rid, text in rng.sample(records, 60):
        _, _, frag = fragment(text, rng)
        pos = [k for k in range(1, len(frag) - 1) if strict(frag[k]) and fold(strict(frag[k])) not in ignore]
        if not pos:
            continue
        k = rng.choice(pos)
        new = next(w for w in rng.sample(vocab, 40) if strict(w) != strict(frag[k]))
        m = verifier.hadith.match(" ".join(frag[:k] + [new] + frag[k + 1:]))
        assert m is None or m.status != "exact" or not same_text(verifier, m.record_id, rid), rid


def test_grade_is_copied_verbatim(verifier, db, records, rng):
    rid, text = rng.choice(records)
    _, _, frag = fragment(text, rng)
    m = verifier.hadith.match(" ".join(frag))
    stored = {g for (g,) in db.execute("SELECT grade FROM hadith WHERE source_record_id = ?", (m.record_id,))}
    assert m.grade in stored


def test_salawat_written_as_symbol_still_exact(verifier, records):
    phrase = "صلى الله عليه وسلم"
    rid, text = next((r, t) for r, t in records if phrase in t)
    i = text.index(phrase)
    window = text[max(0, i - 40): i + len(phrase) + 60].split()[1:-1]
    m = verifier.hadith.match(" ".join(window).replace(phrase, "ﷺ"))
    assert m and m.status == "exact"


@pytest.mark.parametrize("text,level", [
    ("هل يجوز لي أن أصوم يوم السبت؟", "D"),
    ("زوجي حلف بالطلاق فما العمل", "D"),
    ("ما حكم صلاة الجماعة في البيت؟", "C"),
    ("ذهبت إلى السوق اليوم", "A"),
])
def test_content_level(text, level):
    assert content_level(text) == level
