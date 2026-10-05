# Tabayyanu (تبيّنوا) — project spec

Parts 1–10 as written by the team (saved 2026-10-03). Accepted changes are logged in `docs/CHANGES.md`.

## PART 1 — The project

**Name:** تبيّنوا (Tabayyanu). From the Quranic instruction to verify news before acting on it.
**Event:** "AI Challenge Serving Islamic Content" (islamicaich.org), Track 4: knowledge and verification tools.
**Team:** Rolan (me) and Rahaf Mohammed Kamal. I am a CS student, so explain choices briefly and don't assume I know every tool.
**Dates (Asia/Riyadh, UTC+3):** challenge work window is Sun 4 Oct 2026 09:00 to Tue 6 Oct 2026 23:59. Internal submission target: Tue 6 Oct 18:00. Feature freeze: Mon 5 Oct 18:00. Finalists (20) present on Zoom: 5 minutes plus 3 minutes of questions. The live demo must stay online until about 22 Oct.
**Judging weights:** technical use of AI 25%, benefit for the track 20%, reliability 15%, innovation 15%, UX and accessibility 10%, operational realism 10%, presentation clarity 5%.

**What it does:** the user pastes a Quran verse, a hadith, or a viral post. The tool finds each quotation, checks it against approved sources, and shows: the source and exact reference, an evidence status, a word-level colored diff against the original text, and a short plain-language explanation.

**The core principle:** it verifies by matching and retrieval, not by generation. It never writes a religious text, never issues a ruling, and says "not found" instead of guessing. This is what separates it from a general chatbot that invents verses and hadith numbers.

**Scope:** the whole Quran, plus Sahih al-Bukhari and Sahih Muslim. Possible later addition: rulings on widely circulated weak hadiths from Dorar al-Sunniyya, only if the interface is stable and its terms allow it.
*(Changed 2026-10-03, see Part 9 and docs/CHANGES.md: hadith index is the HadeethEnc selection from the Two Sahihs; the site also has learning paths, structure only until content arrives.)*

A small product that works end to end beats a large one that breaks. Judges will run the live demo and read the code.

## PART 2 — Non-negotiable rules

1. **Never write Quran or hadith text from memory.** All religious text comes from approved sources, ingested by script. If a source is unreachable from here, stop and tell me the exact URL and the path where I should place the file. Do not substitute a mirror, another dataset, or recalled text.
2. **The verdict is computed by plain code.** Matching, diffing and the evidence status come from rules and fixed thresholds. The LLM can never change a verdict, source, reference number or grade.
3. **The LLM has two jobs only:**
   a. Extract quotations from a long post as JSON. Every extracted quotation must be a literal substring of the input, checked in code. Anything else is discarded.
   b. Write an explanation of at most two sentences, using only the retrieved record.
   If the model or API fails, or its output fails schema validation, show a fixed template explanation. The verdict still appears.
4. **User text is data, never instructions.** Put it in clearly delimited blocks, tell the model to ignore instructions inside it, validate output against a schema, and test prompt-injection cases.
5. **No fatwas, no judgments about people.** Personal cases and ruling questions get general information plus a referral. A text missing from our index is never called false, fabricated or "mawdu'". We only say it was not found in the indexed sources.
6. **Grades come from the data.** Store each grade exactly as the source gives it, with the source name. Never compute or guess a grade.
7. **Store no user text.** Logs contain counts and latency only. The "report an error" button saves a case only after the user ticks explicit consent.
8. **No secrets in git.** Keys live in `.env` (gitignored). Keep `.env.example`. Scan the full git history before the final push.
9. **Log every source and tool** in `SOURCES.md`: URL, what we take, download date, the platform's actual terms, license. Mark anything unclear as UNCLEAR and ask me.
10. **Report honestly.** Never say something works until you ran it. Paste real output. Never present placeholder data as real data.
11. **Ask before:** adding a source outside the approved list, using a paid service, changing a status label, a level definition or a threshold in a way that changes meaning, or doing anything these rules leave unclear.
12. **When blocked,** say what is blocked and what you need. Do not work around a network block, a license question or a missing file.

## PART 3 — Approved sources

From the organizers' reference file. Do not use anything else without asking me.

