### Evaluation — split: test, 3 run(s) per case

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
| edge_input | 5 | 4 | 80% | 2 | 5/5 | 0 |
| **Total** | **30** | **29** | **97%** | **2** | **30/30** | **15** |

Latency per request: median 21 ms, p95 63 ms (index load 2.2 s, once at startup). LLM tokens: 0 (explanations are templates).

Failures and critical errors:

- `c63` edge_input: expected `not_found` `None`, got `[["not_found"], []]` — CRITICAL: called_false
- `c64` edge_input: expected `exact` `quran:21:97`, got `[["lexical_diff"], ["quran:21:96-97"]]`
- `c65` edge_input: expected `not_found` `None`, got `[["not_found"], []]` — CRITICAL: called_false
