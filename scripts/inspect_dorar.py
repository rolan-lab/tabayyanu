"""Inspect the Dorar al-Sunniyya hadith JSON search (dorar.net/article/389).

Calls the documented endpoint with a few real phrases and prints the raw
structure, to see whether results carry book, number, text and grade for
Bukhari and Muslim. Prints only; writes nothing.
"""
import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

URL = "https://dorar.net/dorar_api.json"
PHRASES = ["إنما الأعمال بالنيات", "خيركم من تعلم القرآن وعلمه"]


def main() -> None:
    for phrase in PHRASES:
        resp = requests.get(URL, params={"skey": phrase}, timeout=30)
        print(f"\nGET {resp.url}  -> {resp.status_code} {resp.headers.get('content-type')}")
        resp.raise_for_status()
        body = resp.json()
        print("Top-level keys:", list(body.keys()) if isinstance(body, dict) else type(body).__name__)
        ahadith = body.get("ahadith") if isinstance(body, dict) else None
        print("Type of 'ahadith':", type(ahadith).__name__)
        if isinstance(ahadith, dict):
            print("Keys of 'ahadith':", list(ahadith.keys()))
        text = json.dumps(body, ensure_ascii=False, indent=1)
        print(text[:3500] + (" ...[truncated]" if len(text) > 3500 else ""))
        print(f"Total response length: {len(text)} chars")


if __name__ == "__main__":
    main()