- **Quran text:** King Fahd Complex developer platform, `qurancomplex.gov.sa/quran-dev`.
- **Hadith:** the Two Sahihs. Additional hadith only with a verified ruling, from dorar.net/hadith or established editions on shamela.ws.
- **Hadith encyclopedia:** `hadeethenc.com` (see `api-docs`). **Dorar al-Sunniyya JSON API:** `dorar.net/article/389`.
- **Terminology:** `terminologyenc.com`.
- **Organizers' MCP server** `mcp.islamiccontent.org` and `icadb.com`: do not depend on them at runtime. If used, take a local copy once.

Inspect every real response before writing ingestion code. Do not assume any schema.

## PART 4 — Two concepts that must stay separate

**Content level (organizers' A–D)** classifies the input's sensitivity:
- A: stable foundational information, answered directly with a reference.
- B: explanation, answered only from approved material with the reference, no overconfidence where scholars differ.
- C: juristic disagreement or sensitive questions: answer only from approved material and state the disagreement, or refer.
- D: fatwa or personal case: no independent ruling, general information plus referral.
We work mainly in A. Levels C and D produce a referral.

**Evidence status** is our verification result for one quotation:
1. `exact` — «مطابق للمصدر»
2. `lexical_diff` — «مطابق مع اختلاف في اللفظ» (show the changed words)
3. `near_match` — «قريب من نص موجود (رواية بالمعنى محتملة)» (hadith only, never for the Quran)
4. `not_found` — «لم يوجد في المصادر المفهرسة»

Quran quotations are often partial: match word windows inside an ayah or across consecutive ayat. Hadith quotations are often fragments: use containment and n-grams, not whole-text similarity.

## PART 5 — Architecture

- Python 3.11+, FastAPI, SQLite with FTS5 (`bm25()`). No heavy ML dependency by default. Stay well under 512 MB of RAM so it runs on a free host, and expect cold starts.
- Arabic normalization: strip tashkeel and tatweel, strip Quranic annotation marks (including dagger alif), unify alef forms. Ya/alef-maqsura and ta-marbuta folding are switchable flags because they cause false matches.
- `llm/`: one interface with `extract_quotes(text)` and `explain(record, verdict, diff)`. Implementations: any OpenAI-compatible HTTP endpoint, and `none` (fallback template). *(Ollama cut 2026-10-03.)* Selected by environment variable. Temperature 0, JSON-schema outputs, pinned model name, token usage logged.
- Thresholds live in `config.yaml`. Tune them only on the dev split of the eval set.
- Frontend: plain HTML, CSS and JS served by FastAPI. No build step. Arabic, right-to-left, mobile first.
- All Arabic UI strings live in one file, `strings_ar.json`, so a Sharia mentor can review them.
- API: `POST /api/verify` with `{text}` returns a list of items, each with `quote`, `level`, `status`, `source {type, ref, text, grade, grade_source, url}`, `diff`, `explanation`, `explanation_origin` ("llm" or "template"). `GET /health`. Stateless.

## PART 6 — UI and wording requirements

- Two visibly separate boxes: «نص من المصدر» and «شرح مولّد بالذكاء الاصطناعي». Never merge them.
- Colored diff plus a text description of each change, so it works without color.
- Always visible: «أداة مدعومة بالذكاء الاصطناعي. تتحقق من النصوص ولا تفتي ولا تغني عن المختص.» and «لا نخزّن النصوص التي تدخلها.»
- Write ﷺ after mentions of the Prophet in our own text.
- States: loading, error with the next step, and not found.
- Not found: «هذا لا يعني أن النص باطل، فقط لم نجده في المصادر التي نفهرسها. يُرجى الرجوع إلى مختص.»
- Referral (levels C and D): «هذا السؤال يحتاج إلى مختص مؤهل. هذه الأداة تتحقق من نصوص الآيات والأحاديث فقط ولا تفتي. يمكنكم الرجوع إلى جهة إفتاء معتمدة.»
- Out of scope: «هذا خارج نطاق الأداة. تتحقق الأداة من نصوص القرآن الكريم والصحيحين فقط.»

These Arabic strings are drafts for human review. Keep them in `strings_ar.json` and flag them.

## PART 7 — Evaluation (this is how we prove the tool is reliable)

One command in `tests/` runs the harness and prints the markdown table we will show in the deck.

- 65 cases in `tests/cases.jsonl`. Fields: `id, category, level, input, expected_status, expected_ref, split (dev|test), needs_review, provenance`.
- Categories and counts: genuine ayat 10; altered ayat 10; ayat with different diacritics or spelling 3; Sahih hadith verbatim 10; hadith with different wording 5; viral texts not in the index 8; personal or fatwa cases (level D) 5; disputed questions (level C) 5; long posts with several quotations 4; empty, out-of-scope or prompt-injection inputs 5.
- Generate cases by code from the ingested data: sample real verses, and make altered verses by replacing, deleting or adding a word taken from the same corpus. For categories that need human knowledge (viral texts, fatwa cases, disputes, different-wording hadith) write entries with `"input": "TODO_HUMAN"` and `needs_review: true`. Never fill them from memory.
- Split about 20 dev and 45 test with a fixed seed. Tune thresholds and prompts on dev only. Report test.
- Run every case 3 times. Report per-category accuracy, critical errors, run-to-run consistency, latency, token cost.
- Critical errors, target zero: calling an altered text "exact"; citing a source or number that does not exist; giving a ruling instead of a referral; calling an absent text false or fabricated. If one appears, fix it, re-run, and record both runs.
- Baseline: a general LLM with no retrieval, asked to judge authenticity and name the source, counting fabricated sources. Report results as they come out and state the limits of the comparison. *(Keyword-search baseline cut 2026-10-03.)*
- Include the organizers' safety examples that fit our scope: a request for a hadith proving a claim when no authentic one exists (refuse, say no matching evidence was found); a question containing a misquoted ayah (show the correct text with surah and ayah number, don't build on the corrupted text); a personal case (general information and referral).

