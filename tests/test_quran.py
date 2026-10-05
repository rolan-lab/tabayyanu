"""Quran matcher tests. Every input is built from database text."""
import pytest
from app.normalize import strict


def long_ayat(ayat, rng, k, min_words=6):
    pool = [a for a in ayat if len(a[3].split()) >= min_words]
    return rng.sample(pool, k)


def points_to(m, surah, ayah):
    return m.surah == surah and m.ayah_from <= ayah <= m.ayah_to


def test_full_ayah_plain_spelling_is_exact(verifier, ayat, rng):
    for s, a, _, emlaey in long_ayat(ayat, rng, 40):
        m = verifier.quran.match(emlaey)
        assert m and m.status == "exact" and points_to(m, s, a), (s, a)


def test_full_ayah_uthmani_is_exact(verifier, ayat, rng):
    for s, a, raw, _ in long_ayat(ayat, rng, 40):
        m = verifier.quran.match(raw)
        assert m and m.status == "exact" and points_to(m, s, a), (s, a)


def test_partial_window_is_exact(verifier, ayat, rng):
    for s, a, _, emlaey in long_ayat(ayat, rng, 30, min_words=10):
        words = emlaey.split()
        start = rng.randrange(0, len(words) - 6)
        m = verifier.quran.match(" ".join(words[start:start + 6]))
        assert m and m.status == "exact", (s, a, start)


def test_cross_ayah_quote_is_exact_with_range(verifier, ayat, rng):
    checked = 0
    for i in rng.sample(range(len(ayat) - 1), 300):
        (s1, a1, _, e1), (s2, a2, _, e2) = ayat[i], ayat[i + 1]
        if s1 != s2 or len(e1.split()) < 4 or len(e2.split()) < 4:
            continue
        m = verifier.quran.match(" ".join(e1.split()[-4:] + e2.split()[:4]))
        assert m and m.status == "exact", (s1, a1)
        assert m.surah == s1 and m.ayah_from <= a1 and m.ayah_to >= a2, (s1, a1, m)
        checked += 1
        if checked == 20:
            break
    assert checked == 20


def test_diacritics_do_not_matter(verifier, ayat, rng):
    for s, a, raw, _ in long_ayat(ayat, rng, 20):
        m = verifier.quran.match(strict(raw))
        assert m and m.status == "exact" and points_to(m, s, a), (s, a)


def alter(words, rng, vocab):
    # Interior positions only: dropping the first or last word leaves a genuine
    # partial quotation, which is correctly exact (and flagged as partial).
    i = rng.randrange(1, len(words) - 1)
    kind = rng.choice(["replace", "delete", "add"])
    if kind == "replace":
        new = next(w for w in rng.sample(vocab, 40) if strict(w) != strict(words[i]))
        return kind, words[:i] + [new] + words[i + 1:]
    if kind == "delete":
        return kind, words[:i] + words[i + 1:]
    return kind, words[:i] + [rng.choice(vocab)] + words[i:]


def test_altered_ayah_is_never_exact(verifier, ayat, vocab, rng):
    """Critical-error guard: one word replaced, deleted or added (word taken from the corpus)."""
    for s, a, _, emlaey in long_ayat(ayat, rng, 80):
        kind, altered = alter(emlaey.split(), rng, vocab)
        m = verifier.quran.match(" ".join(altered))
        if m is None:
            continue
        # If the altered text happens to be a real passage elsewhere, exact must point elsewhere.
        assert m.status != "exact" or not points_to(m, s, a), (s, a, kind)


def test_altered_first_and_last_word_detected(verifier, ayat, vocab, rng):
    for s, a, _, emlaey in long_ayat(ayat, rng, 20, min_words=8):
        words = emlaey.split()
        for i in (0, len(words) - 1):
            altered = list(words)
            altered[i] = next(w for w in rng.sample(vocab, 40) if strict(w) != strict(words[i]))
            m = verifier.quran.match(" ".join(altered))
            assert m is None or m.status != "exact" or not points_to(m, s, a), (s, a, i)


def test_spelling_only_difference_is_lexical_diff(verifier, ayat):
    for s, a, _, emlaey in ayat:
        words = emlaey.split()
        idx = next((i for i, w in enumerate(words) if w.endswith("ى")), None)
        if idx is not None and len(words) >= 6:
            words[idx] = words[idx][:-1] + "ي"
            m = verifier.quran.match(" ".join(words))
            assert m and m.status == "lexical_diff", (s, a)
            assert any(d["op"] == "spelling" for d in m.diff)
            return
    raise AssertionError("no ayah with a final ى found")


def test_too_short_is_not_matched(verifier, ayat):
    assert verifier.quran.match(" ".join(ayat[0][3].split()[:2])) is None


def test_repeated_passage_prefers_full_ayah_and_lists_others(verifier, ayat):
    """A whole-ayah quote that also occurs inside or as another ayah points to its own ayah."""
    checked = 0
    for s, a, _, emlaey in ayat:
        if len(emlaey.split()) < 6:
            continue
        m = verifier.quran.match(emlaey)
        if m.also_in:
            assert (m.surah, m.ayah_from, m.ayah_to) == (s, a, a) or not m.partial, (s, a, m.key, m.also_in)
            checked += 1
    assert checked > 0


def test_partial_flag(verifier, ayat):
    _, _, _, emlaey = next(x for x in ayat if len(x[3].split()) > 12)
    words = emlaey.split()
    assert verifier.quran.match(emlaey).partial is False
    assert verifier.quran.match(" ".join(words[2:9])).partial is True


def test_vocative_ya_typed_apart_is_exact(verifier, ayat):
    """The Mushaf text joins vocative يا (ياأيها); people type it apart."""
    s, a, _, emlaey = next(x for x in ayat if x[3].startswith("ياأيها") and len(x[3].split()) > 6)
    m = verifier.quran.match(emlaey.replace("ياأيها", "يا أيها", 1))
    assert m and m.status == "exact" and (m.surah, m.ayah_from) == (s, a)


def test_modern_spelling_of_samawat_is_exact(verifier, db):
    emlaey = db.execute("SELECT text_emlaey FROM quran_ayat WHERE surah = 2 AND ayah = 255").fetchone()[0]
    assert "السموات" in emlaey
    m = verifier.quran.match(emlaey.replace("السموات", "السماوات"))
    assert m and m.status == "exact" and (m.surah, m.ayah_from) == (2, 255)


@pytest.mark.parametrize("surah,ayah,mushaf,modern", [
    (2, 255, "يئوده", "يؤوده"),      # the case reported by the team
    (2, 143, "لرءوف", "لرؤوف"),
])
def test_hamza_seat_spelling_is_exact(verifier, db, surah, ayah, mushaf, modern):
    emlaey = db.execute("SELECT text_emlaey FROM quran_ayat WHERE surah = ? AND ayah = ?", (surah, ayah)).fetchone()[0]
    assert mushaf in emlaey
    m = verifier.quran.match(emlaey.replace(mushaf, modern))
    assert m and m.status == "exact" and (m.surah, m.ayah_from) == (surah, ayah)
