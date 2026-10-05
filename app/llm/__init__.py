"""LLM adapter. The model has two jobs only: extract quotations and explain a computed verdict.

Selected by the LLM_BACKEND environment variable:
  none           no model; callers fall back to deterministic extraction and template text
  openai_compat  any OpenAI-compatible /chat/completions endpoint (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL)

Every output is validated in code. On any failure the methods return None and the
caller uses the deterministic path. A model can never change a verdict.
"""
import os
import re

from app.llm.prompts import EXPLAIN_SCHEMA, EXPLAIN_SYSTEM, EXTRACT_SCHEMA, EXTRACT_SYSTEM, wrap_user_text

FALSE_WORDS = ("باطل", "موضوع", "مكذوب", "مزيف", "مختلق", "لا أصل له", "ضعيف",
               "fabricated", "false", "fake", "forged", "weak", "baseless")
RULING_WORDS = ("يجوز", "حرام", "حلال", "يجب", "واجب", "مكروه", "فتوى", "أفتي",
                "permissible", "forbidden", "haram", "halal", "obligatory", "fatwa", "ruling")
QUOTE_MARKS = re.compile(r"[﴿﴾«»\"“”{}]")


class NoLLM:
    name = "none"

    def extract_quotes(self, text: str):
        return None

    def explain(self, record: dict, verdict: str, diff: list, quote: str, lang: str = "ar"):
        return None

    def search_keywords(self, question: str):
        return None

    def pick_lessons(self, question: str, candidates: list):
        return None


def validate_quotes(quotes, text: str) -> list[str] | None:
    """Keep only quotations that are literal substrings of the input."""
    if not isinstance(quotes, list):
        return None
    return [q.strip() for q in quotes if isinstance(q, str) and q.strip() and q.strip() in text]


# Claims of a full match, rejected when the computed status is not "exact".
FULL_MATCH_CLAIMS = ("مطابق تماما", "مطابق تمامًا", "مطابق للمصدر", "لا يوجد اختلاف", "لا اختلاف", "بدون اختلاف",
                     "exactly matches", "identical", "no difference", "fully matches", "matches the source exactly")


def validate_explanation(value, status: str = "exact") -> str | None:
    if not isinstance(value, str):
        return None
    if status != "exact" and any(c in value.lower() for c in FULL_MATCH_CLAIMS):
        return None  # would contradict the verdict computed by code
    text = value.strip()
    sentences = [s for s in re.split(r"[.!؟?]+", text) if s.strip()]
    if not text or len(text) > 400 or len(sentences) > 2:
        return None
    if QUOTE_MARKS.search(text) or any(w in text.lower() for w in FALSE_WORDS + RULING_WORDS):
        return None
    return text


def get_llm():
    backend = os.environ.get("LLM_BACKEND", "none").strip().lower()
    if backend == "openai_compat":
        from app.llm.openai_compat import OpenAICompat
        return OpenAICompat(
            base_url=os.environ["LLM_BASE_URL"],
            api_key=os.environ.get("LLM_API_KEY", ""),
            model=os.environ["LLM_MODEL"],
        )
    return NoLLM()


__all__ = ["get_llm", "NoLLM", "validate_quotes", "validate_explanation",
           "EXTRACT_SYSTEM", "EXPLAIN_SYSTEM", "EXTRACT_SCHEMA", "EXPLAIN_SCHEMA", "wrap_user_text"]