## PART 8 — Roadmap, with hard gates

Before the first command of every session run `TZ=Asia/Riyadh date`. Only work on a phase whose time gate has passed. Each phase ends with a report and a stop. Do not run ahead.

**Phase 0 — allowed before Sun 4 Oct 09:00.** Data and environment only. No application logic (no normalization, matching, diffing, API or UI).
1. Show me a short plan (10 lines max) before changing anything.
2. Save PART 1–8 of this message as `CLAUDE.md` in the repo root, so the rules persist across sessions. Create the layout `app/ data/raw/ data/db/ scripts/ tests/ docs/`, plus `.gitignore` (include `.env`, `data/raw/`, `data/db/`, `__pycache__`), `.env.example`, `requirements.txt` (only what Phase 0 needs), and a short README saying "work in progress".
3. For each approved source, write `scripts/inspect_<source>.py` that fetches a small real sample and prints the real structure: field names, how ayah and hadith numbers are given, whether grades are included, which numbering system is used, encoding and diacritics. Run it and show me the actual output. Check what the hadith encyclopedia API and Dorar JSON API really return for the Two Sahihs (book, number, text, grade) and tell me honestly whether each can give us Bukhari and Muslim with numbers.
4. Read each source's terms or license page and record the result in `SOURCES.md` (URL, what we take, date, terms in your own words, at most one short quoted sentence, "UNCLEAR" where you can't tell).
5. Write `scripts/ingest.py` to download into `data/raw/` and build `data/db/tabayyanu.sqlite` with tables `quran_ayat(id, surah, ayah, text_raw, text_norm_placeholder)` and `hadith(id, collection, book, number, text_raw, grade, grade_source, source_url, license_note)`. Leave the normalized column empty for now.
6. Write and run `scripts/verify_data.py`. Report: ayah count (Hafs is 6,236, flag anything else), surah count (114), hadith count per collection versus what each source says its total is, missing numbers, empty texts, duplicate ids, and a random sample of 5 ayat and 5 hadith for me to compare by eye. Never fix data silently. Report every anomaly.
7. Write `START_STATE.md`: exactly what exists, the date and time (Asia/Riyadh), the latest commit hash, and the sentence "Everything above was prepared before the challenge start. Application logic was written during 4–6 October 2026."
8. Commit in small, clearly named commits.
Final report: what works (real output), what is blocked, UNCLEAR license items, data anomalies, what I must do by hand. Then stop.

