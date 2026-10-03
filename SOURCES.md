# Sources and tools

Every external source and tool used by Tabayyanu. Terms are summarized in our own
words; quotes are at most one short sentence. **UNCLEAR** means we could not find
an explicit statement that covers our use, and the team must decide or ask.

Checked on: 2026-10-03 (Asia/Riyadh).

---

## 1. Quran text: King Fahd Glorious Quran Printing Complex (KFGQPC), developer platform

| | |
|---|---|
| Page | https://qurancomplex.gov.sa/quran-dev/ |
| File | https://download.qurancomplex.gov.sa/resources_dev/kfgqpc_hafs_v30.zip ("الخط الحاسوبي يونيكود (رواية حفص)", version 15.0, last modified 30-09-2026 per the platform) |
| Integrity | SHA-256 `227E6B1564D980F2BD09C2C35EBFB0330AC268C79A7C247CD1AB665BC635F245` (published on the platform; our download matches) |
| What we take | `kfgqpc_hafs_v30-data/kfgqpc_hafs_v30.json`: 6,236 records with `sura_no`, `aya_no`, `aya_text_unicode` (Uthmani script, full diacritics, ends with U+06DD + ayah number), `aya_text_emlaey` (plain spelling "used for search purpose"). Riwaya: Hafs. |
| Downloaded | 2026-10-03 by `scripts/ingest.py` (cached in `data/raw/qurancomplex/`) |
| Terms | The platform page has no license text, only "جميع الحقوق محفوظة". The Complex's site policy (https://policy.qurancomplex.gov.sa, section "ترخيص الاستخدام") says all site content is the Complex's property, protected by copyright, except services, computer files and software tools that the Complex declares available for public use. The developer platform presents these files as intended for building applications. |
| License | **UNCLEAR.** Use in an application looks intended (that is the platform's stated purpose), but there is no explicit license grant or attribution requirement written anywhere we found. We display the text unmodified and credit the Complex. |

## 2. Hadith: HadeethEnc (موسوعة الأحاديث النبوية), API v1

| | |
|---|---|
| Docs | https://hadeethenc.com/api-docs (redirects to https://documenter.getpostman.com/view/5211979/TVev3j7q) |
| Endpoints used | `/api/v1/categories/roots/?language=ar`, `/api/v1/hadeeths/list/?language=ar&category_id=..&page=..&per_page=..`, `/api/v1/hadeeths/multiple/?language=ar&ids=..` |
| What we take | Arabic records (`id, title, hadeeth, attribution, grade, reference, ...`). We keep only records whose `reference` cites صحيح البخاري or صحيح مسلم, with the hadith number parsed from that reference line. Text, grade and attribution are stored exactly as given. Public page per record: `https://hadeethenc.com/ar/browse/hadith/{id}` (checked, returns 200). |
| Coverage | **A curated selection, not the complete Two Sahihs.** About 4,273 records across all categories (sum over root categories; a record can sit in more than one category). Matn wording is HadeethEnc's, often taken from compilations such as Riyad al-Salihin or Umdat al-Ahkam, and can merge narrations (for example "وفي لفظ للبخاري"). |
| Downloaded | 2026-10-03 by `scripts/ingest.py` (cached in `data/raw/hadeethenc/`) |
| Terms | Stated on the API docs overview: content may be used on two conditions: no modification, addition or deletion of content, and clear attribution to the publisher and the source (HadeethEnc.com). Quote: "No modification, addition, or deletion of the content." |
| License | Clear for our use, provided we show text unmodified (normalized copies are for matching only, never displayed as the source) and credit HadeethEnc.com with a link. |

## 3. Hadith search: Dorar al-Sunniyya (الدرر السنية), JSON API

| | |
|---|---|
| Docs | https://dorar.net/article/389 |
| Endpoint | `https://dorar.net/dorar_api.json?skey=<phrase>` |
| What it returns | `{"ahadith": {"result": "<html string>"}}`: one HTML blob with about 15 hits. Each hit has the matn, narrator (الراوي), scholar (المحدث), book (المصدر), page or number (الصفحة أو الرقم) and the scholar's ruling (خلاصة حكم المحدث). No collection filter, no pagination, no bulk export. |
| What we take | **Nothing yet.** Inspected only (`scripts/inspect_dorar.py`). It cannot supply the Two Sahihs in bulk. A possible later use (rulings on widely circulated weak hadith) is optional per CLAUDE.md. |
| Terms | No terms-of-use page found (checked the API page, /about link, /feedback FAQ). The API page offers the service to site owners to display encyclopedia search results on their sites. Footer: "جميع الحقوق محفوظة لمؤسسة الدرر السنية". The homepage returns HTTP 403 to scripted requests; the API endpoint answers. |
| License | **UNCLEAR** for storing or caching results. Live display of search results looks intended. |

## 4. Organizers' MCP server: Islamic Content

| | |
|---|---|
| Endpoint | `https://mcp.islamiccontent.org/mcp` (streamable HTTP; the bare domain returns 404 to POST) |
| What it is | Server "islamic-content" v0.1.0. Tools: `search`, `fetch`, `get_quran_verses`, `list_quran_translations`, `get_quran_audio`, `get_hadith` (takes a HadeethEnc id), `browse_hadith_categories`, `browse_library`, `get_library_item`, `list_library_categories`, `list_languages`. Its hadith collection is HadeethEnc. |
| What we take | **Nothing.** Inspected only (initialize + tools/list). It adds no hadith data beyond source 2. Not used at runtime, per CLAUDE.md. |
| Terms | Not found in the server's responses. **UNCLEAR**, but irrelevant while we take nothing from it. |

## 5. Shamela (المكتبة الشاملة), not used

| | |
|---|---|
| Terms | https://shamela.ws/page/terms (Shamela MCP terms, last updated 19 Sep 2026): read-only research and citation service; forbids rebuilding the full index beyond published limits; rights in books and editions stay with their holders, and the terms grant no reuse rights beyond that. |
| Status | **Not used. UNCLEAR / likely not permitted** for bulk extraction of Bukhari and Muslim. Pending a team decision (see START_STATE.md, open questions). |

---

## Tools

| Tool | Version | License | Use |
|---|---|---|---|
| Python | 3.13.7 | PSF | Scripts |
| requests | 2.32.3 | Apache-2.0 | HTTP downloads |
| SQLite (Python stdlib `sqlite3`) | bundled | Public domain | Local database |
