"""Arabic text normalization for matching.

Two levels:
  strict(text)  - removes diacritics, Quranic marks, tatweel, punctuation and
                  digits, and unifies alef forms. Two texts equal under strict()
                  are the same words.
  folded(text)  - strict() plus the optional letter folds from config.yaml
                  (ya / ta marbuta / hamza carriers). Used only to find
                  candidates, never to decide that a quote is exact.
"""
import re
import unicodedata

# Harakat, shadda, sukun, tanween, dagger alif (U+0670) and other combining marks.
_DIACRITICS = re.compile(
    "["
    "ؐ-ؚ"   # Quranic signs above/below letters
    "ً-ٟ"   # harakat, tanween, shadda, sukun, hamza above/below marks
    "ٰ"          # superscript (dagger) alef
    "ۖ-ۭ"   # Quranic annotation marks, small letters, end of ayah, rub el hizb
    "࣓-ࣿ"   # extended Quranic marks (e.g. open tanween)
    "ـ"          # tatweel
    "​-‏‪-‮⁦-⁩﻿"  # zero-width and direction marks
    "]"
)
_ALEF_FORMS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا"})
_HAMZA_SEATS = str.maketrans({"ؤ": "ء", "ئ": "ء"})
# Anything that is not an Arabic letter or whitespace becomes a space
# (punctuation, brackets, digits, Latin text).
_NON_LETTERS = re.compile(r"[^ء-غف-ي\s]")
_SPACES = re.compile(r"\s+")


def strict(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    text = _DIACRITICS.sub("", text)
    text = text.translate(_ALEF_FORMS)
    text = _NON_LETTERS.sub(" ", text)
    # The KFGQPC plain-spelling text writes «السموات» (182 times); people write «السماوات».
    # Same word, two spellings; no other word contains «سموات».
    text = text.replace("سموات", "سماوات")
    # Hamza seat is a spelling convention: the Mushaf text writes «يئوده، رءوف، مسئولا»,
    # people write «يؤوده، رؤوف، مسؤولا». Treat ء / ؤ / ئ as one letter, like the alef forms.
    text = text.translate(_HAMZA_SEATS)
    return _SPACES.sub(" ", text).strip()


def fold(word_or_text: str, fold_ya=True, fold_ta_marbuta=True, fold_hamza_carriers=True) -> str:
    """Apply the optional letter folds to text that is already strict()."""
    out = word_or_text
    if fold_ya:
        out = out.replace("ى", "ي")
    if fold_ta_marbuta:
        out = out.replace("ة", "ه")
    if fold_hamza_carriers:
        out = out.replace("ؤ", "و").replace("ئ", "ي").replace("ء", "")
    return out


def folded(text: str, **flags) -> str:
    return _SPACES.sub(" ", fold(strict(text), **flags)).strip()


def words(text: str) -> list[str]:
    """Split raw text into display words, keeping only those that survive strict()."""
    return [w for w in (text or "").split() if strict(w)]
