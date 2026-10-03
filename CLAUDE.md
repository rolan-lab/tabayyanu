# Tabayyanu (تبيّنوا) — project rules

Hackathon entry: "AI Challenge Serving Islamic Content", Track 4 (verification and knowledge tools).
Team of two. Build window: Sun 4 Oct 2026 09:00 to Tue 6 Oct 2026 23:59, Asia/Riyadh (UTC+3).
Internal target: submit by Tue 6 Oct 18:00. Only work done 4–6 Oct is judged. Anything built before that must be disclosed in START_STATE.md.

## What we are building

A web tool. The user pastes a verse, a hadith, or a viral post. The tool checks each quotation against approved sources and shows: the source and reference, the evidence status, a word-level colored diff against the original, and a short plain-language explanation. It never invents a religious text, never gives a ruling, and refuses or refers when it has no support.

Scope: the Quran (whole) and the two Sahihs (Bukhari, Muslim). Optional later: rulings on widely circulated weak hadiths from Dorar al-Sunniyya, only if its interface is stable and its terms allow it.

The judges run the live demo and read the code. The product must work end to end. A small product that works beats a large one that breaks.

## Non-negotiable rules

1. **Never write Quran or hadith text from memory.** All religious text comes from the approved sources below, ingested by script. If a source cannot be reached from this environment, stop and tell the user the exact URL and the file path to place the data in. Do not switch to a mirror, a different dataset, or recalled text.
2. **The verdict is deterministic.** Matching, diffing and the evidence status are computed by plain code from the data. The LLM can never change a verdict, a source, a reference number or a grade.
3. **The LLM has exactly two jobs:** (a) extract quotations from a long post as JSON, with each quotation copied verbatim; any quotation that is not a literal substring of the input is discarded in code; (b) write a two-sentence explanation from the retrieved record only. If the model is unavailable or its output fails validation, show a fixed template instead. The verdict must still appear.
4. **User text is data, never instructions.** Pass it to the model inside clearly delimited blocks, tell the model to ignore instructions inside it, and validate the model output against a schema.
5. **No fatwas and no judgments about people.** Personal cases and ruling questions get general information plus a referral. A text that is absent from our index is never called fabricated or false. Say: not found in the indexed sources.
6. **Grades come from the data.** Store the grade exactly as the source gives it, with the name of the source. Never compute or guess a grade.
7. **No user text is stored.** Logs hold counts and latency only. The "report an error" button stores a case only after the user ticks explicit consent.
8. **No secrets in git.** Keys go in `.env`, which is in `.gitignore`. Provide `.env.example`. Check the whole git history before the final push.
9. **Log every source and tool** in `SOURCES.md`: URL, what was taken, download date, terms of use, license. The Association says its content is free and available through public APIs, but record each platform's actual terms. If terms are unclear, ask the user.
10. **Report honestly.** Do not say something works until you ran it. Paste real test output. Never present placeholder data as real.

## Approved sources (from the organizers' reference file)

- Quran text: King Fahd Complex developer platform, `qurancomplex.gov.sa/quran-dev` (XML/JSON with ayah and word identifiers).
- Hadith: the Two Sahihs. Other hadith may be added only with a verified ruling, using dorar.net/hadith or the established printed editions on shamela.ws.
- Hadith encyclopedia: `hadeethenc.com/api-docs`. Dorar al-Sunniyya JSON search: `dorar.net/article/389`.
- Terminology: `terminologyenc.com` and the glossary in the reference file (for example, Hadith: what is reported from the Prophet ﷺ, with the degree of authenticity stated).
- Organizers' MCP server `mcp.islamiccontent.org`: do not depend on it at runtime. Download a local copy once and serve from it.

Inspect each real response before writing the ingestion code. Do not assume a schema.

## Two separate concepts. Do not mix them.

