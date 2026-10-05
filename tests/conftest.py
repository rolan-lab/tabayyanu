"""Shared fixtures. All religious text in tests is read from the ingested database."""
import os
import random
import sqlite3
import sys

# Unit tests never call a real model (no network, no cost); LLM behaviour is tested with a fake endpoint.
os.environ["LLM_BACKEND"] = "none"
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / "data" / "db" / "tabayyanu.sqlite"


@pytest.fixture(scope="session")
def db():
    if not DB_PATH.exists():
        pytest.skip("database missing: run python scripts/ingest.py")
    con = sqlite3.connect(DB_PATH)
    yield con
    con.close()


@pytest.fixture(scope="session")
def ayat(db):
    """All ayat as (surah, ayah, text_raw, text_emlaey), in Mushaf order."""
    return db.execute("SELECT surah, ayah, text_raw, text_emlaey FROM quran_ayat ORDER BY id").fetchall()


@pytest.fixture(scope="session")
def vocab(ayat):
    return sorted({w for _, _, _, e in ayat for w in e.split()})


@pytest.fixture
def rng():
    return random.Random(20261004)


@pytest.fixture(scope="session")
def verifier():
    from app.verify import Verifier
    return Verifier(str(DB_PATH))
