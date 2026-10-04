"""Evaluation harness: runs tests/cases.jsonl and prints the markdown table for the deck.

Usage:
    python tests/run_eval.py                 # test split, 3 runs per case
    python tests/run_eval.py --split dev     # tune thresholds and prompts on dev only
    python tests/run_eval.py --split all --runs 1 --out docs/results.md

Cases whose input is still "TODO_HUMAN" are skipped and counted.

Critical errors (target zero):
  altered_exact   an altered text (expected lexical_diff / not_found) called exact at the expected place
  bad_reference   a returned reference that does not exist in the database
  ruling          a ruling given instead of a referral (ruling words in a generated explanation)
  called_false    a text called false / fabricated
"""
import argparse
import json
import sqlite3
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.verify import STRINGS, Verifier  # noqa: E402

DB = ROOT / "data" / "db" / "tabayyanu.sqlite"
CASES = ROOT / "tests" / "cases.jsonl"
FALSE_WORDS = ("باطل", "موضوع", "مكذوب", "مزيف", "مختلق", "لا أصل له")
RULING_WORDS = ("يجوز لك", "لا يجوز", "حرام عليك", "حلال لك", "يجب عليك", "فتواي")


def outcome(result: dict) -> list[str]:
    """What the system said, as comparable labels (one per item)."""
    if result.get("notice") == "empty_input":
        return ["empty"]
    labels = []
    for item in result["items"]:
        labels.append(item["kind"] if item["kind"] != "quote" else item["status"])
    return labels


def refs_of(result: dict) -> list[str]:
    out = []
    for item in result["items"]:
        src = item.get("source") or {}
        if src.get("type") == "quran":
            out.append(f"quran:{src['surah']}:{src['ayah_from']}-{src['ayah_to']}")
        elif src.get("type") == "hadith":
            out.append(f"hadith:{src['record_id']}")
    return out


class Checker:
    def __init__(self, verifier: Verifier):
        self.v = verifier
        con = sqlite3.connect(DB)
        self.ayat = {(s, a) for s, a in con.execute("SELECT surah, ayah FROM quran_ayat")}
        con.close()

    def ref_hits(self, expected: str, item: dict) -> bool:
        """Does the item point to the expected place (or an identical passage)?"""
        src = item.get("source") or {}
        kind, _, rest = expected.partition(":")
        if kind == "quran" and src.get("type") == "quran":
            s, _, span = rest.partition(":")
            a, _, b = span.partition("-")
            s, a, b = int(s), int(a), int(b or a)
            places = [(src["surah"], src["ayah_from"], src["ayah_to"])] + [tuple(x) for x in item.get("also_in", [])]
            return any(ps == s and pa <= a and pb >= b for ps, pa, pb in places)
        if kind == "hadith" and src.get("type") == "hadith":
            recs = self.v.hadith.records
            return src["record_id"] == rest or recs[src["record_id"]]["text"] == recs.get(rest, {}).get("text")
        return False

    def ref_exists(self, item: dict) -> bool:
        src = item.get("source") or {}
        if src.get("type") == "quran":
            return all((src["surah"], a) in self.ayat for a in range(src["ayah_from"], src["ayah_to"] + 1))
        if src.get("type") == "hadith":
            return src["record_id"] in self.v.hadith.records
        return True

    def score(self, case: dict, result: dict) -> tuple[bool, list[str]]:
        got = outcome(result)
        quotes = [i for i in result["items"] if i["kind"] == "quote"]
        expected = case["expected_status"].split(",")
        exp_refs = (case["expected_ref"] or "").split(",") if case["expected_ref"] else []
        critical = []

        for item in result["items"]:
            if not self.ref_exists(item):
                critical.append("bad_reference")
            text = " ".join(filter(None, [item.get("explanation"), item.get("note")]))
            text = text.replace(STRINGS["not_found_note"], "")  # mandated note: "does NOT mean the text is false"
            if any(w in text for w in FALSE_WORDS):
                critical.append("called_false")
            if item.get("explanation_origin") == "llm" and any(w in text for w in RULING_WORDS):
                critical.append("ruling")
        if case["category"] in ("altered_ayah",) or "lexical_diff" in expected:
            for exp_status, exp_ref in zip(expected, exp_refs):
                if exp_status != "exact" and any(q["status"] == "exact" and self.ref_hits(exp_ref, q) for q in quotes):
                    critical.append("altered_exact")

        if len(expected) > 1:  # several quotations: each expected one must be found with its status
            ok = all(any(q["status"] == st and self.ref_hits(rf, q) for q in quotes)
                     for st, rf in zip(expected, exp_refs))
        elif expected[0] in ("empty", "referral", "out_of_scope"):
            ok = expected[0] in got
        elif expected[0] == "not_found":
            ok = got == ["not_found"]
        else:
            ok = bool(quotes) and quotes[0]["status"] == expected[0] and \
                (not exp_refs or self.ref_hits(exp_refs[0], quotes[0]))
        return ok, sorted(set(critical))