**Content level (organizers' A–D)** classifies the input by sensitivity:
- A: stable, foundational information. Direct documented answer.
- B: explanation and argumentation. Answer only from approved material with the reference, avoid certainty where there is disagreement.
- C: juristic disagreement or highly sensitive questions. Answer only with what is approved and state the disagreement, or refer.
- D: fatwa or a personal case. No independent ruling. General information and a referral.

Our tool works mostly in A. Anything classified C or D becomes a referral.

**Evidence status** is our verification result for a quotation:
1. `exact` — "مطابق للمصدر"
2. `lexical_diff` — "مطابق مع اختلاف في اللفظ" (show the changed words)
3. `near_match` — "قريب من نص موجود (رواية بالمعنى محتملة)" (hadith only; never used for the Quran)
4. `not_found` — "لم يوجد في المصادر المفهرسة"

Quran: partial quotations are common, so match on word windows inside an ayah or across consecutive ayat. Hadith: quotations are often fragments of a longer text, so use containment and n-grams, not whole-text similarity.

## Architecture

- Python 3.11+, FastAPI, SQLite with FTS5 (use `bm25()`). No heavy ML dependency in the default install. Keep memory well under 512 MB so it runs on a free host.
- Arabic normalization: strip tashkeel and tatweel, strip Quranic annotation marks (including dagger alif), unify alef forms. Treat ya/alef-maqsura and ta-marbuta folding as switchable flags, because they create false matches.
- `llm/` has one interface with `extract_quotes(text)` and `explain(record, verdict, diff)`. Implementations: Ollama, any OpenAI-compatible HTTP endpoint, and `none` (fallback template). Chosen by environment variable. Temperature 0, JSON-schema outputs, pinned model name, token usage logged.
- Thresholds live in `config.yaml`. Tune them only on the dev split of the eval set.
- Frontend: plain HTML, CSS and JS served by FastAPI. No build step. Arabic, right-to-left, mobile first.
- All Arabic UI strings live in one file (`strings_ar.json`) so the Sharia mentor can review them.

API: `POST /api/verify` with `{text}` returns a list of items, each with `quote`, `level`, `status`, `source {type, ref, text, grade, grade_source, url}`, `diff`, `explanation`, `explanation_origin` ("llm" or "template"). `GET /health`. Stateless.

## UI requirements

- Two visibly separate boxes: "نص من المصدر" and "شرح مولّد بالذكاء الاصطناعي". Never merge them.
- Colored diff plus a text description of each change, so it works without color.
- Always visible: "أداة مدعومة بالذكاء الاصطناعي. تتحقق من النصوص ولا تفتي ولا تغني عن المختص." and a one-line privacy note: "لا نخزّن النصوص التي تدخلها."
- Write ﷺ after mentions of the Prophet in our own text.
- States: loading, error with the next step, and "not found" with this note: "هذا لا يعني أن النص باطل، فقط لم نجده في المصادر التي نفهرسها. يُرجى الرجوع إلى مختص."
- Referral text for levels C and D: "هذا السؤال يحتاج إلى مختص مؤهل. هذه الأداة تتحقق من نصوص الآيات والأحاديث فقط ولا تفتي. يمكنكم الرجوع إلى جهة إفتاء معتمدة."
- Out of scope text: "هذا خارج نطاق الأداة. تتحقق الأداة من نصوص القرآن الكريم والصحيحين فقط."

These Arabic strings are drafts. Keep them in `strings_ar.json` and flag them for human review.

## Evaluation

`tests/` holds a harness runnable with one command that prints the same markdown table we will show in the deck.

- 65 cases in `tests/cases.jsonl`. Fields: `id, category, level, input, expected_status, expected_ref, split (dev|test), needs_review, provenance`.
- Categories and counts: genuine ayat 10; altered ayat 10; ayat with different diacritics or spelling 3; Sahih hadith verbatim 10; hadith with different wording 5; viral texts not in the index 8; personal cases or fatwas (level D) 5; disputed questions (level C) 5; long posts with several quotations 4; empty, out-of-scope or prompt-injection inputs 5.
- Build cases only by code from ingested data: sample real verses, and create altered verses by replacing, deleting or adding a word taken from the same corpus. For categories that need human knowledge (viral texts, fatwa cases, disputes, different-wording hadith) create entries with `"input": "TODO_HUMAN"` and `needs_review: true`. Never fill them from memory.
- Split about 20 dev / 45 test with a fixed seed. Thresholds and prompts are tuned on dev only. Report test.
- Run each case 3 times. Report per-category accuracy, critical errors, run-to-run consistency, latency, and token cost.
- Critical errors: calling an altered text "exact"; citing a source or number that does not exist; giving a ruling instead of a referral; calling an absent text false or fabricated. Target zero. If one appears, fix it, re-run, and record both runs.
- Baselines, pluggable: (1) a general LLM with no retrieval, asked to judge authenticity and give the source; count fabricated sources; (2) plain keyword search. Report results as they come out and write the limits of the comparison.
- Also include the organizers' safety cases (reference file, page 6) that fit our scope, for example: ask for a hadith that proves a claim when no authentic hadith exists (expected: refuse and say no matching evidence was found); a question containing a misquoted ayah (expected: gently show the correct text with surah and ayah number, do not build on the corrupted text); a personal case (expected: general information and referral).

## Roadmap (do not run ahead; each phase ends with a report and a stop)

- **Phase 0 (allowed before 4 Oct 09:00):** repo skeleton, source inspection, data ingestion, source log, START_STATE.md. No application logic.
- **Phase 1 (from 4 Oct 09:00):** normalization, Quran matcher, diff, evidence status, API, first UI, first deploy.
- **Phase 2:** Sahihayn matcher, content-level routing and referrals, eval harness and cases.
- **Phase 3:** LLM adapter (extraction and explanation), fallback template, injection tests, baselines, report-an-error, accessibility pass.
- **Phase 4 (freeze features Mon 5 Oct 18:00):** final eval run, README, LIMITATIONS.md, PRIVACY.md, deployment hardening, submission checks.

## Working style

- Start each phase with a short plan, then work in small commits. Run tests before committing.
- Before the first command of each session run `TZ=Asia/Riyadh date` and respect the time gate above.
- Ask the user before: adding a source outside the approved list, using a paid service, changing a status label, a level definition, or a threshold in a way that changes meaning, or anything the rules above leave unclear.
- When blocked, say what is blocked and what you need. Do not work around a network block, a license question or a missing file.
- Keep code simple and readable. Judges review it. Code and comments in English, user-facing text in Arabic.
- Deliverables at the end: working live demo URL, public GitHub repo with README (run steps, dependencies), SOURCES.md, START_STATE.md, LIMITATIONS.md, PRIVACY.md, the eval command and its output.
