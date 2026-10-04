"""Learning-path validation and resolution. The sample path exists only in this test."""
from app import paths
from tests.conftest import DB_PATH


def sample(db, verse_text="فقرة عادية يكتبها الفريق عن موضوع الدرس."):
    rid = db.execute("SELECT source_record_id FROM hadith LIMIT 1").fetchone()[0]
    return {"paths": [{
        "id": "test-path", "title": "test", "status": "draft", "modules": [{
            "id": "m1", "title": "m", "lessons": [{"id": "l1", "title": "l", "blocks": [
                {"type": "text", "body": verse_text},
                {"type": "quran", "surah": 1, "ayah_from": 1, "ayah_to": 3},
                {"type": "hadith", "record_id": rid},
                {"type": "question", "prompt": "q", "options": ["a", "b"], "answer": 1},
                {"type": "check", "body": "x"},
            ]}]}]}]}


def test_valid_sample_passes(db, verifier):
    assert paths.validate(sample(db), str(DB_PATH), verifier) == []


def test_typed_verse_in_text_block_is_rejected(db, verifier, ayat):
    typed = next(a for a in ayat if len(a[3].split()) > 8)[3]
    problems = paths.validate(sample(db, verse_text=typed), str(DB_PATH), verifier)
    assert any("typed quran text" in p for p in problems)


def test_bad_references_are_rejected(db, verifier):
    data = sample(db)
    blocks = data["paths"][0]["modules"][0]["lessons"][0]["blocks"]
    blocks[1]["ayah_to"] = 999
    blocks[2]["record_id"] = "no-such-record"
    blocks[3]["answer"] = 5
    problems = paths.validate(data, str(DB_PATH), verifier)
    assert len(problems) >= 3


def test_resolve_fills_text_from_database_and_hides_drafts(db, verifier):
    data = sample(db)
    assert paths.resolve(data, str(DB_PATH), verifier) == []  # draft hidden
    resolved = paths.resolve(data, str(DB_PATH), verifier, include_drafts=True)
    blocks = resolved[0]["modules"][0]["lessons"][0]["blocks"]
    expected = " ".join(r[0] for r in db.execute(
        "SELECT text_raw FROM quran_ayat WHERE surah = 1 AND ayah BETWEEN 1 AND 3 ORDER BY ayah"))
    assert blocks[1]["text"] == expected
    assert blocks[2]["text"] and blocks[2]["grade_source"] == "HadeethEnc.com"
