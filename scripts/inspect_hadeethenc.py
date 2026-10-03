"""Inspect the HadeethEnc API (hadeethenc.com/api-docs).

Fetches a few real responses and prints their structure so we can see
whether it gives Bukhari / Muslim with book, number, text and grade.
Prints only; writes nothing.
"""
import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://hadeethenc.com/api/v1"


def get(path: str, **params):
    resp = requests.get(f"{BASE}/{path}", params=params, timeout=30)
    print(f"\nGET {resp.url}  -> {resp.status_code} {resp.headers.get('content-type')}")
    resp.raise_for_status()
    return resp.json()


def show(obj, limit=1500):
    text = json.dumps(obj, ensure_ascii=False, indent=1)
    print(text[:limit] + (" ...[truncated]" if len(text) > limit else ""))


def main() -> None:
    roots = get("categories/roots/", language="ar")
    print(f"Root categories: {len(roots)}")
    show(roots[:3])

    cats = get("categories/list/", language="ar")
    print(f"All categories: {len(cats)}")
    total = sum(int(c.get("hadeeths_count") or 0) for c in roots)
    print(f"Sum of hadeeths_count over root categories: {total}")

    listing = get("hadeeths/list/", language="ar", category_id=roots[0]["id"], page=1, per_page=3)
    show(listing)

    one = get("hadeeths/one/", language="ar", id=2962)
    print("Fields of hadeeths/one:", list(one.keys()))
    show(one, limit=4000)

    search = get("hadeeths/search/", language="ar", phrase="إنما الأعمال بالنيات")
    show(search, limit=2000)

    # Several real records: what do 'attribution', 'grade' and 'reference' look like?
    sample_ids = [h["id"] for h in listing.get("data", [])]
    for hid in sample_ids:
        rec = get("hadeeths/one/", language="ar", id=hid)
        print("  attribution:", rec.get("attribution"))
        print("  grade      :", rec.get("grade"))
        print("  reference  :", rec.get("reference"))


if __name__ == "__main__":
    main()
