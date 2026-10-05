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
| edge_input | 5 | 5 | 100% | 0 | 5/5 | 0 |
| **Total** | **30** | **30** | **100%** | **0** | **30/30** | **15** |

Latency per request: median 1427 ms, p95 5434 ms (index load 4.6 s, once at startup).
LLM `openai_compat` model `gpt-4.1-mini-2025-04-14`: 123 calls, 35922 prompt + 5541 completion tokens, 0 failed and 26 rejected outputs (template used).
