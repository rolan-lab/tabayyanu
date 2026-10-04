"""Download source data into data/raw/ and build data/db/tabayyanu.sqlite.

Sources (see SOURCES.md):
  - Quran: KFGQPC Hafs package, kfgqpc_hafs_v30.zip (SHA-256 checked).
  - Hadith: HadeethEnc API v1, Arabic records whose reference cites
    Sahih al-Bukhari or Sahih Muslim.

Raw downloads are cached; delete data/raw/<source>/ to re-download.
The database is rebuilt from the raw files on every run.
Text, grades and references are stored exactly as the sources give them.
text_norm holds app.normalize.strict() of the plain-spelling text (matching only;
the raw text is what users see). The KFGQPC Uthmani font is extracted to
app/static/fonts/ (gitignored) for displaying Quran text.
"""
import hashlib
import io
import json
import re
import sqlite3
import sys
import time
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.normalize import folded, strict  # noqa: E402
import yaml  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "db" / "tabayyanu.sqlite"

QURAN_URL = "https://download.qurancomplex.gov.sa/resources_dev/kfgqpc_hafs_v30.zip"
QURAN_SHA256 = "227E6B1564D980F2BD09C2C35EBFB0330AC268C79A7C247CD1AB665BC635F245"
QURAN_ZIP = RAW / "qurancomplex" / "kfgqpc_hafs_v30.zip"
# The same official file, bundled in the repo for hosts that cannot reach the Complex's
# server (it timed out from Render, Frankfurt, 2026-10-04). Accepted only if its SHA-256
# equals the value published by the Complex. See data/vendor/README.md.
QURAN_ZIP_BUNDLED = ROOT / "data" / "vendor" / "kfgqpc_hafs_v30.zip"
QURAN_JSON_IN_ZIP = "kfgqpc_hafs_v30-data/kfgqpc_hafs_v30.json"
QURAN_FONT_IN_ZIP = "kfgqpc_hafs_v30-font/kfgqpc_hafs_v30.ttf"
FONT_DEST = ROOT / "app" / "static" / "fonts" / "kfgqpc_hafs_v30.ttf"

HEC_API = "https://hadeethenc.com/api/v1"
HEC_DIR = RAW / "hadeethenc"
HEC_ROOTS = HEC_DIR / "categories_roots_ar.json"
HEC_RECORDS = HEC_DIR / "hadeeths_ar.jsonl"
HEC_PAGE_URL = "https://hadeethenc.com/ar/browse/hadith/{id}"
HEC_LICENSE = "HadeethEnc.com: use without modification, addition or deletion; attribute HadeethEnc.com"
HEC_DELAY_S = 0.3  # pause between API calls, to be polite to the server

# HadeethEnc references come in three real formats (see scripts/inspect_hadeethenc.py output):
#   one source per line:      "صحيح مسلم (1/ 65) (38)."
#   one line, '،'-separated:   "صحيح البخاري (3/ 34) (1948)، صحيح مسلم (2/ 785) (1113)، ..."
#   bibliography, no number:  "- صحيح مسلم، للإمام مسلم بن الحجاج، تحقيق ..."
# So each line is split into segments on '،' ',' '؛' outside parentheses, and a segment
# counts only if it starts with the collection name ("فتح الباري شرح صحيح البخاري" does not).
COLLECTION_PREFIXES = {"bukhari": "صحيح البخاري", "muslim": "صحيح مسلم"}
SEGMENT_SEPARATORS = "،,؛"
LIST_MARKER = re.compile(r"^[\s\-–—\d.]*")  # leading "- " or "1- " list markers
# The hadith number: a parenthesized group of digits (no "/", which marks volume/page).
NUMBER_GROUP = re.compile(r"\(([\d٠-٩][\d٠-٩\s،,\-–]*)\)")

