# Sources and tools

Every external source and tool used by Tabayyanu. Terms are summarized in our own
words; quotes are at most one short sentence. **UNCLEAR** means we could not find
an explicit statement that covers our use, and the team must decide or ask.

Checked on: 2026-10-03 (Asia/Riyadh).

## 0. Organizers' reference file

"المرجعية والحزمة العلمية والبيانات", version dated 20/3/1448, 15 pages, issued by the
challenge organizers. Cited only; the file is not redistributed in this repository.
It sets the approved references per domain (page 3–4), the content levels A–D (page 2),
the required output standards (page 5), safety test cases (page 6), a terminology sample
(page 7) and the platform list (pages 8–15).

Relevant to licensing: page 8 records the Association for Multilingual Islamic Content
statement of 17 Sep 2026 that its content is free for individuals and organizations and
available through public APIs and an MCP server. This covers the Association's platforms
(HadeethEnc, QuranEnc, IslamHouse, terminologyenc, icadb), not the King Fahd Complex,
Dorar or Shamela.

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
| License | **UNCLEAR, accepted by the team (2026-10-03, see docs/CHANGES.md).** Use in an application looks intended (that is the platform's stated purpose), but there is no explicit license grant or attribution requirement written anywhere we found. We display the text unmodified and credit the Complex; LIMITATIONS.md will note this. |

## 2. Hadith: HadeethEnc (موسوعة الأحاديث النبوية), API v1

| | |
|---|---|
| Docs | https://hadeethenc.com/api-docs (redirects to https://documenter.getpostman.com/view/5211979/TVev3j7q) |
| Endpoints used | `/api/v1/categories/roots/?language=ar`, `/api/v1/hadeeths/list/?language=ar&category_id=..&page=..&per_page=..`, `/api/v1/hadeeths/multiple/?language=ar&ids=..` |
| What we take | Arabic records (`id, title, hadeeth, attribution, grade, reference, ...`). We keep only records whose `reference` cites صحيح البخاري or صحيح مسلم, with the hadith number parsed from that reference line. Text, grade and attribution are stored exactly as given. Public page per record: `https://hadeethenc.com/ar/browse/hadith/{id}` (checked, returns 200). |
| Coverage | **A curated selection, not the complete Two Sahihs.** About 4,273 records across all categories (sum over root categories; a record can sit in more than one category). Matn wording is HadeethEnc's, often taken from compilations such as Riyad al-Salihin or Umdat al-Ahkam, and can merge narrations (for example "وفي لفظ للبخاري"). |
| Downloaded | 2026-10-03 by `scripts/ingest.py` (cached in `data/raw/hadeethenc/`) |
| Terms | Stated on the API docs overview: content may be used on two conditions: no modification, addition or deletion of content, and clear attribution to the publisher and the source (HadeethEnc.com). Quote: "No modification, addition, or deletion of the content." |
| License | Clear for our use (also covered by the Association statement in the reference file, page 8), provided we show text unmodified (normalized copies are for matching only, never displayed as the source) and credit HadeethEnc.com with a link. |

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

## 4b. Terminology: terminologyenc.com (موسوعة المصطلحات الإسلامية)

| | |
|---|---|
| Site | https://terminologyenc.com/ar (listed in the organizers' file, page 10, as a site to browse) |
| API | **Undocumented.** No API docs or developer page found on the site or by web search. The HadeethEnc-style paths answer: `/api/v1/languages` (22 languages), `/api/v1/categories/roots/?language=ar` (16 roots), `/api/v1/terms/list/?language=ar&category_id=..`, `/api/v1/terms/one/?language=ar&id=..`. A term has `term, idio_def, brief_expl, brief_ling_def, ling_def, value, root, categories, translations` (`scripts/inspect_terminologyenc.py`). |
| What we take | **Nothing yet.** Possible Phase 3 use: short definitions of terms shown in results (e.g. صحيح, متفق عليه). |
| Terms | No terms page on the site. The about page calls it a free, reliable reference and says its aim includes providing translations in electronic formats for portals and applications. Run by the Association, so the free-use statement in the reference file (page 8) applies. |
| License | Content: free use per the Association statement. Endpoints: undocumented, so they may change without notice. |

## 4c. Association Central DB: icadb.com

| | |
|---|---|
| API | https://icadb.com/api/docs/ (Swagger UI behind a login page). Its OpenAPI schema at `https://icadb.com/api/docs/?format=openapi` is public and describes a "Public read-only API" with 27 paths; it declares HTTP Basic auth, but list and export endpoints answered without credentials (`scripts/inspect_icadb.py`). |
| Hadith content | Encyclopedia "موسوعة الأحاديث" (external_id 101, 842 cards) and "موسوعة الأحاديث الإصدار الأول" (external_id 117, 3,552 cards). Card fields: title, matn, grade (درجة الحديث), attribution (التخريج), meaning, word meanings, benefits, references. Cards carry `old_id` values in HadeethEnc's id range: this is the HadeethEnc material, not additional hadith. "موسوعة شرح صحيح مسلم (الدرر السنية)" (external_id 130) has 0 cards. |
| What we take | **Nothing.** Adds no coverage over source 2. Not used at runtime (CLAUDE.md, Part 3). |
| License | Free per the Association statement (reference file, page 8); the homepage says the data is available free through APIs or downloadable copies. |

## 5. Shamela (المكتبة الشاملة), inspected, text not used

| | |
|---|---|
| Listed by organizers | Reference file page 15: full database at https://shamela.ws/page/download → `https://dev.shamela.ws/downloads/shamela-database-1448.zip` (13,294,044,352 bytes, Last-Modified 30 Jul 2026). |
| What we did | `scripts/inspect_shamela.py` reads only the zip's central directory over HTTP range requests (about 1 MB), then fetches the catalogue `database/master.db` (980 KB compressed) into `data/raw/shamela/`. We also fetched one book file, `database/book/727/1727.db` (121 KB compressed), to check its schema. |
| What we found | 9,825 entries. Catalogue has 8,593 books. Editions: Sahih Muslim "ت عبد الباقي" is book 1727 (group 711); Sahih al-Bukhari "ط السلطانية" is book 1681 (group 1681). Per-book `.db` files hold only a page map (`page`: id, part, page, number) and a heading tree (`title`), **no text**. Book text lives in a Lucene index, `database/store/page/` (94 files, 14.1 GB), shared by all books. |
| Server behaviour | Cloudflare. Back-to-back range requests, or a range request after a HEAD on the same session, get a full 200 response instead of 206; requests spaced 3 s apart get 206. The script spaces requests and refuses any non-206 response before reading its body. |
| Terms | https://shamela.ws/page/terms is the only terms page linked (from the download page too). It covers the Shamela MCP service: read-only research and citation; no rebuilding of the full index beyond published limits; rights in books and editions stay with their holders and the terms grant no reuse rights. The download page itself states no license. |
| Status | **Text not used.** Extracting the two Sahihs would need most of the 14.1 GB Lucene index plus a custom decoder. License for reuse: **UNCLEAR** (organizers list the download as an approved resource; Shamela's own terms grant no reuse rights). |

---

## Tools

| Tool | Version | License | Use |
|---|---|---|---|
| Python | 3.11+ (dev on 3.13.7) | PSF | Everything |
| requests | 2.32.3 | Apache-2.0 | Data downloads, LLM HTTP calls |
| SQLite with FTS5 (Python stdlib `sqlite3`) | bundled (3.50.4 in dev) | Public domain | Database and full-text search (`bm25()`) |
| FastAPI | 0.115.6 | MIT | Web API |
| Uvicorn | 0.32.1 | BSD-3-Clause | Web server |
| PyYAML | 6.0.2 | MIT | `config.yaml` |
| pytest / httpx | 8.3.4 / 0.28.1 | MIT / BSD-3-Clause | Tests |
| KFGQPC Hafs Uthmanic font (`kfgqpc_hafs_v30.ttf`) | from the same KFGQPC package as source 1 | as source 1 (UNCLEAR, accepted) | Displaying Quran text; extracted at build time, not committed |
| IBM Plex Sans Arabic (Google Fonts) | — | SIL Open Font License 1.1 | UI font, loaded from fonts.googleapis.com |
| LLM endpoint (optional) | set by `LLM_MODEL` | provider's terms | Quote extraction and short explanations only; off by default |
