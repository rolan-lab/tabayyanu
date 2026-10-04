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

Latency per request: median 31 ms, p95 66 ms (index load 3.6 s, once at startup). LLM tokens: 0 (explanations are templates).

**Notes on this run (2026-10-04, Phase 2):**
- Run 1 (`results_phase2_test_run1.md`) reported 29/30 and 2 critical errors. Both "called_false" flags were a checker false positive: the mandated not-found note «هذا لا يعني أن النص باطل» contains the word باطل inside a negation. The checker now ignores that exact note.
- Run 1's real failure, `c64` (prompt-injection sentence ending with ":" before a real ayah), exposed a bug in how quotations are split. The fix was made after seeing this **test** case, so this run is not a fully unseen measurement for that pattern. A separate unit test covers it.
- 15 test cases are still `TODO_HUMAN` (hadith in other wording, viral texts, personal and disputed questions) and are not counted.
