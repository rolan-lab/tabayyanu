# Start state

What existed in this repository before the challenge build window
(Sun 4 Oct 2026 09:00 – Tue 6 Oct 2026 23:59, Asia/Riyadh).

- Written: Sat 2026-10-03 16:07 Asia/Riyadh (UTC+3); updated 16:47 the same day
- Latest commit when updated: `52292c833414be79f06823763276eca31b3e5cc9`
  (this update is committed right after it; the full pre-start history is in `git log`)

## Files in the repository

| Path | What it is |
|---|---|
| `CLAUDE.md` | Project rules and roadmap |
| `README.md` | Project name and "work in progress" |
| `.gitignore`, `.env.example`, `requirements.txt` | Repo setup (`requests` only) |
| `SOURCES.md` | Source log: URLs, what is taken, dates, terms, UNCLEAR items |
| `scripts/inspect_qurancomplex.py` | Downloads the KFGQPC Hafs package, checks SHA-256, prints its structure |
| `scripts/inspect_hadeethenc.py` | Prints real HadeethEnc API responses |
| `scripts/inspect_dorar.py` | Prints real Dorar JSON search responses |
| `scripts/inspect_shamela.py` | Reads the Shamela database zip's file index over HTTP range requests and fetches its book catalogue only |
| `scripts/ingest.py` | Downloads source data into `data/raw/` and builds `data/db/tabayyanu.sqlite` (tables `quran_ayat`, `hadith`; no normalization) |
| `scripts/verify_data.py` | Reports counts, gaps, duplicates and anomalies in the database; changes nothing |
| `docs/phase0_verify_output.txt` | Output of `verify_data.py` on 2026-10-03 |
| `app/`, `tests/`, `data/raw/`, `data/db/`, `docs/` | Empty directories (`.gitkeep`) |

Not in git (ignored): `data/raw/` (downloaded source files), `data/db/` (built database), `.venv/`.

## Data state

- Quran: 6,236 ayat, 114 surahs, from KFGQPC `kfgqpc_hafs_v30.zip` (SHA-256 matches the published value).
- Hadith: 3,574 HadeethEnc records downloaded; 1,785 rows citing Sahih al-Bukhari and 2,055 citing
  Sahih Muslim (about 1,700 without a hadith number in the source reference). A curated selection,
  not the complete Two Sahihs. Details and anomalies: `docs/phase0_verify_output.txt`.
- Shamela: catalogue (`master.db`) and one book page map (`book_1727.db`) in `data/raw/shamela/`.
  No book text: Shamela keeps text in a 14.1 GB Lucene index that was not downloaded.

## Not yet written

No application logic: no Arabic normalization, matching, diffing, evidence status, API, UI,
LLM adapter or evaluation harness.

## Open questions (team decision pending)

1. Hadith scope: use the HadeethEnc subset, or obtain full texts of the Two Sahihs. The Shamela
   database listed by the organizers stores text only in a 14.1 GB Lucene index (see SOURCES.md).
2. Extra columns beyond the planned schema: `text_emlaey`, `source_record_id`, `attribution`, `ref_raw`.
3. KFGQPC Quran files: no explicit license found (see SOURCES.md).

Everything above was prepared before the challenge start. Application logic was written during 4–6 October 2026.
