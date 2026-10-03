"""Inspect icadb.com, the Association's Central DB (organizers' reference file, page 10).

Its OpenAPI schema (https://icadb.com/api/docs/?format=openapi) describes a
"Public read-only API". This script prints the endpoint list, the encyclopedias
with their card counts, and the fields of the hadith encyclopedia, to answer one
question: does icadb hold more Sahih hadith than HadeethEnc? Prints only.
Not used at runtime (CLAUDE.md, Part 3).
"""
import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://icadb.com"


def get(path: str, **params):
    resp = requests.get(f"{BASE}{path}", params=params, timeout=30)
    print(f"\nGET {resp.url} -> {resp.status_code} {resp.headers.get('content-type')}")
    resp.raise_for_status()
    return resp.json()


def show(obj, limit=1500):
    text = json.dumps(obj, ensure_ascii=False, indent=1)
    print(text[:limit] + (" ...[truncated]" if len(text) > limit else ""))


def main() -> None:
    schema = get("/api/docs/", format="openapi")
    print("Title:", schema["info"]["title"], "| Description:", schema["info"].get("description"))
    print("Declared security:", schema.get("securityDefinitions"), schema.get("security"))
    print("Paths:", len(schema["paths"]))

    encyclopedias = get("/api/encyclopedias/list/")
    for enc in encyclopedias:
        print(f"  id {enc['id']:>3}  cards {enc['cards_count']:>5}  {enc['name']}")

    # Path parameter {encyclopedia_id} takes the external_id (the internal id returns 404).
    for enc in (e for e in encyclopedias if "الأحاديث" in e["name"] or "صحيح" in e["name"]):
        print(f"\n== {enc['name']} (external_id {enc['external_id']}, {enc['cards_count']} cards)")
        if not enc["cards_count"]:
            continue
        fields = get(f"/api/encyclopedias/{enc['external_id']}/fields/")
        show(fields)
        cards = get(f"/api/encyclopedias/{enc['external_id']}/cards/latest/", page=1, page_size=1)
        print("First card (latest version):")
        show(cards, limit=2500)


if __name__ == "__main__":
    main()
