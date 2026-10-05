"""FastAPI app: POST /api/verify, GET /health, GET /api/meta, and the static frontend.

Stateless. No user text is stored or logged: logs hold counts and latency only.
"""
import hashlib
import json
import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import paths
from app.guide import Guide
from app.verify import Verifier

ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    """Minimal .env reader (KEY=VALUE lines); real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env_file(ROOT / ".env")


DB_PATH = os.environ.get("DB_PATH", str(ROOT / "data" / "db" / "tabayyanu.sqlite"))
STATIC = ROOT / "app" / "static"
MAX_CHARS = 5000

log = logging.getLogger("tabayyanu")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    started = time.monotonic()
    state["verifier"] = Verifier(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    state["counts"] = {
        "ayat": con.execute("SELECT COUNT(*) FROM quran_ayat").fetchone()[0],
        "hadith": con.execute("SELECT COUNT(*) FROM hadith").fetchone()[0],
    }
    # The site's motto verse (49:6), taken from the database like every other text.
    surah_name, surah_name_en, text = con.execute(
        "SELECT surah_name_ar, surah_name_en, text_raw FROM quran_ayat WHERE surah = 49 AND ayah = 6").fetchone()
    state["motto"] = {"text": text, "surah_name": surah_name, "surah_name_en": surah_name_en, "surah": 49, "ayah": 6}
    state["examples"] = build_examples(con)
    con.close()
    include_drafts = os.environ.get("SHOW_DRAFT_PATHS") == "1"  # team preview only
    paths_file = Path(os.environ.get("PATHS_FILE", paths.PATHS_FILE))
    state["paths"] = paths.resolve(paths.load(paths_file), DB_PATH, state["verifier"], include_drafts)
    state["guide"] = Guide(state["paths"], state["verifier"])
    log.info("loaded index in %.2fs: %s, llm=%s", time.monotonic() - started, state["counts"],
             state["verifier"].llm.name)
    yield


app = FastAPI(title="Tabayyanu", lifespan=lifespan)


class VerifyRequest(BaseModel):
    text: str = Field(..., max_length=MAX_CHARS)
    lang: str = Field("ar", pattern="^(ar|en)$")


@app.post("/api/verify")
def verify(req: VerifyRequest):
    started = time.monotonic()
    try:
        result = state["verifier"].verify(req.text, req.lang)
    except Exception:
        log.exception("verify failed")  # message only; the input text is never logged
        raise HTTPException(status_code=500, detail="verify_failed")
    statuses = [i["status"] for i in result["items"]]
    log.info("verify items=%d statuses=%s chars=%d ms=%.0f",
             len(statuses), statuses, len(req.text), (time.monotonic() - started) * 1000)
    return result


REPORTS = Path(os.environ.get("REPORTS_PATH", str(ROOT / "data" / "reports" / "reports.jsonl")))


class ReportRequest(BaseModel):
    consent: bool
    quote: str = Field(..., max_length=MAX_CHARS)
    status: str | None = Field(None, max_length=40)
    ref: str | None = Field(None, max_length=300)
    comment: str = Field("", max_length=1000)


@app.post("/api/report")
def report(req: ReportRequest):
    """Store an error report only with explicit consent (rule 7). Nothing else is stored."""
    if req.consent is not True:
        raise HTTPException(status_code=400, detail="consent_required")
    REPORTS.parent.mkdir(parents=True, exist_ok=True)
    row = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **req.model_dump()}
    with REPORTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log.info("report stored (with consent)")
    return {"ok": True}


@app.get("/health")
def health():
    llm = state["verifier"].llm.name if "verifier" in state else None
    return {"status": "ok", "llm": llm, **state.get("counts", {})}


def build_examples(con) -> list[dict]:
    """Demo inputs built from database text (never typed by hand): a real ayah, the same ayah
    with one word missing, a Sahih hadith, a post that quotes both, and a ruling question."""
    words = con.execute("SELECT text_emlaey FROM quran_ayat WHERE surah = 2 AND ayah = 286").fetchone()[0].split()
    ayah = " ".join(words[:14])
    altered = " ".join(words[:5] + words[6:14])
    hadith = con.execute("SELECT text_raw FROM hadith WHERE source_record_id = '5913' LIMIT 1").fetchone()[0]
    matn = hadith[hadith.index("«") + 1:hadith.index("»")] if "«" in hadith else hadith
    return [
        {"key": "ayah", "text": ayah},
        {"key": "altered", "text": altered},
        {"key": "hadith", "text": matn},
        {"key": "post", "text": f"انشروا هذا المنشور: قال تعالى ﴿{altered}﴾ وقال رسول الله صلى الله عليه وسلم «{matn}»"},
        {"key": "question", "text": "هل يجوز لي أن أجمع الصلاة إذا كنت مسافرًا؟"},
    ]


@app.get("/api/examples")
def examples():
    return {"examples": state["examples"]}


@app.get("/api/meta")
def meta():
    lessons = sum(len(m["lessons"]) for p in state["paths"] for m in p["modules"])
    return {"motto": state["motto"], "max_chars": MAX_CHARS, "paths": len(state["paths"]), "lessons": lessons,
            "hadith_records": len(state["verifier"].hadith.records), **state["counts"]}


class GuideRequest(BaseModel):
    question: str = Field(..., max_length=500)
    lang: str = Field("ar", pattern="^(ar|en)$")


@app.post("/api/guide")
def guide(req: GuideRequest):
    """Learning-path guide: links to lessons only (no generated answer). The question is not stored."""
    started = time.monotonic()
    result = state["guide"].ask(req.question, req.lang)
    log.info("guide kind=%s lessons=%d picked_by=%s ms=%.0f", result["kind"], len(result["lessons"]),
             result.get("picked_by"), (time.monotonic() - started) * 1000)
    return result


@app.get("/api/paths")
def learning_paths():
    return {"paths": state["paths"]}


def asset_version() -> str:
    """Short hash of the static files, so browsers fetch new scripts and styles after a deploy."""
    digest = hashlib.sha1()
    for f in sorted(STATIC.glob("*.*")):
        digest.update(f.read_bytes())
    return digest.hexdigest()[:10]


ASSET_VERSION = asset_version()


@app.get("/")
def index():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for name in ("style.css", "app.js", "paths.js", "guide.js"):
        html = html.replace(f"/static/{name}", f"/static/{name}?v={ASSET_VERSION}")
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=STATIC), name="static")
