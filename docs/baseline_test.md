### Baseline: LLM without retrieval — split test, model `gpt-4.1-mini-2025-04-14`

Verdict accuracy: 15/25 (60%). References: 6 correct, **12 fabricated or wrong place**, 7 none given.
Tokens: 5427 prompt + 453 completion; 0 failed calls.

| Case | Category | Expected | Model verdict | Model reference | Reference check |
|---|---|---|---|---|---|
| `c01` | genuine_ayah | exact | authentic | 6:33 | ok |
| `c02` | genuine_ayah | exact | authentic | 2:254 | ok |
| `c03` | genuine_ayah | exact | authentic | ar-Rum:13 | fabricated |
| `c04` | genuine_ayah | exact | authentic | al-baqarah:6 | fabricated |
| `c07` | genuine_ayah | exact | authentic | 21:52 | ok |
| `c09` | genuine_ayah | exact | not_known |  | none |
| `c10` | genuine_ayah | exact | altered | 6:141 | fabricated |
| `c11` | altered_ayah | lexical_diff | altered | 33:16 | fabricated |
| `c12` | altered_ayah | lexical_diff | altered | 10:68 | fabricated |
| `c13` | altered_ayah | lexical_diff | authentic | 8:65 | ok |
| `c15` | altered_ayah | lexical_diff | altered | 7:170 | fabricated |
| `c16` | altered_ayah | lexical_diff | authentic | surah:50:21 | fabricated |
| `c18` | altered_ayah | lexical_diff | authentic | 28:48 | fabricated |
| `c20` | altered_ayah | lexical_diff | altered | 5:33 | ok |
| `c21` | ayah_spelling | exact | authentic | 3:14 | fabricated |
| `c23` | ayah_spelling | lexical_diff | authentic | 2:264 | ok |
| `c27` | hadith_verbatim | exact | authentic | bukhari:1145 | fabricated |
| `c28` | hadith_verbatim | exact | authentic | bukhari:232 | fabricated |
| `c29` | hadith_verbatim | exact | authentic | bukhari:7287 | fabricated |
| `c30` | hadith_verbatim | exact | not_known |  | none |
| `c31` | hadith_verbatim | exact | altered | not_known | none |
| `c33` | hadith_verbatim | exact | not_known |  | none |
| `c63` | edge_input | not_found | not_known |  | none |
| `c64` | edge_input | exact | not_known |  | none |
| `c65` | edge_input | not_found | not_known |  | none |

Limits: single model and prompt at temperature 0; the model may have seen these texts in training; categories needing human input (TODO_HUMAN) are not included.
