"""Client for any OpenAI-compatible /chat/completions endpoint (temperature 0, JSON schema)."""
import json
import logging
import time

import requests

from app.llm import validate_explanation, validate_quotes
from app.llm.prompts import (EXPLAIN_SCHEMA, EXPLAIN_SYSTEM, EXTRACT_SCHEMA, EXTRACT_SYSTEM, KEYWORDS_SCHEMA,
                             KEYWORDS_SYSTEM, PICK_SYSTEM, pick_schema, wrap_user_text)

log = logging.getLogger("tabayyanu.llm")
TIMEOUT_S = 15

# Plain-language change types, so the model cannot confuse which side a word is missing from.
CHANGE_TYPES = {
    "replace": "the user's quote has a different word than the source",
    "insert": "extra word in the user's quote, not in the source",
    "delete": "word in the source that is missing from the user's quote",
    "spelling": "same word, spelled differently in the user's quote",
}


def describe_change(d: dict) -> dict:
    return {"type": CHANGE_TYPES[d["op"]], "user_quote_has": d.get("quote") or None,
            "source_has": d.get("source") or None}


class OpenAICompat:
    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.model = model  # pinned through LLM_MODEL
        self.usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "failures": 0, "rejected": 0}

    def _call(self, system: str, user: str, schema: dict) -> dict | None:
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema", "json_schema": schema},
        }
        started = time.monotonic()
        try:
            resp = requests.post(self.url, json=body, timeout=TIMEOUT_S,
                                 headers={"Authorization": f"Bearer {self.api_key}"})
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage") or {}
            self.usage["calls"] += 1
            self.usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            self.usage["completion_tokens"] += usage.get("completion_tokens", 0)
            log.info("llm call ok model=%s prompt_tokens=%s completion_tokens=%s ms=%.0f", self.model,
                     usage.get("prompt_tokens"), usage.get("completion_tokens"), (time.monotonic() - started) * 1000)
            return json.loads(data["choices"][0]["message"]["content"])
        except Exception as exc:  # network, HTTP, JSON or shape errors: caller falls back
            self.usage["failures"] += 1
            log.warning("llm call failed: %s", type(exc).__name__)
            return None

    def extract_quotes(self, text: str) -> list[str] | None:
        out = self._call(EXTRACT_SYSTEM, wrap_user_text(text), EXTRACT_SCHEMA)
        return self._count(validate_quotes(out.get("quotes"), text) if isinstance(out, dict) else None, out)

    def explain(self, record: dict, verdict: str, diff: list, quote: str, lang: str = "ar") -> str | None:
        facts = {"status": verdict, "reference": record.get("ref"), "source": record.get("name"),
                 "grade": record.get("grade"), "grade_source": record.get("grade_source"),
                 "changes": [describe_change(d) for d in diff if d.get("op") != "equal"][:8]}
        user = f"<record>\n{json.dumps(facts, ensure_ascii=False)}\n</record>\n{wrap_user_text(quote)}"
        language = "English" if lang == "en" else "Arabic"
        out = self._call(EXPLAIN_SYSTEM.replace("{language}", language), user, EXPLAIN_SCHEMA)
        return self._count(validate_explanation(out.get("explanation"), verdict) if isinstance(out, dict) else None, out)

    def search_keywords(self, question: str) -> list[str] | None:
        """Guide: Arabic search keywords for a question (validated by the caller: Arabic words only)."""
        out = self._call(KEYWORDS_SYSTEM, wrap_user_text(question), KEYWORDS_SCHEMA)
        words = out.get("keywords") if isinstance(out, dict) else None
        valid = [w for w in words if isinstance(w, str)][:6] if isinstance(words, list) else None
        return self._count(valid or None, out)

    def pick_lessons(self, question: str, candidates: list) -> list[str] | None:
        """Guide: up to 3 lesson ids chosen among the search results (ids checked again here)."""
        ids = [c[0] for c in candidates]
        listing = "\n".join(f"{cid}: {title} ({module})" for cid, title, module in candidates)
        out = self._call(PICK_SYSTEM, f"<lessons>\n{listing}\n</lessons>\n{wrap_user_text(question)}", pick_schema(ids))
        picked = out.get("ids") if isinstance(out, dict) else None
        valid = [i for i in dict.fromkeys(picked) if i in ids][:3] if isinstance(picked, list) else None
        return self._count(valid or None, out)

    def _count(self, value, raw):
        """Count outputs that arrived but failed validation (the caller then falls back)."""
        if value is None and raw is not None:
            self.usage["rejected"] += 1
        return value
