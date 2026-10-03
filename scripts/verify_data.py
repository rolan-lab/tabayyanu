"""Check data/db/tabayyanu.sqlite against expectations and report every anomaly.

Reports only. Nothing is changed or "fixed".
Usage: python scripts/verify_data.py [--seed N]
"""
import argparse
import json
import random
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "db" / "tabayyanu.sqlite"
HEC_ROOTS = ROOT / "data" / "raw" / "hadeethenc" / "categories_roots_ar.json"
HEC_RECORDS = ROOT / "data" / "raw" / "hadeethenc" / "hadeeths_ar.jsonl"

EXPECTED_AYAT = 6236   # Hafs count
EXPECTED_SURAHS = 114
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

anomalies: list[str] = []


def flag(msg: str) -> None:
    anomalies.append(msg)
    print(f"  ANOMALY: {msg}")


def check_quran(con: sqlite3.Connection, rng: random.Random) -> None:
    print("\n== Quran (quran_ayat) ==")
    n = con.execute("SELECT COUNT(*) FROM quran_ayat").fetchone()[0]
    print(f"  ayat: {n} (expected {EXPECTED_AYAT})")
    if n != EXPECTED_AYAT:
        flag(f"ayat count {n} != {EXPECTED_AYAT}")

    surahs = con.execute("SELECT COUNT(DISTINCT surah), MIN(surah), MAX(surah) FROM quran_ayat").fetchone()
    print(f"  surahs: {surahs[0]} (min {surahs[1]}, max {surahs[2]}, expected {EXPECTED_SURAHS})")
    if surahs[0] != EXPECTED_SURAHS:
        flag(f"surah count {surahs[0]} != {EXPECTED_SURAHS}")

    # Missing ayah numbers inside each surah (numbers should run 1..max with no gaps).
    gaps = 0
    for surah, in con.execute("SELECT DISTINCT surah FROM quran_ayat ORDER BY surah"):
        nums = [r[0] for r in con.execute("SELECT ayah FROM quran_ayat WHERE surah=? ORDER BY ayah", (surah,))]
        missing = sorted(set(range(1, max(nums) + 1)) - set(nums))
        if missing or nums[0] != 1:
            gaps += 1
            flag(f"surah {surah}: missing ayah numbers {missing}")
    print(f"  surahs with gaps in ayah numbering: {gaps}")

    dup_pairs = con.execute(
        "SELECT surah, ayah, COUNT(*) FROM quran_ayat GROUP BY surah, ayah HAVING COUNT(*) > 1").fetchall()
    print(f"  duplicate (surah, ayah) pairs: {len(dup_pairs)}")
    for d in dup_pairs:
        flag(f"duplicate surah:ayah {d[0]}:{d[1]} x{d[2]}")
    # id is the PRIMARY KEY, so SQLite already rejects duplicate ids; check order instead.
    out_of_order = con.execute("""
        SELECT COUNT(*) FROM quran_ayat a JOIN quran_ayat b ON b.id = a.id + 1
        WHERE (b.surah, b.ayah) <= (a.surah, a.ayah)""").fetchone()[0]
    print(f"  ids not in surah:ayah order: {out_of_order}")
    if out_of_order:
        flag(f"{out_of_order} consecutive ids out of surah:ayah order")

    for col in ("text_raw", "text_emlaey"):
        empty = con.execute(f"SELECT COUNT(*) FROM quran_ayat WHERE TRIM(COALESCE({col}, '')) = ''").fetchone()[0]
        print(f"  empty {col}: {empty}")
        if empty:
            flag(f"{empty} empty {col}")

    # text_raw ends with U+06DD END OF AYAH + the ayah number in Arabic-Indic digits.
    # Check that number matches the ayah column.
    mismatch = []
    for rid, surah, ayah, text in con.execute("SELECT id, surah, ayah, text_raw FROM quran_ayat"):
        m = re.search("۝([٠-٩]+)\\s*$", text)
        if not m or int(m.group(1).translate(ARABIC_DIGITS)) != ayah:
            mismatch.append(f"{surah}:{ayah}")
    print(f"  text_raw whose trailing ayah marker number != ayah column: {len(mismatch)}")
    if mismatch:
        flag(f"ayah marker mismatch at {mismatch[:20]}")

    # Unexpected invisible characters in the plain-spelling column.
    odd = Counter()
    where = {}
    for surah, ayah, text in con.execute("SELECT surah, ayah, text_emlaey FROM quran_ayat"):
        for ch in text:
            if unicodedata.category(ch) == "Cf":
                odd[ch] += 1
                where.setdefault(ch, []).append(f"{surah}:{ayah}")
    for ch, cnt in odd.items():
        flag(f"text_emlaey contains U+{ord(ch):04X} {unicodedata.name(ch, '?')} x{cnt} at {where[ch][:10]}")
    tatweel = con.execute("SELECT COUNT(*) FROM quran_ayat WHERE text_emlaey LIKE '%' || char(1600) || '%'").fetchone()[0]
    print(f"  text_emlaey rows containing tatweel (U+0640): {tatweel} (noted; Phase 1 normalization strips it)")

    ids = [r[0] for r in con.execute("SELECT id FROM quran_ayat")]
    print("\n  Random sample of 5 ayat (compare by eye with a printed Mushaf):")
    for rid in sorted(rng.sample(ids, 5)):
        surah, ayah, text = con.execute("SELECT surah, ayah, text_raw FROM quran_ayat WHERE id=?", (rid,)).fetchone()
        print(f"   [{surah}:{ayah}] {text}")


