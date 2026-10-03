"""Inspect the King Fahd Complex Hafs package (qurancomplex.gov.sa/quran-dev).

Downloads the zip into data/raw/qurancomplex/, checks the SHA-256 published on
the platform page, lists the archive, and prints the real structure of the
JSON file: field names, numbering, and the characters used in the text.
Prints only; writes nothing except the downloaded zip.
"""
import hashlib
import io
import json
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

URL = "https://download.qurancomplex.gov.sa/resources_dev/kfgqpc_hafs_v30.zip"
# Copied from the package's "تعريف" tab on https://qurancomplex.gov.sa/quran-dev/ (3 Oct 2026).
PUBLISHED_SHA256 = "227E6B1564D980F2BD09C2C35EBFB0330AC268C79A7C247CD1AB665BC635F245"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "qurancomplex"


def download(url: str, dest: Path) -> bytes:
    if dest.exists():
        print(f"Using cached {dest}")
        return dest.read_bytes()
    print(f"GET {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return resp.content


def describe_chars(text: str) -> None:
    """Print every non-letter code point (marks, symbols) with its Unicode name."""
    counts = Counter(ch for ch in text if unicodedata.category(ch) != "Lo")
    for ch, n in counts.most_common():
        name = unicodedata.name(ch, "?")
        print(f"    U+{ord(ch):04X} {unicodedata.category(ch)} x{n:<7} {name}")


def main() -> None:
    data = download(URL, RAW_DIR / "kfgqpc_hafs_v30.zip")
    sha = hashlib.sha256(data).hexdigest().upper()
    print(f"Size: {len(data):,} bytes")
    print(f"SHA-256 computed : {sha}")
    print(f"SHA-256 published: {PUBLISHED_SHA256}")
    print(f"Match: {sha == PUBLISHED_SHA256}")

    zf = zipfile.ZipFile(io.BytesIO(data))
    print("\nArchive contents:")
    for info in zf.infolist():
        print(f"  {info.file_size:>12,}  {info.filename}")

    json_names = [n for n in zf.namelist() if n.lower().endswith(".json")]
    if not json_names:
        print("\nNo JSON file in archive. Stop and inspect manually.")
        return
    name = json_names[0]
    raw = zf.read(name)
    print(f"\nInspecting {name}")
    print(f"  Starts with UTF-8 BOM: {raw.startswith(b'\xef\xbb\xbf')}")
    records = json.loads(raw.decode("utf-8-sig"))
    print(f"  Top-level type: {type(records).__name__}, length: {len(records)}")

    first = records[0]
    print("  Fields of first record (name: python type):")
    for key, value in first.items():
        print(f"    {key}: {type(value).__name__}")

    print("\n  First 2 records, raw:")
    for rec in records[:2]:
        print("   ", json.dumps(rec, ensure_ascii=False))
    print("\n  Last record, raw:")
    print("   ", json.dumps(records[-1], ensure_ascii=False))

    sura_key = "sura_no" if "sura_no" in first else None
    if sura_key:
        suras = {r[sura_key] for r in records}
        print(f"\n  Distinct sura_no: {len(suras)} (min {min(suras)}, max {max(suras)})")

    for field in ("aya_text", "aya_text_unicode", "aya_text_emlaey"):
        if field in first:
            joined = "".join(r[field] for r in records)
            print(f"\n  Non-letter code points in '{field}' (whole file):")
            describe_chars(joined)


if __name__ == "__main__":
    main()
