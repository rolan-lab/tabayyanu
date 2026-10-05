# Limitations

What the tool does not do, and where it can be wrong. Kept honest on purpose.

## Coverage

- **Hadith index is a selection, not the complete Two Sahihs.** It holds 2,484 HadeethEnc records that cite Sahih al-Bukhari or Sahih Muslim. No approved source gave us the full texts in usable form (SOURCES.md, §5). A genuine Sahih hadith outside this selection gets `not_found`, which only means "not in our index".
- **Hadith wording is HadeethEnc's.** Many records come from compilations (Riyad al-Salihin, Umdat al-Ahkam) and may merge narrations; the wording can differ from the edition at the cited number.
- **About 1,700 citation rows have no hadith number**, because HadeethEnc cites only the edition. The tool says so instead of guessing a number.
- **Grades are copied as HadeethEnc gives them.** A few grades cover several narrations at once (e.g. one narration weak, another sound).
- **Quran: Hafs only**, from the King Fahd Complex text.

## Matching

- **Quotes shorter than 3 words (Quran) or 4 content words (hadith) are not verified**: too ambiguous.
- **Spelling-only differences** (ى/ي, ة/ه, hamza seat) are reported as `lexical_diff`, never `exact`, to avoid calling an altered text exact. Some users will see a "difference" that is only spelling; the diff labels it as such.
- **Partial quotations** are `exact` when every word matches, and are flagged as partial.
- **Narration by meaning** (`near_match`) is detected only through shared word pairs; a paraphrase with different words can be missed.
- **Salawat and narrator formulas** (صلى الله عليه وسلم, رضي الله عنه…) are ignored when comparing hadith, so their presence or absence is not reported.
- **Long posts**: without a model, quotations are found from brackets and sentence punctuation; quotations run into the surrounding text without punctuation may be reported with extra words.

- **Quotations shortened with «…»** are reported as `lexical_diff` (never `exact`); the tool does not yet treat «…» as a deliberate gap.
- **English hadith translation** exists for 1,650 of the 2,484 indexed records (HadeethEnc's own coverage).

## Routing and AI

- **Level routing uses fixed word lists** (`config.yaml`). It can miss a ruling question phrased differently, or route an ordinary question to a referral. The lists need review by a Sharia mentor.
- **The model is optional.** Explanations from the model are validated (two sentences, no rulings, no "false", no full-match claim for a non-exact verdict), but the wording still needs human review. Model calls go to an external API when enabled.
- **Arabic UI strings are drafts** awaiting review (`app/static/strings_ar.json`).

## Evaluation

- 21 of 65 cases need human input (`TODO_HUMAN`): viral texts, paraphrased hadith, personal and disputed questions. They are not counted until filled.
- Cases are generated from the same data the tool indexes; this measures matching and safety behaviour, not coverage of texts outside the index.
- One test-split failure was fixed after it was seen (`docs/results_phase2_test_run2.md` notes it).

## Licensing and operation

- **King Fahd Complex Quran files have no explicit license grant** we could find; we use them as published for developers, unmodified and credited (SOURCES.md).
- **Learning paths** are written by the team and converted by script; they still need review by a Sharia mentor (see docs/paths_conversion_report.md). Short dhikr phrases inside lesson sentences are not turned into reference blocks.
- **Free hosting**: the app may sleep when idle and take some seconds to wake. Error reports are stored on the server's disk, which a free host may reset.
