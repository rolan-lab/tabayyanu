"""Check content/paths.json: structure, references, and no typed Quran/hadith text.

Usage: python scripts/validate_paths.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import paths  # noqa: E402
from app.verify import Verifier  # noqa: E402

DB = str(ROOT / "data" / "db" / "tabayyanu.sqlite")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    data = paths.load()
    problems = paths.validate(data, DB, Verifier(DB))
    n = len(data.get("paths", []))
    if problems:
        print(f"{len(problems)} problem(s) in {n} path(s):")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print(f"OK: {n} path(s), no problems.")
