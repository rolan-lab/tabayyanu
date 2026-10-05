# Results

Final evaluation, run on 2026-10-06 (Asia/Riyadh). Reproduce with the commands in README.md.

## 1. Tabayyanu, test split, without a model (deterministic)

| Category | Cases run | Correct | Accuracy | Critical errors | Consistent | Pending (TODO_HUMAN) |
|---|---:|---:|---:|---:|---:|---:|
| genuine_ayah | 7 | 7 | 100% | 0 | 7/7 | 0 |
| altered_ayah | 7 | 7 | 100% | 0 | 7/7 | 0 |
| ayah_spelling | 2 | 2 | 100% | 0 | 2/2 | 0 |
| hadith_verbatim | 6 | 6 | 100% | 0 | 6/6 | 0 |
| hadith_wording | 0 | 0 | — | 0 | 0/0 | 3 |
| viral_not_indexed | 0 | 0 | — | 0 | 0/0 | 6 |
| personal_fatwa | 0 | 0 | — | 0 | 0/0 | 3 |
| disputed | 0 | 0 | — | 0 | 0/0 | 3 |
| long_post | 3 | 3 | 100% | 0 | 3/3 | 0 |
| edge_input | 5 | 5 | 100% | 0 | 5/5 | 0 |
| **Total** | **30** | **30** | **100%** | **0** | **30/30** | **15** |

Latency per request: median 10 ms, p95 17 ms (index load 2.6 s, once at startup).
LLM: none (deterministic extraction, template explanations, 0 tokens).

## 2. Tabayyanu, test split, with the model (gpt-4.1-mini-2025-04-14)

| Category | Cases run | Correct | Accuracy | Critical errors | Consistent | Pending (TODO_HUMAN) |
|---|---:|---:|---:|---:|---:|---:|
| genuine_ayah | 7 | 7 | 100% | 0 | 7/7 | 0 |
| altered_ayah | 7 | 7 | 100% | 0 | 7/7 | 0 |
| ayah_spelling | 2 | 2 | 100% | 0 | 2/2 | 0 |
| hadith_verbatim | 6 | 6 | 100% | 0 | 6/6 | 0 |
| hadith_wording | 0 | 0 | — | 0 | 0/0 | 3 |
| viral_not_indexed | 0 | 0 | — | 0 | 0/0 | 6 |
| personal_fatwa | 0 | 0 | — | 0 | 0/0 | 3 |
| disputed | 0 | 0 | — | 0 | 0/0 | 3 |
| long_post | 3 | 3 | 100% | 0 | 3/3 | 0 |
| edge_input | 5 | 5 | 100% | 0 | 5/5 | 0 |
| **Total** | **30** | **30** | **100%** | **0** | **30/30** | **15** |

Latency per request: median 1427 ms, p95 5434 ms (index load 4.6 s, once at startup).
LLM `openai_compat` model `gpt-4.1-mini-2025-04-14`: 123 calls, 35922 prompt + 5541 completion tokens, 0 failed and 26 rejected outputs (template used).

## 3. Baseline: the same model without retrieval

Verdict accuracy: 15/25 (60%). References: 6 correct, **12 fabricated or wrong place**, 7 none given.
Tokens: 5427 prompt + 453 completion; 0 failed calls.

Full table: [baseline_test.md](baseline_test.md).

## Reading these numbers

- Our verdicts come from code, so they are identical with and without the model (sections 1 and 2); the model only adds quotation extraction and wording of the explanation. 26 of 123 model outputs were rejected by our validator and replaced by the fixed template.
- Same inputs, same model: without our database the model got 60% of verdicts right and gave 12 references that do not exist or point to the wrong place; with our database, 100% and 0 invented references.
- Limits: 30 test cases are runnable; 15 test cases (and 21 overall) still need human-written inputs (`TODO_HUMAN`) — viral texts, paraphrased hadith, personal and disputed questions. Cases are generated from the indexed data, so they measure matching and safety behaviour, not coverage of texts outside the index. One test failure in Phase 2 was fixed after being seen (see `results_phase2_test_run2.md`). The baseline is one model with one prompt at temperature 0; its references varied between runs on the same inputs.