SCHEMA = """
CREATE TABLE quran_ayat (
    id INTEGER PRIMARY KEY,          -- 'id' from the KFGQPC file (1..6236)
    surah INTEGER NOT NULL,          -- sura_no
    surah_name_ar TEXT,              -- sura_name_ar, exactly as given
    ayah INTEGER NOT NULL,           -- aya_no
    text_raw TEXT NOT NULL,          -- aya_text_unicode, exactly as given
    text_emlaey TEXT,                -- aya_text_emlaey, exactly as given (plain spelling for search)
    text_norm TEXT NOT NULL          -- strict() of text_emlaey, for matching only
);
CREATE TABLE hadith (
    id TEXT PRIMARY KEY,             -- 'hadeethenc:<record id>:<collection>'
    collection TEXT NOT NULL,        -- 'bukhari' | 'muslim'
    book TEXT,                       -- kitab name; NULL when the source does not give it
    number TEXT,                     -- hadith number(s) as written in the source reference
    text_raw TEXT NOT NULL,          -- matn exactly as given by the source
    grade TEXT,                      -- grade exactly as given by the source
    grade_source TEXT,               -- who gives the grade
    source_url TEXT NOT NULL,
    license_note TEXT NOT NULL,
    source_record_id TEXT NOT NULL,  -- id of the record at the source
    attribution TEXT,                -- e.g. 'متفق عليه', exactly as given
    ref_raw TEXT,                    -- the reference segment the number was taken from, as given
    text_norm TEXT NOT NULL          -- strict() of text_raw, for matching only
);
-- Full-text index over unique HadeethEnc records (folded text), ranked with bm25().
CREATE VIRTUAL TABLE hadith_fts USING fts5(source_record_id UNINDEXED, text);
"""


def fetch_quran_zip() -> bytes:
    if not QURAN_ZIP.exists():
        try:
            print(f"GET {QURAN_URL}")
            resp = requests.get(QURAN_URL, timeout=(15, 120))
            resp.raise_for_status()
            content = resp.content
        except requests.RequestException as exc:
            if not QURAN_ZIP_BUNDLED.exists():
                raise
            print(f"  official server not reachable ({type(exc).__name__}); using the bundled official file")
            content = QURAN_ZIP_BUNDLED.read_bytes()
        QURAN_ZIP.parent.mkdir(parents=True, exist_ok=True)
        QURAN_ZIP.write_bytes(content)
    data = QURAN_ZIP.read_bytes()
    sha = hashlib.sha256(data).hexdigest().upper()
    if sha != QURAN_SHA256:
        sys.exit(f"Quran zip SHA-256 mismatch: got {sha}, expected {QURAN_SHA256}. Stopping.")
    print(f"Quran zip OK ({len(data):,} bytes, SHA-256 matches the published value)")
    return data


def hec_get(path: str, **params):
    time.sleep(HEC_DELAY_S)
    resp = requests.get(f"{HEC_API}/{path}", params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_hadeethenc() -> None:
    """Download every Arabic HadeethEnc record once into a JSONL file."""
    if HEC_RECORDS.exists():
        print(f"Using cached {HEC_RECORDS}")
        return
    HEC_DIR.mkdir(parents=True, exist_ok=True)
    roots = hec_get("categories/roots/", language="ar")
    HEC_ROOTS.write_text(json.dumps(roots, ensure_ascii=False, indent=1), encoding="utf-8")

    ids: list[str] = []
    seen: set[str] = set()
    for cat in roots:
        page = 1
        while True:
            listing = hec_get("hadeeths/list/", language="ar", category_id=cat["id"], page=page, per_page=500)
            for item in listing["data"]:
                if item["id"] not in seen:
                    seen.add(item["id"])
                    ids.append(item["id"])
            if page >= int(listing["meta"]["last_page"]):
                break
            page += 1
        print(f"  root category {cat['id']} ({cat['title']}): listed, {len(ids)} unique ids so far")

    tmp = HEC_RECORDS.with_suffix(".partial")
    with tmp.open("w", encoding="utf-8") as out:
        for start in range(0, len(ids), 50):
            batch = ids[start:start + 50]
            records = hec_get("hadeeths/multiple/", language="ar", ids=",".join(batch))
            for rec in records:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"  fetched details {min(start + 50, len(ids))}/{len(ids)}")
    tmp.rename(HEC_RECORDS)


