# Accepted changes to the spec

Each entry: date and time (Asia/Riyadh), what changed, why. `CLAUDE.md` is kept in line with this log.

## 2026-10-03 17:38 — CLAUDE.md holds Parts 1–10
- **What:** `CLAUDE.md` contains Parts 1–10 of the team spec, not only Parts 1–8 as Phase 0 step 2 says.
- **Why:** Part 9 (change rules) and Part 10 (working style) must persist across sessions too. Approved by Rolan.

## 2026-10-03 17:38 — Extra database columns kept
- **What:** beyond the planned schema, `quran_ayat` has `text_emlaey`, and `hadith` has `source_record_id`, `attribution`, `ref_raw`. All are copied unchanged from the sources.
- **Why:** `text_emlaey` is the KFGQPC plain spelling "used for search purpose"; the hadith columns keep the raw reference each number was parsed from, so every number can be traced. Approved by Rolan.

## 2026-10-03 17:38 — Hadith corpus: HadeethEnc subset
- **What:** the hadith index is the HadeethEnc records that cite Sahih al-Bukhari or Sahih Muslim (3,574 records downloaded; 1,785 Bukhari and 2,055 Muslim citation rows). It is described as a selection from the Two Sahihs, not the complete collections.
- **Why:** no approved source gives the complete Two Sahihs in usable form: HadeethEnc is curated, Dorar's API is search-only, and the Shamela database keeps text only in a 14.1 GB Lucene index (see SOURCES.md). Texts outside the index get `not_found`, never "false". Approved by Rolan.
- **Flag:** this narrows the "Scope" line in Part 1. It must be stated in README and LIMITATIONS.md.

## 2026-10-03 17:55 — Learning paths added (structure only)
- **What:** TryHackMe-style learning paths (path → module → lesson) about Islam and Islamic law. Structure only; paths stay empty until the team supplies content. Content comes only from the team, a mentor or approved sources; the AI never writes lessons or rulings. Progress lives in the visitor's browser (localStorage), no accounts. Lessons can send a text to the verifier. Planned for Phase 2.
- **Why:** team wants a learning platform with the verifier as its validity checker. Fits Track 4 ("knowledge and verification tools").
- **Flags:** changes the Part 1 scope; the Part 6 out-of-scope message still applies to the verifier only. Islamic-law lessons touch levels C/D, so content needs human review. A path must be filled before the demo (Mon 5 Oct 18:00) or the section looks unfinished. Estimated cost 6–8 hours.

## 2026-10-03 17:55 — Home layout and visual style
- **What:** home shows learning paths and the verifier side by side; the verifier is the working core. Dark theme with gold accent, Quran text in the KFGQPC Uthmani font, readable contrast.
- **Why:** team choice and reference images.

## 2026-10-03 17:55 — Cuts to pay for learning paths
- **What:** dropped the Ollama adapter (keep OpenAI-compatible and `none`) and the keyword-search baseline (keep the no-retrieval LLM baseline).
- **Why:** frees about the time learning paths need. **Flag:** changes Part 7 (evaluation baselines).

## 2026-10-03 17:38 — KFGQPC Quran license accepted as documented
- **What:** we use the KFGQPC Hafs files without an explicit license grant, display the text unchanged, and credit the Complex.
- **Why:** the developer platform publishes the files for application developers, and the Complex's site policy excepts files it makes available for public use. Recorded in SOURCES.md; to be noted in LIMITATIONS.md. Approved by Rolan.

## 2026-10-04 14:30 — API additions during Phases 1–3 (status labels unchanged)
- **What:** each item has `kind` (`quote` | `referral` | `out_of_scope`); referral and out-of-scope items have `status: null` and carry the fixed Part 6 text. Quran items add `partial` and `also_in` (other places with the same exact text). Quotes too short to verify are `not_found` with `note_key: "too_short"` and their own note. Items add `diff_notes` (text description of each change) and `status_label`.
- **Why:** referrals are not verification results, so they must not borrow a status; partial and repeated passages needed to be visible to stay honest about references. No status label or level definition changed.
- **Flag:** level routing word lists in `config.yaml` (including agreement words «يتفقون», «إجماع» added before the eval cases were generated) are drafts for mentor review.