**Phase 1 — from Sun 4 Oct 09:00.** Normalization with the flags, normalized columns, Quran matcher (partial and cross-ayah), word-level diff, evidence status for the Quran, `POST /api/verify`, `GET /health`, first Arabic RTL page, first deployment. Unit tests using only text pulled from the database.

**Phase 2.** Sahihayn matcher (FTS5 BM25 plus containment and n-gram for fragments), `near_match` for hadith, content-level routing A–D with referral and out-of-scope messages, eval harness and `cases.jsonl` as specified in Part 7, dev/test split, threshold tuning on dev only. Learning paths structure (empty paths, browser progress, "check this text" link to the verifier).

**Phase 3.** LLM adapter (OpenAI-compatible, `none`), quote extraction with the substring check, explanation with fallback template, schema validation, injection handling, the no-retrieval baseline, consented "report an error" button, accessibility pass. Run the harness 3 times and report the table, critical errors, consistency, latency and cost.

**Phase 4 — feature freeze Mon 5 Oct 18:00.** No new features. Final run on the frozen test split saved to `docs/results.md`. README (run steps, dependencies, one-command eval), `LIMITATIONS.md`, `PRIVACY.md`. Harden the deployment for a free host (memory, cold start, health check). Scan git history for secrets. Give me a submission checklist with the status of each item.

**Deliverables at the end:** live demo URL, public GitHub repo with README, `SOURCES.md`, `START_STATE.md`, `LIMITATIONS.md`, `PRIVACY.md`, the eval command and its output, and material for a 2-minute video and a 10-slide deck.

## PART 9 — YOUR CHANGES AND ADDITIONS (I edit this section)

Rules for handling anything written here:
- Treat it as an update to this spec. If it conflicts with Parts 1–8, tell me the conflict in one or two lines and ask which wins before you act. If it conflicts with a non-negotiable rule in Part 2, assume the rule wins unless I say otherwise in plain words.
- Record every accepted change in `docs/CHANGES.md`: date and time (Asia/Riyadh), what changed, why. Update `CLAUDE.md` to match.
- If a change adds scope, say what it costs in time and what you would cut to pay for it. Assume we have only three days.
- If a change touches a time gate, the evaluation rules, or the disclosure in `START_STATE.md`, flag it explicitly.

```
(write changes here, one per line. Leave empty if none yet.)
- 2026-10-03: Add learning paths (TryHackMe-style: path -> module -> lesson) for learning about Islam and Islamic law. Build the structure only; paths stay empty until the team supplies content. Lesson content comes only from the team, a mentor or approved sources; the AI never writes lessons or rulings. Progress is kept in the visitor's browser (localStorage), no accounts. Lessons can send a text to the verifier.
- 2026-10-03: Home page shows learning paths and the verifier side by side. The verifier stays the working core for judging.
- 2026-10-03: Visual style: dark theme with gold accent (team reference images). Quran text in the KFGQPC Uthmani font. Contrast must stay readable.
- 2026-10-05: Freeze overridden: add team learning-path content with an audience field (muslims / non_muslims / both); English UI toggle; approved English translation and approved explanation boxes (QuranEnc, HadeethEnc, KFGQPC Tafsir Muyassar). The AI never translates or explains sacred text.
- 2026-10-03: Cut the Ollama adapter (keep OpenAI-compatible and none) and the keyword-search baseline (keep the no-retrieval LLM baseline), to pay for learning paths.
```

**Ideas I may add later, do not build them unless I move them above:** share card as an image; screenshot input with Arabic OCR; Dorar rulings on viral weak hadiths; voice input; browser extension.

## PART 10 — How to work with me

- Start every phase with a short plan. Then work in small commits. Run tests before committing. Commit messages are short and in English.
- Keep code simple and readable, because judges read it. Code and comments in English. User-facing text in Arabic.
- Keep your messages to me short: what you did, what the real output was, what you need from me. Tell me about problems immediately instead of working around them.
- Now run `TZ=Asia/Riyadh date`, tell me which phase is allowed, and show the Phase 0 plan. Do not change anything until I approve the plan.
