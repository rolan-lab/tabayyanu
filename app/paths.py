"""Learning paths: loading, validation and reference resolution.

Paths are team-written content in content/paths.json (see docs/PATHS_FORMAT.md).
Quran and hadith appear in lessons only as references; their text is always
read from the database here, never from the content file.
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATHS_FILE = ROOT / "content" / "paths.json"
AUDIENCES = {"muslims", "non_muslims", "both"}
BLOCK_FIELDS = {
    "text": {"body"},
    "quran": {"surah", "ayah_from", "ayah_to"},
    "hadith": {"record_id"},
    "question": {"prompt", "options", "answer"},
    "check": {"body"},
}


def load(path: Path = PATHS_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict, db_path: str, verifier=None) -> list[str]:
    """Return a list of problems (empty = valid). With a verifier, text blocks are
    checked for typed Quran or hadith text, which must be a reference block instead."""
    problems = []
    con = sqlite3.connect(db_path)
    ayat = {(s, a) for s, a in con.execute("SELECT surah, ayah FROM quran_ayat")}
    records = {r for (r,) in con.execute("SELECT DISTINCT source_record_id FROM hadith")}
    con.close()
    seen = set()
    for p in data.get("paths", []):
        where = f"path {p.get('id')!r}"
        for key in ("id", "title", "status", "modules"):
            if key not in p:
                problems.append(f"{where}: missing '{key}'")
        if p.get("status") not in ("draft", "published"):
            problems.append(f"{where}: status must be 'draft' or 'published'")
        if p.get("audience", "both") not in AUDIENCES:
            problems.append(f"{where}: audience must be one of {sorted(AUDIENCES)}")
        if p.get("id") in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(p.get("id"))
        for m in p.get("modules", []):
            for lesson in m.get("lessons", []):
                lw = f"{where} / {m.get('id')} / {lesson.get('id')}"
                for i, b in enumerate(lesson.get("blocks", [])):
                    bw = f"{lw} block {i}"
                    kind = b.get("type")
                    if kind not in BLOCK_FIELDS:
                        problems.append(f"{bw}: unknown type {kind!r}")
                        continue
                    missing = BLOCK_FIELDS[kind] - set(b)
                    if missing:
                        problems.append(f"{bw}: missing {sorted(missing)}")
                        continue
                    if kind == "quran":
                        for a in range(b["ayah_from"], b["ayah_to"] + 1):
                            if (b["surah"], a) not in ayat:
                                problems.append(f"{bw}: ayah {b['surah']}:{a} does not exist")
                    if kind == "hadith" and str(b["record_id"]) not in records:
                        problems.append(f"{bw}: hadith record {b['record_id']} is not in the index")
                    if kind == "question" and not (0 <= b["answer"] < len(b["options"])):
                        problems.append(f"{bw}: answer index out of range")
                    if kind in ("text", "question") and verifier is not None:
                        body = b.get("body") or b.get("prompt")
                        for item in verifier.verify(body)["items"]:
                            if item.get("status") in ("exact", "lexical_diff"):
                                problems.append(f"{bw}: contains typed {item['source']['type']} text "
                                                f"({item['source']['ref']}); use a reference block")
    return problems


def resolve(data: dict, db_path: str, verifier, include_drafts: bool = False) -> list[dict]:
    """Paths for the site, with Quran/hadith reference blocks filled from the database."""
    con = sqlite3.connect(db_path)
    out = []
    for p in data.get("paths", []):
        if p.get("status") != "published" and not include_drafts:
            continue
        p = json.loads(json.dumps(p))  # copy
        for m in p.get("modules", []):
            for lesson in m.get("lessons", []):
                for b in lesson.get("blocks", []):
                    if b.get("type") == "quran":
                        rows = con.execute(
                            "SELECT surah_name_ar, text_raw FROM quran_ayat WHERE surah = ? AND ayah BETWEEN ? AND ?"
                            " ORDER BY ayah", (b["surah"], b["ayah_from"], b["ayah_to"])).fetchall()
                        b["text"] = " ".join(r[1] for r in rows)
                        b["surah_name"] = rows[0][0] if rows else None
                    elif b.get("type") == "hadith":
                        rec = verifier.hadith.records.get(str(b["record_id"]))
                        if rec:
                            b.update({"text": rec["text"], "grade": rec["grade"], "grade_source": "HadeethEnc.com",
                                      "attribution": rec["attribution"], "url": rec["url"],
                                      "citations": rec["citations"]})
        out.append(p)
    con.close()
    return out
