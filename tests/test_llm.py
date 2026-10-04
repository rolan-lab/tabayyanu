"""LLM adapter tests with a fake OpenAI-compatible endpoint (no network, no key)."""
import json

import pytest

from app import llm as llm_pkg
from app.llm import openai_compat
from app.llm.openai_compat import OpenAICompat
from app.verify import Verifier
from tests.conftest import DB_PATH


class FakeResponse:
    def __init__(self, content, usage=None, status=200):
        self.content, self.usage, self.status_code = content, usage or {}, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return {"choices": [{"message": {"content": self.content}}], "usage": self.usage}


def fake_endpoint(monkeypatch, replies):
    """Each call pops the next reply: a dict (sent as JSON), a raw string, or an Exception."""
    calls = []

    def post(url, json=None, timeout=None, headers=None):
        calls.append(json)
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        content = reply if isinstance(reply, str) else __import__("json").dumps(reply, ensure_ascii=False)
        return FakeResponse(content, {"prompt_tokens": 100, "completion_tokens": 20})

    monkeypatch.setattr(openai_compat.requests, "post", post)
    return calls


@pytest.fixture
def client():
    return OpenAICompat("http://fake/v1", "test-key", "pinned-model")


def test_request_is_temperature_zero_with_schema_and_delimited_text(monkeypatch, client):
    calls = fake_endpoint(monkeypatch, [{"quotes": []}])
    client.extract_quotes("نص المستخدم")
    body = calls[0]
    assert body["temperature"] == 0 and body["model"] == "pinned-model"
    assert body["response_format"]["type"] == "json_schema"
    assert "<user_text>" in body["messages"][1]["content"]


def test_extracted_quotes_must_be_literal_substrings(monkeypatch, client):
    text = "انشروا هذا: الحمد لله كثيرا. ولا تنسونا"
    fake_endpoint(monkeypatch, [{"quotes": ["الحمد لله كثيرا", "نص لم يرد في المنشور إطلاقا"]}])
    assert client.extract_quotes(text) == ["الحمد لله كثيرا"]


@pytest.mark.parametrize("reply", ["not json", {"wrong": 1}, RuntimeError("timeout")])
def test_bad_model_output_returns_none(monkeypatch, client, reply):
    fake_endpoint(monkeypatch, [reply])
    assert client.extract_quotes("أي نص") is None
    assert client.usage["failures"] + client.usage["rejected"] == 1


@pytest.mark.parametrize("text,ok", [
    ("النص مطابق لما في المصدر بعد تجاهل التشكيل.", True),
    ("هذا يجوز لك فعله.", False),                     # ruling word
    ("النص باطل ولا أصل له.", False),                 # calls a text false
    ("قال تعالى ﴿نص﴾ وهو مطابق.", False),             # quotation brackets
    ("جملة أولى. جملة ثانية. جملة ثالثة.", False),     # more than two sentences
])
def test_explanation_validation(text, ok):
    assert (llm_pkg.validate_explanation(text) is not None) == ok


def test_pipeline_uses_llm_explanation_but_never_its_verdict(monkeypatch, ayat):
    _, _, _, emlaey = next(a for a in ayat if len(a[3].split()) > 8)
    words = emlaey.split()
    altered = " ".join(words[:3] + words[4:])  # one word deleted: must stay lexical_diff
    v = Verifier(str(DB_PATH), llm=OpenAICompat("http://fake/v1", "k", "m"))
    # 1st call: extraction (nothing extra); 2nd: a valid explanation.
    fake_endpoint(monkeypatch, [{"quotes": []}, {"explanation": "في النص كلمة ناقصة مقارنة بالآية في المصدر."}])
    item = v.verify(altered)["items"][0]
    assert item["status"] == "lexical_diff" and item["explanation_origin"] == "llm"


def test_explanation_contradicting_the_verdict_is_rejected(monkeypatch, ayat):
    _, _, _, emlaey = next(a for a in ayat if len(a[3].split()) > 8)
    words = emlaey.split()
    v = Verifier(str(DB_PATH), llm=OpenAICompat("http://fake/v1", "k", "m"))
    # The model claims a full match for an altered text: rejected, template used, status unchanged.
    fake_endpoint(monkeypatch, [{"quotes": []}, {"explanation": "النص مطابق تماما للمصدر."}])
    item = v.verify(" ".join(words[:3] + words[4:]))["items"][0]
    assert item["status"] == "lexical_diff" and item["explanation_origin"] == "template"


def test_pipeline_falls_back_to_template_when_model_fails(monkeypatch, ayat):
    _, _, _, emlaey = next(a for a in ayat if len(a[3].split()) > 8)
    v = Verifier(str(DB_PATH), llm=OpenAICompat("http://fake/v1", "k", "m"))
    fake_endpoint(monkeypatch, [RuntimeError("down")])
    item = v.verify(emlaey)["items"][0]
    assert item["status"] == "exact" and item["explanation_origin"] == "template"


def test_hallucinated_extraction_is_discarded(monkeypatch, ayat):
    _, _, _, emlaey = next(a for a in ayat if len(a[3].split()) > 8)
    post = f"منشور طويل للتجربة فيه كلام كثير. {emlaey} . وكلام آخر في النهاية للتجربة"
    v = Verifier(str(DB_PATH), llm=OpenAICompat("http://fake/v1", "k", "m"))
    # Model "extracts" a different ayah that is not in the post: it must be dropped.
    other = next(a for a in ayat if len(a[3].split()) > 8 and a[3] != emlaey)[3]
    fake_endpoint(monkeypatch, [{"quotes": [other]}] + [{"explanation": "شرح قصير."}] * 4)
    refs = [i["source"]["ref"] for i in v.verify(post)["items"] if i.get("source")]
    assert refs and all(other not in json.dumps(refs, ensure_ascii=False) for _ in refs)
