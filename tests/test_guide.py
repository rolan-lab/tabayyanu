"""Learning-path guide: points to lessons only. Uses a small sample path built in the test."""
import pytest

from app.guide import Guide, stem
from app.llm.openai_compat import OpenAICompat
from tests.test_llm import fake_endpoint


def lesson(lid, title, body):
    return {"id": lid, "title": title, "blocks": [{"type": "text", "body": body}]}


@pytest.fixture
def paths():
    return [{"id": "p", "title": "مسار", "modules": [{"id": "m", "title": "وحدة", "lessons": [
        lesson("l1", "طريقة الوضوء", "الوضوء طهارة يستعد بها المسلم للصلاة. يغسل وجهه ويديه."),
        lesson("l2", "الصبر", "الصبر على البلاء من الإيمان، والقلق يخف بالذكر والدعاء."),
        lesson("l3", "السيرة", "تزوج النبي خديجة رضي الله عنها قبل البعثة."),
    ]}]}]


def test_stem_joins_verb_and_noun_forms():
    assert stem("أتوضأ") == stem("الوضوء")


def test_search_without_model_finds_lesson_and_excerpt(verifier, paths):
    g = Guide(paths, verifier)
    r = g.ask("كيف أتوضأ؟")
    assert r["kind"] == "lessons" and r["lessons"][0]["lesson"] == "طريقة الوضوء"
    assert r["lessons"][0]["href"] == "#/lesson/p/m/l1"
    assert "الوضوء" in r["lessons"][0]["excerpt"]  # excerpt is the team's own text


def test_ruling_question_gets_referral(verifier, paths):
    r = Guide(paths, verifier).ask("هل يجوز لي أن أؤخر الوضوء؟")
    assert r["kind"] == "referral"


def test_empty_question(verifier, paths):
    assert Guide(paths, verifier).ask("  ")["kind"] == "empty"


def test_model_picks_are_validated(monkeypatch, verifier, paths):
    llm = OpenAICompat("http://fake/v1", "k", "m")
    verifier.llm, old = llm, verifier.llm
    try:
        g = Guide(paths, verifier)
        # Keywords in Arabic; then the model returns one valid id and one invented id.
        fake_endpoint(monkeypatch, [{"keywords": ["خديجة", "زواج"]}, {"ids": ["p/m/l3", "invented/id"]}])
        r = g.ask("Who was the Prophet's first wife?", "en")
        assert [x["lesson"] for x in r["lessons"]] == ["السيرة"] and r["picked_by"] == "llm"
    finally:
        verifier.llm = old