## 2026-10-04 14:30 — Server access log disabled
- **What:** the server runs with `--no-access-log`.
- **Why:** default access lines record client IP addresses; rule 7 allows counts and latency only.

## 2026-10-04 23:10 — Official Quran file bundled in the repository
- **What:** `data/vendor/kfgqpc_hafs_v30.zip`, the unmodified KFGQPC file (SHA-256 `227E6B15…F245`, as published). `scripts/ingest.py` tries the official URL first and falls back to this copy; either copy must match the published SHA-256 or the build stops (tested, including a one-byte tamper test).
- **Why:** Render's build servers (Frankfurt) cannot connect to `download.qurancomplex.gov.sa` (connection timeout, 2026-10-04), so the deployment could not build. Not a mirror or another dataset: the same official file, verified by hash.
- **Flag:** this redistributes the file through our public GitHub repository, beyond using and displaying it. The KFGQPC license is UNCLEAR (SOURCES.md). Decided by Rolan.

## 2026-10-05 21:30 — Feature freeze overridden by the team (flag: time gate)
- **What:** after the Mon 18:00 freeze, Rolan approved three additions: (1) learning-path content from the team's text files plus an audience field (Muslims / non-Muslims / both); (2) an English version of the interface; (3) approved English translations and approved explanations shown next to verified texts.
- **Why:** team request. Not built: recommended-books page.
- **Rules kept:** the AI does not translate or explain sacred text. Translations and explanations come from approved sources only, in their own box, labelled with the source: English Quran translation from QuranEnc (Association, reference file p. 9), hadith translation and شرح from HadeethEnc, Quran explanation from التفسير الميسر on the KFGQPC developer platform. Approved as new sources by Rolan (rule 11). The AI box stays a two-sentence note on the verdict.

## 2026-10-06 01:30 — Team learning paths converted; two matcher spelling fixes
- **What:** `scripts/convert_paths.py` turns the team's files in `content/source/` into `content/paths.json`: path "أساسيات الدين للمسلم" (audience muslims, 6 modules) and "تعرّف على الإسلام" (non_muslims, 2 modules), one lesson per numbered section. Verses become reference blocks (official text shown); hadith found in our index become hadith blocks; other quotations stay as the team wrote them in a labelled `cited` block with a check button. Review list: `docs/paths_conversion_report.md`. The two Hajj/Umrah files describe a planned assistant rather than lessons and are kept as a **draft path** (hidden) pending the team's decision. Path titles are drafts.
- **Rule refinement:** short phrases of up to 7 words inside a sentence (e.g. a dhikr) may stay in lesson text; longer typed verses or hadith must be reference blocks.
- **Matcher fixes found through the team's text:** vocative «يا» typed apart is joined to the next word (the Mushaf data never has a standalone يا); «السماوات» and «السموات» are treated as the same word (the plain-spelling Mushaf text writes «السموات»). Both are spelling conventions, not different words. Dev and test evaluations re-run afterwards: unchanged (100%, 0 critical errors).
- **Explanations:** diff changes are described to the model in plain words (it had reversed which side a missing word was on).

## 2026-10-06 00:10 — Learning-path guide and English in lessons (flag: rule 3, Part 2)
- **What:** (1) a small assistant at the bottom right that answers only by **finding lessons**: it returns links to matching lessons with a short excerpt of the team's own text, a referral for ruling or personal questions, and a "verify" link when the question contains a verse or hadith. (2) In lessons, verses and hadith stay in Arabic and also show the approved English translations (QuranEnc, HadeethEnc); the lesson text itself stays Arabic.
- **Rule 3 extension, approved by Rolan:** the model gets a third job: turn the visitor's question into Arabic search keywords and choose up to three lessons from the search results (ids validated in code). It writes no answer text, no religious text and no ruling; everything shown is the team's lessons or fixed wording. Without a model, plain keyword search is used.
- **Not done:** free chat (rejected: risk of invented texts or rulings); machine translation of lesson text.