def run(split: str, runs: int):
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = [c for c in cases if split == "all" or c["split"] == split]
    pending = [c for c in selected if c["input"] == "TODO_HUMAN"]
    runnable = [c for c in selected if c["input"] != "TODO_HUMAN"]

    started = time.monotonic()
    verifier = Verifier(str(DB))
    load_s = time.monotonic() - started
    checker = Checker(verifier)

    per_case = []
    latencies = []
    for case in runnable:
        oks, crits, outs = [], set(), []
        for _ in range(runs):
            t = time.monotonic()
            result = verifier.verify(case["input"])
            latencies.append((time.monotonic() - t) * 1000)
            ok, crit = checker.score(case, result)
            oks.append(ok)
            crits.update(crit)
            outs.append(json.dumps([outcome(result), refs_of(result)], ensure_ascii=False))
        per_case.append({"case": case, "ok": all(oks), "critical": sorted(crits),
                         "consistent": len(set(outs)) == 1, "last": outs[-1]})
    return selected, pending, per_case, latencies, load_s


def table(split, runs, selected, pending, per_case, latencies, load_s) -> str:
    cats = defaultdict(lambda: {"n": 0, "ok": 0, "crit": 0, "pending": 0, "consistent": 0})
    for c in pending:
        cats[c["category"]]["pending"] += 1
    for r in per_case:
        k = cats[r["case"]["category"]]
        k["n"] += 1
        k["ok"] += r["ok"]
        k["crit"] += bool(r["critical"])
        k["consistent"] += r["consistent"]
    lines = [f"### Evaluation — split: {split}, {runs} run(s) per case", "",
             "| Category | Cases run | Correct | Accuracy | Critical errors | Consistent | Pending (TODO_HUMAN) |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    order = ["genuine_ayah", "altered_ayah", "ayah_spelling", "hadith_verbatim", "hadith_wording",
             "viral_not_indexed", "personal_fatwa", "disputed", "long_post", "edge_input"]
    tot = {"n": 0, "ok": 0, "crit": 0, "consistent": 0, "pending": 0}
    for name in order + sorted(set(cats) - set(order)):
        if name not in cats:
            continue
        k = cats[name]
        acc = f"{100 * k['ok'] / k['n']:.0f}%" if k["n"] else "—"
        lines.append(f"| {name} | {k['n']} | {k['ok']} | {acc} | {k['crit']} | {k['consistent']}/{k['n']} | {k['pending']} |")
        for key in tot:
            tot[key] += k[key]
    acc = f"{100 * tot['ok'] / tot['n']:.0f}%" if tot["n"] else "—"
    lines.append(f"| **Total** | **{tot['n']}** | **{tot['ok']}** | **{acc}** | **{tot['crit']}** | "
                 f"**{tot['consistent']}/{tot['n']}** | **{tot['pending']}** |")
    if latencies:
        p95 = sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]
        lines += ["", f"Latency per request: median {statistics.median(latencies):.0f} ms, p95 {p95:.0f} ms "
                      f"(index load {load_s:.1f} s, once at startup). LLM tokens: 0 (explanations are templates)."]
    failures = [r for r in per_case if not r["ok"] or r["critical"]]
    if failures:
        lines += ["", "Failures and critical errors:", ""]
        for r in failures:
            c = r["case"]
            lines.append(f"- `{c['id']}` {c['category']}: expected `{c['expected_status']}` "
                         f"`{c['expected_ref']}`, got `{r['last']}`"
                         + (f" — CRITICAL: {', '.join(r['critical'])}" if r["critical"] else ""))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", help="also write the table to this file")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    md = table(args.split, args.runs, *run(args.split, args.runs))
    print(md)
    if args.out:
        Path(args.out).write_text(md + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
