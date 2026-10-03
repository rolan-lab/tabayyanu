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

## 2026-10-03 17:38 — KFGQPC Quran license accepted as documented
- **What:** we use the KFGQPC Hafs files without an explicit license grant, display the text unchanged, and credit the Complex.
- **Why:** the developer platform publishes the files for application developers, and the Complex's site policy excepts files it makes available for public use. Recorded in SOURCES.md; to be noted in LIMITATIONS.md. Approved by Rolan.