def split_segments(line: str) -> list[str]:
    """Split a reference line on separators that are not inside parentheses."""
    segments, current, depth = [], [], 0
    for ch in line:
        depth += (ch == "(") - (ch == ")")
        if ch in SEGMENT_SEPARATORS and depth == 0:
            segments.append("".join(current))
            current = []
        else:
            current.append(ch)
    segments.append("".join(current))
    return [LIST_MARKER.sub("", s).strip() for s in segments if s.strip()]


def sahih_citations(reference: str) -> list[tuple[str, str | None, str]]:
    """Return (collection, number or None, segment) for each Sahih citation segment.

    The number is taken only from the segment that names the collection; it is
    never borrowed from a neighbouring segment.
    """
    found = []
    for line in (reference or "").splitlines():
        for segment in split_segments(line):
            for collection, prefix in COLLECTION_PREFIXES.items():
                if segment.startswith(prefix):
                    groups = NUMBER_GROUP.findall(segment)
                    number = groups[-1].strip() if groups else None
                    found.append((collection, number, segment))
    return found


def build_db(quran_zip: bytes) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)

    archive = zipfile.ZipFile(io.BytesIO(quran_zip))
    FONT_DEST.parent.mkdir(parents=True, exist_ok=True)
    FONT_DEST.write_bytes(archive.read(QURAN_FONT_IN_ZIP))
    ayat = json.loads(archive.read(QURAN_JSON_IN_ZIP).decode("utf-8"))
    con.executemany(
        "INSERT INTO quran_ayat (id, surah, surah_name_ar, ayah, text_raw, text_emlaey, text_norm)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(a["id"], a["sura_no"], a["sura_name_ar"], a["aya_no"], a["aya_text_unicode"],
          a["aya_text_emlaey"], strict(a["aya_text_emlaey"])) for a in ayat],
    )
    print(f"quran_ayat: inserted {len(ayat)} rows")

    rows = []
    records = [json.loads(line) for line in HEC_RECORDS.read_text(encoding="utf-8").splitlines() if line]
    for rec in records:
        # Citations with a number first, so a numbered citation wins over a bare bibliography entry.
        citations = sorted(sahih_citations(rec.get("reference", "")), key=lambda c: c[1] is None)
        for collection, number, line in citations:
            rows.append((
                f"hadeethenc:{rec['id']}:{collection}", collection, None, number,
                rec["hadeeth"], rec.get("grade"), "HadeethEnc.com",
                HEC_PAGE_URL.format(id=rec["id"]), HEC_LICENSE,
                rec["id"], rec.get("attribution"), line, strict(rec["hadeeth"]),
            ))
    # A record citing the same collection twice would collide on id; keep the first
    # (numbered citations sort first) and report the rest.
    unique, dupes = {}, []
    for row in rows:
        if row[0] in unique:
            dupes.append(row)
        else:
            unique[row[0]] = row
    con.executemany(f"INSERT INTO hadith VALUES ({', '.join('?' * 13)})", unique.values())
    flags = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))["normalize"]
    texts = {row[9]: row[4] for row in unique.values()}  # source_record_id -> text_raw
    con.executemany("INSERT INTO hadith_fts (source_record_id, text) VALUES (?, ?)",
                    [(rid, folded(text, **flags)) for rid, text in texts.items()])
    print(f"hadith_fts: indexed {len(texts)} unique records")
    print(f"hadith: {len(records)} HadeethEnc records read, {len(unique)} Sahih citation rows inserted")
    if dupes:
        print(f"  NOTE: {len(dupes)} extra citations of an already-cited collection in the same record"
              f" were not inserted (first 10 shown):")
        for row in dupes[:10]:
            print(f"    {row[0]} kept number {unique[row[0]][3]!r}; skipped: {row[11]}")
    con.commit()
    con.close()
    print(f"Built {DB_PATH}")


def main() -> None:
    quran_zip = fetch_quran_zip()
    fetch_hadeethenc()
    build_db(quran_zip)


if __name__ == "__main__":
    main()
