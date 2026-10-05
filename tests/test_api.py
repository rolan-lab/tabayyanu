from fastapi.testclient import TestClient

from app.main import app

ITEM_KEYS = {"quote", "level", "status", "source", "diff", "explanation", "explanation_origin"}


def first_long_ayah(ayat):
    return next(a for a in ayat if len(a[3].split()) > 8)


def test_health_and_meta(db):
    with TestClient(app) as c:
        h = c.get("/health").json()
        assert h["status"] == "ok" and h["ayat"] == 6236
        meta = c.get("/api/meta").json()
        assert meta["motto"]["surah"] == 49 and meta["motto"]["text"]


def test_verify_exact_ayah(ayat):
    surah, _, _, emlaey = first_long_ayah(ayat)
    with TestClient(app) as c:
        item = c.post("/api/verify", json={"text": emlaey}).json()["items"][0]
    assert set(item) >= ITEM_KEYS
    assert item["status"] == "exact" and item["source"]["surah"] == surah
    assert item["explanation_origin"] == "template"


def test_verify_strips_framing_and_brackets(ayat):
    _, _, _, emlaey = first_long_ayah(ayat)
    with TestClient(app) as c:
        r = c.post("/api/verify", json={"text": f"قال تعالى: ﴿{emlaey}﴾ صدق الله العظيم"}).json()
    assert [i["status"] for i in r["items"]] == ["exact"]


def test_verify_empty_and_too_long(db):
    with TestClient(app) as c:
        assert c.post("/api/verify", json={"text": "   "}).json() == {"items": [], "notice": "empty_input"}
        assert c.post("/api/verify", json={"text": "ا" * 5001}).status_code == 422


def test_unknown_text_is_not_found_and_never_called_false(db):
    with TestClient(app) as c:
        item = c.post("/api/verify", json={"text": "هذا نص تجريبي عادي لا علاقة له بالمصادر إطلاقا"}).json()["items"][0]
    assert item["status"] == "not_found"
    for word in ("باطل", "موضوع", "مكذوب", "مزيف"):
        assert word not in item["explanation"]


def test_prose_sentence_before_colon_does_not_spoil_exact(ayat):
    _, _, _, emlaey = first_long_ayah(ayat)
    with TestClient(app) as c:
        r = c.post("/api/verify", json={"text": f"وصلتني هذه الرسالة اليوم من أحد الأصدقاء الكرام: {emlaey}"}).json()
    assert [i["status"] for i in r["items"] if i["status"] != "not_found"] == ["exact"]


def test_short_trailing_piece_keeps_whole_text_verdict(ayat):
    """An altered tail split off by a full stop must not be dropped silently."""
    _, _, _, emlaey = next(a for a in ayat if len(a[3].split()) > 12)
    words = emlaey.split()
    text = " ".join(words[:-2]) + ". " + words[-1] + " زيادة"
    with TestClient(app) as c:
        statuses = [i["status"] for i in c.post("/api/verify", json={"text": text}).json()["items"]]
    assert "exact" not in statuses or len(statuses) > 1


def test_report_requires_consent(tmp_path, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "REPORTS", tmp_path / "reports.jsonl")
    with TestClient(app) as c:
        assert c.post("/api/report", json={"consent": False, "quote": "نص"}).status_code == 400
        assert not (tmp_path / "reports.jsonl").exists()
        assert c.post("/api/report", json={"consent": True, "quote": "نص", "comment": "خطأ"}).json() == {"ok": True}
    assert (tmp_path / "reports.jsonl").read_text(encoding="utf-8").count("\n") == 1


def test_examples_come_from_database_and_verify(db):
    with TestClient(app) as c:
        examples = {e["key"]: e["text"] for e in c.get("/api/examples").json()["examples"]}
        assert set(examples) == {"ayah", "altered", "hadith", "post", "question"}
        status = lambda t: [i["status"] or i["kind"] for i in c.post("/api/verify", json={"text": t}).json()["items"]]
        assert status(examples["ayah"]) == ["exact"]
        assert status(examples["altered"]) == ["lexical_diff"]
        assert status(examples["hadith"]) == ["exact"]
        assert status(examples["question"]) == ["referral"]


def test_index_versions_assets_and_disables_cache():
    with TestClient(app) as c:
        r = c.get("/")
    assert r.headers["cache-control"] == "no-cache"
    assert "/static/app.js?v=" in r.text and "/static/style.css?v=" in r.text