def check_hadith(con: sqlite3.Connection, rng: random.Random) -> None:
    print("\n== Hadith (hadith) ==")
    roots = json.loads(HEC_ROOTS.read_text(encoding="utf-8"))
    records = [json.loads(line) for line in HEC_RECORDS.read_text(encoding="utf-8").splitlines() if line]
    stated = sum(int(r["hadeeths_count"]) for r in roots)
    ids = [r["id"] for r in records]
    print(f"  HadeethEnc: sum of hadeeths_count over {len(roots)} root categories = {stated}")
    print(f"  HadeethEnc: unique record ids downloaded = {len(set(ids))} (difference = records filed under"
          f" more than one root category)")
    if len(ids) != len(set(ids)):
        flag(f"{len(ids) - len(set(ids))} duplicate record ids in raw HadeethEnc download")
    print("  HadeethEnc does not state a total for Sahih al-Bukhari or Sahih Muslim; it is a curated selection.")

    for coll in ("bukhari", "muslim"):
        rows, uniq, nonull, mn, mx = con.execute("""
            SELECT COUNT(*), COUNT(DISTINCT number), COUNT(number),
                   MIN(CAST(number AS INTEGER)), MAX(CAST(number AS INTEGER))
            FROM hadith WHERE collection=?""", (coll,)).fetchone()
        print(f"  {coll}: {rows} rows, {uniq} distinct numbers, {rows - nonull} without a number,"
              f" number range {mn}..{mx}")
        if rows - nonull:
            flag(f"{coll}: {rows - nonull} rows have no parsable number")
        dup_numbers = con.execute("""
            SELECT number, COUNT(*) FROM hadith WHERE collection=? AND number IS NOT NULL
            GROUP BY number HAVING COUNT(*) > 1""", (coll,)).fetchall()
        print(f"  {coll}: numbers cited by more than one HadeethEnc record: {len(dup_numbers)}"
              f" (expected; different records can quote the same hadith)")
        odd_numbers = [r[0] for r in con.execute(
            "SELECT number FROM hadith WHERE collection=? AND number IS NOT NULL", (coll,))
            if not r[0].translate(ARABIC_DIGITS).isdigit()]
        if odd_numbers:
            flag(f"{coll}: {len(odd_numbers)} numbers are not a single integer, e.g. {odd_numbers[:8]}")

    no_book = con.execute("SELECT COUNT(*) FROM hadith WHERE book IS NULL").fetchone()[0]
    print(f"  rows with book = NULL: {no_book} (HadeethEnc references give volume/page, not the kitab name)")
    empty = con.execute("SELECT COUNT(*) FROM hadith WHERE TRIM(COALESCE(text_raw, '')) = ''").fetchone()[0]
    print(f"  empty text_raw: {empty}")
    if empty:
        flag(f"{empty} hadith rows with empty text")
    html = con.execute("SELECT COUNT(*) FROM hadith WHERE text_raw LIKE '%<%>%'").fetchone()[0]
    if html:
        flag(f"{html} hadith texts contain HTML-like tags")

    print("  grade values (exactly as given):")
    for grade, cnt in con.execute("SELECT grade, COUNT(*) FROM hadith GROUP BY grade ORDER BY 2 DESC"):
        print(f"    {cnt:>5}  {grade!r}")

    # Does the attribution agree with which Sahihs the reference cites?
    cites = {}
    for rid, coll in con.execute("SELECT source_record_id, collection FROM hadith"):
        cites.setdefault(rid, set()).add(coll)
    by_id = {r["id"]: r for r in records}
    expect = {"متفق عليه": {"bukhari", "muslim"}, "رواه البخاري": {"bukhari"}, "رواه مسلم": {"muslim"}}
    disagree = Counter()
    examples = {}
    for rid, colls in cites.items():
        attr = (by_id[rid].get("attribution") or "").strip()
        if attr in expect and expect[attr] != colls:
            key = f"attribution {attr!r} but reference cites {sorted(colls)}"
            disagree[key] += 1
            examples.setdefault(key, rid)
    for key, cnt in disagree.items():
        flag(f"{cnt} records: {key} (e.g. HadeethEnc id {examples[key]})")

    # Records attributed to a Sahih whose reference has no line starting with the collection name.
    missed = Counter()
    missed_ex = {}
    for rec in records:
        attr = (rec.get("attribution") or "").strip()
        if rec["id"] not in cites and attr in expect:
            missed[attr] += 1
            missed_ex.setdefault(attr, rec["id"])
    for attr, cnt in missed.items():
        flag(f"{cnt} records attributed {attr!r} have no parsable Sahih reference line"
             f" (e.g. HadeethEnc id {missed_ex[attr]}); not ingested")

    # Parser spot-check: expected numbers read off raw references printed during inspection
    # (scripts/inspect_hadeethenc.py and verify output on 2026-10-03), not from memory.
    spot = {("2962", "bukhari"): "6864", ("2962", "muslim"): "1678",
            ("65506", "bukhari"): "1948", ("65506", "muslim"): "1113",
            ("66235", "bukhari"): "2518", ("66235", "muslim"): "84",
            ("5913", "bukhari"): "5027", ("5907", "muslim"): "791"}
    bad = []
    for (rid, coll), want in spot.items():
        got = con.execute("SELECT number FROM hadith WHERE source_record_id=? AND collection=?",
                          (rid, coll)).fetchone()
        if not got or got[0] != want:
            bad.append(f"{rid}/{coll}: want {want}, got {got[0] if got else None}")
    print(f"  parser spot-check: {len(spot) - len(bad)}/{len(spot)} correct")
    for b in bad:
        flag(f"parser spot-check failed: {b}")

    # Which text follows the collection name in accepted segments? (audit what counted as a citation)
    tails = Counter()
    for (ref,) in con.execute("SELECT ref_raw FROM hadith"):
        tail = ref.removeprefix("صحيح البخاري").removeprefix("صحيح مسلم").strip()
        tails[tail.split()[0][:12] if tail else "(nothing)"] += 1
    print("  first token after the collection name in accepted citations:")
    for tail, cnt in tails.most_common(15):
        print(f"    {cnt:>5}  {tail!r}")

    # Bare segments like "(1/ 191) (203)" following a Sahih citation: not assigned to any
    # collection by ingest (it would be a guess), so count them here.
    bare = 0
    bare_ex = None
    for rec in records:
        for line in (rec.get("reference") or "").splitlines():
            if re.search(r"(صحيح البخاري|صحيح مسلم)[^،]*\([\d\s]+\)\s*،\s*\(\d+/\s*\d+\)\s*\(\d+\)", line):
                bare += 1
                bare_ex = bare_ex or rec["id"]
    if bare:
        flag(f"{bare} reference lines have a bare '(vol/page) (number)' right after a Sahih citation;"
             f" that extra number is not ingested (e.g. HadeethEnc id {bare_ex})")

    print("  attribution values over all downloaded records (top 12):")
    for attr, cnt in Counter((r.get("attribution") or "").strip() for r in records).most_common(12):
        print(f"    {cnt:>5}  {attr!r}")

    hids = [r[0] for r in con.execute("SELECT id FROM hadith")]
    print("\n  Random sample of 5 hadith (compare by eye with a printed edition):")
    for hid in sorted(rng.sample(hids, 5)):
        coll, number, text, grade, url, ref = con.execute(
            "SELECT collection, number, text_raw, grade, source_url, ref_raw FROM hadith WHERE id=?",
            (hid,)).fetchone()
        print(f"   [{coll} {number}] grade={grade!r}  {url}")
        print(f"     ref: {ref}")
        print(f"     {text}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261003)
    args = parser.parse_args()
    if not DB_PATH.exists():
        sys.exit(f"{DB_PATH} not found. Run scripts/ingest.py first.")
    con = sqlite3.connect(DB_PATH)
    rng = random.Random(args.seed)
    print(f"Database: {DB_PATH}  (sample seed {args.seed})")
    check_quran(con, rng)
    check_hadith(con, rng)
    print(f"\n== Summary: {len(anomalies)} anomalies ==")
    for a in anomalies:
        print(f"  - {a}")


if __name__ == "__main__":
    main()
