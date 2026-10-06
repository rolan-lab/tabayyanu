"""Convert the team's lesson text files (content/source/) into content/paths.json.

Usage: python scripts/convert_paths.py

The team's wording is kept as written. The only changes:
  - Quran quotations  ﴿...﴾ [سورة: آية]  become `quran` reference blocks, so the site
    shows the official KFGQPC text. The typed text is checked with our verifier and every
    difference is reported.
  - Hadith quotations «...» followed by رواه / متفق عليه are checked against our index.
    Found: a `hadith` block (HadeethEnc text and grade). Not found: a `cited` block that
    keeps the team's text, labelled as not verified in our indexed sources.
A review report is written to docs/paths_conversion_report.md.

Structure: one path per folder (audience from the folder), one module per file, one lesson
per section (sections are separated by a line "⸻").
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.normalize import folded, strict  # noqa: E402
from app.verify import Verifier  # noqa: E402

SOURCE = ROOT / "content" / "source"
OUT = ROOT / "content" / "paths.json"
REPORT = ROOT / "docs" / "paths_conversion_report.md"
DB = ROOT / "data" / "db" / "tabayyanu.sqlite"

# Folder -> path settings. Titles are drafts for the team to confirm.
PATHS = [
    {"folder": "Muslims", "id": "muslim-basics", "title": "أساسيات الدين للمسلم", "audience": "muslims",
     "description": "الشهادتان والإيمان والطهارة والصلاة والسيرة النبوية وموضوعات تهم المسلم.",
     "order": ["الشهادتان في الإسلام", "الايمان", "طريقة الوضوء الصحيحة", "الصلاة في الإسلام",
               "لسيرة النبوية", "مواضيع تهم المسلمين"], "art": "mihrab",
     "module_art": {"الايمان": "star", "طريقة الوضوء الصحيحة": "water", "الصلاة في الإسلام": "mihrab",
                    "لسيرة النبوية": "dome"}},
    {"folder": "nonMuslums", "id": "discover-islam", "title": "تعرّف على الإسلام", "audience": "non_muslims",
     "description": "أسئلة يطرحها غير المسلمين عن الإسلام، ونظرة الإسلام إلى الإنسان والصحة النفسية.",
     "order": ["بعد المواضيع الجدليه تهم غير المسلمين", "الإسلام والصحة النفسية والعلاج النف"], "art": "book"},
    # These two files describe a planned Hajj/Umrah assistant rather than lessons: kept as a draft
    # (not shown on the site) until the team decides.
    {"folder": "Muslims", "id": "hajj-umrah-draft", "title": "الحج والعمرة (مسودة)", "audience": "muslims",
     "description": "مسودة: وصف لمساعد ذكي للحج والعمرة، بانتظار قرار الفريق.", "status": "draft",
     "order": ["الحج", "العمره"], "art": "kaaba", "module_art": {"الحج": "kaaba", "العمره": "kaaba"}},
]
SEPARATOR = "⸻"
VERSE = re.compile(r"﴿(.+?)﴾\s*\[\s*([^\]:\d]+?)\s*:\s*([\d٠-٩]+)\s*(?:[-–]\s*([\d٠-٩]+))?\s*\]\s*\.?", re.S)
HADITH = re.compile(r"«([^»]{12,}?)»\s*((?:رواه|أخرجه)\s[^.\n«]{2,60}|متفق عليه)\s*\.?")
ORDINAL = re.compile(r"^(?:أولًا|أولاً|ثانيًا|ثانياً|ثالثًا|ثالثاً|رابعًا|رابعاً|خامسًا|خامساً|سادسًا|سادساً|سابعًا|سابعاً|"
                     r"ثامنًا|ثامناً|تاسعًا|تاسعاً|عاشرًا|عاشراً|الحادي عشر|الثاني عشر|ال\S+ عشر|العشرون|ال\S+ والعشرون|"
                     r"ال\S+ والثلاثون|الثلاثون|الأربعون|ال\S+ والأربعون|الخاتمة|خاتمة|المصادر)\s*[:：]?")
ENDING = re.compile(r"^(?:الخاتمة|خاتمة|المصادر)")  # closing sections: start a lesson, but are not "numbered"
LIST_LINE = re.compile(r"^\s*(?:\d+\s*[.)-]|[•·▪-])\s*")
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def slug(i: int) -> str:
    return f"l{i + 1:02d}"


class Converter:
    def __init__(self):
        self.v = Verifier(str(DB))
        con = sqlite3.connect(DB)
        self.surahs = {}
        for num, name in con.execute("SELECT DISTINCT surah, surah_name_ar FROM quran_ayat"):
            self.surahs[folded(name)] = num
        self.ayah_counts = dict(con.execute("SELECT surah, MAX(ayah) FROM quran_ayat GROUP BY surah"))
        con.close()
        self.report = []

    def surah_number(self, name: str):
        key = folded(name)
        return self.surahs.get(key) or self.surahs.get(folded("ال" + name)) or \
            (self.surahs.get(key[2:]) if key.startswith("ال") else None)

    # ---- quotations -> blocks -------------------------------------------------
    def verse_block(self, typed: str, surah_name: str, a1: str, a2: str | None, where: str) -> dict | None:
        s = self.surah_number(surah_name)
        a1 = int(a1.translate(ARABIC_DIGITS))
        a2 = int(a2.translate(ARABIC_DIGITS)) if a2 else a1
        m = self.v.quran.match(typed)
        note = ""
        given_ok = s is not None and 1 <= a1 <= a2 <= self.ayah_counts.get(s, 0) and \
            self.parts_in_ayat(typed, s, a1, a2)
        if given_ok and m and m.status == "exact":
            m.status = "exact"  # the text is also exactly in the referenced ayah: keep the team's reference
        elif m and m.status == "exact" and (s is None or (m.surah, m.ayah_from) != (s, a1)) and \
                not (s == m.surah and m.ayah_from <= a1 <= m.ayah_to):
            # The typed text is exactly elsewhere: trust the text and report the reference.
            note = f"reference [{surah_name}: {a1}] differs from where the text is ({m.surah}:{m.ayah_from}); used the text's place"
            s, a1, a2 = m.surah, m.ayah_from, m.ayah_to
        if s is None or not (1 <= a1 <= a2 <= self.ayah_counts.get(s, 0)):
            self.report.append(f"- **{where}** — verse reference not understood: [{surah_name}: {a1}] — kept as cited text")
            return None
        status = m.status if m else "not_found"
        if status != "exact" and not note and self.parts_in_ayat(typed, s, a1, a2):
            status = "confirmed in the referenced ayah (short or shortened with …)"
        elif status != "exact" and not note:
            details = "; ".join(f"{d['op']}: «{d['quote'] or d['source']}»" for d in (m.diff if m else []) if d["op"] != "equal")
            note = f"typed text is `{status}` against the Mushaf ({details or 'no match'}); the official text is shown"
        self.report.append(f"- {where} — Quran {s}:{a1}{'' if a2 == a1 else '-' + str(a2)} `{status}`"
                           + (f" — ⚠ {note}" if note else ""))
        return {"type": "quran", "surah": s, "ayah_from": a1, "ayah_to": a2}

    def parts_in_ayat(self, typed: str, s: int, a1: int, a2: int) -> bool:
        """True if every part of the quote (split at …) appears, in order, in the referenced ayat."""
        con = sqlite3.connect(DB)
        rows = con.execute("SELECT text_emlaey, text_raw FROM quran_ayat WHERE surah = ? AND ayah BETWEEN ? AND ?"
                           " ORDER BY ayah", (s, a1, a2)).fetchall()
        con.close()
        parts = [p for p in re.split(r"…|\.\.\.", typed) if strict(p)]
        for column in (0, 1):  # plain spelling, then Uthmani
            target = " " + " ".join(strict(r[column]) for r in rows) + " "
            pos, ok = 0, True
            for p in parts:
                i = target.find(" " + strict(p) + " ", pos)
                if i < 0:
                    ok = False
                    break
                pos = i + len(strict(p))
            if ok and parts:
                return True
        return False

    def hadith_block(self, typed: str, attribution: str, where: str) -> dict:
        m = self.v.hadith.match(typed.replace("…", " ").replace("...", " "))
        if m:
            self.report.append(f"- {where} — hadith «{typed[:50]}…» ({attribution}) → HadeethEnc {m.record_id} "
                               f"`{m.status}`" + ("" if m.status == "exact" else " — ⚠ check wording"))
            return {"type": "hadith", "record_id": m.record_id}
        self.report.append(f"- **{where}** — hadith «{typed[:60]}…» ({attribution}) not in our index — kept as cited text, "
                           f"labelled unverified")
        return {"type": "cited", "body": f"«{typed}»", "attribution": attribution, "indexed": False}

    def standalone_quote(self, block: dict, where: str) -> dict:
        """A text block that is one whole quotation (e.g. a verse typed without its reference, or a
        formula such as the shahada): an exact Quran match becomes a reference block; anything else
        becomes a quotation block the reader can check with the verifier."""
        if block["type"] != "text" or len(block["body"].split()) > 40:
            return block
        items = self.v.verify(block["body"])["items"]
        if len(items) != 1 or items[0].get("status") != "exact":
            return block
        if strict(items[0]["quote"]) != strict(block["body"]):
            return block
        src = items[0]["source"]
        if src["type"] == "quran":
            self.report.append(f"- {where} — standalone verse → Quran {src['surah']}:{src['ayah_from']} `exact`")
            return {"type": "quran", "surah": src["surah"], "ayah_from": src["ayah_from"], "ayah_to": src["ayah_to"]}
        self.report.append(f"- {where} — standalone quotation «{block['body'][:50]}» kept as a quotation block "
                           f"(matches {src['ref']})")
        return {"type": "cited", "body": block["body"], "attribution": "", "indexed": True}

    def paragraph_blocks(self, text: str, where: str) -> list[dict]:
        """Split a paragraph around verse and hadith quotations."""
        blocks, pos = [], 0
        matches = sorted([(m.start(), m.end(), "verse", m) for m in VERSE.finditer(text)] +
                         [(m.start(), m.end(), "hadith", m) for m in HADITH.finditer(text)], key=lambda x: x[0])
        for start, end, kind, m in matches:
            if start < pos:
                continue
            before = text[pos:start].strip()
            if before:
                blocks.append({"type": "text", "body": before})
            if kind == "verse":
                b = self.verse_block(m.group(1), m.group(2), m.group(3), m.group(4), where)
                blocks.append(b or {"type": "cited", "body": f"﴿{m.group(1)}﴾", "attribution": f"[{m.group(2)}: {m.group(3)}]"})
            else:
                blocks.append(self.hadith_block(m.group(1), m.group(2).strip(), where))
            pos = end
        rest = text[pos:].strip()
        if rest:
            blocks.append({"type": "text", "body": rest})
        return blocks

    # ---- files -> lessons ----------------------------------------------------------
    def lessons(self, text: str, file_title: str) -> list[dict]:
        """Lessons start at numbered headings (أولًا، ثانيًا…) when the file has them; otherwise at
        each ⸻ section that opens with a heading. Untitled sections join the lesson before them."""
        sections = [s.strip() for s in text.split(SEPARATOR) if s.strip()]
        numbered = any(ORDINAL.match(line.strip()) and not ENDING.match(line.strip()) for line in text.splitlines())
        groups = []  # [title, [paragraphs]]
        for i, section in enumerate(sections):
            paras = [p.strip() for p in re.split(r"\n\s*\n", section) if p.strip()]
            if i == 0 and paras and paras[0] == file_title:
                paras = paras[1:]
            for j, para in enumerate(paras):
                starts = self.is_heading(para) and (bool(ORDINAL.match(para)) if numbered
                                                    else (j == 0 or bool(ENDING.match(para))))
                if starts:
                    groups.append([para, []])
                else:
                    if not groups:
                        groups.append([file_title if not numbered else "مقدمة", []])
                    groups[-1][1].append(para)
        lessons = []
        for title, paras in groups:
            # Re-join a verse or hadith split over two paragraphs (quote, then its reference).
            joined = []
            for p in paras:
                if joined and (re.match(r"^\[[^\]]+\]\.?$", p) or re.match(r"^(?:رواه|متفق عليه)", p)):
                    joined[-1] += " " + p
                else:
                    joined.append(p)
            blocks = []
            where = f"{file_title} / {title}"
            for p in joined:
                blocks += [{"type": "heading", "body": p}] if self.is_heading(p) else self.paragraph_blocks(p, where)
            blocks = [self.standalone_quote(b, where) for b in self.merge_lists(blocks)]
            if blocks:
                lessons.append({"id": slug(len(lessons)), "title": title, "blocks": blocks})
        return lessons

    @staticmethod
    def is_heading(p: str) -> bool:
        line = p.strip()
        limit = 120 if ORDINAL.match(line) else 60  # numbered headings can be long questions
        return ("\n" not in line and len(line) <= limit and not line.endswith((".", ":", "،", "؛", "»", "﴾"))
                and not LIST_LINE.match(line) and "﴿" not in line and "«" not in line)

    @staticmethod
    def merge_lists(blocks: list[dict]) -> list[dict]:
        """Consecutive short text blocks (list items) become one text block with line breaks."""
        out = []
        for b in blocks:
            if (b["type"] == "text" and out and out[-1]["type"] == "text"
                    and (LIST_LINE.match(b["body"]) or len(b["body"]) < 50)
                    and (LIST_LINE.match(out[-1]["body"].splitlines()[-1]) or len(out[-1]["body"].splitlines()[-1]) < 50)):
                out[-1]["body"] += "\n" + b["body"]
            else:
                out.append(b)
        return out

    def run(self):
        paths = []
        for spec in PATHS:
            modules = []
            for name in spec["order"]:
                f = SOURCE / spec["folder"] / f"{name}.txt"
                text = f.read_text(encoding="utf-8").replace("\r\n", "\n")
                first = next(line.strip() for line in text.splitlines() if line.strip())
                file_title = name if ORDINAL.match(first) else first  # a file without a title line
                self.report.append(f"\n### {spec['folder']}/{name}.txt → module “{file_title}”\n")
                lessons = self.lessons(text, file_title)
                module = {"id": f"m{len(modules) + 1:02d}", "title": file_title, "lessons": lessons,
                          "source_file": f"content/source/{spec['folder']}/{name}.txt"}
                if name in spec.get("module_art", {}):
                    module["art"] = spec["module_art"][name]  # decorative illustration (app/static/art.js)
                modules.append(module)
                self.report.append(f"\n{len(lessons)} lessons.")
            paths.append({"id": spec["id"], "title": spec["title"], "description": spec["description"],
                          "audience": spec["audience"], "status": spec.get("status", "published"),
                          "art": spec.get("art"),
                          "level": "مبتدئ", "sources": ["محتوى كتبه فريق تبيّنوا (content/source/)"],
                          "modules": modules})
        data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
        data["paths"] = paths
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        REPORT.write_text("# Learning-path conversion report\n\nGenerated by `scripts/convert_paths.py`. "
                          "⚠ marks items for the team to review. Bold items were kept as the team's text "
                          "and are labelled unverified on the site.\n" + "\n".join(self.report) + "\n",
                          encoding="utf-8")
        n_lessons = sum(len(m["lessons"]) for p in paths for m in p["modules"])
        print(f"{len(paths)} paths, {sum(len(p['modules']) for p in paths)} modules, {n_lessons} lessons -> {OUT}")
        kinds = {}
        for p in paths:
            for m in p["modules"]:
                for lesson in m["lessons"]:
                    for b in lesson["blocks"]:
                        kinds[b["type"]] = kinds.get(b["type"], 0) + 1
        print("blocks:", kinds)
        print("warnings:", sum("⚠" in r for r in self.report), "| unverified kept:", sum(r.startswith("- **") for r in self.report))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    Converter().run()
