from app.normalize import fold, folded, strict

LETTERS = set(" ءابةتثجحخدذرزسشصضطظعغفقكلمنهويىؤئ")


def test_strict_leaves_only_letters_on_uthmani(ayat):
    for _, _, raw, _ in ayat:
        out = strict(raw)
        assert set(out) <= LETTERS, set(out) - LETTERS
        assert "  " not in out


def test_strict_matches_stored_text_norm(db):
    for emlaey, norm in db.execute("SELECT text_emlaey, text_norm FROM quran_ayat LIMIT 300"):
        assert strict(emlaey) == norm


def test_alef_forms_unified():
    assert strict("أ إ آ ٱ ا") == "ا ا ا ا ا"


def test_tatweel_and_direction_marks_removed():
    assert strict("كـــتب‎") == "كتب"


def test_folds_are_switchable():
    assert fold("مصطفى") == "مصطفي"
    assert fold("مصطفى", fold_ya=False, fold_ta_marbuta=False, fold_hamza_carriers=False) == "مصطفى"
    assert folded("رحمة") == "رحمه"
