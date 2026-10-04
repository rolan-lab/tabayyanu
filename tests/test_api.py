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
