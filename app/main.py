"""FastAPI app: POST /api/verify, GET /health, GET /api/meta, and the static frontend.

Stateless. No user text is stored or logged: logs hold counts and latency only.
"""
import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import paths
from app.verify import Verifier

ROOT = Path(__file__).resolve().parent.parent
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
    surah_name, text = con.execute(
        "SELECT surah_name_ar, text_raw FROM quran_ayat WHERE surah = 49 AND ayah = 6").fetchone()
    state["motto"] = {"text": text, "surah_name": surah_name, "surah": 49, "ayah": 6}
    con.close()
    include_drafts = os.environ.get("SHOW_DRAFT_PATHS") == "1"  # team preview only
    paths_file = Path(os.environ.get("PATHS_FILE", paths.PATHS_FILE))
    state["paths"] = paths.resolve(paths.load(paths_file), DB_PATH, state["verifier"], include_drafts)
    log.info("loaded index in %.2fs: %s", time.monotonic() - started, state["counts"])
    yield


app = FastAPI(title="Tabayyanu", lifespan=lifespan)


class VerifyRequest(BaseModel):
    text: str = Field(..., max_length=MAX_CHARS)


@app.post("/api/verify")
def verify(req: VerifyRequest):
    started = time.monotonic()
    try:
        result = state["verifier"].verify(req.text)
    except Exception:
        log.exception("verify failed")  # message only; the input text is never logged
        raise HTTPException(status_code=500, detail="verify_failed")
    statuses = [i["status"] for i in result["items"]]
    log.info("verify items=%d statuses=%s chars=%d ms=%.0f",
             len(statuses), statuses, len(req.text), (time.monotonic() - started) * 1000)
    return result


@app.get("/health")
def health():
    return {"status": "ok", **state.get("counts", {})}


@app.get("/api/meta")
def meta():
    return {"motto": state["motto"], "max_chars": MAX_CHARS, **state["counts"]}


@app.get("/api/paths")
def learning_paths():
    return {"paths": state["paths"]}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
