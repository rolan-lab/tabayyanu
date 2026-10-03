"""Inspect terminologyenc.com (Islamic terminology encyclopedia).

The site publishes no API documentation (checked 2026-10-03). It is run by the
same Association as HadeethEnc, and /api/v1/languages answers, so this script
tries the HadeethEnc-style paths and prints exactly what each one returns.
These endpoints are UNDOCUMENTED. Prints only; writes nothing.
"""
import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://terminologyenc.com/api/v1"
# HadeethEnc paths (documented there), tried here by analogy.
PATHS = [
    ("languages", {}),
    ("categories/roots/", {"language": "ar"}),
    ("categories/list/", {"language": "ar"}),
]


def get(path: str, params: dict):
    resp = requests.get(f"{BASE}/{path}", params=params, timeout=30)
    ctype = resp.headers.get("content-type", "")
    print(f"\nGET {resp.url} -> {resp.status_code} {ctype}")
    if resp.status_code != 200 or "json" not in ctype:
        print("  (not JSON / not 200)", resp.text[:200].replace("\n", " "))
        return None
    return resp.json()


def show(obj, limit=1200):
    text = json.dumps(obj, ensure_ascii=False, indent=1)
    print(text[:limit] + (" ...[truncated]" if len(text) > limit else ""))


def main() -> None:
    results = {path: get(path, params) for path, params in PATHS}
    for path, body in results.items():
        if body is not None:
            print(f"\n== {path}: {type(body).__name__}, length {len(body)}")
            show(body[:3] if isinstance(body, list) else body)

    roots = results.get("categories/roots/")
    if roots:
        first = roots[0]
        print("\nFields of a root category:", list(first.keys()))
        listing = get("terms/list/", {"language": "ar", "category_id": first["id"], "page": 1, "per_page": 3})
        if listing is None:
            listing = get("hadeeths/list/", {"language": "ar", "category_id": first["id"], "page": 1, "per_page": 3})
        if listing is not None:
            show(listing)
            items = listing.get("data", []) if isinstance(listing, dict) else listing
            if items:
                one = get("terms/one/", {"language": "ar", "id": items[0]["id"]})
                if one is not None:
                    print("Fields of one term:", list(one.keys()))
                    show(one, limit=2500)


if __name__ == "__main__":
    main()
